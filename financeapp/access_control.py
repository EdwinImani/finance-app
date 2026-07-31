ADMINISTRATOR_GROUP = "Administrator"
ADMIN_GROUP = "Admin"
MANAGER_GROUP = "Manager"
STAFF_GROUP = "Staff"


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
