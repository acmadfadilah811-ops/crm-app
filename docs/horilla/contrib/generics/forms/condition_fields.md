# Condition field helpers (`horilla_generics/forms/condition_fields.py`)

## Purpose

`condition_fields.py` provides reusable form-level helpers for dynamic condition-row behavior in Horilla forms (mainly single-step condition builders).

It handles:

- dynamic condition field creation
- HTMX wiring for dependent field/value widgets
- model name inference from request/instance
- dynamic condition choice building
- initial value seeding in edit mode
- extraction and validation of condition rows from POST data

This module is called from `HorillaModelForm` workflows without requiring a dedicated mixin class.

---

## High-level workflow

Typical condition-row lifecycle:

1. resolve target model (`model_name`) and condition choices
2. dynamically add condition fields to form (`add_condition_fields`)
3. wire HTMX for content-type-driven field options (`add_generic_htmx_to_field`)
4. prefill initial row values in edit mode (`set_initial_condition_values`)
5. parse submitted rows (`extract_condition_rows`)
6. validate submitted choices/FK values (`clean_condition_fields`)

This supports interactive "field / operator / value" rule editors.

---

## Core helper functions

## `_condition_field_label(model_field, field_name)`

Returns display label:

- model `verbose_name` when available
- fallback humanized field name

---

## `_condition_select_attrs(field_name, row_id, data_placeholder=None)`

Builds common select widget attrs:

- css class (`js-example-basic-single headselect`)
- placeholder
- row-scoped `id`/`name` (`<field>_<row_id>`)

Used as base attrs for multiple condition widgets.

---

## Dynamic field construction

## `add_condition_fields(form)`

Main builder that injects condition fields into form dynamically.

Inputs from form object:

- `condition_fields`
- `condition_model` (optional)
- `condition_field_choices`
- `condition_hx_include`
- `row_id`, `model_name`
- edit context (`instance_obj`, related-name hints)

### Behavior by field type/path

1. **`field` selector**
   - builds `ChoiceField` using `condition_field_choices["field"]`
   - adds HTMX attrs to load value widget from:
     - `horilla_generics:get_field_value_widget`
   - supports existing condition prefill (`_existing_field`, `_existing_value`)
   - includes `condition_model`/`model_name` metadata in `hx-vals`

2. **`value` field**
   - skipped here (rendered dynamically by widget endpoint/row template)

3. **choice-backed fields**
   - from explicit `condition_field_choices` or model field choices
   - rendered as select with placeholder

4. **ForeignKey fields**
   - rendered as `ChoiceField` with initial first-100 options
   - configured for Select2 pagination endpoint:
     - `horilla_generics:model_select2`
   - stores metadata (`data-url`, `data-form-class`, etc.)

5. **primitive input fields**
   - `CharField` -> text input
   - `IntegerField` -> number input
   - `BooleanField` -> checkbox
   - fallback -> text input

All dynamically added custom fields are marked with `is_custom_field` where relevant.

### Operator HTMX refresh hook

If operator field exists and condition model is set:

- attaches HTMX to operator widget so changing operator (e.g., to `between`) refreshes value widget container and can render start/end inputs.

---

## Generic HTMX wiring for content-type field

## `add_generic_htmx_to_field(form)`

Adds HTMX attrs to the form’s content-type selector so changing content type can reload available condition fields.

Field detection strategy:

1. explicit `view_class.content_type_field` from resolver context
2. fallback scan of form model FK fields pointing to `HorillaContentType`

URL resolution strategy:

1. `form.__class__.htmx_field_choices_url` (if provided)
2. app-specific reverse patterns:
   - `<app>:<model>_field_choices_view`
   - `<app>:<content_type_field>_field_choices_view`
   - `<app>:get_<model>_field_choices`
3. fallback:
   - `horilla_generics:get_model_field_choices`

Adds attrs:

- `hx-get`, `hx-target`, `hx-swap`, `hx-include`, `hx-vals`, `hx-trigger=change`

Supports optional class-level filter config (`htmx_field_filter`) for field-type restrictions.

---

## Model name and choice resolution

## `get_model_name_from_request_or_instance(form, kwargs)`

Resolves model name from:

1. `initial["model_name"]`
2. request GET/POST (`model_name`, `model`)
3. numeric content-type id -> resolves via `HorillaContentType`
4. existing instance relationships (`model.model`, `rule.module`, `module`)

Used to drive dynamic field choices for "field" selector.

---

## `get_model_field_choices(form, model_name)`

Finds model by name across app configs and returns editable field choices.

Output starts with:

- `("", "---------")`

Skips common non-editable/system fields:

- `id`, `pk`, `created_at`, `updated_at`, `created_by`, `updated_by`, `company`, `additional_info`

Includes both:

- regular fields
- many-to-many fields

---

## `get_condition_field_choices_from_model(form, field_name, condition_model=None)`

Returns choices for a condition-model field when field has declared `choices`.

Fallback:

- `[("", "---------")]`

---

## `build_condition_field_choices(form, model_name=None)`

Builds full `condition_field_choices` dictionary:

- `field` key -> model field choices (if model name available)
- other condition fields -> from condition-model field choices

Used before dynamic field injection.

---

## Initial values and row extraction

## `set_initial_condition_values(form)`

In edit mode, preloads first existing condition row values into form fields (mostly row `0`) when available.

Related manager resolution:

- `condition_related_name` or fallback candidates list.

---

## `extract_condition_rows(form)`

Parses submitted POST data into normalized condition rows.

Supports row-key styles:

- `<field>_<row_id>`
- base field names for row `0`

Special handling:

- for operator `between`, reads `value_start_<id>` and `value_end_<id>` and stores as comma pair.

Validation in extraction stage:

- row included only when required core keys exist (`field`, `operator`)
- adds numeric `order` from row id

Output example:

```python
[
  {"field": "status", "operator": "exact", "value": "open", "order": 0},
  {"field": "created_at", "operator": "between", "value": "2026-01-01,2026-01-31", "order": 1},
]
```

---

## Validation helper

## `clean_condition_fields(form, cleaned_data)`

Per-field validation for condition forms (when condition model exists):

- validates `ModelChoiceField` selections against fresh queryset (`form._get_fresh_queryset(...)`)
- validates `ChoiceField` values against current valid choices list
- adds form errors for invalid choices instead of raising

This protects against stale/tampered select values.

---

## Integration points in form classes

Expected form attributes/methods used by these helpers:

- `condition_fields`, `condition_model`, `condition_field_choices`
- `row_id`, `model_name`, `instance_obj`
- `condition_related_name`, `condition_related_name_candidates`
- `condition_hx_include`
- optional `_get_fresh_queryset(...)` (for strict FK validation)

Typically wired from `HorillaModelForm` / single-form builder flow.

---

## Practical usage example

### In form init (conceptual)

```python
from horilla_generics.forms import condition_fields

class RuleForm(HorillaModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_name = condition_fields.get_model_name_from_request_or_instance(self, kwargs)
        self.condition_field_choices = condition_fields.build_condition_field_choices(self, model_name)
        condition_fields.add_condition_fields(self)
        condition_fields.add_generic_htmx_to_field(self)
        condition_fields.set_initial_condition_values(self)
```

### In clean

```python
def clean(self):
    cleaned = super().clean()
    condition_fields.clean_condition_fields(self, cleaned)
    self.cleaned_data["condition_rows"] = condition_fields.extract_condition_rows(self)
    return cleaned
```

---

## Caveats

- many helper branches are defensive and swallow exceptions with logging; debugging complex row issues may require examining logs.
- model lookup by name scans all app configs and depends on unique model naming.
- value encoding for `between` uses comma-joined string; downstream parsers must split reliably.
- dynamic HTMX behavior depends on template/container IDs matching expected naming conventions.

---

## Summary

`condition_fields.py` is the dynamic condition-row engine for Horilla forms. It provides end-to-end helpers for condition field generation, HTMX interaction, model-aware choice loading, submission parsing, and validation, enabling flexible rule-builder UIs with minimal repetitive form code.
