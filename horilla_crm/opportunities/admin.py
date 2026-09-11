"""Django admin configuration for opportunities app."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from horilla_crm.opportunities.models import (
    DefaultOpportunityMember,
    Opportunity,
    OpportunityContactRole,
    OpportunitySettings,
    OpportunitySplitType,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)

admin.site.register(Opportunity)
admin.site.register(OpportunityStage)
admin.site.register(OpportunityContactRole)
admin.site.register(OpportunityTeamMember)
admin.site.register(DefaultOpportunityMember)
admin.site.register(OpportunityTeam)
admin.site.register(OpportunitySettings)
admin.site.register(OpportunitySplitType)
