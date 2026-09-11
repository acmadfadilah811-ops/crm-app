# Timeline settings helpers (`horilla_generics/views/helpers/timeline_settings.py`)

## Purpose

This module persists per-user timeline span preferences:

- which field is used as timeline **start**
- which field is used as timeline **end**

Preferences are stored in `TimelineSpanBy` and consumed by `HorillaTimelineView` so users can keep preferred date-field mappings across sessions.

---

## Components

1. `TimelineSettingsFormView` (HTMX modal FormView to save preferences)
2. `get_timeline_span_by_row(...)` (read one saved row)
3. `get_saved_timeline_fields(...)` (read `(start_field, end_field)` tuple)

---

## Data model used

`TimelineSpanBy` key dimensions:

- `user`
- `app_label`
- `model_name` (matched case-insensitively in helper reads)

Persisted values:

- `start_field`
- `end_field`

Form class used:

- `TimelineSpanByForm` (from `horilla_generics.forms.generics`)

---

## View: `TimelineSettingsFormView`

```python
class TimelineSettingsFormView(FormView):
```

- HTMX-only (`@htmx_required`)
- template: `timeline_span_form.html`
- form: `TimelineSpanByForm`
- route: `horilla_generics:timeline_settings`

### `get_form_kwargs` flow

Reads identity params from GET/POST:

- `model` (GET) or `model_name` (POST)
- `app_label`

Builds initial context values:

- `main_url` (where timeline lives)
- `preserve_qs` (serialized query params excluding `app_label`, `model`, `main_url`)

Loads existing preference row:

- query by `app_label`, current user, and `model_name__iexact`.

If exists:

- passes row as form `instance`.

If not:

- creates unsaved `TimelineSpanBy` instance with empty start/end,
- optionally pre-fills from GET:
  - `timeline_start`
  - `timeline_end`

### `get_context_data`

Adds:

- `settings_title = "Timeline settings"`.

### `form_valid`

1. forces `form.instance.user = request.user`.
2. saves preference row.
3. reads `main_url` and optional `preserve_qs`.
4. prepares timeline params (`layout=timeline`, start/end fields) in memory.
5. returns script:

```html
<script>$('#reloadButton').click();closeModal();</script>
```

So UI reloads current timeline context after saving.

> Note: the code prepares URL param pairs but currently does not emit direct redirect URL; it relies on page reload behavior.

---

## Helper: `get_timeline_span_by_row(user, app_label, model_name)`

Returns `TimelineSpanBy` row or `None`.

Important behavior:

- case-insensitive model name match (`model_name__iexact`)

This avoids mismatch when caller passes `User` vs stored `user` (or any model name with different casing).

---

## Helper: `get_saved_timeline_fields(user, app_label, model_name)`

Returns:

- `(start_field, end_field)` from saved row, or
- `(None, None)` when absent.

Used by timeline views for preference fallback.

---

## Integration with timeline view

`HorillaTimelineView` calls `get_saved_timeline_fields(...)` in:

- `get_timeline_start_field()`
- `get_timeline_end_field()`

Resolution priority in timeline view:

1. GET override (`timeline_start`, `timeline_end`)
2. saved timeline settings (this module)
3. class defaults

---

## Integration with navbar/actions

Navbar builds timeline settings modal URL with params like:

- `model`
- `app_label`
- `main_url`
- existing timeline-related query state

User opens settings modal, saves form, and timeline refreshes via reload trigger.

---

## Template behavior (`timeline_span_form.html`)

Form posts to `timeline_settings` endpoint and includes hidden:

- `model_name`
- `app_label`
- `main_url`
- `preserve_qs`

Visible controls:

- `start_field` select
- `end_field` select

Choices are populated by `TimelineSpanByForm` using model date/datetime fields, with model-level validation in `clean()`.

---

## Example 1: Open timeline settings modal

```html
<button
  hx-get="{% url 'horilla_generics:timeline_settings' %}?model=Lead&app_label=leads&main_url=/leads/leads-view/&layout=timeline&timeline_scale=months"
  hx-target="#modalBox"
  hx-swap="innerHTML"
  onclick="openModal()">
  Timeline settings
</button>
```

---

## Example 2: Save preference

POST payload (conceptual):

```text
model_name=Lead
app_label=leads
start_field=created_at
end_field=updated_at
main_url=/leads/leads-view/
preserve_qs=timeline_scale%3Dweeks%26view_type%3Dall
```

Result:

- `TimelineSpanBy` upsert for current user+model.
- modal closes and timeline reloads.

---

## Example 3: Read saved values in code

```python
from horilla_generics.views.helpers.timeline_settings import get_saved_timeline_fields

start_field, end_field = get_saved_timeline_fields(request.user, "leads", "Lead")
```

Used for fallback behavior in timeline render logic.

---

## Notes

- View is HTMX-only; direct non-HTMX usage is not intended.
- Case-insensitive model matching is deliberate and important for consistency.
- `preserve_qs` is collected and parsed in save flow, enabling future redirect-style behavior if needed.

---

## Summary

`timeline_settings.py` is the persistence bridge between timeline UI controls and user-specific start/end field preferences. It keeps timeline field selection sticky per model and feeds those values back into `HorillaTimelineView` fallback resolution.
