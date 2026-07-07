from django.contrib import admin
from financeapp.admin_mixins import SaveRedirectToWelcomeMixin
from .models import Account, Transaction


class AccountingAdmin(SaveRedirectToWelcomeMixin, admin.ModelAdmin):
    pass


admin.site.register(Account, AccountingAdmin)
admin.site.register(Transaction, AccountingAdmin)
