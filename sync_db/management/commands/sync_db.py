"""
Management command to sync database structure and remap app references.
"""

import json

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import F, Value
from django.db.models.functions import Concat, Replace, Substr


class LogMixin:
    """Rich terminal logging helpers for management commands."""

    WIDTH = 54

    # ── badges ──────────────────────────────────────────
    BADGE_OK = "\033[1;42;97m OK   \033[0m"  # green bg,  white text
    BADGE_STEP = "\033[1;44;97m STEP \033[0m"  # blue bg,   white text
    BADGE_INFO = "\033[1;46;97m INFO \033[0m"  # cyan bg,   white text  ← was 30
    BADGE_WARN = "\033[1;43;97m WARN \033[0m"  # yellow bg, white text  ← was 30
    BADGE_ERR = "\033[1;41;97m ERR  \033[0m"  # red bg,    white text
    BADGE_SKIP = "\033[1;47;97m SKIP \033[0m"  # gray bg,   white text  ← was 30

    def section(self, title):
        """Print a boxed section header."""
        bar = "═" * self.WIDTH
        self.stdout.write(self.style.HTTP_INFO(f"\n╔{bar}╗"))
        padded = title.ljust(self.WIDTH)
        self.stdout.write(self.style.HTTP_INFO(f"║  {padded}║"))
        self.stdout.write(self.style.HTTP_INFO(f"╚{bar}╝"))

    def step(self, message):
        """Log an in-progress step message."""
        self.stdout.write(f"{self.BADGE_STEP} {self.style.WARNING(message)}")

    def success(self, message):
        """Log a successful step message."""
        self.stdout.write(f"{self.BADGE_OK} {self.style.SUCCESS(message)}")

    def info(self, message):
        """Log an informational message."""
        self.stdout.write(f"{self.BADGE_INFO} {self.style.NOTICE(message)}")

    def warn(self, message):
        """Log a warning message."""
        self.stdout.write(f"{self.BADGE_WARN} {self.style.WARNING(message)}")

    def error(self, message):
        """Log an error message."""
        self.stdout.write(f"{self.BADGE_ERR} {self.style.ERROR(message)}")

    def skip(self, message):
        """Log a skipped step message."""
        self.stdout.write(f"{self.BADGE_SKIP} {self.style.NOTICE(message)}")

    def tree(self, items, label=""):
        """Print a compact tree of key → value remaps."""
        if label:
            self.stdout.write(self.style.NOTICE(f"  {label}"))
        last = len(items) - 1
        for i, (k, v) in enumerate(items):
            connector = "└─" if i == last else "├─"
            self.stdout.write(f"  \033[90m{connector} {k}\033[0m → \033[96m{v}\033[0m")

    def divider(self):
        """Print a horizontal divider line."""
        self.stdout.write(self.style.NOTICE("  " + "─" * (self.WIDTH - 2)))


class Command(LogMixin, BaseCommand):
    """Migrate and remap Horilla CRM v1.9 database labels to v1.10.0."""

    help = "Sync db: migrate DB structure, remap app labels, update references"

    APP_REMAP = {
        "horilla_activity": "activity",
        "horilla_automations": "automations",
        "horilla_cadences": "cadences",
        "horilla_calendar": "calendar",
        "horilla_core": "core",
        "horilla_dashboard": "dashboard",
        "horilla_duplicates": "duplicates",
        "horilla_generics": "generics",
        "horilla_keys": "keys",
        "horilla_mail": "mail",
        "horilla_notifications": "notifications",
        "horilla_reports": "reports",
        "horilla_theme": "theme",
        "horilla_utils": "utils",
    }

    def handle(self, *args, **options):
        """Run migration remap, content-type updates, audit fixes, and session clear."""
        self.section("SYNC DB STARTED")
        self.info("Syncing DB from Horilla CRM v1.9 to v1.10.0")

        # ==========================================
        # 1. Migration records
        # ==========================================
        self.section("Updating migration records")
        self.step("Remapping app labels in migration table")
        self.tree(list(self.APP_REMAP.items()))

        for old, new in self.APP_REMAP.items():
            MigrationRecorder.Migration.objects.filter(app=old).update(app=new)

        self.success("Migration records updated")

        # ==========================================
        # 2. Fake migrate
        # ==========================================
        self.section("Fake migrating all apps")
        self.step("Running: manage.py migrate --fake")

        call_command("migrate", "--fake", verbosity=0)

        self.success("Fake migrations completed")

        # ==========================================
        # 3. Remove sync_db records
        # ==========================================
        self.section("Preparing sync_db migration")
        self.step("Cleaning up stale sync_db migration records")

        deleted_count, _ = MigrationRecorder.Migration.objects.filter(
            app="sync_db"
        ).delete()

        self.info(f"Removed {deleted_count} sync_db migration record(s)")

        # ==========================================
        # 4. Run sync_db
        # ==========================================
        self.section("Applying sync_db migrations")
        self.step("Running: manage.py migrate sync_db")

        call_command("migrate", "sync_db", verbosity=1)

        self.success("sync_db migration completed")

        # ==========================================
        # 5. ContentTypes
        # ==========================================
        self.section("Remapping ContentTypes")

        self.remap_content_types()

        # ==========================================
        # 6. app_label fields
        # ==========================================
        self.section("Updating custom app_label fields")

        self.update_app_label_fields()

        # ==========================================
        # 6.1 RecycleBin model_name fix
        # ==========================================
        self.section("Fixing RecycleBin model_name")

        self.update_recyclebin_model_names()
        # ==========================================
        # 7. Audit logs
        # ==========================================
        self.section("Updating audit logs")

        self.update_audit_logs()

        # ==========================================
        # 8. Sessions
        # ==========================================
        self.section("Clearing sessions")
        self.step("Running: manage.py clearsessions")

        call_command("clearsessions", verbosity=0)

        self.success("Sessions cleared")

        self.section("SYNC DB COMPLETED")
        self.success("Migration successful!")

    # =====================================================
    # CONTENT TYPE REMAP
    # =====================================================
    def remap_content_types(self):
        """Remap ContentType app_label values from legacy horilla_* names."""
        self.warn("Remapping content types...")

        new_labels = list(self.APP_REMAP.values())
        ContentType = apps.get_model("contenttypes", "ContentType")
        ContentType.objects.filter(app_label__in=new_labels).delete()

        for old, new in self.APP_REMAP.items():
            ContentType.objects.filter(app_label=old).update(app_label=new)

        self.success("Content types remapped")

    # =====================================================
    # CUSTOM app_label FIELD UPDATE
    # =====================================================
    def update_app_label_fields(self):
        """Update stored app_label fields on core models after app rename."""
        self.warn("Updating app_label fields...")

        MODELS = [
            ("core", "KanbanGroupBy"),
            ("core", "TimelineSpanBy"),
            ("core", "QuickFilter"),
            ("core", "ImportHistory"),
            ("core", "ListColumnVisibility"),
            ("core", "DetailFieldVisibility"),
        ]

        total_updates = 0

        for app_name, model_name in MODELS:
            try:
                Model = apps.get_model(app_name, model_name)
            except LookupError:
                self.skip(f"{app_name}.{model_name}")
                continue

            if not hasattr(Model, "app_label"):
                continue

            for old, new in self.APP_REMAP.items():
                manager = (
                    Model.all_objects
                    if hasattr(Model, "all_objects")
                    else Model.objects
                )
                updated = manager.filter(app_label=old).update(app_label=new)
                total_updates += updated

        self.success(f"app_label fields updated ({total_updates} rows)")

    # =====================================================
    # AUDIT LOG UPDATE
    # =====================================================
    def update_audit_logs(self):
        """Patch audit log object_repr and changes JSON after app label remap."""
        try:
            LogEntry = apps.get_model("auditlog", "LogEntry")
        except LookupError:
            self.skip("auditlog not installed — skipping")
            return

        self.step("Updating audit log entries...")

        # ===============================
        # object_repr (FAST SQL)
        # ===============================
        try:
            for old, new in self.APP_REMAP.items():
                LogEntry.objects.filter(object_repr__icontains=old).update(
                    object_repr=Replace(F("object_repr"), old, new)
                )

            self.success("object_repr updated (SQL)")

        except Exception as e:
            self.warn(f"SQL failed, falling back to Python: {e}")

            for entry in (
                LogEntry.objects.all()
                .only("id", "object_repr")
                .iterator(chunk_size=500)
            ):
                if not entry.object_repr:
                    continue

                value = entry.object_repr
                updated = False

                for old, new in self.APP_REMAP.items():
                    if old in value:
                        value = value.replace(old, new)
                        updated = True

                if updated:
                    entry.object_repr = value
                    entry.save(update_fields=["object_repr"])

            self.success("object_repr updated (Python fallback)")

        # ===============================
        # changes JSON (SAFE)
        # ===============================
        self.step("Patching changes JSON field...")
        updated_count = 0

        for entry in (
            LogEntry.objects.all().only("id", "changes").iterator(chunk_size=500)
        ):
            if not entry.changes:
                continue

            data = entry.changes

            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    continue

            original = json.dumps(data)
            new_value = original

            for old, new in self.APP_REMAP.items():
                if old in new_value:
                    new_value = new_value.replace(old, new)

            if new_value != original:
                try:
                    entry.changes = json.loads(new_value)
                    entry.save(update_fields=["changes"])
                    updated_count += 1
                except Exception:
                    continue

        self.success(f"changes field updated ({updated_count} rows)")

    # =====================================================
    # RECYCLE BIN UPDATE
    # =====================================================
    def update_recyclebin_model_names(self):
        """Rewrite RecycleBin model_name prefixes after app label remap."""
        try:
            RecycleBin = apps.get_model("core", "RecycleBin")
        except LookupError:
            self.skip("core.RecycleBin not found — skipping")
            return

        self.warn("Updating RecycleBin model_name field (ORM-safe)...")

        total_updates = 0

        for old, new in self.APP_REMAP.items():
            prefix_old = f"{old}."
            prefix_len = len(prefix_old)

            updated = RecycleBin.objects.filter(
                model_name__startswith=prefix_old
            ).update(
                model_name=Concat(
                    Value(f"{new}."), Substr(F("model_name"), prefix_len + 1)
                )
            )

            total_updates += updated

        self.success(f"RecycleBin model_name updated ({total_updates} rows)")
