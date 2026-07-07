from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.admin.sites import NotRegistered

from financeapp.admin_mixins import SaveRedirectToWelcomeMixin


class WelcomeRedirectUserAdmin(SaveRedirectToWelcomeMixin, UserAdmin):
    pass


class WelcomeRedirectGroupAdmin(SaveRedirectToWelcomeMixin, GroupAdmin):
    pass


for model in (User, Group):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass


admin.site.register(User, WelcomeRedirectUserAdmin)
admin.site.register(Group, WelcomeRedirectGroupAdmin)
