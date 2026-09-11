"""URL configuration for the meeting integration app."""

from horilla.urls import path

from . import views

app_name = "meeting"

urlpatterns = [
    # Admin: Settings → Integrations
    path(
        "integration/settings/",
        views.MeetingIntegrationSettingsView.as_view(),
        name="meeting_integration_settings",
    ),
    # Admin: read-only list views for allowed users / roles
    path(
        "integration/allowed-users/",
        views.MeetingAllowedUsersListView.as_view(),
        name="meeting_allowed_users_list",
    ),
    path(
        "integration/allowed-roles/",
        views.MeetingAllowedRolesListView.as_view(),
        name="meeting_allowed_roles_list",
    ),
    # Admin: access edit modals
    path(
        "integration/access-roles/",
        views.MeetingAccessRolesView.as_view(),
        name="meeting_access_roles",
    ),
    path(
        "integration/access-users/",
        views.MeetingAccessUsersView.as_view(),
        name="meeting_access_users",
    ),
    # User: My Settings → Meeting
    path(
        "user/settings/",
        views.MeetingUserSettingsView.as_view(),
        name="meeting_user_settings",
    ),
    # Generate link (called from activity form)
    path(
        "generate-link/",
        views.GenerateMeetingLinkView.as_view(),
        name="generate_meeting_link",
    ),
    # Zoom OAuth
    path("zoom/authorize/", views.ZoomAuthorizeView.as_view(), name="zoom_authorize"),
    path("zoom/callback/", views.ZoomCallbackView.as_view(), name="zoom_callback"),
    # Microsoft Teams OAuth
    path(
        "teams/authorize/", views.TeamsAuthorizeView.as_view(), name="teams_authorize"
    ),
    path("teams/callback/", views.TeamsCallbackView.as_view(), name="teams_callback"),
]
