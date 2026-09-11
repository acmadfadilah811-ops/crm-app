"""Signal handlers for contacts module."""

# Standard library imports
import threading

# Third-party imports (Django)
from django.dispatch import receiver

# First party imports (Horilla)
from horilla.apps import apps
from horilla.auth.models import User
from horilla.contrib.keys.models import ShortcutKey
from horilla.contrib.keys.utils import resolve_page_url
from horilla.db.models.signals import post_save

# Local imports
from horilla_crm.contacts.models import Contact, ContactAccountRelationship

_thread_locals = threading.local()

# Define your contacts signals here


@receiver(post_save, sender=User)
def create_contact_shortcuts(sender, instance, created, **kwargs):
    """Create default keyboard shortcuts for contacts when a user is created."""
    page = resolve_page_url("contacts:contacts_view")
    if not page:
        return

    predefined = [
        {"page": page, "key": "N", "command": "alt"},
    ]

    for item in predefined:
        ShortcutKey.all_objects.get_or_create(
            user=instance,
            key=item["key"],
            command=item["command"],
            defaults={
                "page": item["page"],
                "company": instance.company,
            },
        )


def set_contact_account_id(account_id, company):
    """Store contact_id in thread-local storage"""
    print(f"Setting account_id: {account_id} in thread-local storage")
    _thread_locals.contact_account_id = account_id
    _thread_locals.contact_company = company


def get_and_clear_contact_account_id():
    """Get and clear account_id from thread-local storage"""
    account_id = getattr(_thread_locals, "contact_account_id", None)
    company = getattr(_thread_locals, "contact_company", None)

    if hasattr(_thread_locals, "contact_account_id"):
        delattr(_thread_locals, "contact_account_id")
    if hasattr(_thread_locals, "contact_company"):
        delattr(_thread_locals, "contact_company")

    return account_id, company


@receiver(post_save, sender=Contact)
def create_contact_account_role(sender, instance, created, **kwargs):
    """
    Automatically create ContactAccountRelationship when a Contact is created.
    """
    if created:
        account_id, company = get_and_clear_contact_account_id()
        if account_id is not None:
            Account = apps.get_model("accounts", "Account")
            try:
                account = Account.objects.get(pk=account_id)

                _role, _created_role = ContactAccountRelationship.objects.get_or_create(
                    contact=instance,
                    account=account,
                    company=company or getattr(instance, "company", None),
                )
            except Account.DoesNotExist:
                print(f"Account with id {account_id} does not exist")
