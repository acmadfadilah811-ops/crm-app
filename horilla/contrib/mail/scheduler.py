"""
mail scheduler module"""

# Standard library imports
import logging
import sys

# Third-party imports (Django)
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def refresh_outlook_auth_token():
    """
    scheduler method to refresh token
    """
    # Local imports
    from .models import HorillaMailConfiguration
    from .views.outlook import refresh_outlook_token

    apis = HorillaMailConfiguration.objects.filter(token__isnull=False, type="outlook")
    for api in apis:
        try:
            refresh_outlook_token(api)
            logger.info("Updated token for %s outlook ", api)
        except Exception as e:
            logger.error("Error in refresh outlook token: %s", e)


if not any(
    cmd in sys.argv
    for cmd in ["makemigrations", "migrate", "compilemessages", "flush", "shell"]
):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        refresh_outlook_auth_token,
        "interval",
        minutes=50,
        id="refresh_outlook_auth_token",
    )
    scheduler.start()
