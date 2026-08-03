from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User


ADMIN_ROLE_GROUPS = {"Manager", "Staff"}


class AdminUserCreationForm(UserCreationForm):
    """Create admin users through Django's validators and password hasher."""

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
            self.save_m2m()
        return user


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
