"""Feature registration for the scoring_rules app."""

from horilla.registry.feature import register_feature

register_feature(
    "scoring",
    "scoring_models",
    include_models=[
        ("leads", "lead"),
        ("opportunities", "opportunity"),
        ("accounts", "account"),
        ("contacts", "contact"),
    ],
)
