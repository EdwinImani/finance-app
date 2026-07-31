from django.utils import timezone


ADMINISTRATOR_GROUP = "Administrator"
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
        user.is_superuser or user_is_in_group(user, ADMINISTRATOR_GROUP)
    )


def is_manager(user):
    return user_is_in_group(user, MANAGER_GROUP)


def is_staff_role(user):
    # The Administrator role takes precedence over an accidental Staff membership.
    return not is_administrator(user) and user_is_in_group(user, STAFF_GROUP)


def is_owned_by_user_today(obj, user):
    created_at = getattr(obj, "created_at", None)
    return bool(
        obj
        and getattr(obj, "created_by_id", None) == getattr(user, "pk", None)
        and created_at
        and timezone.localdate(created_at) == timezone.localdate()
    )
