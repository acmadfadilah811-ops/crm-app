# `password_utils.py`

## 🎯 Purpose

`horilla/settings/password_utils.py` provides helper functions to:
- generate a secure init password (first run)
- store it in a local file: `<project_root>/.init_password`
- read it later so the init password stays stable

This keeps init password logic out of `base.py`.

## Main flow (functions)

### `get_project_root()`

Returns project root directory (where `manage.py` is located) by walking up from this file’s path.

### `get_password_file_path()`

Returns:
- `project_root / ".init_password"`

### `generate_secure_password()`

Creates a cryptographically secure token using:
- `secrets.token_urlsafe(32)`

### `create_password_file()`

Generates a password, writes it to `.init_password`, and applies `0600` permissions when supported.

### `read_password_from_file()`

Reads and returns the password string from `.init_password`.

Returns `None` if the file doesn’t exist or can’t be read.

### `get_or_create_init_password()`

Priority order:
1. `DB_INIT_PASSWORD` environment variable (if set)
2. password from `.init_password` file (if exists)
3. generate a new password and save it

### `get_init_password()`

Convenience alias for `get_or_create_init_password()`.

## Usage example

In your settings:

```python
# horilla/settings/local_settings.py
from horilla.settings.password_utils import get_init_password

DB_INIT_PASSWORD = get_init_password()
```

Now `DB_INIT_PASSWORD` will be consistent:
- uses env var if you set it
- otherwise reads `.init_password` if present
- otherwise generates it once and persists it in the file

## Notes

This utility is designed for *init password* automation, not for runtime password changes.
