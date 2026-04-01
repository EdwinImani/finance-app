from datetime import date
from decimal import Decimal

from django.db.models import Q

from company.models import CompanySetting
from invoices.models import CommercialInvoice, ProformaInvoice
from products.models import Product


ZERO = Decimal("0.00")


def _sum_invoice_stats(queryset):
    gross = ZERO
    freight = ZERO
    vat = ZERO
    total = ZERO

    for invoice in queryset.prefetch_related("items"):
        gross += invoice.subtotal()
        freight += invoice.freight or ZERO
        vat += invoice.vat_amount()
        total += invoice.total_amount()

    return {
        "gross": gross,
        "freight": freight,
        "vat": vat,
        "total": total,
    }
def company_branding(request):
    company = CompanySetting.objects.first()
    if not company:
        return {
            "company_brand_name": "",
            "company_brand_logo_url": "",
            "company_year": None,
            "company_currency": "",
            "dashboard_period_start": None,
            "dashboard_period_end": None,
            "dashboard_sales_count": 0,
            "dashboard_sales": {"gross": ZERO, "freight": ZERO, "vat": ZERO, "total": ZERO},
            "dashboard_alerts": {
                "products_missing_part_number": 0,
                "proformas_missing_hs_code": 0,
                "products_low_stock": 0,
            },
        }

    logo_url = company.company_logo.url if company.company_logo else ""
    selected_year = company.year
    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)

    sales_qs = CommercialInvoice.objects.filter(invoice_date__year=selected_year)
    sales_dates = list(sales_qs.values_list("invoice_date", flat=True))
    sales_dates = [d for d in sales_dates if d]
    dashboard_alerts = {
        "products_missing_part_number": Product.objects.filter(
            Q(part_number__isnull=True) | Q(part_number="")
        ).count(),
        "proformas_missing_hs_code": ProformaInvoice.objects.filter(
            Q(hs_code__isnull=True) | Q(hs_code="")
        ).count(),
        "products_low_stock": Product.objects.filter(unit_qty__lte=5).count(),
    }

    return {
        "company_brand_name": company.company_name,
        "company_brand_logo_url": logo_url,
        "company_year": selected_year,
        "company_currency": company.currency,
        "dashboard_period_start": year_start,
        "dashboard_period_end": max(sales_dates) if sales_dates else year_end,
        "dashboard_sales_count": sales_qs.count(),
        "dashboard_sales": _sum_invoice_stats(sales_qs),
        "dashboard_alerts": dashboard_alerts,
    }
