"""
URLs for the theme app
"""

# Third-party imports (Django)
from horilla.urls import path

# Local imports
from . import views

app_name = "theme"

urlpatterns = [
    # Define your URL patterns here
    path("color-theme-view/", views.ThemeView.as_view(), name="color_theme_view"),
    path("change-theme/", views.ChangeThemeView.as_view(), name="change_theme"),
    path("set-default/", views.SetDefaultThemeView.as_view(), name="set_default_theme"),
]
