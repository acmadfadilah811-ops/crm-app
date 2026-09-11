# Asset template tags (`horilla_generics/templatetags/horilla_tags/asset_tags.py`)
## Purpose
`asset_tags.py` exposes template tags that pull front-end assets from Horilla’s asset registry.
It provides:
- JavaScript asset list loader
- HTML fragment loader by slot/page
This enables pluggable UI extension points where apps can register assets centrally and templates render them dynamically.
---
## Imports and dependencies
This module delegates to:
- `horilla.registry.asset_registry.get_registered_js`
- `horilla.registry.asset_registry.get_registered_html`
It registers template tags using shared package registry:
- `from ._registry import register`
So tags are available through `{% load horilla_tags %}`.
---
## Tag reference
## `load_registered_js` (simple_tag)
Signature:
- `load_registered_js()`
Behavior:
- returns list of registered JS static paths from asset registry.
Intended template use:
- iterate over returned paths and emit `<script src="...">`.
Conceptual example:
```django
{% load horilla_tags %}
{% load_registered_js as js_files %}
{% for js_file in js_files %}
  <script src="{% static js_file %}"></script>
{% endfor %}
```
---
## `load_registered_html` (simple_tag)
Signature:
- `load_registered_html(slot, page="base")`
Parameters:
- `slot`: target insertion region name (for example navbar/footer/sidebar hook)
- `page`: logical page/layout namespace (defaults to `"base"`)
Behavior:
- returns registered HTML fragment references/content for the given slot/page from asset registry.
Intended template use:
- render extension fragments in defined layout hook points.
Conceptual example:
```django
{% load horilla_tags %}
{% load_registered_html "navbar_end" "base" as navbar_fragments %}
{% for fragment in navbar_fragments %}
  {% include fragment %}
{% endfor %}
```
---
## Registry-driven architecture
This module does not hardcode any app-specific asset paths.
Instead, other apps/modules register assets into the central asset registry, and these tags read the aggregated result at render time.
Benefits:
- modular feature injection
- decoupled app-level asset registration
- no template edits required for each new plugin module
---
## Typical flow
1. feature/app registers JS/HTML assets in asset registry
2. base/layout template calls `load_registered_js` and/or `load_registered_html`
3. template renders returned assets in proper hook locations
4. extensions appear automatically when registry entries exist
---
## Error handling notes
`asset_tags.py` itself is intentionally thin and does not wrap calls with try/except.
Validation, deduplication, and fallback behavior are expected to be handled by the underlying asset registry implementation.
---
## Child/template usage patterns
### JS inclusion in base layout
```django
{% load horilla_tags static %}
{% load_registered_js as registered_js %}
{% for path in registered_js %}
  <script src="{% static path %}"></script>
{% endfor %}
```
### Slot-based HTML injection
```django
{% load horilla_tags %}
{% load_registered_html "dashboard_cards" "dashboard" as cards %}
{% for tpl in cards %}
  {% include tpl %}
{% endfor %}
```
### Default page namespace usage
```django
{% load horilla_tags %}
{% load_registered_html "footer_extras" as footer_extras %}
```
Equivalent to page `"base"` when second argument is omitted.
---
## Caveats
- Returned values depend entirely on registry population; empty registry returns empty lists/fragments.
- For JS paths, templates typically need `{% static %}` wrapping unless registry already stores absolute URLs.
- For HTML fragments, ensure included templates are trusted/valid and follow expected context contracts.
---
## Summary
`asset_tags.py` is the template-facing bridge to Horilla’s asset registry. It provides simple tags for loading registered JS paths and slot/page-scoped HTML fragments, enabling modular and scalable asset injection in shared layouts.
