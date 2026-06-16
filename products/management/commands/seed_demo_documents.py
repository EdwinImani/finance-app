from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from invoices.models import (
    CommercialInvoice,
    CommercialInvoiceItem,
    CommercialInvoicePacking,
    ProformaInvoice,
    ProformaInvoiceItem,
)
from partners.models import Partner
from products.management.commands.seed_demo_catalog import PARTNERS, PRODUCTS
from products.models import Product
from purchase.models import PurchaseOrder, PurchaseOrderItem


class Command(BaseCommand):
    help = "Seed demo purchase orders, proformas, and a 30-item commercial invoice."

    @transaction.atomic
    def handle(self, *args, **options):
        partners = self._get_partners()
        products = self._get_products()

        purchase_count = self._seed_purchase_orders(partners, products)
        proforma_count = self._seed_proformas(partners, products)
        commercial = self._seed_commercial_invoice(partners, products)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo documents ready: "
                f"{purchase_count} purchase orders, "
                f"{proforma_count} proforma invoices, "
                f"commercial invoice {commercial.invoice_number} with "
                f"{commercial.items.count()} items."
            )
        )

    def _get_partners(self):
        partners = {}

        for index, (description, partner_type) in enumerate(PARTNERS, start=1):
            partner, _ = Partner.objects.update_or_create(
                description=description,
                defaults={
                    "partner_type": partner_type,
                    "email": f"contact{index:02d}@demo-finance.local",
                    "fax": f"+33 1 45 00 {index:02d} {index:02d}",
                    "website": f"https://partner{index:02d}.demo-finance.local",
                },
            )
            partners[description] = partner

        return partners

    def _get_products(self):
        products = []

        for index, (name, hs_code) in enumerate(PRODUCTS, start=1):
            part_number = f"20260615{index:012d}"
            product, _ = Product.objects.update_or_create(
                part_number=part_number,
                defaults={
                    "description": f"Demo {name}",
                    "hs_code": hs_code,
                    "note": "Generated demo product data",
                    "unit_qty": 1000,
                    "sale_price": Decimal("100.00") + Decimal(index * 17),
                    "purchase_price": Decimal("60.00") + Decimal(index * 11),
                },
            )
            products.append(product)

        return products

    def _seed_purchase_orders(self, partners, products):
        specs = [
            (date(2026, 1, 12), "Blue Harbor Trading", "Cedar Supply Partners", 0),
            (date(2026, 2, 4), "Falcon Industrial Sales", "Greenline Procurement", 4),
            (date(2026, 3, 18), "Juno Distribution", "Kappa Request Office", 8),
            (date(2026, 4, 9), "Nova End User Services", "Orion Purchase Desk", 12),
            (date(2026, 5, 27), "Riviera Import Export", "Solstice Client Group", 16),
            (date(2026, 6, 15), "Blue Harbor Trading", "Greenline Procurement", 2),
        ]

        for index, (purchase_date, seller, requester, offset) in enumerate(specs, start=1):
            order, _ = PurchaseOrder.objects.update_or_create(
                purchase_number=f"PO/2026-DOC-{index:04d}",
                defaults={
                    "purchase_date": purchase_date,
                    "seller": partners[seller],
                    "requester": partners[requester],
                    "sent_by": f"Demo Buyer {index}",
                    "shipment": ["Air Freight", "Sea Freight", "Road Transport"][index % 3],
                    "freight": Decimal("75.00") + Decimal(index * 22),
                    "vat_percent": Decimal("20.00"),
                    "sales_condition": "Demo purchase condition",
                    "payment_condition": "30 days bank transfer",
                    "delivery_terms": "DAP Paris",
                },
            )
            PurchaseOrderItem.objects.filter(purchase_order=order).delete()

            for item_index in range(5):
                product = products[(offset + item_index) % len(products)]
                PurchaseOrderItem.objects.create(
                    purchase_order=order,
                    product=product,
                    quantity=3 + item_index + index,
                    unit_price=product.purchase_price,
                )

        return len(specs)

    def _seed_proformas(self, partners, products):
        specs = [
            (date(2026, 1, 7), "Aster Import Group", "Delta Medical Buyer", 0),
            (date(2026, 2, 21), "Euro Bridge Logistics", "Helios End Client", 5),
            (date(2026, 3, 29), "Iris Components", "Lumen Global Import", 10),
            (date(2026, 4, 16), "Mistral Seller Hub", "Polar Trade House", 3),
            (date(2026, 5, 30), "Quartz Equipment", "Terra Supplier Network", 8),
        ]

        for index, (invoice_date, importer, end_user, offset) in enumerate(specs, start=1):
            invoice, _ = ProformaInvoice.objects.update_or_create(
                invoice_number=f"PF/2026-DOC-{index:04d}",
                defaults={
                    "invoice_date": invoice_date,
                    "importer": partners[importer],
                    "end_user": partners[end_user],
                    "freight": Decimal("140.00") + Decimal(index * 31),
                    "discount": Decimal("10.00") * Decimal(index % 2),
                    "vat_percent": Decimal("20.00"),
                    "our_reference": f"RFQ-2026-{index:04d}",
                    "price_for": "Demo proforma with varied dates",
                },
            )
            ProformaInvoiceItem.objects.filter(invoice=invoice).delete()

            for item_index in range(6):
                product = products[(offset + item_index) % len(products)]
                ProformaInvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    item_date=invoice_date + timedelta(days=item_index),
                    quantity=2 + item_index,
                    unit_price=product.sale_price,
                )

        return len(specs)

    def _seed_commercial_invoice(self, partners, products):
        invoice, _ = CommercialInvoice.objects.update_or_create(
            invoice_number="FR/2026-DOC-0030",
            defaults={
                "invoice_date": date(2026, 6, 15),
                "importer": partners["Aster Import Group"],
                "end_user": partners["Delta Medical Buyer"],
                "freight": Decimal("480.00"),
                "discount": Decimal("125.00"),
                "vat_percent": Decimal("20.00"),
                "our_order_no": "SO-2026-0030",
                "our_reference": "PF/2026-DOC-0030",
                "packing_specification": "30 demo line items packed on 3 pallets",
                "dispatching_note": "Dispatch by grouped demo shipment",
            },
        )
        CommercialInvoiceItem.objects.filter(invoice=invoice).delete()
        CommercialInvoicePacking.objects.filter(invoice=invoice).delete()

        for index in range(30):
            product = products[index % len(products)]
            CommercialInvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=1 + (index % 5),
                unit_price=product.sale_price + Decimal(index),
            )

        for index in range(1, 4):
            CommercialInvoicePacking.objects.create(
                invoice=invoice,
                no_packing=f"PALLET-{index}",
                gross_weight=Decimal("140.00") + Decimal(index * 15),
                net_weight=Decimal("120.00") + Decimal(index * 12),
                dimension_length=Decimal("120.00"),
                dimension_width=Decimal("80.00"),
                dimension_height=Decimal("110.00") + Decimal(index * 5),
            )

        return invoice
