# Horilla Translation Utilities

## 🎯 Purpose

`horilla/utils/translation/` is a thin wrapper around Django’s translation framework.

It exists to make imports consistent across the codebase:

- instead of `from django.utils.translation import gettext_lazy ...`
- you can use `from horilla.utils.translation import gettext_lazy ...`

In practice, this repo heavily uses the common alias:

```python
from horilla.utils.translation import gettext_lazy as _
```

So your app code can translate strings while keeping one standard import path.

---

## 📦 Module layout

```text
horilla/utils/translation/
└── __init__.py   # re-exports django.utils.translation functions
```

This page is `docs/horilla/utils/translation.md`.

---

## 🔁 What it re-exports

`horilla.utils.translation` re-exports these names from `django.utils.translation`:

- `activate(language)`
- `deactivate()`
- `get_language()`
- `get_language_bidi()`
- `get_language_info(language)`
- `gettext(message)` (immediate translation)
- `gettext_lazy(message)` (lazy translation; safe for model/label definitions)
- `ngettext(singular, plural, number)`
- `ngettext_lazy(singular, plural, number)`
- `npgettext(context, singular, plural, number)`
- `npgettext_lazy(context, singular, plural, number)`
- `override(language)` (context manager)
- `pgettext(context, message)`
- `pgettext_lazy(context, message)`

---

## 🧠 Core concept: `gettext_lazy as _`

Django code typically uses `_` as an alias for translation. This repo follows the same pattern.

`gettext_lazy` is used when you define translatable strings that may be evaluated later (examples: verbose names, menu labels, etc.).

### Example

```python
from horilla.utils.translation import gettext_lazy as _


class MyModel(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name=_("Title"),
    )
```

---

## 🧪 Other common usage patterns

### Immediate translation (`gettext`)

Use `gettext` when you need the translated value immediately (e.g., building a runtime message).

```python
from horilla.utils.translation import gettext as _

message = _("Saved successfully")
```

### Plural forms (`ngettext_lazy`)

```python
from horilla.utils.translation import ngettext_lazy


count_label = ngettext_lazy(
    "1 item",
    "%(count)d items",
    number=5,
)
```

### Override language (`override`)

`override` is a context manager to temporarily switch languages.

```python
from horilla.utils.translation import override


with override("en"):
    text = _("Settings")
```

---

## 📌 When to use which function

- Use `gettext_lazy` / `ngettext_lazy` for strings that are stored on classes/models and evaluated later.
- Use `gettext` / `ngettext` when you need the translated text immediately.
- Use `override(...)` when you need to render content in a different language for a specific request/section.

---

## 🏁 Summary

`horilla.utils.translation` gives a single import location for Django translation utilities.

Most of the time, use:
- `from horilla.utils.translation import gettext_lazy as _`

and treat it exactly like Django’s `gettext_lazy` behavior.
