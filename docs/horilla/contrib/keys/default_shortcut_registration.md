# Default shortcut registration guide (`signals.py` in each app)

## What this is

Default keyboard shortcuts are created automatically through Django `post_save` signals on `User`.

The pattern is:

- base/global shortcuts are added in `horilla_keys/signals.py`
- app-specific shortcuts are added in each app's own `signals.py`
- those signal modules are auto-imported at startup by each app config (`AppLauncher`)

So the extension mechanism is exactly what you described: **add shortcut registration logic in your app's `signals.py`**.

---

## Core flow

## 1) User is created

When a `User` row is inserted, every connected `@receiver(post_save, sender=User)` runs.

This includes:

- `create_all_default_shortcuts` from `horilla_keys/signals.py`
- any app-level shortcut creators like:
  - `create_dashboard_shortcuts`
  - `create_report_shortcuts`
  - `create_calendar_shortcuts`
  - `create_leads_shortcuts`
  - etc.

Because all of them listen to the same signal, shortcuts from multiple apps are populated in one user-creation flow.

---

## 2) Why app signals are discovered

Each app config inherits from `AppLauncher` and usually contains:

```python
auto_import_modules = ["registration", "signals", "menu"]
```

In startup (`AppLauncher.ready()`), `_auto_import_modules()` imports each listed module:

```python
importlib.import_module(f"{self.name}.{module}")
```

That import executes your `signals.py`, which registers your receiver function.

If `"signals"` is missing from `auto_import_modules`, your default shortcuts will not be registered.

---

## 3) Database uniqueness behavior

`ShortcutKey` model has:

```python
unique_together = ("user", "key", "command")
```

Important effect:

- for one user, each key+modifier combo can exist only once
- if two apps try to assign same combo (example `alt + D`), one will conflict
- this is why most app signal handlers use `get_or_create(...)` or bulk insert with conflict ignore

---

## Existing patterns in codebase

## A) Global/base shortcuts (`horilla_keys/signals.py`)

This module builds a list and uses one bulk insert:

- creates common shortcuts like home/profile/users/branches
- uses `bulk_create(..., ignore_conflicts=True)` for efficiency and conflict tolerance

Best for: multiple static records from one place.

## B) App-level shortcuts (`<app>/signals.py`)

Most apps define:

1. a `predefined` list
2. loop items
3. `ShortcutKey.all_objects.get_or_create(...)`

This makes app registration idempotent and safe if signal fires more than once.

---

## Required pattern for adding shortcuts from an app

## Step 1: ensure app auto-imports `signals`

In your app config (`apps.py`):

```python
auto_import_modules = ["registration", "signals", "menu"]
```

(Include additional modules if needed, but keep `"signals"` present.)

## Step 2: add receiver in `signals.py`

Create or update: `your_app/signals.py`

```python
from horilla.db.models.signals import post_save
from django.dispatch import receiver

from horilla.auth.models import User
from horilla.urls import reverse_lazy
from horilla_keys.models import ShortcutKey


@receiver(post_save, sender=User)
def create_your_app_shortcuts(sender, instance, created, **kwargs):
    # Recommended guard: only populate defaults on user creation.
    if not created:
        return

    predefined = [
        {
            "page": str(reverse_lazy("your_app:list_view")),
            "key": "T",
            "command": "alt",
        },
        {
            "page": str(reverse_lazy("your_app:board_view")),
            "key": "Y",
            "command": "alt",
        },
    ]

    for item in predefined:
        ShortcutKey.all_objects.get_or_create(
            user=instance,
            key=item["key"],
            command=item["command"],
            defaults={
                "page": item["page"],
                "company": instance.company,
            },
        )
```

## Step 3: choose unique key combinations

Before finalizing new defaults:

- check already-used defaults across apps
- avoid collisions for the same `(key, command)`
- keep shortcuts intuitive by module (example reports `R`, campaigns `C`)

---

## Recommended conventions

- Use `reverse_lazy("namespace:view_name")` (not hard-coded URLs) where possible.
- Always include `company=instance.company` in defaults.
- Add `if not created: return` to prevent unnecessary checks on user updates.
- Keep one small `predefined` list per app for readability.
- Use `get_or_create` for idempotency, unless you intentionally batch with `bulk_create`.

---

## End-to-end example (new app)

Suppose you add app `horilla_helpdesk` and want default shortcuts.

### `horilla_helpdesk/apps.py`

```python
from horilla.apps import AppLauncher


class HelpdeskConfig(AppLauncher):
    name = "horilla_helpdesk"
    auto_import_modules = ["registration", "signals", "menu"]
```

### `horilla_helpdesk/signals.py`

```python
from horilla.db.models.signals import post_save
from django.dispatch import receiver

from horilla.auth.models import User
from horilla.urls import reverse_lazy
from horilla_keys.models import ShortcutKey


@receiver(post_save, sender=User)
def create_helpdesk_shortcuts(sender, instance, created, **kwargs):
    if not created:
        return

    predefined = [
        {"page": str(reverse_lazy("helpdesk:ticket_list")), "key": "T", "command": "alt"},
        {"page": str(reverse_lazy("helpdesk:team_board")), "key": "J", "command": "alt"},
    ]

    for item in predefined:
        ShortcutKey.all_objects.get_or_create(
            user=instance,
            key=item["key"],
            command=item["command"],
            defaults={"page": item["page"], "company": instance.company},
        )
```

Result:

- every newly created user receives helpdesk shortcuts
- existing users are unaffected unless you run a separate migration/backfill command

---

## Existing user backfill (important)

Signals only apply at user creation time.

If you add new default shortcuts later, existing users will not receive them automatically.
Use one of these approaches:

- management command that loops users and runs `get_or_create`
- data migration for controlled rollout
- one-time admin action

Keep same idempotent logic so reruns are safe.

---

## Troubleshooting checklist

- `signals.py` not running:
  - confirm app config extends `AppLauncher`
  - confirm `"signals"` exists in `auto_import_modules`
  - confirm app is installed in settings
- shortcut not created:
  - verify no `(user, key, command)` collision
  - verify URL name in `reverse_lazy(...)` is valid
  - verify `instance.company` is available at user creation
- duplicate/extra operations:
  - add `if not created: return`
  - keep logic idempotent with `get_or_create`

---

## Summary

To add default shortcuts from any app:

1. register a `post_save(User)` receiver in that app's `signals.py`,
2. create `ShortcutKey` rows using idempotent logic (`get_or_create`),
3. ensure app config auto-imports `"signals"` so receiver is loaded.

This is the same extension architecture already used across dashboard, reports, calendar, CRM modules, and other apps.
