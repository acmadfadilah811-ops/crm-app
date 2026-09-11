"""Forms for creating and validating `horilla.contrib.reports` models (Report, ReportFolder)."""

# Third-party imports (Django)
from django import forms

from horilla.contrib.generics.forms import HorillaModelForm

# First party imports (Horilla)
from horilla.urls import reverse_lazy

# Local imports
from .models import Report, ReportFolder


# Define your reports forms here
class ReportForm(HorillaModelForm):
    """Form for creating and editing reports with module, columns, and folder selection."""

    field_order = [
        "name",
        "module",
        "folder",
        "selected_columns",
        "report_owner",
    ]

    class Meta:
        """Meta options for ReportForm."""

        model = Report
        fields = "__all__"
        exclude = [
            "row_groups",
            "column_groups",
            "aggregate_columns",
            "filters",
            "chart_type",
            "chart_field",
            "chart_field_stacked",
            "chart_value_field",
            "is_favourite",
            "shared_with",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folder"].queryset = (
            ReportFolder.objects.all()
            if self.request.user.is_superuser
            else ReportFolder.objects.filter(report_folder_owner=self.request.user)
        )

        self.fields["module"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("reports:get_module_columns_htmx"),
                "hx-target": "#id_columns",
                "hx-trigger": "change",
                "hx-swap": "outerHTML",
                "hx-include": "[name='module']",
            }
        )

        self.fields["selected_columns"].widget = forms.SelectMultiple(
            attrs={
                "class": "js-example-basic-multiple headselect w-full",
                "id": "id_columns",
                "name": "selected_columns",
                "tabindex": "-1",
                "aria-hidden": "true",
                "multiple": True,
                "required": True,
            }
        )

    def clean_selected_columns(self):
        """Convert the list to comma-separated string and validate that at least one column is selected"""
        selected = self.cleaned_data.get("selected_columns", [])

        if isinstance(selected, str):
            if selected.startswith("[") and selected.endswith("]"):
                try:
                    # Standard library imports
                    import ast

                    selected = ast.literal_eval(selected)
                except Exception:
                    selected = [
                        item.strip().strip("'\"")
                        for item in selected.strip("[]").split(",")
                        if item.strip()
                    ]
            else:
                selected = [selected] if selected.strip() else []

        if isinstance(selected, list):
            filtered_selected = [item for item in selected if item.strip()]
            return ",".join(filtered_selected)

        return ""


class ChangeChartReportForm(HorillaModelForm):
    """Form for changing the chart type of a report."""

    field_order = ["chart_type"]

    class Meta:
        """Meta options for ChangeChartReportForm."""

        model = Report
        fields = "__all__"
        exclude = [
            "name",
            "module",
            "folder",
            "selected_columns",
            "row_groups",
            "column_groups",
            "aggregate_columns",
            "filters",
            "chart_field",
            "chart_field_stacked",
            "chart_value_field",
            "is_favourite",
            "shared_with",
            "report_owner",
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.get("request")
        super().__init__(*args, **kwargs)

        total_groups = self.request.GET.get("total")

        try:
            total_groups = int(total_groups)
        except (TypeError, ValueError):
            total_groups = 0

        chart_choices = Report.CHART_TYPES

        if total_groups <= 1:
            chart_choices = [
                c
                for c in chart_choices
                if c[0]
                not in [
                    "stacked_vertical",
                    "stacked_horizontal",
                    "heatmap",
                    "sankey",
                ]
            ]

        self.fields["chart_type"].choices = chart_choices
