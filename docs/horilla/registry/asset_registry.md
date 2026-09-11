# Asset Registry (`asset_registry.py`)

## Purpose

`horilla/registry/asset_registry.py` lets apps register:

- JavaScript static paths
- HTML template fragments for layout slots

Templates later fetch these via template tags and inject them in deterministic order.

## Core APIs

### `register_js(static_paths)`

Registers JS file paths into `REGISTERED_JS_FILES`.

Accepts:
- single string
- list/tuple of strings

Behavior:
- Deduplicates paths (same file is not added twice)
- Stores static-relative paths like `assets/js/my_feature.js`

### `get_registered_js()`

Returns all registered JS paths.

---

### `register_html(template_path, slot, priority=50, page="base")`

Registers one HTML fragment template into a specific slot.

Allowed slots:
- `head_start`
- `head_end`
- `body_start`
- `body_end`

Behavior:
- Validates slot name
- Deduplicates by `(template_path, slot, page)`
- Lower `priority` renders earlier
- Supports page filtering via `page` (e.g. `"base"`, `"login"`, or `"*"`)

### `get_registered_html(slot, page="base")`

Returns template paths for a slot/page, sorted by priority.

---

## How It Connects To `templates/index.html`

`index.html` uses template tags from `horilla_generics`:

- `{% load_registered_html "head_start" as head_start_html %}`
- `{% load_registered_html "head_end" as head_end_html %}`
- `{% load_registered_html "body_start" as body_start_html %}`
- `{% load_registered_js as register_js %}`
- `{% load_registered_html "body_end" as body_end_html %}`

Then it includes them:

- HTML fragments: `{% for tpl in ... %}{% include tpl %}{% endfor %}`
- JS files: `{% for js_file in register_js %}<script src="{% static js_file %}"></script>{% endfor %}`

So:
- `register_html(...)` controls where fragment templates are injected in `index.html`.
- `register_js(...)` controls extra JS files loaded near the end of `index.html`.

---

## Practical Usage (in app `registration.py`)

### Register JS

```python
from horilla.registry.asset_registry import register_js

register_js("assets/js/my_feature.js")
register_js(["assets/js/a.js", "assets/js/b.js"])
```

These files are rendered in `index.html` at the dynamic JS section:

```django
{% load_registered_js as register_js %}
{% for js_file in register_js %}
  <script src="{% static js_file %}"></script>
{% endfor %}
```

### Register HTML slot fragments

```python
from horilla.registry.asset_registry import register_html

# Add CSP/meta/setup before core scripts
register_html(
    template_path="my_app/slots/security_meta.html",
    slot="head_start",
    priority=10,
    page="base",
)

# Add extra script/config just before </head>
register_html(
    template_path="my_app/slots/tailwind_dynamic_config.html",
    slot="head_end",
    priority=20,
    page="base",
)

# Add body bootstrap markup right after <body>
register_html(
    template_path="my_app/slots/body_bootstrap.html",
    slot="body_start",
    priority=30,
    page="base",
)

# Add deferred scripts before </body>
register_html(
    template_path="my_app/slots/deferred_handlers.html",
    slot="body_end",
    priority=90,
    page="base",
)
```

These fragments are injected in `index.html` at matching slot blocks (`head_start`, `head_end`, `body_start`, `body_end`).

---

## Template Tags Used

`horilla_generics` template tags expose:
- `load_registered_js`
- `load_registered_html`

---

## Notes / Best Practices

- Use `register_js` for standalone JS static files.
- Use `register_html` when you need exact placement in layout (`head_*`/`body_*`).
- Keep priorities small and intentional (e.g., `10`, `20`, `50`, `90`) for predictable order.
- Use `page="*"` when a fragment should appear on all page variants; otherwise keep page-specific values.
