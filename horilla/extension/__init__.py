"""
Horilla extension package: model _inherit_model and form _inherit_form.

Patches makemigrations and migrate to use HorillaAutodetector so injected fields
generate migrations in the owning extension app, not in the target app.
"""

from horilla.extension.models import (
    EXTENSION_REGISTRY,
    INJECTION_MAP,
    AlterInjectedField,
    ExtensionModelBase,
    HorillaAutodetector,
    InjectField,
    RemoveInjectedField,
)

__all__ = [
    "HorillaAutodetector",
    "ExtensionModelBase",
    "EXTENSION_REGISTRY",
    "INJECTION_MAP",
    "InjectField",
    "AlterInjectedField",
    "RemoveInjectedField",
]


def _patch_migration_autodetectors():
    try:
        from django.core.management.commands.makemigrations import (
            Command as MakeMigrationsCommand,
        )
        from django.core.management.commands.migrate import Command as MigrateCommand

        MakeMigrationsCommand.autodetector = HorillaAutodetector
        MigrateCommand.autodetector = HorillaAutodetector
    except ImportError:
        pass


_patch_migration_autodetectors()
