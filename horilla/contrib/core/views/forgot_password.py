"""
Module providing forgot password and password reset functionality for Horilla users.
Includes HTMX support for dynamic interactions.
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import make_msgid
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View

from horilla.auth.models import User
from horilla.contrib.mail.models import HorillaMailConfiguration
from horilla.core.exceptions import ValidationError

# First party imports (Horilla)
from horilla.shortcuts import redirect, render
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpResponse

# Local imports
from ..models import Company

logger = logging.getLogger(__name__)

NAMA_SITUS = "CRM Star Photo & Advertising"


def _samarkan_email(email):
    """a***n@gmail.com -- cukup untuk memastikan tujuan tanpa membuka alamat utuh."""
    nama, _at, domain = (email or "").partition("@")
    if len(nama) <= 2:
        return f"{nama[:1]}***@{domain}"
    return f"{nama[0]}***{nama[-1]}@{domain}"


class ForgotPasswordView(View):
    """
    View to handle the forgot password workflow.

    GET: Display the forgot password form.
    POST: Process the form submission and send a password reset email.
    """

    template_name = "forgot_password/forgot_password.html"
    success_template = "forgot_password/forgot_password_success_partial.html"

    def get(self, request):
        """Display the forgot password form"""
        return render(request, self.template_name)

    def _form_error(self, request, isian, pesan):
        return render(request, self.template_name, {"email_or_username": isian, "error": pesan})

    def post(self, request):
        """Kirim tautan reset (2026-09-28): akun tidak terdaftar & kegagalan kirim
        diberi tahu (atas permintaan user; aplikasi internal, dibatasi 1x/menit
        per akun & per IP), email berupa teks biasa pendek yang lebih cepat
        sampai dan tidak masuk spam dibanding versi HTML."""
        email_or_username = (request.POST.get("email") or "").strip()
        if not email_or_username:
            return self._form_error(request, "", _("Isi username atau email akun CRM Anda."))

        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0].strip()
        kunci_ip = f"lupa_pw_ip:{ip}"
        if cache.get(kunci_ip):
            return self._form_error(
                request, email_or_username, _("Tunggu 1 menit sebelum meminta tautan reset lagi.")
            )
        cache.set(kunci_ip, True, 60)

        user = (
            User.objects.filter(username__iexact=email_or_username).first()
            or User.objects.filter(email__iexact=email_or_username).order_by("pk").first()
        )
        if user is None or not user.is_active:
            logger.info("Password reset requested for unknown account: %s", email_or_username)
            return self._form_error(
                request, email_or_username,
                _("Username atau email tidak terdaftar di CRM. Periksa kembali ejaannya."),
            )
        if not user.email:
            return self._form_error(
                request, email_or_username,
                _("Akun ini belum punya email. Hubungi admin/HR untuk mengisi email karyawan."),
            )
        kunci_user = f"lupa_pw_user:{user.pk}"
        if cache.get(kunci_user):
            return self._form_error(
                request, email_or_username,
                _("Tautan reset baru saja dikirim. Tunggu 1 menit sebelum meminta lagi, dan cek folder Spam."),
            )

        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = request.build_absolute_uri(f"/reset-password/{uid}/{token}/")

            primary_config = HorillaMailConfiguration.objects.filter(
                is_primary=True, company=user.company
            ).first()

            if not primary_config:
                hq_company = Company.objects.filter(hq=True).first()
                if hq_company:
                    primary_config = HorillaMailConfiguration.objects.filter(
                        is_primary=True, company=hq_company
                    ).first()
            if not primary_config:
                # Konfigurasi utama yang belum tertaut perusahaan (2026-09-28).
                primary_config = HorillaMailConfiguration.objects.filter(is_primary=True).first()

            # Teks biasa pendek (2026-09-28): versi HTML berulang kali masuk spam
            # Gmail dan baru muncul lama kemudian, sedangkan email uji teks biasa
            # dari akun pengirim yang sama langsung sampai.
            nama = user.get_full_name() or user.username
            isi = (
                f"Halo {nama},\n\n"
                f"Ada permintaan reset password untuk akun {NAMA_SITUS} Anda "
                f"(username: {user.username}).\n\n"
                f"Buat password baru lewat tautan ini:\n{reset_link}\n\n"
                "Kalau Anda tidak meminta reset password, abaikan email ini; "
                "password Anda tidak berubah.\n"
            )
            email = EmailMultiAlternatives(
                subject=f"Reset Password - {NAMA_SITUS}",
                body=isi,
                from_email=(
                    primary_config.from_email
                    if primary_config
                    else settings.DEFAULT_FROM_EMAIL
                ),
                to=[user.email],
                headers={"Message-ID": make_msgid(domain=request.get_host().split(":")[0] or None)},
            )
            email.send(fail_silently=False)
        except Exception:
            logger.exception("Password reset email failed for: %s", email_or_username)
            return self._form_error(
                request, email_or_username,
                _("Email gagal dikirim karena gangguan server email. Coba lagi beberapa saat, atau hubungi admin."),
            )

        cache.set(kunci_user, True, 60)
        return render(request, self.success_template, {"email_tujuan": _samarkan_email(user.email)})


class PasswordResetConfirmView(View):
    """
    View to handle the password reset confirmation workflow.

    GET: Display the reset password form if the token is valid.
    POST: Process the form submission to reset the user's password.
    """

    template_name = "forgot_password/password_reset_confirm.html"
    success_template = "forgot_password/password_reset_success_partial.html"

    def get(self, request, uidb64, token):
        """Display the password reset form"""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            if default_token_generator.check_token(user, token):
                context = {
                    "validlink": True,
                    "uidb64": uidb64,
                    "token": token,
                }
            else:
                context = {"validlink": False}

        except Exception as e:
            context = {"validlink": False, "error": str(e)}

        return render(request, self.template_name, context)

    def post(self, request, uidb64, token):
        """Handle password reset via HTMX"""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            if not default_token_generator.check_token(user, token):
                messages.error(
                    request, "Password reset link is invalid or has expired."
                )
                context = {"validlink": False}
                return render(request, self.template_name, context)

            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not new_password or not confirm_password:
                messages.error(request, _("Please fill in all password fields."))
            elif new_password != confirm_password:
                messages.error(request, _("Passwords do not match."))
            else:
                try:
                    validate_password(new_password, user=user)
                except ValidationError as e:
                    for message in e.messages:
                        messages.error(request, message)
                else:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(
                        request, "Your password has been reset successfully."
                    )

                    if request.headers.get("HX-Request") == "true":
                        response = HttpResponse()
                        response["HX-Redirect"] = "/login/"
                        response["HX-Push-Url"] = "/login/"
                        return response

                    return redirect("core:login")

            context = {
                "validlink": True,
                "uidb64": uidb64,
                "token": token,
                "new_password": new_password,
                "confirm_password": confirm_password,
            }
            return render(request, self.template_name, context)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            messages.error(request, _("Invalid password reset link."))
            context = {"validlink": False}
            return render(request, self.template_name, context)
