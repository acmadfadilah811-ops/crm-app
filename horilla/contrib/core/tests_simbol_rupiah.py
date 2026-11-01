"""Nominal uang tampil "Rp." (bukan kode IDR) dan field uang di form diberi keterangan mata uang (2026-11-02)."""

from types import SimpleNamespace

from django import forms
from django.test import TestCase

from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.finance import MultipleCurrency
from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.generics.forms.form_class_mixin import HorillaFormMixin
from horilla_crm.campaigns.models import Campaign


class SimbolMataUangTests(TestCase):
    def test_idr_tampil_rp_dan_mata_uang_lain_tetap_kode(self):
        idr = MultipleCurrency(currency="IDR", conversion_rate=1, decimal_places=0)
        self.assertEqual(idr.simbol(), "Rp.")
        self.assertEqual(idr.display_with_symbol(1500000), "Rp. 1,500,000")
        usd = MultipleCurrency(currency="USD", conversion_rate=1, decimal_places=2)
        self.assertEqual(usd.display_with_symbol(100), "USD 100.00")

    def test_format_eropa_untuk_idr(self):
        idr = MultipleCurrency(currency="IDR", conversion_rate=1, decimal_places=0)
        pengguna = SimpleNamespace(number_format="european_format")
        self.assertEqual(idr.display_with_symbol(1500000, user=pengguna), "Rp. 1.500.000")


class LabelMataUangFormTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com", currency="IDR")
        self.user = HorillaUser.objects.create(username="pemakai.uji", company=self.company)
        self.assertTrue(MultipleCurrency.all_objects.filter(company=self.company, is_default=True, currency="IDR").exists())

    def _form_palsu(self, model):
        form = HorillaFormMixin()
        form._meta = SimpleNamespace(model=model)
        form.request = SimpleNamespace(user=self.user)
        form.fields = {
            "budget_cost": forms.DecimalField(label="Budget Cost"),
            "expected_revenue": forms.DecimalField(label="Expected Revenue"),
            "campaign_name": forms.CharField(label="Campaign Name"),
        }
        return form

    def test_field_uang_diberi_rp_dan_field_lain_tidak(self):
        form = self._form_palsu(Campaign)
        form._apply_currency_labels()
        self.assertEqual(form.fields["budget_cost"].label, "Budget Cost (Rp.)")
        self.assertEqual(form.fields["expected_revenue"].label, "Expected Revenue (Rp.)")
        self.assertEqual(form.fields["campaign_name"].label, "Campaign Name")
        self.assertEqual(form.fields["budget_cost"].widget.attrs["placeholder"], "Rp.")

    def test_dipanggil_dua_kali_tidak_menggandakan_label(self):
        form = self._form_palsu(Campaign)
        form._apply_currency_labels()
        form._apply_currency_labels()
        self.assertEqual(form.fields["budget_cost"].label, "Budget Cost (Rp.)")

    def test_model_tanpa_field_uang_tidak_diubah(self):
        form = self._form_palsu(HorillaUser)
        form._apply_currency_labels()
        self.assertEqual(form.fields["budget_cost"].label, "Budget Cost")
