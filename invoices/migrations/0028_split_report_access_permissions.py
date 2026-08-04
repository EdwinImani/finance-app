from django.db import migrations


OLD_CODENAME = "view_reports"
COMMERCIAL_CODENAME = "view_commercial_invoice_reports"
PURCHASE_CODENAME = "view_purchase_order_reports"


def split_existing_report_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    content_type = ContentType.objects.filter(
        app_label="invoices",
        model="commercialinvoice",
    ).first()
    if not content_type:
        return

    commercial_permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename=COMMERCIAL_CODENAME,
        defaults={"name": "Can access Commercial Invoice reports"},
    )
    purchase_content_type = ContentType.objects.filter(
        app_label="purchase",
        model="purchaseorder",
    ).first()
    if not purchase_content_type:
        return
    purchase_permission, _ = Permission.objects.get_or_create(
        content_type=purchase_content_type,
        codename=PURCHASE_CODENAME,
        defaults={"name": "Can access Purchase Order reports"},
    )

    old_permission = Permission.objects.filter(
        content_type=content_type,
        codename=OLD_CODENAME,
    ).first()
    if not old_permission:
        return

    for group in old_permission.group_set.all():
        group.permissions.add(commercial_permission, purchase_permission)
    for user in old_permission.user_set.all():
        user.user_permissions.add(commercial_permission, purchase_permission)
    old_permission.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0027_commercialinvoice_view_reports_permission"),
        ("purchase", "0009_purchaseorder_view_reports_permission"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="commercialinvoice",
            options={
                "permissions": (
                    (
                        "view_all_documents",
                        "Can view all users' invoices and purchase orders",
                    ),
                    (
                        "view_commercial_invoice_reports",
                        "Can access Commercial Invoice reports",
                    ),
                ),
            },
        ),
        migrations.RunPython(
            split_existing_report_permission,
            migrations.RunPython.noop,
        ),
    ]
