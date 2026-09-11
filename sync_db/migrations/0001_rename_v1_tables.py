from django.db import migrations

TABLE_RENAMES = [
    # ================= CORE =================
    ("horilla_core_activetab", "core_activetab"),
    ("horilla_core_businesshour", "core_businesshour"),
    ("horilla_core_company", "core_company"),
    ("horilla_core_customerrole", "core_customerrole"),
    ("horilla_core_datedconversionrate", "core_datedconversionrate"),
    ("horilla_core_department", "core_department"),
    ("horilla_core_detailfieldvisibility", "core_detailfieldvisibility"),
    ("horilla_core_exportschedule", "core_exportschedule"),
    ("horilla_core_fieldpermission", "core_fieldpermission"),
    ("horilla_core_fiscalyear", "core_fiscalyear"),
    ("horilla_core_fiscalyearinstance", "core_fiscalyearinstance"),
    ("horilla_core_holiday", "core_holiday"),
    ("horilla_core_holiday_specific_users", "core_holiday_specific_users"),
    ("horilla_core_horillaattachment", "core_horillaattachment"),
    ("horilla_core_horillauser", "core_horillauser"),
    ("horilla_core_horillauser_groups", "core_horillauser_groups"),
    ("horilla_core_horillauser_user_permissions", "core_horillauser_user_permissions"),
    ("horilla_core_importhistory", "core_importhistory"),
    ("horilla_core_kanbangroupby", "core_kanbangroupby"),
    ("horilla_core_listcolumnvisibility", "core_listcolumnvisibility"),
    ("horilla_core_multiplecurrency", "core_multiplecurrency"),
    ("horilla_core_partnerrole", "core_partnerrole"),
    ("horilla_core_period", "core_period"),
    ("horilla_core_pinnedview", "core_pinnedview"),
    ("horilla_core_quarter", "core_quarter"),
    ("horilla_core_quickfilter", "core_quickfilter"),
    ("horilla_core_recentlyviewed", "core_recentlyviewed"),
    ("horilla_core_recyclebin", "core_recyclebin"),
    ("horilla_core_recyclebinpolicy", "core_recyclebinpolicy"),
    ("horilla_core_role", "core_role"),
    ("horilla_core_role_permissions", "core_role_permissions"),
    ("horilla_core_savedfilterlist", "core_savedfilterlist"),
    ("horilla_core_teamrole", "core_teamrole"),
    ("horilla_core_timelinespanby", "core_timelinespanby"),
    # ================= ACTIVITY =================
    ("horilla_activity_activity", "activity_activity"),
    ("horilla_activity_activity_assigned_to", "activity_activity_assigned_to"),
    ("horilla_activity_activity_participants", "activity_activity_participants"),
    # ================= AUTOMATIONS =================
    ("horilla_automations_automationcondition", "automations_automationcondition"),
    ("horilla_automations_automationrunlog", "automations_automationrunlog"),
    ("horilla_automations_horillaautomation", "automations_horillaautomation"),
    (
        "horilla_automations_horillaautomation_also_sent_to",
        "automations_horillaautomation_also_sent_to",
    ),
    # ================= CADENCES =================
    ("horilla_cadences_cadence", "cadences_cadence"),
    ("horilla_cadences_cadencecondition", "cadences_cadencecondition"),
    ("horilla_cadences_cadencefollowup", "cadences_cadencefollowup"),
    # ================= CALENDAR =================
    ("horilla_calendar_customcalendar", "calendar_customcalendar"),
    ("horilla_calendar_customcalendarcondition", "calendar_customcalendarcondition"),
    ("horilla_calendar_googlecalendarconfig", "calendar_googlecalendarconfig"),
    ("horilla_calendar_googleintegrationsetting", "calendar_googleintegrationsetting"),
    ("horilla_calendar_useravailability", "calendar_useravailability"),
    ("horilla_calendar_usercalendarpreference", "calendar_usercalendarpreference"),
    # ================= DASHBOARD =================
    ("horilla_dashboard_componentcriteria", "dashboard_componentcriteria"),
    ("horilla_dashboard_dashboard", "dashboard_dashboard"),
    ("horilla_dashboard_dashboard_favourited_by", "dashboard_dashboard_favourited_by"),
    ("horilla_dashboard_dashboardcomponent", "dashboard_dashboardcomponent"),
    ("horilla_dashboard_dashboardfolder", "dashboard_dashboardfolder"),
    (
        "horilla_dashboard_dashboardfolder_favourited_by",
        "dashboard_dashboardfolder_favourited_by",
    ),
    ("horilla_dashboard_defaulthomelayoutorder", "dashboard_defaulthomelayoutorder"),
    # ================= DUPLICATES =================
    ("horilla_duplicates_duplicaterule", "duplicates_duplicaterule"),
    ("horilla_duplicates_duplicaterulecondition", "duplicates_duplicaterulecondition"),
    ("horilla_duplicates_matchingrule", "duplicates_matchingrule"),
    ("horilla_duplicates_matchingrulecriteria", "duplicates_matchingrulecriteria"),
    # ================= KEYS =================
    ("horilla_keys_shortcutkey", "keys_shortcutkey"),
    # ================= MAIL =================
    ("horilla_mail_horillamail", "mail_horillamail"),
    ("horilla_mail_horillamailattachment", "mail_horillamailattachment"),
    ("horilla_mail_horillamailconfiguration", "mail_horillamailconfiguration"),
    ("horilla_mail_horillamailtemplate", "mail_horillamailtemplate"),
    # ================= NOTIFICATIONS =================
    ("horilla_notifications_notification", "notifications_notification"),
    (
        "horilla_notifications_notificationtemplate",
        "notifications_notificationtemplate",
    ),
    # ================= REPORTS =================
    ("horilla_reports_report", "reports_report"),
    ("horilla_reports_report_shared_with", "reports_report_shared_with"),
    ("horilla_reports_reportfolder", "reports_reportfolder"),
    # ================= THEME =================
    ("horilla_theme_companytheme", "theme_companytheme"),
    ("horilla_theme_horillacolortheme", "theme_horillacolortheme"),
]


def rename_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = connection.introspection.table_names()

    for old, new in TABLE_RENAMES:
        if old in existing_tables:
            schema_editor.execute(f'ALTER TABLE "{old}" RENAME TO "{new}";')


def reverse_rename_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = connection.introspection.table_names()

    for old, new in TABLE_RENAMES:
        if new in existing_tables:
            schema_editor.execute(f'ALTER TABLE "{new}" RENAME TO "{old}";')


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunPython(rename_tables, reverse_rename_tables),
    ]
