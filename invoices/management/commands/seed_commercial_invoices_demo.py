from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from invoices.models import CommercialInvoice, CommercialInvoiceItem
from partners.models import Partner, PartnerAddress, PartnerPhone
from products.models import Product


PARTNERS = [
    {
        "description": "Maghreb Import Distribution",
        "partner_type": "importer",
        "email": "contact@mid.example",
        "website": "https://mid.example",
        "addresses": ["102 Route d'Oran, Alger, Algeria"],
        "phones": ["+213 21 45 67 89"],
    },
    {
        "description": "North Africa Industrial Trade",
        "partner_type": "importer",
        "email": "sales@nait.example",
        "website": "https://nait.example",
        "addresses": ["18 Rue des Exportateurs, Casablanca, Morocco"],
        "phones": ["+212 522 88 10 20"],
    },
    {
        "description": "Sahara Energy Services",
        "partner_type": "enduser",
        "email": "procurement@sahara-energy.example",
        "website": "https://sahara-energy.example",
        "addresses": ["Zone Industrielle Sud, Hassi Messaoud, Algeria"],
        "phones": ["+213 29 90 11 22"],
    },
    {
        "description": "Atlas Drilling Solutions",
        "partner_type": "enduser",
        "email": "orders@atlas-drilling.example",
        "website": "https://atlas-drilling.example",
        "addresses": ["55 Industrial Park, Rabat, Morocco"],
        "phones": ["+212 537 20 30 40"],
    },
]


PRODUCTS = [
    {
        "description": "Industrial Pressure Sensor",
        "part_number": "IPS-2200",
        "note": "4-20mA output",
        "unit_qty": 500,
        "sale_price": Decimal("185.00"),
        "purchase_price": Decimal("118.00"),
    },
    {
        "description": "Stainless Control Valve",
        "part_number": "SCV-80A",
        "note": "DN80 manual valve",
        "unit_qty": 250,
        "sale_price": Decimal("520.00"),
        "purchase_price": Decimal("389.00"),
    },
    {
        "description": "PLC Expansion Module",
        "part_number": "PLC-X8",
        "note": "8 digital inputs",
        "unit_qty": 350,
        "sale_price": Decimal("325.00"),
        "purchase_price": Decimal("238.00"),
    },
    {
        "description": "Shielded Signal Cable 100m",
        "part_number": "SSC-100",
        "note": "Twisted pair cable roll",
        "unit_qty": 600,
        "sale_price": Decimal("130.00"),
        "purchase_price": Decimal("82.00"),
    },
    {
        "description": "Explosion Proof Junction Box",
        "part_number": "EJB-44",
        "note": "ATEX certified enclosure",
        "unit_qty": 180,
        "sale_price": Decimal("415.00"),
        "purchase_price": Decimal("285.00"),
    },
]


INVOICE_SPECS = [
    (2025, 1, 9, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("650.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 6), ("PLC Expansion Module", 3)]),
    (2025, 1, 21, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("420.00"), Decimal("20.00"), [("Stainless Control Valve", 2), ("Shielded Signal Cable 100m", 5)]),
    (2025, 2, 6, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("510.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 4)]),
    (2025, 2, 18, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("780.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 8), ("PLC Expansion Module", 4)]),
    (2025, 3, 4, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("590.00"), Decimal("20.00"), [("Stainless Control Valve", 3), ("Industrial Pressure Sensor", 5)]),
    (2025, 3, 27, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("860.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 3), ("Shielded Signal Cable 100m", 6)]),
    (2025, 4, 8, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("470.00"), Decimal("20.00"), [("PLC Expansion Module", 5)]),
    (2025, 4, 22, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("905.00"), Decimal("20.00"), [("Stainless Control Valve", 4), ("Industrial Pressure Sensor", 7)]),
    (2025, 5, 5, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("530.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 10), ("PLC Expansion Module", 2)]),
    (2025, 5, 19, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("690.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 3)]),
    (2025, 6, 3, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("845.00"), Decimal("20.00"), [("Stainless Control Valve", 5), ("Shielded Signal Cable 100m", 4)]),
    (2025, 6, 24, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("610.00"), Decimal("20.00"), [("PLC Expansion Module", 6), ("Industrial Pressure Sensor", 2)]),
    (2025, 7, 7, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("720.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 1), ("Stainless Control Valve", 3)]),
    (2025, 7, 29, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("455.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 8)]),
    (2025, 8, 12, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("980.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 12), ("PLC Expansion Module", 5)]),
    (2025, 8, 26, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("560.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 4)]),
    (2025, 9, 9, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("630.00"), Decimal("20.00"), [("Stainless Control Valve", 2), ("PLC Expansion Module", 3), ("Shielded Signal Cable 100m", 3)]),
    (2025, 9, 23, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("740.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 10), ("Explosion Proof Junction Box", 1)]),
    (2025, 10, 14, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("690.00"), Decimal("20.00"), [("PLC Expansion Module", 7), ("Shielded Signal Cable 100m", 5)]),
    (2025, 10, 30, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("840.00"), Decimal("20.00"), [("Stainless Control Valve", 4), ("Explosion Proof Junction Box", 2)]),
    (2025, 11, 13, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("605.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 5), ("Shielded Signal Cable 100m", 4)]),
    (2025, 11, 27, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("915.00"), Decimal("20.00"), [("PLC Expansion Module", 5), ("Stainless Control Valve", 3)]),
    (2025, 12, 10, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("755.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 6)]),
    (2025, 12, 22, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("880.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 9), ("PLC Expansion Module", 4)]),
    (2026, 1, 8, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("710.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 7), ("PLC Expansion Module", 2)]),
    (2026, 1, 20, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("520.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 6), ("Explosion Proof Junction Box", 1)]),
    (2026, 2, 5, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("935.00"), Decimal("20.00"), [("Stainless Control Valve", 4), ("Industrial Pressure Sensor", 6)]),
    (2026, 2, 17, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("645.00"), Decimal("20.00"), [("PLC Expansion Module", 5), ("Shielded Signal Cable 100m", 5)]),
    (2026, 3, 3, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("870.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 3), ("Industrial Pressure Sensor", 3)]),
    (2026, 3, 18, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("590.00"), Decimal("20.00"), [("Stainless Control Valve", 2), ("PLC Expansion Module", 4)]),
    (2026, 4, 4, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("780.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 11), ("Industrial Pressure Sensor", 2)]),
    (2026, 4, 23, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("960.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Stainless Control Valve", 3)]),
    (2026, 5, 7, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("615.00"), Decimal("20.00"), [("PLC Expansion Module", 6), ("Industrial Pressure Sensor", 4)]),
    (2026, 5, 21, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("845.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 8), ("Explosion Proof Junction Box", 2)]),
    (2026, 6, 11, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("995.00"), Decimal("20.00"), [("Stainless Control Valve", 5), ("PLC Expansion Module", 3)]),
    (2026, 6, 26, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("680.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 9), ("Shielded Signal Cable 100m", 2)]),
    (2026, 7, 9, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("735.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 5)]),
    (2026, 7, 24, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("540.00"), Decimal("20.00"), [("PLC Expansion Module", 4), ("Shielded Signal Cable 100m", 4)]),
    (2026, 8, 6, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("905.00"), Decimal("20.00"), [("Stainless Control Valve", 4), ("Explosion Proof Junction Box", 1)]),
    (2026, 8, 27, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("620.00"), Decimal("20.00"), [("Industrial Pressure Sensor", 6), ("PLC Expansion Module", 3)]),
    (2026, 9, 10, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("875.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 10), ("Explosion Proof Junction Box", 2)]),
    (2026, 9, 29, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("710.00"), Decimal("20.00"), [("Stainless Control Valve", 2), ("Industrial Pressure Sensor", 7)]),
    (2026, 10, 15, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("955.00"), Decimal("20.00"), [("PLC Expansion Module", 8), ("Shielded Signal Cable 100m", 4)]),
    (2026, 10, 28, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("665.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 2), ("Industrial Pressure Sensor", 3)]),
    (2026, 11, 12, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("810.00"), Decimal("20.00"), [("Stainless Control Valve", 3), ("PLC Expansion Module", 4)]),
    (2026, 11, 25, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("590.00"), Decimal("20.00"), [("Shielded Signal Cable 100m", 7), ("Industrial Pressure Sensor", 4)]),
    (2026, 12, 9, "Maghreb Import Distribution", "Sahara Energy Services", Decimal("930.00"), Decimal("20.00"), [("Explosion Proof Junction Box", 3), ("Stainless Control Valve", 2)]),
    (2026, 12, 19, "North Africa Industrial Trade", "Atlas Drilling Solutions", Decimal("760.00"), Decimal("20.00"), [("PLC Expansion Module", 5), ("Shielded Signal Cable 100m", 6)]),
]


class Command(BaseCommand):
    help = "Create many demo commercial invoices for 2025 and 2026 with varied dates."

    @transaction.atomic
    def handle(self, *args, **options):
        partners = self._seed_partners()
        products = self._seed_products()
        created, skipped = self._seed_invoices(partners, products)
        self.stdout.write(
            self.style.SUCCESS(
                f"Commercial invoices seeded. Created: {created}, skipped existing: {skipped}."
            )
        )

    def _seed_partners(self):
        partners = {}

        for data in PARTNERS:
            partner, _ = Partner.objects.update_or_create(
                description=data["description"],
                defaults={
                    "partner_type": data["partner_type"],
                    "email": data["email"],
                    "website": data["website"],
                },
            )
            PartnerAddress.objects.filter(partner=partner).delete()
            PartnerPhone.objects.filter(partner=partner).delete()

            for address in data["addresses"]:
                PartnerAddress.objects.create(partner=partner, address=address)

            for phone in data["phones"]:
                PartnerPhone.objects.create(partner=partner, phone_number=phone)

            partners[partner.description] = partner

        return partners

    def _seed_products(self):
        products = {}

        for data in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                description=data["description"],
                defaults={
                    "part_number": data["part_number"],
                    "note": data["note"],
                    "unit_qty": data["unit_qty"],
                    "sale_price": data["sale_price"],
                    "purchase_price": data["purchase_price"],
                },
            )
            products[product.description] = product

        return products

    def _seed_invoices(self, partners, products):
        created = 0
        skipped = 0

        for index, spec in enumerate(INVOICE_SPECS, start=1):
            year, month, day, importer_name, end_user_name, freight, vat_percent, items = spec
            invoice_number = f"FR/{year}/DEMO{index:04d}"

            if CommercialInvoice.objects.filter(invoice_number=invoice_number).exists():
                skipped += 1
                continue

            invoice = CommercialInvoice.objects.create(
                invoice_number=invoice_number,
                invoice_date=date(year, month, day),
                importer=partners[importer_name],
                end_user=partners[end_user_name],
                freight=freight,
                discount=Decimal("0.00"),
                vat_percent=vat_percent,
                our_order_no=f"SO-{year}-{index:04d}",
                our_reference=f"DEMO-REF-{year}-{index:04d}",
            )

            for item_index, (product_name, quantity) in enumerate(items, start=1):
                product = products[product_name]
                CommercialInvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    hs_code=f"HS-{year % 100:02d}{index:04d}{item_index}",
                    quantity=quantity,
                    unit_price=product.sale_price,
                )

            created += 1

        return created, skipped
