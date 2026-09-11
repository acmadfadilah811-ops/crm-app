# Toolkit package init (`horilla_generics/views/toolkit/__init__.py`)

## Purpose

`__init__.py` in the toolkit package works as an export hub for reusable list/form utilities used by Horilla generic views.

It consolidates imports so consumers can import toolkit utilities from one place instead of importing each submodule directly.

---

## Module docstring meaning

The file-level docstring describes the toolkit scope:

- bulk delete helpers
- bulk export helpers
- bulk update helpers
- quick filter helpers/mixins for list views
- common form mixin for single-step and multi-step form views

---

## What this file exports

This module re-exports all public symbols from:

- `bulk_delete`
- `bulk_export`
- `bulk_update`
- `quick_filter`
- `form_mixin`

via wildcard imports:

```python
from horilla_generics.views.toolkit.bulk_delete import *
from horilla_generics.views.toolkit.bulk_export import *
from horilla_generics.views.toolkit.bulk_update import *
from horilla_generics.views.toolkit.quick_filter import *
from horilla_generics.views.toolkit.form_mixin import *
```

---

## Why this pattern is used

Benefits:

- **Convenient imports** for consuming modules (`from ...toolkit import X, Y`).
- **Centralized API surface** for toolkit-related helpers.
- **Lower call-site noise** in large view files.

Trade-offs:

- wildcard exports can hide exact symbol origin,
- can increase risk of name collisions if submodules expose similar names,
- maintainers should keep public symbols stable across submodules.

---

## Where it is used

Typical usage in the codebase:

- `horilla_generics/views/list.py` imports multiple toolkit helpers from the package-level namespace.
- Other view modules may import directly from specific toolkit submodules (`form_mixin`, `single_form_builder`, etc.) when they need explicit symbols.

---

## Example usage (aggregated import)

```python
from horilla_generics.views.toolkit import (
    bulk_delete_queryset,
    bulk_update_queryset,
    apply_quick_filter,
)
```

This style depends on toolkit `__init__.py` re-exporting those symbols from submodules.

---

## Example usage (direct import)

```python
from horilla_generics.views.toolkit.form_mixin import FormViewCommonMixin
```

Use this when you want explicit origin and clearer static navigation.

---

## Maintenance notes

- If a new toolkit submodule should be exposed package-wide, add its import here.
- If you deprecate symbols in a toolkit submodule, check package-level imports to avoid breaking consumers.
- Keep toolkit-level exports focused on stable, reusable primitives for generic views.

---

## Summary

`horilla_generics/views/toolkit/__init__.py` is a lightweight but important aggregation layer that defines the toolkit package public surface and simplifies imports across the generic view framework.
