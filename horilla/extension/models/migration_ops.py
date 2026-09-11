"""
Custom migration operations for _inherit_model field injection.
"""

from django.db import migrations, models
from django.db.migrations.operations.fields import AlterField, RemoveField


class InjectField(migrations.AddField):
    """
    Add a field to a model in another app.

    The migration file lives in the extension app; DDL alters the target app's table.
    """

    def __init__(self, target_app_label, model_name, name, field, **kwargs):
        self.target_app_label = target_app_label
        super().__init__(model_name=model_name, name=name, field=field, **kwargs)

    def state_forwards(self, app_label, state):
        """Register the injected field on the target model in project state."""
        state.add_field(
            self.target_app_label,
            self.model_name.lower(),
            self.name,
            self.field.clone(),
            preserve_default=self.preserve_default,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Add the column on the target app's database table."""
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(
                self.target_app_label, self.model_name
            )
            field = to_model._meta.get_field(self.name)
            if not self.preserve_default:
                field.default = self.field.default
            schema_editor.add_field(from_model, field)
            if not self.preserve_default:
                field.default = models.NOT_PROVIDED

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Remove the column from the target app's database table."""
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            schema_editor.remove_field(
                from_model, from_model._meta.get_field(self.name)
            )

    def deconstruct(self):
        """Serialize the operation for migration files."""
        _name, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        """Human-readable description for migration logging."""
        return (
            f"Inject field {self.name} into {self.target_app_label}.{self.model_name}"
        )


class AlterInjectedField(AlterField):
    """
    Alter a field on another app's model.

    Stored in the extension app's migrations (same routing idea as InjectField).
    """

    def __init__(self, target_app_label, model_name, name, field, **kwargs):
        self.target_app_label = target_app_label
        preserve_default = kwargs.pop("preserve_default", True)
        super().__init__(model_name, name, field, preserve_default=preserve_default)

    def state_forwards(self, app_label, state):
        """Apply the field alteration on the target model in project state."""
        state.alter_field(
            self.target_app_label,
            self.model_name_lower,
            self.name,
            self.field,
            self.preserve_default,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Alter the column on the target app's database table."""
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(
                self.target_app_label, self.model_name
            )
            from_field = from_model._meta.get_field(self.name)
            to_field = to_model._meta.get_field(self.name)
            if not self.preserve_default:
                to_field.default = self.field.default
            schema_editor.alter_field(from_model, from_field, to_field)
            if not self.preserve_default:
                to_field.default = models.NOT_PROVIDED

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Reverse the alteration (same forward DDL for AlterField)."""
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        """Serialize the operation for migration files."""
        _path, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        """Human-readable description for migration logging."""
        return (
            f"Alter injected field {self.name} on "
            f"{self.target_app_label}.{self.model_name}"
        )


class RemoveInjectedField(RemoveField):
    """
    Remove an injected field from another app's model.

    Routed when INJECTION_MAP still records the owning extension app.
    """

    def __init__(self, target_app_label, model_name, name):
        self.target_app_label = target_app_label
        super().__init__(model_name, name)

    def state_forwards(self, app_label, state):
        """Remove the injected field from the target model in project state."""
        state.remove_field(
            self.target_app_label,
            self.model_name_lower,
            self.name,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Drop the column from the target app's database table."""
        from_model = from_state.apps.get_model(self.target_app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            schema_editor.remove_field(
                from_model, from_model._meta.get_field(self.name)
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Re-add the column on the target app's database table."""
        to_model = to_state.apps.get_model(self.target_app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(
                self.target_app_label, self.model_name
            )
            schema_editor.add_field(from_model, to_model._meta.get_field(self.name))

    def deconstruct(self):
        """Serialize the operation for migration files."""
        _path, args, kwargs = super().deconstruct()
        kwargs["target_app_label"] = self.target_app_label
        return self.__class__.__name__, args, kwargs

    def describe(self):
        """Human-readable description for migration logging."""
        return (
            f"Remove injected field {self.name} from "
            f"{self.target_app_label}.{self.model_name}"
        )
