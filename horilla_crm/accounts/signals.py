"""Signal handlers for accounts module."""

# Third-party imports (Django)
from django.dispatch import receiver

# First party imports (Horilla)
from horilla.auth.models import User
from horilla.contrib.core.signals import company_currency_changed
from horilla.contrib.keys.models import ShortcutKey
from horilla.contrib.keys.utils import resolve_page_url
from horilla.db.models.signals import post_save

# Local imports
from horilla_crm.accounts.models import Account

# Define your accounts signals here


@receiver(post_save, sender=User)
def create_account_shortcuts(sender, instance, created, **kwargs):
    """Create default keyboard shortcuts for accounts when a user is created."""
    page = resolve_page_url("accounts:accounts_view")
    if not page:
        return

    predefined = [
        {"page": page, "key": "A", "command": "alt"},
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


@receiver(company_currency_changed)
def update_accounts_on_currency_change(sender, **kwargs):
    """
    Update Account currency fields (like annual_revenue) when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    accounts_to_update = []

    # Assuming Account has a ForeignKey to company, else adjust filtering accordingly
    accounts = Account.objects.filter(company=company).only("id", "annual_revenue")

    for account in accounts:
        needs_update = False

        if account.annual_revenue is not None:
            account.annual_revenue *= conversion_rate
            needs_update = True

        if needs_update:
            accounts_to_update.append(account)

    if accounts_to_update:
        Account.objects.bulk_update(
            accounts_to_update, ["annual_revenue"], batch_size=1000
        )
