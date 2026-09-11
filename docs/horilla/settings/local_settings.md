# `local_settings.py`

## 🎯 Purpose

`horilla/settings/local_settings.py` is intended for **local overrides**.

In your current repo snapshot, this file is empty/placeholder, but the expected pattern is:
- developers customize settings per machine/environment here
- base settings remain in `base.py`

## How it is loaded

`horilla/settings/__init__.py` does:
- `from horilla.settings.base import *`
- `from horilla.settings.local_settings import *`

So anything you define in `local_settings.py` can override variables imported from `base.py`.

## Example override

```python
# horilla/settings/local_settings.py

DEBUG = False
ALLOWED_HOSTS = ["crm.example.com"]
```

---

If you add variables here, ensure they are compatible with what `base.py` expects.
