ADMINISTRATOR_GROUP = "Administrator"
ADMIN_GROUP = "Admin"
MANAGER_GROUP = "Manager"
STAFF_GROUP = "Staff"
VIEW_ALL_DOCUMENTS_PERMISSION = "invoices.view_all_documents"
VIEW_COMMERCIAL_REPORTS_PERMISSION = "invoices.view_commercial_invoice_reports"
VIEW_PURCHASE_REPORTS_PERMISSION = "purchase.view_purchase_order_reports"


def user_is_in_group(user, group_name):
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=group_name).exists()
    )


def is_administrator(user):
    """Return whether the user may administer users and groups."""
    return bool(user and user.is_authenticated) and (
        user.is_superuser
        or user.groups.filter(name__in=(ADMIN_GROUP, ADMINISTRATOR_GROUP)).exists()
    )


def is_manager(user):
    return user_is_in_group(user, MANAGER_GROUP)


def is_staff_role(user):
    # The Administrator role takes precedence over an accidental Staff membership.
    return not is_administrator(user) and user_is_in_group(user, STAFF_GROUP)


def is_owned_by_user(obj, user):
    return bool(obj) and getattr(obj, "created_by_id", None) == getattr(user, "pk", None)


def can_view_all_documents(user):
    """Return whether a user may see documents created by other users."""
    return bool(user and user.is_authenticated) and (
        is_administrator(user)
        or user.has_perm(VIEW_ALL_DOCUMENTS_PERMISSION)
    )


def can_view_commercial_reports(user):
    """Return whether a user may open Commercial Invoice reports."""
    return bool(user and user.is_authenticated) and (
        is_administrator(user)
        or user.has_perm(VIEW_COMMERCIAL_REPORTS_PERMISSION)
    )


def can_view_purchase_reports(user):
    """Return whether a user may open Purchase Order reports."""
    return bool(user and user.is_authenticated) and (
        is_administrator(user)
        or user.has_perm(VIEW_PURCHASE_REPORTS_PERMISSION)
    )
