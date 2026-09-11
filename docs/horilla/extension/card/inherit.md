# Horilla `_inherit_card` — Card View Extension Guide

> **Status:** Implemented (`horilla/extension/card/`)
> **Spec:** [spec.md](./spec.md)
> **Related:** [List `_inherit_list`](../list/inherit.md) · [Kanban `_inherit_kanban`](../kanban/inherit.md)

Extend existing `HorillaCardView` subclasses (`LeadCardView`, `ContactCardView`, etc.) **without** editing core CRM card view classes.

---

## Table of contents

1. [Problem](#problem)
2. [Solution overview](#solution-overview)
3. [Quick start](#quick-start)
4. [Rules](#rules)
5. [Layout hooks](#layout-hooks)
6. [List vs card extensions](#list-vs-card-extensions)
7. [Bootstrap and resolution](#bootstrap-and-resolution)
8. [Non-goals (v1)](#non-goals-v1)
9. [Debugging](#debugging)
10. [Full example: Lead card + `industry_code`](#full-example-lead-card--industry_code)

---

## Problem

CRM modules expose a **card layout** on a separate URL from the table list:

| View | URL name (Lead) | Class |
|------|-----------------|-------|
| Table list | `leads:leads_list` | `LeadListView` |
| Card grid | `leads:leads_card` | `LeadCardView` |

`HorillaCardView` subclasses `HorillaListView` and uses the same `columns` list to render `partials/card_view_cards.html`, but:

- Core `LeadCardView` defines its **own** `columns` (often shorter than the list).
- `_inherit_list` on `LeadListView` does **not** automatically apply to `LeadCardView`.
- Card defaults differ (`paginate_by=24`, `bulk_select_option=False`).

`_inherit_card` targets the card view class directly.

---

## Solution overview

```text
my_lead_extensions/cards.py
    LeadCardExtension  (_inherit_card = "...LeadCardView")
              │
              ▼
    CARD_EXTENSION_REGISTRY → LeadCardViewExtended
              │
              ▼
    leads:leads_card  →  card_view.html
```

Navbar layout toggle (`layout=card`) loads this URL via `LeadNavbar.card_url`.

---

## Quick start

```python
# my_lead_extensions/cards.py
from horilla.extension.card import CardExtension


class LeadCardExtension(CardExtension):
    _inherit_card = "horilla_crm.leads.views.core.LeadCardView"

    columns_insert = [
        ("lead_source", "industry_code"),
    ]
```

```python
# my_lead_extensions/apps.py
auto_import_modules = [
    # ...
    "lists",   # LeadListView
    "cards",   # LeadCardView — required
    "kanbans",
]
```

Restart the dev server after changes.

---

## Rules

| Rule | Detail |
|------|--------|
| Target | Concrete `HorillaCardView` subclass path |
| Base class | `CardExtension`, not `LeadCardView` |
| Do not instantiate | Registration-only |
| Priority | `_inherit_card_priority` |
| Column keys | ORM field names used in `columns` (same as list) |

---

## Layout hooks

Same hooks as [list/inherit.md](../list/inherit.md#layout-hooks-class-attributes):

```python
class LeadCardExtension(CardExtension):
    _inherit_card = "horilla_crm.leads.views.core.LeadCardView"

    columns_insert = [("email", "industry_code")]
    columns_append = []
    actions_append = []  # card row actions if defined on view
    paginate_by = 24     # scalar override (optional)
```

### How `columns` render on cards

`card_view_cards.html` uses the first column for the card title link and additional columns for subtitle lines. Insert anchors relative to existing card columns (see core `LeadCardView.columns`).

---

## List vs card extensions

| Goal | Register on |
|------|-------------|
| Table list only | `_inherit_list` → `LeadListView` |
| Card grid only | `_inherit_card` → `LeadCardView` |
| Both layouts | **Both** extensions (duplicate `columns_insert` is OK) |

```python
# lists.py
class LeadListExtension(ListExtension):
    _inherit_list = "horilla_crm.leads.views.core.LeadListView"
    columns_insert = [("industry", "industry_code")]

# cards.py
class LeadCardExtension(CardExtension):
    _inherit_card = "horilla_crm.leads.views.core.LeadCardView"
    columns_insert = [("lead_source", "industry_code")]
```

---

## Bootstrap and resolution

| When | What |
|------|------|
| Startup | `apply_card_extensions(force=True)` |
| Each card request | `HorillaListView.as_view()` → `resolve_card_view_class()` |

Extension apps may load after CRM in `INSTALLED_APPS`.

---

## Non-goals (v1)

- One registration covering list + card (use two targets)
- Replacing `card_view.html` from extensions
- Auto-sync list columns into card columns

See [spec.md](./spec.md).

---

## Debugging

```python
from horilla.extension.card import (
    get_card_extensions,
    print_card_view_mro,
    resolve_card_view_class,
)
from horilla_crm.leads.views.core import LeadCardView

print(get_card_extensions(LeadCardView))
composed = resolve_card_view_class(LeadCardView)
print(composed.columns)
```

```bash
python manage.py test horilla.extension.card.tests
```

---

## Full example: Lead card + `industry_code`

```python
# models.py — _inherit adds industry_code
# forms.py, filters.py, lists.py, navbars.py — other layers
# cards.py
class LeadCardExtension(CardExtension):
    _inherit_card = "horilla_crm.leads.views.core.LeadCardView"
    columns_insert = [("lead_source", "industry_code")]
```

Open Leads → switch layout to **Card** in the navbar → `industry_code` appears on tiles when composed.

---

## See also

- [spec.md](./spec.md)
- [../inherit.md](../inherit.md)
- [../list/inherit.md](../list/inherit.md)
