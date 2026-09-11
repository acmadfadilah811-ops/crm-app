# Permission template tags (`horilla_generics/templatetags/horilla_tags/permission_tags.py`)

## Purpose

`permission_tags.py` provides template-level permission helpers for:

- direct permission checks
- superuser-aware permission evaluation with flexible input formats
- section/menu visibility URL resolution based on permissions

These tags/filters reduce repetitive `user.has_perm(...)` logic in templates and help drive permission-aware navigation.

---

## Registered APIs

This module exposes:

- simple tag: `has_perm`
- filter: `has_super_user`
- simple tag: `has_section_perm_url`

All available through:

```django
{% load horilla_tags %}
```

---

## `has_perm` (simple_tag, takes context)

Signature:

- `has_perm(context, perm_name)`

Behavior:

- reads `context["request"].user`
- returns `user.has_perm(perm_name)`

Usage:

```django
{% has_perm "horilla_core.view_horillauser" as can_view_horillauser %}
{% if can_view_horillauser %}
  ...
{% endif %}
```

Use when template already has request context and you want one explicit permission check.

---

## `has_super_user` (filter)

Signature:

- `has_super_user(user, perm_data)`

Purpose:

- returns `True` when user is superuser or permission conditions are met.

Authentication guard:

- unauthenticated/missing user -> `False`

Superuser guard:

- `user.is_superuser` -> `True` immediately

### Accepted `perm_data` formats

1. **string**
   - one permission codename
   - result: `user.has_perm(perm)`

2. **list/tuple**
   - permission set
   - result: OR semantics (`any(...)`)

3. **dict**
   - format:
     - `{"perms": [...], "all_perms": True/False}`
   - when `all_perms=True`: AND semantics (`all(...)`)
   - otherwise OR semantics (`any(...)`)
   - if `perms` empty: returns `True`

Fallback for unsupported type:

- `False`

### Template examples

```django
{{ request.user|has_super_user:"crm.view_lead" }}
{{ request.user|has_super_user:perm_list }}
{{ request.user|has_super_user:perm_config }}
```

Where `perm_config` can be:

```python
{"perms": ["crm.view_lead", "crm.change_lead"], "all_perms": True}
```

---

## `has_section_perm_url` (simple_tag)

Signature:

- `has_section_perm_url(user, section_name)`

Purpose:

- checks whether user can access at least one sub-item in a menu section,
- returns the first accessible URL for that section,
- used for permission-aware section entry points.

Data source:

- `get_sub_section_menu()` from `horilla.menu.sub_section_menu`

Expected item structure in section list:

- `{"url": "...", "perm": {"perms": [...], "all_perms": bool}}`

### Return behavior

- unauthenticated user -> `False`
- section missing/empty items -> `"/"` (fallback root)
- item with no `perm` or empty perms -> returns item URL
- permissioned item:
  - AND semantics when `all_perms=True`
  - OR semantics otherwise
- if none matched -> `False`

### Template example

```django
{% has_section_perm_url request.user "recruitment" as section_url %}
{% if section_url %}
  <a href="{{ section_url }}">Recruitment</a>
{% endif %}
```

---

## How this module fits navigation flow

Typical usage pattern:

1. use `has_super_user` for small inline permission checks
2. use `has_perm` when you need exact codename check with context
3. use `has_section_perm_url` to render section-level links only when at least one child item is allowed

This supports progressive menu rendering from coarse section access to fine-grained action visibility.

---

## Caveats and notes

- `has_perm` expects `request` in template context; missing request would raise template error upstream.
- `has_section_perm_url` returns mixed types (`str` URL, `False` boolean); templates should treat truthy/falsey carefully.
- For empty section config, returning `"/"` is intentional fallback but may not suit all projects.
- Dict mode in `has_super_user` treats missing/empty `perms` as `True`; ensure caller data is intentional.

---

## Summary

`permission_tags.py` provides concise, reusable permission helpers for Horilla templates. It supports direct checks, superuser-aware multi-permission logic, and section-level menu URL resolution based on first accessible sub-item permissions, enabling cleaner permission-driven UI rendering.
