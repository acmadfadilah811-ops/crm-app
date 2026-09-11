# History display filters (`horilla_generics/templatetags/horilla_tags/history_display.py`)
## Purpose
`history_display.py` provides template filters that clean up and enrich audit/history log presentation.
It focuses on:
- collapsing noisy create+update combinations,
- fixing M2M change rendering artifacts,
- generating human-friendly labels for mail/activity create events,
- providing activity create details for UI display.
This module is especially useful when rendering `auditlog.models.LogEntry` histories in timelines or detail tabs.
---
## Registered filters
This module registers:
- `collapse_redundant_history`
- `history_changes_display`
- `mail_create_display`
- `activity_create_display`
- `activity_create_details`
It also includes internal helpers used by these filters.
---
## Redundant history collapsing
## `_is_redundant_history_entry(entry, same_group_entries)` (internal)
Returns `True` for update entries that should be hidden when:
- entry action is `UPDATE`,
- same group contains a `CREATE` entry
- for the same `content_type` and same object PK.
Goal:
- collapse "created + immediate updates" noise into one logical entry.
---
## `collapse_redundant_history(entries)`
Template filter that removes entries identified as redundant by helper above.
Usage:
```django
{% for entry in entries|collapse_redundant_history %}
  ...
{% endfor %}
```
Behavior:
- returns original input if empty/falsy,
- otherwise list-comprehension filtered set.
---
## Label maps used by activity/mail filters
## `ACTIVITY_TYPE_ADDED_LABELS`
Maps Activity `activity_type` value -> display label:
- `task` -> "Task added"
- `event` -> "Event added"
- `meeting` -> "Meeting added"
- `log_call` -> "Call added"
## `MAIL_STATUS_CREATE_LABELS`
Maps mail status -> create label:
- `sent` -> "Email sent"
- `draft` -> "Draft saved"
- `scheduled` -> "Scheduled mail"
- `failed` -> "Mail failed"
These maps are localized via `_()`.
---
## M2M-friendly change display
## `history_changes_display(entry)`
Returns a display-safe changes dictionary for log entry rendering.
Why needed:
- auditlog M2M payloads are structured dicts (type/operation/objects),
- default `changes_display_dict` can show misleading `type -> operation` entries.
What this filter does:
1. starts from `entry.changes_display_dict` and `entry.changes_dict`
2. for each M2M change:
   - resolves human field verbose name (via model metadata when possible),
   - reads operation (`add`, `delete`, others),
   - joins object labels,
   - creates display string:
     - `"Added: A, B"` or `"Removed: X"`
   - writes normalized entry as `["--", display]`
3. removes bogus artifacts where value looked like `["type", "operation"]`
4. returns cleaned result dict.
This yields much clearer change rows in templates.
---
## Activity helper internals
## `_get_activity_type_from_entry(entry)` (internal)
Returns activity type string for Activity log entries or `None`.
Resolution order:
1. verify entry content type model name is `Activity`
2. try `entry.serialized_data["fields"]["activity_type"]`
3. fallback: query Activity row by `object_pk/object_id`
Valid values constrained by `ACTIVITY_TYPE_ADDED_LABELS` keys.
---
## `_get_activity_from_entry(entry)` (internal)
Returns the `Activity` model instance for an Activity log entry by object pk, else `None`.
Used by detailed activity display filter.
---
## Mail create label helper
## `_get_mail_create_label(entry)` (internal)
Returns create label for entries where:
- action is `CREATE`,
- model contains `mail_status` field.
Flow:
1. detect model from content type
2. ensure `mail_status` field exists
3. load object by entry pk
4. map status via `MAIL_STATUS_CREATE_LABELS`
Returns empty string when not applicable.
---
## Mail/activity registered filters
## `mail_create_display(entry)`
Wrapper over `_get_mail_create_label`.
Used in history templates to show:
- Email sent / Draft saved / Scheduled mail / Mail failed
for create events of mail-status models.
---
## `activity_create_display(entry)`
For Activity `CREATE` entries:
- returns type label from `ACTIVITY_TYPE_ADDED_LABELS`
- e.g. Task/Event/Meeting/Call added
Returns empty string for non-Activity or non-create entries.
---
## `activity_create_details(entry)`
Returns structured details dict for Activity `CREATE` entries:
```python
{
  "type_label": "Task added",
  "status": "Completed"
}
```
Behavior:
1. ensure create action,
2. load activity object,
3. validate activity type in mapping,
4. resolve status label:
   - from `STATUS_CHOICES` when available
   - fallback raw status or `"--"`,
5. return dict.
Returns `None` for non-matching entries.
---
## Template usage examples
### Collapse redundant create/update noise
```django
{% for entry in entries|collapse_redundant_history %}
  ...
{% endfor %}
```
### Safe changes rendering (including M2M)
```django
{% with changes=entry|history_changes_display %}
  {% for field, pair in changes.items %}
    <li>{{ field }}: {{ pair.1 }}</li>
  {% endfor %}
{% endwith %}
```
### Mail/activity create labels
```django
{{ entry|mail_create_display }}
{{ entry|activity_create_display }}
```
### Activity details payload
```django
{% with info=entry|activity_create_details %}
  {% if info %}
    {{ info.type_label }} ({{ info.status }})
  {% endif %}
{% endwith %}
```
---
## Error handling model
- Most helpers are defensive: broad exceptions return safe defaults (`""`, `None`, unchanged structures).
- Filters avoid hard failures during template rendering even for missing content types/objects.
- This is intentional for robust history views across heterogeneous models.
---
## Caveats
- Redundancy collapse checks within provided group only; grouping correctness depends on caller context.
- Activity model detection currently relies on model name `"Activity"` string match.
- Filters may perform DB lookups per entry (mail/activity helpers); large history lists may benefit from prefetch/optimization at view layer.
---
## Summary
`history_display.py` is the presentation-normalization layer for Horilla audit history. It reduces redundant noise, fixes M2M change display quality, and adds semantic labels/details for mail and activity create events so history timelines are clearer and more meaningful to users.
