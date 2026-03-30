from django.shortcuts import render, redirect
from .forms import ProformaInvoiceForm, CommercialInvoiceForm


def choose_invoice_type(request):
    return render(request, 'invoices/choose_invoice_type.html')


def create_proforma_invoice(request):
    if request.method == 'POST':
        form = ProformaInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            return redirect('choose_invoice_type')
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
            return redirect('choose_invoice_type')
    else:
        form = CommercialInvoiceForm()

    return render(request, 'invoices/commercial_invoice_form.html', {
        'form': form
    })