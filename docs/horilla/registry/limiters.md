# Registry Limiters (`limiters.py`)

## Purpose

`horilla/registry/limiters.py` connects registry data to Django field constraints.

It provides a callable used in `limit_choices_to` so ContentType/model selectors only show models registered for a feature key.

## APIs

### `ContentTypeLimiter(feature_key)`

Callable class that builds:

```python
models.Q(model__in=[...])
```

from:

```python
FEATURE_REGISTRY.get(feature_key, [])
```

It also implements `deconstruct()` so Django can serialize it in migrations.

### `limit_content_types(feature_key)`

Helper that returns `ContentTypeLimiter(feature_key)`.

## Usage example

```python
from horilla.registry.limiters import limit_content_types

content_type = models.ForeignKey(
    HorillaContentType,
    on_delete=models.CASCADE,
    limit_choices_to=limit_content_types("review_process_models"),
)
```

This makes the chooser include only models currently registered under `"review_process_models"`.
