"""Admin configuration for the Campaign module."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import Campaign, CampaignMember

# Register your campaigns models here.

admin.site.register(Campaign)
admin.site.register(CampaignMember)
