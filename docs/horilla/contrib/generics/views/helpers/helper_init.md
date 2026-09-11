# Helpers package index (`horilla_generics/views/helpers/__init__.py`)

## Purpose

`horilla_generics/views/helpers/__init__.py` is the **export hub** for helper view modules used by generic list/detail/form UIs.

It allows callers to import helper classes from one namespace:

```python
from horilla_generics.views import helpers
```

or via package-level `views` aggregation.

---

## What it exports

This file re-exports helper modules with wildcard imports:

- `condition_widget`
- `detail_field`
- `edit_field`
- `filter_list`
- `kanban_groupby`
- `timeline_settings`
- `list_column`
- `select2`

So symbols from those modules become available under `horilla_generics.views.helpers`.

---

## Functional areas covered

### Condition and filter builders

- dynamic condition-row widgets
- saved filter list helpers (save/delete/pin style flows)

### Detail-field customization

- detail field selector/save/reset views for per-user detail layout
- inline field edit/cancel/update helper endpoints

### List/grid presentation helpers

- list column selector and reset helpers
- kanban/group-by settings + load-more helper views
- timeline settings persistence helpers

### Async field data helpers

- select2 data endpoint helpers for model fields/relations

---

## Relation to `horilla_generics/views/__init__.py`

`views/__init__.py` imports:

```python
from horilla_generics.views import helpers
```

This means app URL modules can reference helper views through `views.helpers.<ClassName>`.

Example usage pattern from URL config:

```python
path("timeline-settings/", views.helpers.TimelineSettingsFormView.as_view(), name="timeline_settings")
```

---

## Why this index file exists

Without this aggregator, every consumer would need long module-specific imports like:

```python
from horilla_generics.views.helpers.timeline_settings import TimelineSettingsFormView
```

The package index keeps imports shorter and centralizes the helper public surface.

---

## Maintenance notes

- Add new helper module exports here only if they are part of the shared public helper API.
- Keep wildcard exports consistent with module naming to avoid hidden namespace collisions.
- If import cycles appear, check helper module dependencies and import order in this file.

---

## Summary

`horilla_generics/views/helpers/__init__.py` is a helper-API aggregator: it bundles condition/detail/list/timeline/select2 helper endpoints into one import surface used by `horilla_generics` URL wiring.
