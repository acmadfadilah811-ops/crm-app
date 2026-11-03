"""
Constants for Google Calendar API.

OAuth2 credentials (client_id, client_secret, auth_uri, token_uri) come from the
company-wide GOOGLE_CALENDAR_CLIENT_ID / GOOGLE_CALENDAR_CLIENT_SECRET settings
(set once in .env), so users only click "Connect Google Account". A user can still
upload their own client_secret_*.json in My Settings; that takes priority.
"""

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "openid",
    "email",
]
PRIMARY_CALENDAR_ID = "primary"
