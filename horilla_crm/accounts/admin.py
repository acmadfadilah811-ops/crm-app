"""Django admin configuration for accounts app."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from horilla_crm.accounts.models import Account, PartnerAccountRelationship

# Register your accounts models here.
admin.site.register(Account)
admin.site.register(PartnerAccountRelationship)
