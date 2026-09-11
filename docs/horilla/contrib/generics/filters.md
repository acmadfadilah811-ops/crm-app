# Filtering utilities (`horilla_generics/filters.py`)
## Purpose
`horilla_generics/filters.py` defines the generic filtering foundation used by Horilla list/report UIs:
- operator catalog by field type (`OPERATOR_CHOICES`)
- `HorillaFilterSet` with:
- array-based multi-condition filtering (`field[]`, `operator[]`, `value[]`)
- range filtering (`between` with `start_value`/`end_value`)
- robust empty/not-empty semantics
- smart text search (`search`) with optional split-name logic
It is designed for dynamic filter builders where users can compose multiple rules in one request.
---
## Core constants
## `STRING_LIKE_FIELDS`
Tuple of model field classes treated as text-like for "empty" semantics:
- `CharField`
- `TextField`
- `EmailField`
- `URLField`
- `GenericIPAddressField`
- `SlugField`
Why it matters:
- for these fields, `is empty` means:
- `NULL` **or** `""`
- and `is not empty` means:
- not `NULL` **and** not `""`
This matches user expectations for text fields where blank string is common.
---
## `OPERATOR_CHOICES`
Defines allowed operators per abstract field type:
- `text`: `icontains`, `exact`, `ne`, starts/ends with, empty checks
- `number`/`float`/`decimal`: equality/comparisons + `between` + empty checks
- `date`/`datetime`: equality/order + `between` + empty checks
- `boolean`: `exact`
- `choice`: `exact` + empty checks
- `other`: fallback (`exact`, `icontains`, empty checks)
This map is consumed by UI metadata builders and filter execution logic.
---
## `HorillaFilterSet`
Subclass of `django_filters.FilterSet` with custom query parsing and search behavior.
Defined filter:
- `search = CharFilter(method="filter_search")`
---
## `get_operators_for_field(field_type)`
Class method returning operator list from `OPERATOR_CHOICES`.
Fallback:
- returns `"other"` operators when field type key is unknown.
Used by filter UI to populate operator dropdowns dynamically.
---
## `_convert_boolean_value(value, model, field_name)`
Converts string boolean inputs to real booleans for boolean model fields.
Behavior:
- if target field is `BooleanField`:
- `"true"` -> `True`
- `"false"` -> `False`
- otherwise returns original value unchanged.
This prevents mismatches where query params are strings but DB filter expects boolean.
---
## `filter_queryset(queryset)` (main engine)
Overrides default django-filter behavior to support parallel filter arrays.
### High-level pipeline
1. if form cleaned data exists, call `super().filter_queryset(queryset)` first
2. resolve request object
3. read parallel arrays:
- `field[]`
- `operator[]`
- `value[]`
- `start_value[]`
- `end_value[]`
4. iterate each `(field, operator)` pair
5. apply operator-specific queryset mutation
6. apply free-text search (`search`) at end
The loop uses `zip(fields, operators)`, so only aligned index pairs are processed.
---
### Operator semantics in execution
## `ne` (not equals)
- reads `value[i]`
- applies boolean conversion if needed
- executes `queryset.exclude(**{field: value})`
## `between`
Uses index-aligned:
- `start_value[i]`
- `end_value[i]`
Behavior:
- both provided: `field__gte=start` and `field__lte=end`
- only start: `field__gte=start`
- only end: `field__lte=end`
## `isnull`
- for text-like fields: `(field IS NULL) OR (field == "")`
- other fields: `field__isnull=True`
## `isnotnull`
- for text-like fields: `NOT NULL AND != ""`
- other fields: `field__isnull=False`
## generic operators (e.g. `exact`, `icontains`, `gt`)
- reads `value[i]`
- boolean-converts when relevant
- applies dynamic lookup:
- `queryset.filter(**{f"{field}__{operator}": value})`
---
### Error behavior
Per-condition exceptions are caught and logged:
- filtering continues for remaining conditions
- engine favors resilience over hard-fail for one bad clause
This keeps UI usable even with partially invalid query payloads.
---
### Search integration
After condition loop:
- reads `search` from data/GET
- applies `filter_search(...)` if non-empty.
This means search is combined with condition filters in final queryset.
---
## `filter_search(queryset, name, value)`
Search helper with optional smart split-name handling.
Requires:
- `Meta.search_fields` defined on child filterset.
If absent or empty search value:
- returns queryset unchanged.
---
### Name split logic
Reads optional:
- `Meta.name_split_fields`
If missing and both `first_name` + `last_name` exist in `search_fields`, infers:
- `["first_name", "last_name"]`
When search text contains space and split fields are valid:
1. split into first and second parts (`"john doe"` -> `"john"`, `"doe"`)
2. apply full-string `icontains` OR queries to non-name fields
3. apply AND-style name clause:
- `first_name__icontains=first_part`
- `last_name__icontains=second_part`
When no split scenario:
- apply OR `icontains` across all search fields using full value.
Finally:
- `queryset.filter(queries)`
---
## Child class usage examples
## Example 1: minimal filterset
```python
from horilla_generics.filters import HorillaFilterSet
from leads.models import Lead
class LeadFilterSet(HorillaFilterSet):
class Meta:
  model = Lead
  fields = []
  search_fields = ["name", "email", "company__name"]
```
This enables generic condition filtering + search across listed fields.
### Example 2: split full-name search
```python
class EmployeeFilterSet(HorillaFilterSet):
class Meta:
  model = Employee
  fields = []
  search_fields = ["first_name", "last_name", "email"]
  name_split_fields = ["first_name", "last_name"]
```
Search `"jane doe"` matches first/last in split manner while still searching non-name fields.
### Example 3: dynamic UI operators
```python
operators = EmployeeFilterSet.get_operators_for_field("date")
# [("exact","Equals"), ("gt","After"), ("lt","Before"), ...]
```
Used by frontend filter row builders.
---
## Request payload examples (conceptual)
### Multi-condition filter
```text
GET /employees/?apply_filter=true
field=department&operator=exact&value=5
field=is_active&operator=exact&value=true
search=jane
```
Effect:
- department equals 5
- boolean conversion on `is_active`
- plus text search "jane".
### Range filter
```text
GET /leads/?apply_filter=true
field=created_at&operator=between&start_value=2026-01-01&end_value=2026-01-31
```
Effect:
- created_at within inclusive range.
### Empty-string-aware filter
```text
GET /contacts/?apply_filter=true
field=email&operator=isnull
```
Effect for text-like field:
- email is NULL or empty string.
---
## Integration notes
`HorillaFilterSet` is typically paired with:
- `HorillaListFilterFieldsMixin` metadata/UI helpers (`_get_model_fields`, operator/value partial updates),
- list views that pass request/query params into filterset instance,
- quick-filter and saved-filter URL states.
Together they provide a dynamic, operator-driven filtering UX.
---
## Caveats and behavior notes
- parallel arrays rely on index alignment; malformed client payloads can skip intended conditions.
- operator execution trusts field lookup strings from request; invalid lookups are logged and skipped.
- boolean conversion only applies when target model field is actually `BooleanField`.
- search uses `icontains` OR composition (plus special split-name clause) and may be broad on large datasets without indexes.
---
## Summary
`horilla_generics/filters.py` is the core generic filtering engine for Horilla. It standardizes operator choices by field type, executes robust multi-condition filtering with range/empty semantics, and provides smart search behavior that supports both general text queries and full-name split matching.
