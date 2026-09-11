"""
Management command to seed default HorillaColorTheme records.
"""

# Third-party imports (Django)
from django.core.management.base import BaseCommand

# First party imports (Horilla)
# Local imports
from ...models import HorillaColorTheme
from ...utils import THEMES_DATA


class Command(BaseCommand):
    """Create default HorillaColorTheme records from THEMES_DATA."""

    help = "Create default color themes for the Horilla platform"

    def handle(self, *args, **options):
        """Seed default color themes if none exist yet."""
        # Check if themes already exist
        if HorillaColorTheme.objects.exists():
            self.stdout.write(
                self.style.WARNING("Themes already exist. Skipping creation.")
            )
            return

        created_count = 0
        self.stdout.write("Creating default color themes...")

        for theme_data in THEMES_DATA:
            try:
                is_default = theme_data.get("is_default", False)

                defaults = theme_data.copy()
                defaults["is_default"] = is_default

                theme, created = HorillaColorTheme.objects.get_or_create(
                    name=theme_data["name"],
                    defaults=defaults,
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created theme: {theme.name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"- Theme already exists: {theme.name}")
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Error creating theme {theme_data['name']}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nSuccessfully created {created_count} themes.")
        )
