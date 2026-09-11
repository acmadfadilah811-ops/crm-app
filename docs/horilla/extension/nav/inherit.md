# Horilla `_inherit_nav` — Nav Bar Extension Guide

> **Status:** Implemented (`horilla/extension/nav/`)
> **Spec:** [spec.md](./spec.md)
> **Related:** [List `_inherit_list`](../list/inherit.md) · [Filter `_inherit_filter`](../filter/inherit.md)

Extend existing `HorillaNavView` subclasses (`LeadNavbar`, `LeadStageNavbar`, etc.) **without** editing core `horilla_crm` navbar classes or URL names.

---

## Table of contents

1. [Problem](#problem)
2. [Solution overview](#solution-overview)
3. [Quick start](#quick-start)
4. [Rules](#rules)
5. [Layout hooks](#layout-hooks)
6. [Method overrides](#method-overrides)
7. [Bootstrap and resolution](#bootstrap-and-resolution)
8. [Navbar vs list vs filter](#navbar-vs-list-vs-filter)
9. [Non-goals (v1)](#non-goals-v1)
10. [Debugging](#debugging)
11. [Full example: Lead navbar](#full-example-lead-navbar)

---

## Problem

CRM list pages use a **separate navbar view** loaded into `#navBar` via HTMX:

```text
LeadView.nav_url  →  leads:leads_nav  →  LeadNavbar
LeadView.list_url →  leads:leads_list →  LeadListView
```

Without `_inherit_nav`, extension apps cannot:

- Add entries to the navbar **actions** menu
- Register extra **view type** dropdown options (`custom_view_type`)
- Exclude extension fields from **Add Column to List** (`column_selector_exclude_fields`)
- Adjust flags like `enable_quick_filters` without subclassing `LeadNavbar` in core

---

## Solution overview

```text
my_lead_extensions/navbars.py
    LeadNavbarExtension  (_inherit_nav = "...LeadNavbar")
              │
              ▼
    NAV_EXTENSION_REGISTRY
              │
              ▼
    apply_nav_extensions()  →  LeadNavbarExtended
              │
              ▼
    LeadNavbar.as_view()  →  resolve_nav_view_class() per request
              │
              ▼
    navbar.html  (#navBar HTMX fragment)
```

`path("leads-nav/", views.LeadNavbar.as_view(), name="leads_nav")` stays unchanged.

---

## Quick start

```python
# my_lead_extensions/navbars.py
from horilla.extension.nav import NavExtension


class LeadNavbarExtension(NavExtension):
    _inherit_nav = "horilla_crm.leads.views.core.LeadNavbar"

    column_selector_exclude_fields_append = ["industry_code"]
```

```python
# my_lead_extensions/apps.py
auto_import_modules = [
    "models",
    "forms",
    "filters",
    "navbars",  # required
    "lists",
    "kanbans",
    "details",
]
```

Restart the dev server after changes.

---

## Rules

| Rule | Detail |
|------|--------|
| Target path | Full dotted path to a **concrete** navbar class |
| Base class | Subclass `NavExtension`, not `LeadNavbar` |
| Do not instantiate | Registration-only |
| Priority | `_inherit_nav_priority` — higher runs later |
| Concrete target only | Cannot target `HorillaNavView` itself |

---

## Layout hooks

### `column_selector_exclude_fields_append`

Hides fields from the **Add Column to List** action in the navbar menu (when `enable_actions` is true and layout is list).

```python
column_selector_exclude_fields_append = ["industry_code", "message_id"]
```

Pairs well with `_inherit_list` `columns_insert` — you can show a column on the grid but omit it from the column picker.

### `exclude_kanban_fields_append`

Appends to the comma-separated `exclude_kanban_fields` string used by Kanban / Group By settings modals.

```python
exclude_kanban_fields_append = ["industry_code"]
```

### `actions_append`

Each item matches the dict shape used by `HorillaNavView.actions`:

```python
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

actions_append = [
    {
        "action": _("My report"),
        "attrs": f'''
            hx-get="{reverse_lazy('my_app:report')}"
            hx-target="#modalBox"
            hx-swap="innerHTML"
            onclick="openModal()"
        ''',
    },
]
```

Merged after the target’s `actions` `@cached_property` result.

### `custom_view_type_update`

Adds options to the **view type** `<select>` in `navbar.html`:

```python
custom_view_type_update = {
    "vip_leads": {"name": _("VIP Leads"), "show_list_only": True},
}
```

Merges with the target’s `custom_view_type` dict (including `@cached_property` on `LeadNavbar`).

### `navbar_indication_attrs_update`

Shallow-merge extra HTMX attributes on the back button when `navbar_indication = True` on the target.

### Scalar flags

Set on the extension class body to override the target:

```python
class LeadNavbarExtension(NavExtension):
    _inherit_nav = "horilla_crm.leads.views.core.LeadNavbar"
    enable_quick_filters = True
    filter_option = True
```

---

## Method overrides

Override methods on the extension class; they become mixins on the composed class:

```python
from functools import cached_property
from horilla.urls import reverse_lazy


class LeadNavbarExtension(NavExtension):
    _inherit_nav = "horilla_crm.leads.views.core.LeadNavbar"

    @cached_property
    def new_button(self):
        base = super().new_button
        if base is None:
            return None
        base = dict(base)
        base["url"] = str(reverse_lazy("leads:leads_create")) + "?extended=1"
        return base
```

Use `super()` to preserve core permission checks and URL logic.

---

## Bootstrap and resolution

| When | What runs |
|------|-----------|
| Startup | `bootstrap_extensions()` → `apply_nav_extensions(force=True)` |
| Each navbar HTTP request | `HorillaNavView.as_view()` → `resolve_nav_view_class()` |

Extension apps may load **after** `horilla_crm.*` in `INSTALLED_APPS`.

---

## Navbar vs list vs filter

| Concern | Mechanism | URL (Lead example) |
|---------|-----------|----------------------|
| Top bar (title, view type, search, layout toggles) | `_inherit_nav` on `LeadNavbar` | `leads:leads_nav` |
| Table / kanban content | `_inherit_list` / `_inherit_kanban` on list views | `leads:leads_list`, etc. |
| Filter panel field dropdown | `_inherit_filter` on `LeadFilter` | Used by list view + filter UI |
| Quick filter chips | `exclude_quick_filter_fields_append` on **list** extension | Navbar `enable_quick_filters` |

`column_selector_exclude_fields_append` (nav) ≠ `exclude_append` on filter (filter panel rows).

---

## Non-goals (v1)

- Template / xpath changes to `navbar.html`
- Replacing `nav_url` on `LeadView` from extensions
- DRF / API

See [spec.md](./spec.md).

---

## Debugging

```python
from horilla.extension.nav import (
    get_nav_extensions,
    print_nav_view_mro,
    resolve_nav_view_class,
)
from horilla_crm.leads.views.core import LeadNavbar

print(get_nav_extensions(LeadNavbar))
print_nav_view_mro(LeadNavbar)
composed = resolve_nav_view_class(LeadNavbar)
print(composed.column_selector_exclude_fields)
```

```bash
python manage.py check   # nav_extensions.E001–E004
python manage.py test horilla.extension.nav.tests
```

---

## Full example: Lead navbar

```python
# my_lead_extensions/navbars.py
class LeadNavbarExtension(NavExtension):
    _inherit_nav = "horilla_crm.leads.views.core.LeadNavbar"
    column_selector_exclude_fields_append = ["industry_code"]


# my_lead_extensions/filters.py — filter panel
class LeadFilterExtension(FilterExtension):
    _inherit_filter = "horilla_crm.leads.filters.LeadFilter"
    exclude_append = ["industry_code"]


# my_lead_extensions/lists.py — grid columns
class LeadListExtension(ListExtension):
    _inherit_list = "horilla_crm.leads.views.core.LeadListView"
    columns_insert = [("industry", "industry_code")]
```

---

## See also

- [spec.md](./spec.md)
- [../inherit.md](../inherit.md)
- [../filter/inherit.md](../filter/inherit.md)
