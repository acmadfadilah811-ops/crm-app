# Default dashboard generator guide (`horilla_dashboard/utils.py`)
## What this is
The "default dashboard" on home page is generated dynamically by:
- `DefaultDashboardGenerator` in `horilla_dashboard/utils.py`
- used from `horilla_dashboard/views/home.py`
It is **not** the same as user-created `Dashboard` model layouts.
When user has no explicit default dashboard selected, home page falls back to this generator output.
---
## Core flow
## 1) Home page decides fallback mode
`HomePageView.get()` in `horilla_dashboard/views/home.py`:
1. validates date range params
2. tries `Dashboard.get_default_dashboard(request.user)`
3. if none exists, calls `render_dynamic_default_dashboard()`
That path creates:
```python
generator = DefaultDashboardGenerator(
user,
user_company,
date_range=date_range,
date_from=date_from,
date_to=date_to,
)
```
Then collects:
- `kpi_data = generator.generate_kpi_data()`
- `chart_data = generator.generate_chart_data()`
- `table_data = generator.generate_table_data()`
---
## 2) Generator model registry source
`DefaultDashboardGenerator` reads models from:
```python
DefaultDashboardGenerator.extra_models
```
Each app can append model config dicts into this list.
This is the extension mechanism you mentioned: create app-level `dashboard.py` and append config there.
---
## 3) How app `dashboard.py` files are loaded automatically
Apps based on `AppLauncher` can auto-import modules in `apps.py`:
```python
auto_import_modules = ["registration", "signals", "menu", "dashboard"]
```
During app startup, `AppLauncher.ready()` calls `_auto_import_modules()` and imports:
```python
importlib.import_module(f"{self.name}.{module}")
```
So if your app includes `"dashboard"` in `auto_import_modules`, your `dashboard.py` runs at startup and can register configs.
---
## Required pattern to add a default dashboard component
## Step 1: Create `dashboard.py` inside your app
Example path:
- `your_app/dashboard.py`
## Step 2: Import generator and your model
```python
from horilla_dashboard.utils import DefaultDashboardGenerator
from .models import MyModel
```
## Step 3: Add chart/table helper functions (optional but recommended)
- `chart_func(generator, queryset, model_info)` -> returns chart dict or `None`
- `table_func(generator, model_info)` -> usually calls `generator.build_table_context(...)`
- `table_fields_func(model_class)` -> returns list of columns
## Step 4: Append model config
```python
DefaultDashboardGenerator.extra_models.append({...})
```
## Step 5: Ensure app auto-imports `dashboard`
In your app config:
```python
auto_import_modules = ["registration", "signals", "menu", "dashboard"]
```
Without this, your append code may never run.
---
## Config dictionary contract
Each appended entry generally uses:
- `model` (required): Django model class
- `name` (required): display name for KPI/table/chart titles
- `icon` (required for KPI cards): icon class
- `color` (required for KPI style mapping): keyword (`yellow`, `purple`, etc.)
- `include_kpi` (optional, default `False`): include count KPI card
- `chart_func` (optional): chart generator callback
- `table_func` (optional): table generator callback
- `table_fields_func` (optional): dynamic table column resolver
Minimal example (KPI only):
```python
DefaultDashboardGenerator.extra_models.append(
{
  "model": MyModel,
  "name": "My Items",
  "icon": "fa-cube",
  "color": "blue",
  "include_kpi": True,
}
)
```
---
## How permissions are enforced
Generator checks permissions per model:
- `view_<model>`
- `view_own_<model>`
If user has only `view_own`:
- queryset is filtered by `OWNER_FIELDS` when model defines it
- company scoping applied when model has `company` and user company exists
So components only show data the user is allowed to view.
---
## Date range behavior
Supported ranges:
- `7`, `30`, `60`, `90`
- `custom` (`date_from` / `date_to`)
- `all` / clear values
Date range is applied through `apply_date_range_to_queryset(...)` using first date/datetime field detected by model.
Custom invalid date values are normalized/fallbacked by home view + utility validators.
---
## Real example from `horilla_dashboard` ecosystem (CRM Leads)
Actual registration pattern (from `horilla_crm/leads/dashboard.py`):
```python
DefaultDashboardGenerator.extra_models.append(
{
  "model": Lead,
  "name": "Leads",
  "icon": "fa-user-plus",
  "color": "yellow",
  "include_kpi": True,
  "chart_func": create_lead_charts,
  "table_func": lead_table_func,
  "table_fields_func": lead_table_fields,
}
)
```
What this gives:
- KPI card: total leads
- custom leads chart (from `create_lead_charts`)
- leads table block (from `lead_table_func`)
---
## End-to-end example: add component in your app
```python
# your_app/dashboard.py
from django.db.models import Count
from horilla_dashboard.utils import DefaultDashboardGenerator
from .models import Ticket
def create_ticket_charts(generator, queryset, model_info):
data = queryset.values("priority").annotate(count=Count("id")).order_by("-count")
if not data:
  return None
return {
  "title": "Tickets by Priority",
  "type": "pie",
  "data": {
      "labels": [row["priority"] or "Unknown" for row in data],
      "data": [row["count"] for row in data],
      "labelField": "Priority",
  },
}
def ticket_table_fields(model_class):
return [
  {"name": "title", "verbose_name": "Title"},
  {"name": "priority", "verbose_name": "Priority"},
  {"name": "status", "verbose_name": "Status"},
  {"name": "created_at", "verbose_name": "Created At"},
]
def ticket_table_func(generator, model_info):
return generator.build_table_context(
  model_info=model_info,
  title="Recent Tickets",
  filter_kwargs={},
  no_found_img="assets/img/not-found-list.svg",
  no_record_msg="No tickets found.",
  view_id="tickets_dashboard_list",
)
DefaultDashboardGenerator.extra_models.append(
{
  "model": Ticket,
  "name": "Tickets",
  "icon": "fa-ticket",
  "color": "blue",
  "include_kpi": True,
  "chart_func": create_ticket_charts,
  "table_func": ticket_table_func,
  "table_fields_func": ticket_table_fields,
}
)
```
And in `your_app/apps.py`:
```python
auto_import_modules = ["registration", "signals", "menu", "dashboard"]
```
---
## Common mistakes (and fixes)
- **`dashboard.py` exists but nothing appears**
- Add `"dashboard"` in app `auto_import_modules`.
- **KPI missing but chart/table showing**
- Set `"include_kpi": True`.
- **No data visible**
- Check user has `view_*` or `view_own_*` permissions.
- Check `OWNER_FIELDS` is correct if relying on own-view permissions.
- **Chart/table function errors hidden**
- Generator catches exceptions and logs warnings; check server logs.
- **Wrong date filtering**
- Ensure model has a usable `DateField`/`DateTimeField`.
---
## Notes about ordering/layout
Generated blocks are later arranged in home view:
- KPIs sorted by title
- charts/tables interleaved (roughly two charts then one table)
- optional user-specific default-home layout order can override display sequence
So registration order in `extra_models` is not the only ordering influence.
---
## Summary
To add a component to the default dynamic dashboard:
1. create `dashboard.py` in your app,
2. append a config dict to `DefaultDashboardGenerator.extra_models`,
3. implement optional `chart_func` / `table_func` / `table_fields_func`,
4. ensure app config auto-imports `"dashboard"`.
This is the canonical extension mechanism used in the CRM apps (Leads, Opportunities, Contacts, Accounts, Campaigns).
