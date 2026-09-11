"""
Admin registration for the reviews app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local party imports
# Local imports
from .models import (
    ReviewCondition,
    ReviewJob,
    ReviewProcess,
    ReviewRule,
    ReviewRuleCondition,
)

admin.site.register(ReviewProcess)
admin.site.register(ReviewCondition)
admin.site.register(ReviewRuleCondition)
admin.site.register(ReviewJob)


@admin.register(ReviewRule)
class ReviewRuleAdmin(admin.ModelAdmin):
    """Admin configuration for ReviewRule."""

    filter_horizontal = ("approver_users", "approver_roles")
