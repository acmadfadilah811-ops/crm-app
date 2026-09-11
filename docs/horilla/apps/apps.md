## 📄 `apps.md` — Horilla App Configuration Guide

````md
# Horilla App Configuration Guide (`apps.py`)

This guide explains how to configure a Horilla app using the `AppLauncher`.

Import it using:

```python
from horilla.apps import AppLauncher
```

For the Django app registry (model lookups in generics, kanban, navbar), use the re-exported registry:

```python
from horilla.apps import apps

Model = apps.get_model("leads", "Lead")
```

This is equivalent to `django.apps.apps` but keeps imports consistent with Horilla contrib modules.`

---

## 🚀 1. Basic App Setup

Every Horilla app should define an `AppConfig` class inheriting from `AppLauncher`.

### Example:

```python
from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _

class MyAppConfig(AppLauncher):
    default = True

    name = "my_app"
    verbose_name = _("My App")
```

---

## 🌐 2. URL Registration

Automatically injects app URLs into the main project.

```python
url_prefix = "my-app/"
url_module = "my_app.urls"
url_namespace = "my_app"
```

### Behavior:

* No need to manually edit `urls.py`
* Automatically attaches to `ROOT_URLCONF`

---

## 📦 3. JavaScript Registration

Register static JS files to load globally.

```python
js_files = [
    "my_app/assets/js/script.js",
]
```

or

```python
js_files = "my_app/assets/js/script.js"
```

### Template Usage:

```
{% load_registered_js as register_js %}
{% for js_file in register_js %}
<script src="{% static js_file %}"></script>
{% endfor %}
```

---

## 🔄 4. Auto Import Modules

Automatically loads modules when the app starts.

```python
auto_import_modules = [
    "registration",
    "signals",
    "menu",
]
```

### Common Uses:

* Register signals
* Load menus
* Initialize background logic

---

## ⏰ 5. Celery Schedule Integration

Merge app schedules into global Celery config.

```python
celery_schedule_module = "celery_schedules"
```

### Example:

```python
# my_app/celery_schedules.py

HORILLA_BEAT_SCHEDULE = {
    "my-task": {
        "task": "my_app.tasks.run_task",
        "schedule": 300.0,
    }
}
```

---

## 📊 6. Demo Data Configuration

Used during initial system setup.

### Example:

```python
demo_data = {
    "files": [
        (1, "load_data/users.json"),
    ],
    "key": "users_count",
    "display_name": _("Users"),
    "order": 1,
}
```

---

### Optional Fields:

```python
demo_data = {
    "files": [(1, "load_data/data.json")],
    "options": [100, 500, 1000],
    "default": 500,
}
```

---

### Multiple Entities:

```python
demo_data = [
    {
        "files": [(1, "load_data/employees.json")],
        "key": "employee_count",
        "display_name": _("Employees"),
        "order": 1,
    },
    {
        "files": [(2, "load_data/projects.json")],
        "key": "project_count",
        "display_name": _("Projects"),
        "order": 2,
    }
]
```

---

## 🔌 7. API Path Registration

Override `get_api_paths()` if your app exposes APIs.

```python
def get_api_paths(self):
    return [
        {
            "pattern": "api/",
            "view_or_include": "my_app.api.urls",
            "name": "my_app_api",
            "namespace": "my_app",
        }
    ]
```

---

## ⚙️ 8. What Happens Automatically

When Horilla starts:

1. `ready()` runs
2. URLs are registered
3. JS files are injected, no manual template updates are required
4. Modules are auto-imported
5. Celery schedules are merged

---

## ⚠️ Best Practices

* Keep `js_files` lightweight
* Avoid unnecessary auto imports
* Use unique `url_prefix`
* Use `demo_data` only for setup flows

---

## ✅ Full Example

```python
from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _

class MyAppConfig(AppLauncher):
    default = True

    name = "my_app"
    verbose_name = _("My App")

    url_prefix = "my-app/"
    url_module = "my_app.urls"
    url_namespace = "my_app"

    js_files = "my_app/assets/js/main.js"

    auto_import_modules = [
        "signals",
        "menu",
    ]

    celery_schedule_module = "celery_schedules"

    demo_data = {
        "files": [(1, "load_data/sample.json")],
        "key": "sample_count",
        "display_name": _("Sample Data"),
        "order": 1,
    }
```

---

## 📌 Summary

| Feature            | Supported |
| ------------------ | --------- |
| Auto URL Injection | ✅         |
| JS Asset Registry  | ✅         |
| Module Auto Import | ✅         |
| Celery Integration | ✅         |
| Demo Data Config   | ✅         |
| API Registration   | ✅         |

---

## 🎯 Goal

Make every Horilla app:

* Plug & play
* Minimal setup
* Fully modular

```
