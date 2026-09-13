"""Uji signal sync_users_when_role_permissions_change (signals.py): begitu
izin sebuah Role diedit (ditambah/dihapus/dikosongkan), semua user yang
sedang punya Role itu harus ikut disinkronkan -- sebelum fix ini, user yang
sudah lebih dulu diberi Role hanya disinkron SEKALI saat penugasan Role,
jadi kalau Role-nya dipersempit belakangan, user lama diam-diam tetap
punya akses lama yang lebih luas.

Signal-nya jalan lewat transaction.on_commit, jadi tiap mutasi
role.permissions harus dibungkus captureOnCommitCallbacks(execute=True)
supaya callback-nya benar-benar dieksekusi di dalam test (TestCase
membungkus tiap test dalam transaksi yang di-rollback, bukan di-commit)."""

from django.contrib.auth.models import Permission
from django.test import TestCase

from horilla.contrib.core.models.organization import Role
from horilla.contrib.core.models.user import HorillaUser


class RolePermissionResyncTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(role_name="Tim Marketing Uji")
        self.user = HorillaUser.objects.create(
            username="tim.uji", email="tim.uji@test.horilla", role=self.role
        )
        self.add_campaign = Permission.objects.get(codename="add_campaign")
        self.view_campaign = Permission.objects.get(codename="view_campaign")

    def test_menambah_izin_ke_role_ikut_menambah_ke_semua_user_role_itu(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.add(self.view_campaign)
        self.user.refresh_from_db()
        self.assertTrue(
            self.user.user_permissions.filter(codename="view_campaign").exists()
        )

    def test_role_dipersempit_belakangan_user_lama_ikut_kehilangan_izin_itu(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.add(self.add_campaign)
        self.user.refresh_from_db()
        self.assertTrue(
            self.user.user_permissions.filter(codename="add_campaign").exists()
        )

        # Role dipersempit -- add_campaign dicabut dari role.
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.remove(self.add_campaign)
        self.user.refresh_from_db()
        self.assertFalse(
            self.user.user_permissions.filter(codename="add_campaign").exists(),
            "User seharusnya ikut kehilangan izin yang sudah dicabut dari role-nya",
        )

    def test_role_permissions_clear_mencabut_semua_izin_role_dari_user(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.add(self.add_campaign, self.view_campaign)
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_permissions.count(), 2)

        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.clear()
        self.user.refresh_from_db()
        self.assertFalse(
            self.user.user_permissions.filter(
                codename__in=["add_campaign", "view_campaign"]
            ).exists()
        )

    def test_superuser_tidak_ikut_dicabut_izinnya(self):
        admin = HorillaUser.objects.create(
            username="admin.uji",
            email="admin.uji@test.horilla",
            role=self.role,
            is_superuser=True,
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.add(self.add_campaign)
        admin.refresh_from_db()
        # Superuser tidak pernah disentuh oleh signal ini (has_perm mereka
        # selalu True lewat is_superuser, bukan lewat user_permissions).
        self.assertFalse(
            admin.user_permissions.filter(codename="add_campaign").exists()
        )

    def test_user_role_lain_tidak_ikut_terdampak(self):
        other_role = Role.objects.create(role_name="Role Lain Uji")
        other_user = HorillaUser.objects.create(
            username="lain.uji", email="lain.uji@test.horilla", role=other_role
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.role.permissions.add(self.add_campaign)
        other_user.refresh_from_db()
        self.assertFalse(
            other_user.user_permissions.filter(codename="add_campaign").exists()
        )
