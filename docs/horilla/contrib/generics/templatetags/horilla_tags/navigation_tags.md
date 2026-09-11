# Navigation template tags (`horilla_generics/templatetags/horilla_tags/navigation_tags.py`)

## Purpose

`navigation_tags.py` provides lightweight template tags for navigation state handling:

- injecting dynamic data into template context
- marking nav items as active
- marking menu groups as open
- rotating collapse indicators for active groups

These tags are used to keep sidebar/top-nav templates clean and avoid repeated request-path/view-name checks.

---

## Registered tags

This module registers four `simple_tag(takes_context=True)` tags:

- `unpack_context`
- `is_active`
- `is_open`
- `is_open_collapse`

All are available via:

```django
{% load horilla_tags %}
```

---

## `unpack_context(context, data_dict)`

Adds each key/value from `data_dict` into current template context.

Behavior:

- only acts when `data_dict` is a dict
- mutates `context` in place
- returns empty string (for tag-call compatibility in templates)

Use case:

- flatten nested data structure into direct template variables.

Example:

```django
{% unpack_context menu_item.extra_context %}
```

---

## `is_active(context, *url_names)`

Returns:

- `"text-primary-600"` when current request matches
- `""` otherwise

Matching targets:

- current view name (`request.resolver_match.view_name`)
- current path (`request.path`)

Accepted arguments:

- strings
- lists/tuples of strings

Use case:

- apply active text color/style class for current menu item.

Example:

```django
<a class="{% is_active 'crm:lead-list' %}">Leads</a>
<a class="{% is_active item.active_urls %}">Menu</a>
```

---

## `is_open(context, *url_names)`

Returns:

- `"open"` if current route matches
- `""` otherwise

Accepted argument forms:

- strings (view names or path strings)
- dicts containing `url`
- lists/tuples with mixed supported forms

Normalization details:

- dict `url` values are `rstrip("/")`-normalized
- current path is matched with trailing slash removed

Use case:

- keep parent accordion/menu section expanded when child route is active.

Example:

```django
<div class="submenu {% is_open section.urls %}">
```

---

## `is_open_collapse(context, *url_names)`

Returns:

- `"rotate-90"` when current route is inside provided set
- `""` otherwise

Designed for:

- collapse-arrow icon rotation in active/open navigation groups.

Accepted forms:

- strings
- lists/tuples of dict entries with `url`

Matching behavior:

- compares against current view name and full current path.

Example:

```django
<i class="arrow {% is_open_collapse section.urls %}"></i>
```

---

## Input shapes and matching summary

### View/path source

All state tags rely on:

- `request.resolver_match.view_name`
- `request.path`

If request or resolver match missing:

- tags return empty string safely.

### Differences between tags

- `is_active`:
  - returns styling class `"text-primary-600"`
  - simple list/string flattening
- `is_open`:
  - richer normalization (dict/list/tuple support + path rstrip)
  - returns `"open"`
- `is_open_collapse`:
  - focused on collapse indicator class
  - returns `"rotate-90"`

---

## Practical template patterns

### Active link class

```django
<a class="menu-link {% is_active 'sales:opportunity-list' %}">
  Opportunities
</a>
```

### Open parent section

```django
<li class="menu-group {% is_open item.children %}">
```

### Rotate arrow icon when open

```django
<span class="chevron {% is_open_collapse item.children %}"></span>
```

### Unpack extra metadata

```django
{% unpack_context item.meta %}
{{ badge_text }}
```

---

## Design notes

- Tags return class strings (not booleans), making direct class interpolation easy.
- Helpers are defensive: they fail to empty-string rather than breaking template render.
- Mixed argument support in `is_open`/`is_open_collapse` fits dynamic menu config structures often stored as dict/list objects.

---

## Caveats

- Returned class names are framework/style-specific (`text-primary-600`, `open`, `rotate-90`); adjust tags if your CSS system changes.
- Matching mixes view names and URL paths; ensure menu config values are consistent with route naming strategy.
- `unpack_context` mutates context directly; avoid key collisions with existing template variables.

---

## Summary

`navigation_tags.py` provides reusable navigation-state tags for Horilla templates. It standardizes active/open/collapse class logic using request route context and supports flexible menu data structures, making dynamic navigation templates simpler and more maintainable.
