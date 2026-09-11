"""Django admin configuration for contacts app."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import Contact, ContactAccountRelationship

admin.site.register(Contact)
admin.site.register(ContactAccountRelationship)
