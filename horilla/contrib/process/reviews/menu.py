"""Menu registration for the Review Process module."""

# First party imports (Horilla)
# First party imports (Horilla)
from horilla.contrib.process import ProcessSettings
from horilla.menu import MAIN_CONTENT_HX_ATTRS, sub_section_menu
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

process = ProcessSettings()

process.items.extend(
    [
        {
            "label": _("Review Processes"),
            "url": reverse_lazy("reviews:reviews_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#review-process-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "reviews.view_reviewprocess",
            "order": 1,
        },
    ]
)


@sub_section_menu.register
class ReviewJobsSubSection:
    """My Jobs > Review Jobs sidebar link."""

    # Identity / placement
    section = "my_jobs"
    app_label = "reviews"
    position = 1

    # Display
    verbose_name = _("Review Jobs")
    icon = "/assets/icons/review.svg"

    # Behavior
    url = reverse_lazy("reviews:review_job_view")
    attrs = MAIN_CONTENT_HX_ATTRS

    # Access control
    perm = []
