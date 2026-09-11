"""Custom HTTP error pages for Horilla (used when DEBUG is False)."""

from django.conf import settings
from django.views.csrf import csrf_failure as django_csrf_failure

from horilla.shortcuts import render
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpResponse


def csrf_failure(request, reason=""):
    """
      CSRF verification failed (``CSRF_FAILURE_VIEW``).

      When ``DEBUG`` is True, delegates to Django's default view so developers
    see the technical CSRF help page. When ``DEBUG`` is False, renders
      ``csrf_failure.html`` in the same layout as ``403.html`` / ``404.html``.
    """
    if settings.DEBUG:
        return django_csrf_failure(request, reason=reason)

    context = {
        "reason": reason,
        "message": _(
            "Your session may have expired, or this form was open too long. "
            "Refresh the page and try again."
        ),
    }
    response = render(request, "csrf_failure.html", context, status=403)

    if request.headers.get("HX-Request"):
        redirect_url = (
            request.headers.get("HX-Current-URL")
            or request.headers.get("Referer")
            or request.path
            or "/"
        )
        htmx_response = HttpResponse(status=403)
        htmx_response["HX-Redirect"] = redirect_url
        return htmx_response

    return response
