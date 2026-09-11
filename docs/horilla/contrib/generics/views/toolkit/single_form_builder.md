# Single form builder toolkit (`horilla_generics/views/toolkit/single_form_builder.py`)

## Purpose

`single_form_builder.py` is the dynamic form and condition-row utility module behind `HorillaSingleFormView`.

It handles two major areas:

- **Dynamic form class generation** (field permissions, readonly/hidden behavior, duplicate mode, widget behavior)
- **Condition row lifecycle** (load existing rows, parse submitted rows, add rows via HTMX, save rows)

This module lets single-form views support complex conditional rule editors without hardcoding form classes for each model.

---

## High-level architecture

The module is organized in three blocks:

1. **Condition row helpers**
   - defaults, parsing, row rendering, persistence
2. **Dynamic form builder**
   - runtime `DynamicForm` class construction
3. **Context assembly**
   - condition-related context hydration for templates

`HorillaSingleFormView` delegates to this module for most condition-related operations and for form-class generation when `form_class` is not explicitly provided.

---

## Dynamic form builder

## `get_dynamic_form_class(view)`

Returns a runtime `DynamicForm` class based on the passed view configuration.

Uses view attributes:

- `model`, `fields`, `exclude`
- `full_width_fields`, `dynamic_create_fields`, `hidden_fields`
- `condition_fields`, `condition_model`, `condition_field_choices`
- `condition_hx_include`, `save_and_new`

Also appends default exclusions:

- `created_at`, `updated_at`, `created_by`, `updated_by`, `additional_info`

### Generated class inheritance

```python
class DynamicForm(OwnerQuerysetMixin, HorillaModelForm):
```

Why:

- `OwnerQuerysetMixin` helps queryset filtering for owner-aware relation fields,
- `HorillaModelForm` provides Horilla form behaviors (dynamic create hooks, styling, etc.).

---

### `DynamicForm.Meta` behavior

- `model = view.model`
- `fields = view.fields` or `"__all__"`
- `exclude = view.exclude + default_exclude` (or just defaults)
- auto DateInput widgets for all model `DateField` fields

This gives predictable base form structure even when view only configures model + minimal options.

---

### `DynamicForm.__init__` permission/visibility pipeline

Accepted extra kwargs:

- `field_permissions`
- `duplicate_mode`

Then injects builder-level kwargs for `HorillaModelForm`:

- dynamic create controls
- layout/full-width settings
- hidden + condition field settings
- `save_and_new` flag

Core decision loop per field:

1. skip condition/hidden fields (handled separately),
2. read permission state (`readwrite`, `readonly`, `hidden`),
3. determine if field is mandatory (`_is_field_mandatory`),
4. apply mode-sensitive policy:
   - create/duplicate mode may remove non-mandatory readonly/hidden fields,
   - edit mode keeps readonly fields and applies readonly behavior.

Two result buckets:

- `fields_to_remove`
- `readonly_fields`

Removed fields are deleted from `self.fields`; readonly fields get `_apply_readonly(...)`.

---

### `DynamicForm.clean` readonly enforcement

Even if UI marks a field readonly, submitted payload can be tampered.

`clean()` enforces server-side readonly integrity for edit mode:

1. for each readonly field:
   - fetch model field metadata,
   - compare original value vs submitted value via `_value_changed(...)`,
2. if changed:
   - overwrite cleaned value with original,
   - add validation error `"This field is read-only and cannot be modified."`,
3. if unchanged:
   - still normalize cleaned value to original.

This is a critical anti-tampering layer.

---

## Readonly/mandatory internals

## `_is_field_mandatory(form, field_name, field)`

Model-based required check:

- mandatory when `null=False` and `blank=False`,
- fallback to form field `required` if metadata lookup fails.

---

## `_get_original_value(instance, field_name, model_field)`

Original value extraction:

- M2M => list of related objects
- others => direct attribute

Used by readonly comparison logic.

---

## `_value_changed(model_field, original_value, submitted_value)`

Type-aware change detection:

- M2M: compare PK sets
- FK: compare related PKs
- scalar fields: direct `!=`

Ensures robust comparison regardless of object instances.

---

## `_apply_readonly(form, field_name, duplicate_mode)`

Applies readonly semantics with nuanced widget behavior.

### Special case: create/duplicate + mandatory fields

Readonly is removed for mandatory fields in create/duplicate mode, so required values remain editable and form remains submittable.

### Text-like fields

For text/date/number-like inputs (non-choice):

- keeps field enabled,
- sets widget `readonly`,
- adds disabled-style classes,
- marks `data-readonly`,
- patches widget `get_context` to preserve readonly attribute.

### Select/choice/non-text widgets

For select-like controls:

- sets `field.disabled = True`,
- adds disabled attrs/classes.

This split balances UX (visible values) and browser submission behavior.

---

## Condition row helpers

## `fill_mandatory_condition_defaults(condition_model, condition_fields, row_data)`

Fills missing required condition-model fields to avoid DB errors.

Strategy for missing mandatory fields:

1. model default (execute callable defaults when needed),
2. first choice value for fields with choices,
3. skip unsafe FK guessing (no generic FK default).

Returns new dict (does not mutate input).

---

## `get_existing_conditions(view)`

Loads existing condition rows in edit mode.

Resolution order for related manager:

1. explicit `view.condition_related_name`,
2. candidate names from `condition_related_name_candidates`
   - default: `["conditions", "criteria", "team_members"]`

Ordering:

- `view.condition_order_by` (default `["order", "created_at"]`)

Returns queryset or `None`.

---

## `get_model_name_from_content_type(view, request=None)`

Extracts target model name from `content_type_field`.

Sources:

- POST/GET content type id,
- existing object’s content_type relation in edit mode.

Uses `HorillaContentType` resolution where possible.

Used when condition field options depend on selected target model.

---

## `get_submitted_condition_data(view)`

Parses POST data into row-based structure keyed by row id.

Input pattern expected:

- `<fieldname>_<row_id>`

Special handling:

- for `value` field, supports multivalue input via `getlist` and joins with commas.

Output shape:

```python
{
  "0": {"field": "status", "operator": "equals", "value": "active"},
  "1": {"field": "priority", "operator": "in", "value": "high,medium"},
}
```

---

## `add_condition_row(view, request)`

Returns HTML for one additional condition row (HTMX endpoint behavior).

Key steps:

1. determine `new_row_id`:
   - `row_id=next` uses session counter `condition_row_count`,
   - otherwise increments numeric row_id.
2. build form kwargs from view `get_form_kwargs()` with row context,
3. resolve content-type driven model name and inject into initial data,
4. include edit-mode instance when pk exists,
5. prefill from existing conditions (if row index maps to existing row),
6. instantiate form,
7. refresh dynamic field choices for selected model,
8. attach `hx-vals` / `hx-trigger=change,load` for field widget autoload,
9. merge submitted and existing condition data,
10. render `partials/condition_row.html`.

This method is the core of dynamic condition-row UX.

---

## `get_add_condition_url(view)`

Builds URL that triggers adding a condition row:

- appends `add_condition_row=1`
- propagates `content_type_field` value when available

Used by templates/buttons to request new rows without losing model context.

---

## `save_conditions(view, form=None)`

Persists condition rows for saved main object.

Behavior:

1. requires `condition_fields`, `condition_model`, and `view.object`,
2. reads condition rows from:
   - `form.cleaned_data["condition_rows"]` if available,
   - else parses POST keys,
3. resolves related manager between main and condition model,
4. deletes existing rows (`related_manager.all().delete()`),
5. sorts row keys numerically,
6. fills mandatory defaults,
7. skips rows missing required logical keys (`field`, `operator` when configured),
8. builds `create_kwargs`:
   - FK back to main object
   - condition field values
   - optional `order`
   - optional `company`, `created_by`, `updated_by`
9. creates condition rows one by one.

Important:

- persistence strategy is **replace-all**, not incremental diff update.

---

## `build_condition_context(view, context)`

Mutates template context with condition-related render data.

Adds:

- `existing_conditions`
- `condition_field_choices` (if form exposes it)
- `submitted_condition_data`
- `condition_row_count`
- pre-rendered value widget HTML snippets (`value_widget_html_<row_id>`) for existing rows

Widget HTML generation uses `GetFieldValueWidgetView._get_value_widget_html(...)` to hydrate value controls based on selected field type.

If not in edit-with-conditions mode, still computes `condition_row_count` from submitted data/session.

---

## How `HorillaSingleFormView` integrates this module

Common delegation points in `single_form.py`:

- dynamic form class: `get_dynamic_form_class(self)`
- add-row endpoint: `add_condition_row(self, request)`
- existing condition fetch: `get_existing_conditions(self)`
- submitted data parse: `get_submitted_condition_data(self)`
- context hydration: `build_condition_context(self, context)`
- save step: `save_conditions(self, form)`
- add-row URL: `get_add_condition_url(self)`

This keeps single-form view controller code concise while preserving rich condition behavior.

---

## Child view configuration examples

### Example 1: dynamic form with readonly field permissions

```python
from horilla_generics.views.single_form import HorillaSingleFormView
from leads.models import Lead


class LeadFormView(HorillaSingleFormView):
    model = Lead
    form_class = None  # use dynamic builder
    fields = "__all__"
```

Then pass `field_permissions` in form kwargs from view logic to enable hidden/readonly handling.

### Example 2: condition model setup

```python
class LeadRuleFormView(HorillaSingleFormView):
    model = LeadRule
    condition_model = LeadRuleCondition
    condition_fields = ["field", "operator", "value"]
    condition_related_name = "conditions"
    condition_order_by = ["order", "created_at"]
```

### Example 3: content-type-aware conditions

```python
class AutomationFormView(HorillaSingleFormView):
    model = Automation
    content_type_field = "target_content_type"
    condition_fields = ["field", "operator", "value"]
```

This enables model-specific condition field choices while adding rows.

---

## Caveats and behavior notes

- `save_conditions()` deletes all existing conditions before create; partial edits are not incremental.
- many helper branches catch exceptions silently for resilience; debugging may require extra logging in overrides.
- readonly UI behavior differs by widget type (`readonly` vs `disabled`) to preserve submission semantics.
- row indexing depends on numeric ids and session counters; custom frontend row id strategies should remain compatible.

---

## Summary

`single_form_builder.py` is the dynamic engine for single-form rendering and condition management in Horilla generics. It combines runtime form-class creation, robust readonly enforcement, HTMX condition-row rendering, and replace-all condition persistence into a reusable toolkit used by `HorillaSingleFormView`.
