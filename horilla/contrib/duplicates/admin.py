"""
Admin registration for the duplicates app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import DuplicateRule, MatchingRule, MatchingRuleCriteria

# Register your duplicates models here.


admin.site.register(MatchingRule)
admin.site.register(DuplicateRule)
admin.site.register(MatchingRuleCriteria)
