from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType


ADMIN_ROLE_GROUPS = {"Manager", "Staff"}
VIEW_ALL_DOCUMENTS_CODENAME = "view_all_documents"


def document_access_permission_field():
    return forms.BooleanField(
        required=False,
        label="Can view all users' invoices and purchase orders",
        help_text=(
            "Enable this to let the user see documents created by every user. "
            "Leave it disabled to limit the user to their own documents."
        ),
    )


class DocumentAccessPermissionMixin:
    def _document_access_permission(self, *, create=False):
        permission = Permission.objects.filter(
            content_type__app_label="invoices",
            codename=VIEW_ALL_DOCUMENTS_CODENAME,
        ).first()
        if permission or not create:
            return permission

        content_type = ContentType.objects.filter(
            app_label="invoices",
            model="commercialinvoice",
        ).first()
        if not content_type:
            return None

        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=VIEW_ALL_DOCUMENTS_CODENAME,
            defaults={
                "name": "Can view all users' invoices and purchase orders",
            },
        )
        return permission

    def _set_document_access_initial(self):
        if self.instance and self.instance.pk:
            permission = self._document_access_permission()
            self.fields["can_view_all_documents"].initial = bool(
                permission
                and self.instance.user_permissions.filter(pk=permission.pk).exists()
            )

    def _sync_document_access_permission(self):
        if not self.instance.pk:
            return
        permission = self._document_access_permission(create=True)
        if not permission:
            return
        if self.cleaned_data.get("can_view_all_documents"):
            self.instance.user_permissions.add(permission)
        else:
            self.instance.user_permissions.remove(permission)

    def _save_m2m(self):
        super()._save_m2m()
        self._sync_document_access_permission()


class AdminUserCreationForm(DocumentAccessPermissionMixin, UserCreationForm):
    """Create admin users through Django's validators and password hasher."""

    can_view_all_documents = document_access_permission_field()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "groups",
            "can_view_all_documents",
        )

    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data.get("groups")
        if groups and groups.filter(name__in=ADMIN_ROLE_GROUPS).exists():
            cleaned_data["is_staff"] = True
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Keep the password handling explicit: never assign the raw value to
        # user.password. UserCreationForm has already run Django's validators.
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self._save_m2m()
        return user


class AdminUserChangeForm(DocumentAccessPermissionMixin, UserChangeForm):
    can_view_all_documents = document_access_permission_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_document_access_initial()

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
