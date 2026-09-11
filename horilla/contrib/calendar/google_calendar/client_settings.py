"""
Constants for Google Calendar API.

All OAuth2 credentials (client_id, client_secret, auth_uri, token_uri) are
read from each user's GoogleCalendarConfig.credentials_json field — uploaded
by the user in My Settings. No environment variables are required.
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
