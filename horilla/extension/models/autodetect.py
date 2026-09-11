"""
Migration autodetector that routes injected fields to extension app migrations.
"""

from django.db import models
from django.db.migrations.autodetector import MigrationAutodetector, OperationDependency
from django.db.migrations.operations.fields import AlterField, RemoveField

from horilla.extension.models.migration_ops import (
    AlterInjectedField,
    InjectField,
    RemoveInjectedField,
)
from horilla.extension.models.registry import INJECTION_MAP, lookup_injection_owner


class HorillaAutodetector(MigrationAutodetector):
    """
    Routes AddField / AlterField / RemoveField for injected columns into the
    owning extension app's migrations.

    ``_generate_added_field`` is overridden for ``InjectField`` but must still mirror
    ``MigrationAutodetector._generate_added_field`` for ``preserve_default`` and
    ``MigrationQuestioner`` (``ask_not_null_addition``, etc.); otherwise
    ``makemigrations`` never prompts and ``migrate`` fails on existing rows.

    ``generate_altered_fields``
    and ``_generate_removed_field`` call ``add_operation`` on the target app, so we
    reroute those operations here when ``INJECTION_MAP`` has an entry.

    ``AlterInjectedField`` subclasses ``AlterField`` — exclude it from rerouting to
    avoid wrapping twice.
    """

    def add_operation(self, app_label, operation, dependencies=None, beginning=False):
        """Reroute alter/remove ops for injected fields into the extension app."""
        if isinstance(operation, AlterField) and not isinstance(
            operation, AlterInjectedField
        ):
            ext_app = lookup_injection_owner(
                app_label, operation.model_name, operation.name
            )
            if ext_app:
                operation = AlterInjectedField(
                    target_app_label=app_label,
                    model_name=operation.model_name,
                    name=operation.name,
                    field=operation.field,
                    preserve_default=operation.preserve_default,
                )
                app_label = ext_app

        elif isinstance(operation, RemoveField) and not isinstance(
            operation, RemoveInjectedField
        ):
            ext_app = lookup_injection_owner(
                app_label, operation.model_name, operation.name
            )
            if ext_app:
                operation = RemoveInjectedField(
                    target_app_label=app_label,
                    model_name=operation.model_name,
                    name=operation.name,
                )
                app_label = ext_app

        return super().add_operation(
            app_label, operation, dependencies=dependencies, beginning=beginning
        )

    def _generate_added_field(self, app_label, model_name, field_name):
        """Emit InjectField in the owning extension app with NOT NULL prompts."""
        key = (app_label, model_name.lower(), field_name)

        if key not in INJECTION_MAP:
            super()._generate_added_field(app_label, model_name, field_name)
            return

        ext_app = INJECTION_MAP[key]

        try:
            field = self.to_state.models[app_label, model_name.lower()].get_field(
                field_name
            )
        except Exception:
            super()._generate_added_field(app_label, model_name, field_name)
            return

        # Match django.db.migrations.autodetector.MigrationAutodetector._generate_added_field
        dependencies = [
            OperationDependency(
                app_label, model_name, field_name, OperationDependency.Type.REMOVE
            )
        ]
        if field.remote_field and field.remote_field.model:
            dependencies.extend(
                self._get_dependencies_for_foreign_key(
                    app_label,
                    model_name,
                    field,
                    self.to_state,
                )
            )
        if field.generated:
            dependencies.extend(self._get_dependencies_for_generated_field(field))

        time_fields = (models.DateField, models.DateTimeField, models.TimeField)
        auto_fields = (models.AutoField, models.SmallAutoField, models.BigAutoField)
        preserve_default = (
            field.null
            or field.has_default()
            or field.has_db_default()
            or field.many_to_many
            or (field.blank and field.empty_strings_allowed)
            or (isinstance(field, time_fields) and field.auto_now)
            or (isinstance(field, auto_fields))
        )
        if not preserve_default:
            field = field.clone()
            if isinstance(field, time_fields) and field.auto_now_add:
                field.default = self.questioner.ask_auto_now_add_addition(
                    field_name, model_name
                )
            else:
                field.default = self.questioner.ask_not_null_addition(
                    field_name, model_name
                )
        if field.unique and field.has_default() and callable(field.default):
            self.questioner.ask_unique_callable_default_addition(field_name, model_name)

        self.add_operation(
            ext_app,
            InjectField(
                target_app_label=app_label,
                model_name=model_name,
                name=field_name,
                field=field,
                preserve_default=preserve_default,
            ),
            dependencies=dependencies,
        )

    def _generate_removed_field(self, app_label, model_name, field_name):
        """Emit RemoveInjectedField in the extension app, not the target app."""
        ext_app = lookup_injection_owner(app_label, model_name, field_name)
        if ext_app:
            self.add_operation(
                ext_app,
                RemoveInjectedField(
                    target_app_label=app_label,
                    model_name=model_name,
                    name=field_name,
                ),
                dependencies=[
                    OperationDependency(
                        app_label,
                        model_name,
                        field_name,
                        OperationDependency.Type.REMOVE_ORDER_WRT,
                    ),
                    OperationDependency(
                        app_label,
                        model_name,
                        field_name,
                        OperationDependency.Type.ALTER_FOO_TOGETHER,
                    ),
                    OperationDependency(
                        app_label,
                        model_name,
                        field_name,
                        OperationDependency.Type.REMOVE_INDEX_OR_CONSTRAINT,
                    ),
                    *self._get_generated_field_dependencies_for_removed_field(
                        app_label, model_name, field_name
                    ),
                ],
            )
            return
        super()._generate_removed_field(app_label, model_name, field_name)
