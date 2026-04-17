from django.shortcuts import render, redirect
from .forms import ProformaInvoiceForm, CommercialInvoiceForm


def create_proforma_invoice(request):
    if request.method == 'POST':
        form = ProformaInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            return redirect('admin:index')
    else:
        form = ProformaInvoiceForm()

    return render(request, 'invoices/proforma_invoice_form.html', {
        'form': form
    })


def create_commercial_invoice(request):
    if request.method == 'POST':
        form = CommercialInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            return redirect('admin:index')
    else:
        form = CommercialInvoiceForm()

    return render(request, 'invoices/commercial_invoice_form.html', {
        'form': form
    })
