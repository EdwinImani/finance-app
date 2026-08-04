from decimal import Decimal
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from financeapp.access_control import can_view_all_documents, can_view_purchase_reports
from .models import PurchaseOrder
from .forms import PurchaseReportForm


def purchase_admin_context(request, extra_context=None):
    context = admin.site.each_context(request)
    if extra_context:
        context.update(extra_context)
    return context


@staff_member_required
def purchase_home(request):
    if not can_view_purchase_reports(request.user):
        raise PermissionDenied
    orders = PurchaseOrder.objects.all()
    if not can_view_all_documents(request.user):
        orders = orders.filter(created_by=request.user)
    orders = orders.prefetch_related("items", "seller").order_by("-purchase_date")
    return render(request, "purchase/home.html", purchase_admin_context(request, {"orders": orders}))


@staff_member_required
def purchase_report_filter(request):
    if not can_view_purchase_reports(request.user):
        raise PermissionDenied
    form = PurchaseReportForm(request.GET or None)
    return render(request, "purchase/report_filter.html", purchase_admin_context(request, {"form": form}))


@staff_member_required
def purchase_report_result(request):
    if not can_view_purchase_reports(request.user):
        raise PermissionDenied
    form = PurchaseReportForm(request.GET or None)

    orders = PurchaseOrder.objects.all()
    if not can_view_all_documents(request.user):
        orders = orders.filter(created_by=request.user)
    orders = orders.prefetch_related("items", "items__product", "seller")

    if form.is_valid():
        year = form.cleaned_data.get("year")
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        seller = form.cleaned_data.get("seller")
        product = form.cleaned_data.get("product")

        if year:
            orders = orders.filter(purchase_date__year=year)

        if date_from:
            orders = orders.filter(purchase_date__gte=date_from)

        if date_to:
            orders = orders.filter(purchase_date__lte=date_to)

        if seller:
            orders = orders.filter(seller=seller)

        if product:
            orders = orders.filter(items__product=product).distinct()

    rows = []
    total_qty = Decimal("0.00")
    total_gross = Decimal("0.00")
    total_vat = Decimal("0.00")
    total_freight = Decimal("0.00")
    total_amount = Decimal("0.00")

    chart_labels = []
    chart_values = []

    for order in orders:
        qty = sum(item.quantity for item in order.items.all())
        gross = order.gross_value()
        vat = order.vat_amount()
        freight = order.freight or Decimal("0.00")
        amount = order.total_amount()

        rows.append({
            "date": order.purchase_date,
            "number": order.purchase_number,
            "seller": order.seller.description if order.seller else "-",
            "qty": qty,
            "gross": gross,
            "vat": vat,
            "freight": freight,
            "amount": amount,
        })

        total_qty += Decimal(qty)
        total_gross += gross
        total_vat += vat
        total_freight += freight
        total_amount += amount

        chart_labels.append(order.purchase_date.strftime("%d/%m/%Y"))
        chart_values.append(float(amount))

    context = {
        "form": form,
        "rows": rows,
        "total_qty": total_qty,
        "total_gross": total_gross,
        "total_vat": total_vat,
        "total_freight": total_freight,
        "total_amount": total_amount,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    }

    return render(request, "purchase/report_result.html", purchase_admin_context(request, context))
