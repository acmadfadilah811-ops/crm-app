# URL filters (`horilla_generics/templatetags/horilla_tags/url_filters.py`)

## Purpose

`url_filters.py` provides template-level URL manipulation helpers.

Currently it contains one focused filter:

- `remove_query_param`

This is useful for building clean navigation/filter-reset links directly in templates without custom view code.

---

## Registered filter

## `remove_query_param(url, param)`

Removes one query parameter from a URL string and returns the updated URL.

Template usage:

```django
{{ request.get_full_path|remove_query_param:"section" }}
```

---

## How it works

Implementation steps:

1. parse URL using `urlparse(url)`
2. parse query dict with:
   - `parse_qs(..., keep_blank_values=True)`
3. remove target key:
   - `query_params.pop(param, None)`
4. rebuild query string using:
   - `urlencode(query_params, doseq=True)`
5. reconstruct final URL with original components via:
   - `urlunparse(parsed_url._replace(query=new_query))`

Result preserves:

- path
- scheme/host (if present)
- fragment (`#...`)
- all non-removed query params

---

## Behavior details

### Removes all values for that key

If parameter appears multiple times:

```text
?field=name&field=email&search=john
```

Removing `field` removes all `field` entries.

### Keeps blank-value params

Because `keep_blank_values=True`, params like `foo=` are retained unless explicitly removed.

### Safe no-op when key missing

If parameter does not exist, URL is returned unchanged.

---

## Practical examples

### Remove a filter key

Input:

```text
/employees/?field=department&operator=exact&value=3&page=2
```

Template:

```django
{{ request.get_full_path|remove_query_param:"page" }}
```

Output:

```text
/employees/?field=department&operator=exact&value=3
```

### Remove search key

```django
{{ request.get_full_path|remove_query_param:"search" }}
```

Useful for "clear search" links while preserving other active filters.

### Preserve fragment/hash

Input:

```text
/list/?section=details#tab2
```

Removing `section` keeps:

```text
/list/#tab2
```

---

## Typical template patterns

```django
<a href="{{ request.get_full_path|remove_query_param:'search' }}">
  Clear Search
</a>
```

```django
<a href="{{ request.get_full_path|remove_query_param:'page' }}">
  Reset Pagination
</a>
```

---

## Caveats

- This filter removes exactly one key per call; chain calls to remove multiple params.
- It does not normalize parameter ordering beyond Python dict/urlencode behavior.
- Expects a URL-like string; non-URL values may produce unexpected parse results.

---

## Summary

`url_filters.py` provides a compact but useful template filter for query-string cleanup. `remove_query_param` helps templates generate cleaner links for resetting specific filter/search/pagination state while preserving the rest of the current URL.
