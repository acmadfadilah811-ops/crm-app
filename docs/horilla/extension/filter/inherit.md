# Horilla `_inherit_filter` — FilterSet Extension Guide

> **Status:** Implemented (`horilla/extension/filter/`)
> **Spec:** [spec.md](./spec.md)
> **Related:** [Model `_inherit`](../models/inherit.md) · [Form `_inherit_form`](../forms/inherit.md) · [List `_inherit_list`](../list/inherit.md)

Extend existing `HorillaFilterSet` subclasses (`LeadFilter`, `ContactFilter`, etc.) **without** editing core `horilla_crm` filter modules.

---

## Table of contents

1. [Problem](#problem)
2. [Solution overview](#solution-overview)
3. [How the filter panel uses your filterset](#how-the-filter-panel-uses-your-filterset)
4. [Quick start](#quick-start)
5. [Rules](#rules)
6. [Layout hooks](#layout-hooks)
7. [Declared filters and methods](#declared-filters-and-methods)
8. [Bootstrap and resolution](#bootstrap-and-resolution)
9. [Comparison with list `filterset_class` override](#comparison-with-list-filterset_class-override)
10. [Troubleshooting](#troubleshooting)
11. [Non-goals (v1)](#non-goals-v1)
12. [Debugging](#debugging)
13. [Full example: Lead + `industry_code`](#full-example-lead--industry_code)

---

## Problem

After `_inherit` adds `industry_code` on `leads.Lead`:

| Area | Gap without `_inherit_filter` |
|------|-------------------------------|
| Filter field dropdown (`filter_row.html`) | Injected fields appear when `Meta.fields = "__all__"`; you cannot hide them or tune search without editing core `LeadFilter` |
| Global search in filter panel | `Meta.search_fields` on `LeadFilter` does **not** include `industry_code` unless you extend the filterset |
| Explicit `Meta.fields` list | New column omitted until you subclass `LeadFilter` manually |
| Custom `django_filters.Filter` | Requires subclass + wiring on every view |

`_inherit_filter` merges `Meta` and declared filters at startup. List/kanban views resolve the composed class through `get_filterset_class()` (same idea as `get_form_class()` for forms).

---

## Solution overview

```text
my_lead_extensions/filters.py
    LeadFilterExtension  (_inherit_filter = "...LeadFilter")
              │
              ▼
    FILTER_EXTENSION_REGISTRY
              │
              ▼
    apply_filter_extensions()  →  LeadFilterExtended
              │
              ▼
    LeadListView.get_filterset_class()
      → resolve_filterset_class(LeadFilter)
              │
              ▼
    _get_model_fields()  reads LeadFilterExtended.Meta.exclude
              │
              ▼
    context["filter_fields"]  →  partials/filter_row.html <option> list
```

Core CRM URLs and `filterset_class = LeadFilter` on views stay unchanged.

---

## How the filter panel uses your filterset

The **Select Field** dropdown in `horilla/contrib/generics/templates/partials/filter_row.html` is **not** built from the extension class directly. It loops `filter_fields` from the list view context:

```django
{% for field in filter_fields %}
    <option value="{{ field.name }}">{{ field.verbose_name }}</option>
{% endfor %}
```

| Step | Code | What matters |
|------|------|----------------|
| 1 | `HorillaListView.get_context_data()` | Calls `_get_model_fields(include_properties=False)` |
| 2 | `HorillaListFilterFieldsMixin._get_model_fields()` | Uses `filterset_class = self.get_filterset_class()` (composed when extensions exist) |
| 3 | Per model field | Skips `field.name in filterset_class.Meta.exclude` |
| 4 | Template | Renders remaining names as `<option>` values |

So **`exclude_append` on `FilterExtension`** is the correct way to remove a field from that dropdown. It merges into the composed filterset’s `Meta.exclude`.

### What `exclude_append` affects

| UI / behavior | Controlled by |
|---------------|----------------|
| Filter row **field** dropdown | `Meta.exclude` via `_get_model_fields()` |
| Filter **operators** / value widgets | Same field list |
| `HorillaFilterSet.filter_queryset()` | Rejects filters on excluded top-level field names |
| Filter panel **search** box | `Meta.search_fields` (use `search_fields_append` / inner `Meta.search_fields`) |
| Navbar **quick filters** | Separate: `LeadListView.exclude_quick_filter_fields` or `exclude_quick_filter_fields_append` on `_inherit_list` — **not** `exclude_append` |

### `Meta.fields = "__all__"` (typical CRM filtersets)

Injected ORM columns (e.g. `industry_code`) are already eligible for advanced filters because they exist on the model. Use:

- `exclude_append` — hide from the filter panel
- `search_fields_append` — include in the filter panel search box

You do **not** need `fields_append` when the target uses `fields = "__all__"`.

---

## Quick start

Hide an injected field from the filter panel (recommended for `industry_code`):

```python
# my_lead_extensions/filters.py
from horilla.extension.filter import FilterExtension


class LeadFilterExtension(FilterExtension):
    _inherit_filter = "horilla_crm.leads.filters.LeadFilter"
    exclude_append = ["industry_code"]
```

```python
# my_lead_extensions/apps.py
auto_import_modules = [
    "models",
    "forms",
    "filters",  # required — registers FilterExtension at import
    "lists",
    "kanbans",
    "details",
]
```

```python
# local_settings.py (client-owned)
INSTALLED_APPS += ["my_lead_extensions"]
```

Restart the dev server after changing extension modules.

---

## Rules

| Rule | Detail |
|------|--------|
| Target path | Full dotted path: `"horilla_crm.leads.filters.LeadFilter"` |
| Base class | Subclass `FilterExtension`, not `LeadFilter` |
| Do not instantiate | `FilterExtension` subclasses are registration-only |
| Priority | `_inherit_filter_priority` — higher runs later in mixin order |
| Restart | Server restart required after changing extension modules |
| Field names | `exclude_append` must use the **ORM field name** (e.g. `industry_code`), not the verbose label |

---

## Layout hooks

### `exclude_append`

```python
exclude_append = ["industry_code", "internal_flag"]
```

Merged into composed `Meta.exclude`. Removes fields from:

- `filter_row.html` field `<select>`
- Advanced filter application (excluded names are rejected in `filter_queryset`)

To hide **both** the core Lead field `industry` and your extension field `industry_code`:

```python
exclude_append = ["industry", "industry_code"]
```

### `search_fields_append` / `search_fields_insert`

```python
search_fields_append = ["industry_code"]
search_fields_insert = [("email", "industry_code")]
```

Used by `HorillaFilterSet.filter_search()` for the filter panel search input. Does **not** add a field to the per-row field dropdown unless the field is also on the model and not in `exclude`.

### `fields_append`

Only when the target filterset uses an **explicit** field list (not `"__all__"`):

```python
fields_append = ["industry_code"]
```

Or on inner `Meta`:

```python
class LeadFilterExtension(FilterExtension):
    _inherit_filter = "horilla_crm.leads.filters.LeadFilter"

    class Meta:
        search_fields = ["industry_code"]
        exclude = ["legacy_field"]
```

---

## Declared filters and methods

```python
import django_filters
from horilla.extension.filter import FilterExtension


class LeadFilterExtension(FilterExtension):
    _inherit_filter = "horilla_crm.leads.filters.LeadFilter"

    industry_code_exact = django_filters.CharFilter(
        field_name="industry_code",
        lookup_expr="iexact",
        label="Industry code (exact)",
    )

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset)
```

### `setup_filter_extension(self)`

Optional hook on the extension class. The composer adds a **no-op default** on each extension mixin (methods on `FilterExtension` itself are not copied into the mixin). Override on your subclass when you need to tweak filter instances after `FilterSet.__init__`:

```python
def setup_filter_extension(self):
    if "industry_code" in self.filters:
        self.filters["industry_code"].field.widget.attrs["class"] = "my-class"
```

---

## Bootstrap and resolution

| When | What runs |
|------|-----------|
| Startup | `bootstrap_extensions()` → `apply_filter_extensions(force=True)` |
| Each `get_filterset_class()` | `resolve_filterset_class()` (cached on `FILTER_COMPOSED_MAP`) |

```python
from horilla.extension.bootstrap import bootstrap_extensions

bootstrap_extensions()
```

Extension apps may appear **after** `horilla_crm.*` in `INSTALLED_APPS`.

| View API | Behavior |
|----------|----------|
| `HorillaListView.filterset_class` | Still `LeadFilter` at class definition (unchanged) |
| `HorillaListView.get_filterset_class()` | Returns `LeadFilterExtended` when extensions registered |
| `get_queryset()` / filter context | Uses `get_filterset_class()` for instantiation and `_get_model_fields()` |

---

## Comparison with list `filterset_class` override

| Approach | Use when |
|----------|----------|
| **`_inherit_filter`** | Extend `LeadFilter` for **all** views that set `filterset_class = LeadFilter` |
| **`ListExtension` + scalar `filterset_class = MyFilter`** | Replace the entire filterset for **one** list view only |

Prefer `_inherit_filter` when kanban, card, split, and list views all share `LeadFilter`.

---

## Troubleshooting

### I used `exclude_append = ["industry_code"]` but still see **Industry** in the dropdown

That is usually the **core** CRM field `industry` (choice field on `Lead`), not your extension field `industry_code`.

| Label in UI | Field name | Hidden by `exclude_append = ["industry_code"]`? |
|-------------|------------|--------------------------------------------------|
| Industry | `industry` | No |
| Industry Code | `industry_code` | Yes (when extension is loaded) |

Add `"industry"` to `exclude_append` if you want both hidden.

### I still see **Industry Code** after `exclude_append`

1. Restart the dev server (composed classes are built at startup).
2. Confirm `filters` is in `auto_import_modules` and `my_lead_extensions` is in `INSTALLED_APPS`.
3. Verify composition in shell:

```python
from horilla.extension.filter import resolve_filterset_class
from horilla_crm.leads.filters import LeadFilter
print(list(resolve_filterset_class(LeadFilter).Meta.exclude))
# expect 'industry_code' in the tuple
```

4. Confirm the dropdown is the **filter panel** (`filter_row.html`), not bulk update or quick filters (different field lists).

### Field appears in quick filters but not in advanced filter row

Quick filters use `enable_quick_filters` and `exclude_quick_filter_fields` on the list view. Add on `_inherit_list`:

```python
exclude_quick_filter_fields_append = ["industry_code"]
```

---

## Non-goals (v1)

- Views with `filterset_class = None`
- Changing `Meta.model` on the target
- DRF / API filter backends
- Editing `filter_row.html` or filter panel templates from extensions
- Hot-reload without process restart

See [spec.md](./spec.md) for full non-goals and acceptance criteria.

---

## Debugging

```python
from horilla.extension.filter import (
    get_filter_extensions,
    print_filter_mro,
    resolve_filterset_class,
)
from horilla_crm.leads.filters import LeadFilter

print(get_filter_extensions(LeadFilter))
print_filter_mro(LeadFilter)
composed = resolve_filterset_class(LeadFilter)
print("exclude:", list(composed.Meta.exclude))
print("search_fields:", list(getattr(composed.Meta, "search_fields", []) or []))
```

Simulate filter panel field list (requires request/view setup in full app):

```python
from django.test import RequestFactory
from horilla_crm.leads.views.core import LeadListView
from horilla.extension.list import resolve_list_view_class

request = RequestFactory().get("/crm/leads/leads-list/")
view = resolve_list_view_class(LeadListView)()
view.request = request
view.model = LeadListView.model
names = [f["name"] for f in view._get_model_fields(include_properties=False)]
print("industry_code in filter_fields:", "industry_code" in names)
```

```bash
python manage.py check   # filter_extensions.E001–E004 when extension apps are installed
```

---

## Full example: Lead + `industry_code`

```python
# my_lead_extensions/models.py
class LeadExtension(HorillaCoreModel):
    _inherit = "leads.Lead"
    industry_code = models.CharField(max_length=20, null=True, blank=True)


# my_lead_extensions/filters.py — hide from filter panel; optional search
class LeadFilterExtension(FilterExtension):
    _inherit_filter = "horilla_crm.leads.filters.LeadFilter"
    exclude_append = ["industry_code"]
    # search_fields_append = ["industry_code"]  # only if you want panel search on it


# my_lead_extensions/forms.py — _inherit_form on LeadSingleForm
# my_lead_extensions/lists.py   — columns_insert, bulk_update_fields_append
# my_lead_extensions/kanbans.py / details.py — as needed
```

No edits to `horilla_crm/leads/filters.py` or `LeadListView.filterset_class`.

---

## See also

- [spec.md](./spec.md) — technical specification
- [../inherit.md](../inherit.md) — extension system index
- [../list/inherit.md](../list/inherit.md) — list columns, bulk update, quick filters
