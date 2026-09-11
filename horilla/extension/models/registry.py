"""
Runtime registry for _inherit_model field injection ownership.

INJECTION_MAP has no Django imports. lookup_injection_owner() may use the migration
loader when the field was removed from the extension model before makemigrations.
"""

# (target_app_label, target_model_name_lower, field_name) -> extension_app_label
INJECTION_MAP: dict = {}


def lookup_injection_owner(target_app_label, model_name, field_name):
    """
    Return the extension app that owns an injected column.

    Uses INJECTION_MAP first, then scans disk migrations for InjectField ops so
    removals still route to RemoveInjectedField after the field is deleted from
    the extension model class.
    """
    model_name_lower = model_name.lower()
    key = (target_app_label, model_name_lower, field_name)
    if key in INJECTION_MAP:
        return INJECTION_MAP[key]

    try:
        from django.db.migrations.loader import MigrationLoader

        from horilla.db import connection
        from horilla.extension.models.migration_ops import InjectField
    except ImportError:
        return None

    loader = MigrationLoader(connection, ignore_no_migrations=True)
    for (app_label, _migration_name), migration in loader.disk_migrations.items():
        for operation in migration.operations:
            if isinstance(operation, InjectField):
                if (
                    operation.target_app_label == target_app_label
                    and operation.model_name.lower() == model_name_lower
                    and operation.name == field_name
                ):
                    INJECTION_MAP[key] = app_label
                    return app_label
    return None
