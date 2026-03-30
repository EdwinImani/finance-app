from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from partners.models import Partner, PartnerAddress, PartnerPhone
from products.models import Product
from purchase.models import PurchaseOrder, PurchaseOrderItem


PARTNERS = [
    {
        "description": "Shanghai Tech Supplies",
        "partner_type": "seller",
        "email": "sales@shanghaitech.example",
        "website": "https://shanghaitech.example",
        "addresses": ["88 Pudong Avenue, Shanghai, China"],
        "phones": ["+86 21 5555 0101"],
    },
    {
        "description": "Istanbul Industrial Parts",
        "partner_type": "seller",
        "email": "export@istanbulparts.example",
        "website": "https://istanbulparts.example",
        "addresses": ["15 Organize Sanayi, Istanbul, Turkiye"],
        "phones": ["+90 212 444 7788"],
    },
    {
        "description": "Berlin Automation Works",
        "partner_type": "seller",
        "email": "orders@berlinautomation.example",
        "website": "https://berlinautomation.example",
        "addresses": ["21 Industriepark, Berlin, Germany"],
        "phones": ["+49 30 2200 1188"],
    },
    {
        "description": "Paris Operations Team",
        "partner_type": "requester",
        "email": "ops@paris-ops.example",
        "website": "https://paris-ops.example",
        "addresses": ["24 Rue du Commerce, Paris, France"],
        "phones": ["+33 1 84 00 12 34"],
    },
    {
        "description": "Lyon Project Office",
        "partner_type": "requester",
        "email": "projects@lyon-office.example",
        "website": "https://lyon-office.example",
        "addresses": ["7 Quai Perrache, Lyon, France"],
        "phones": ["+33 4 72 00 45 67"],
    },
    {
        "description": "Marseille Maintenance Hub",
        "partner_type": "requester",
        "email": "maintenance@marseille-hub.example",
        "website": "https://marseille-hub.example",
        "addresses": ["18 Boulevard du Littoral, Marseille, France"],
        "phones": ["+33 4 91 10 20 30"],
    },
]


PRODUCTS = [
    {
        "description": "Industrial Pressure Sensor",
        "part_number": "IPS-2200",
        "note": "4-20mA output",
        "unit_qty": 1,
        "unit_price": Decimal("135.00"),
        "sale_price": Decimal("185.00"),
        "purchase_price": Decimal("118.00"),
    },
    {
        "description": "Stainless Control Valve",
        "part_number": "SCV-80A",
        "note": "DN80 manual valve",
        "unit_qty": 1,
        "unit_price": Decimal("420.00"),
        "sale_price": Decimal("520.00"),
        "purchase_price": Decimal("389.00"),
    },
    {
        "description": "PLC Expansion Module",
        "part_number": "PLC-X8",
        "note": "8 digital inputs",
        "unit_qty": 1,
        "unit_price": Decimal("260.00"),
        "sale_price": Decimal("325.00"),
        "purchase_price": Decimal("238.00"),
    },
    {
        "description": "Shielded Signal Cable 100m",
        "part_number": "SSC-100",
        "note": "Twisted pair cable roll",
        "unit_qty": 100,
        "unit_price": Decimal("95.00"),
        "sale_price": Decimal("130.00"),
        "purchase_price": Decimal("82.00"),
    },
    {
        "description": "Temperature Transmitter",
        "part_number": "TT-410",
        "note": "PT100 compatible",
        "unit_qty": 1,
        "unit_price": Decimal("148.00"),
        "sale_price": Decimal("205.00"),
        "purchase_price": Decimal("126.00"),
    },
    {
        "description": "Industrial Relay Module",
        "part_number": "IRM-16",
        "note": "16-channel relay board",
        "unit_qty": 1,
        "unit_price": Decimal("112.00"),
        "sale_price": Decimal("149.00"),
        "purchase_price": Decimal("93.00"),
    },
]


ORDER_SPECS = [
    ("2025-01-07", "Shanghai Tech Supplies", "Paris Operations Team", "Nadia Benali", "Air Freight", Decimal("72.00"), Decimal("20.00"), "EXW", "30 days transfer", "DAP Paris", [("Industrial Pressure Sensor", 5), ("PLC Expansion Module", 2)]),
    ("2025-01-15", "Istanbul Industrial Parts", "Lyon Project Office", "Karim Haddad", "Road Transport", Decimal("95.00"), Decimal("20.00"), "Standard packing", "50% advance / 50% on shipment", "CPT Lyon", [("Stainless Control Valve", 3), ("Shielded Signal Cable 100m", 4)]),
    ("2025-01-24", "Berlin Automation Works", "Marseille Maintenance Hub", "Ines Boussaid", "Road Express", Decimal("88.00"), Decimal("20.00"), "Export box", "45 days transfer", "DAP Marseille", [("Temperature Transmitter", 6), ("Industrial Relay Module", 4)]),
    ("2025-02-03", "Shanghai Tech Supplies", "Paris Operations Team", "Yasmine Kaci", "Sea Freight", Decimal("140.00"), Decimal("20.00"), "Export carton", "30 days transfer", "CIF Le Havre", [("Shielded Signal Cable 100m", 8), ("Industrial Pressure Sensor", 4)]),
    ("2025-02-11", "Istanbul Industrial Parts", "Marseille Maintenance Hub", "Sonia Merabet", "Road Transport", Decimal("76.00"), Decimal("20.00"), "Standard export packing", "30 days transfer", "DAP Marseille", [("PLC Expansion Module", 3), ("Industrial Relay Module", 6)]),
    ("2025-02-20", "Berlin Automation Works", "Lyon Project Office", "Nora Salem", "Road Transport", Decimal("91.00"), Decimal("20.00"), "Factory sealed", "60 days transfer", "FCA Berlin", [("Temperature Transmitter", 8), ("Stainless Control Valve", 1)]),
    ("2025-03-04", "Shanghai Tech Supplies", "Marseille Maintenance Hub", "Nadia Benali", "Air Freight", Decimal("84.00"), Decimal("20.00"), "EXW", "30 days transfer", "DAP Marseille", [("Industrial Pressure Sensor", 7), ("Temperature Transmitter", 5)]),
    ("2025-03-12", "Istanbul Industrial Parts", "Paris Operations Team", "Karim Haddad", "Road Transport", Decimal("110.00"), Decimal("20.00"), "Reinforced pallet", "50% advance / 50% on shipment", "CPT Paris", [("Stainless Control Valve", 4), ("Shielded Signal Cable 100m", 5)]),
    ("2025-03-21", "Berlin Automation Works", "Lyon Project Office", "Ines Boussaid", "Road Express", Decimal("67.00"), Decimal("20.00"), "Anti-static packing", "30 days transfer", "DAP Lyon", [("Industrial Relay Module", 10), ("PLC Expansion Module", 2)]),
    ("2025-04-02", "Shanghai Tech Supplies", "Paris Operations Team", "Yasmine Kaci", "Sea Freight", Decimal("155.00"), Decimal("20.00"), "Export carton", "45 days transfer", "CIF Marseille", [("Shielded Signal Cable 100m", 12), ("PLC Expansion Module", 4)]),
    ("2025-04-10", "Istanbul Industrial Parts", "Marseille Maintenance Hub", "Sonia Merabet", "Road Transport", Decimal("98.00"), Decimal("20.00"), "Standard packing", "30 days transfer", "DAP Marseille", [("Industrial Pressure Sensor", 9), ("Industrial Relay Module", 3)]),
    ("2025-04-18", "Berlin Automation Works", "Paris Operations Team", "Nora Salem", "Road Express", Decimal("73.00"), Decimal("20.00"), "Protective foam packing", "30 days transfer", "DAP Paris", [("Temperature Transmitter", 7), ("PLC Expansion Module", 3)]),
    ("2025-05-05", "Shanghai Tech Supplies", "Lyon Project Office", "Nadia Benali", "Air Freight", Decimal("86.00"), Decimal("20.00"), "EXW", "30 days transfer", "DAP Lyon", [("Industrial Pressure Sensor", 11)]),
    ("2025-05-13", "Istanbul Industrial Parts", "Paris Operations Team", "Karim Haddad", "Road Transport", Decimal("104.00"), Decimal("20.00"), "Reinforced pallet", "45 days transfer", "CPT Paris", [("Stainless Control Valve", 2), ("Shielded Signal Cable 100m", 7), ("Industrial Relay Module", 2)]),
    ("2025-05-22", "Berlin Automation Works", "Marseille Maintenance Hub", "Ines Boussaid", "Road Express", Decimal("80.00"), Decimal("20.00"), "Factory sealed", "60 days transfer", "FCA Berlin", [("Temperature Transmitter", 10), ("Industrial Relay Module", 5)]),
    ("2025-06-03", "Shanghai Tech Supplies", "Paris Operations Team", "Yasmine Kaci", "Sea Freight", Decimal("132.00"), Decimal("20.00"), "Export carton", "30 days transfer", "CIF Marseille", [("PLC Expansion Module", 6), ("Shielded Signal Cable 100m", 6)]),
    ("2025-06-12", "Istanbul Industrial Parts", "Lyon Project Office", "Sonia Merabet", "Road Transport", Decimal("94.00"), Decimal("20.00"), "Standard export packing", "30 days transfer", "DAP Lyon", [("Industrial Pressure Sensor", 8), ("Stainless Control Valve", 2)]),
    ("2025-06-25", "Berlin Automation Works", "Paris Operations Team", "Nora Salem", "Road Express", Decimal("78.00"), Decimal("20.00"), "Anti-static packing", "30 days transfer", "DAP Paris", [("Temperature Transmitter", 5), ("PLC Expansion Module", 5), ("Industrial Relay Module", 4)]),
    ("2025-07-04", "Shanghai Tech Supplies", "Marseille Maintenance Hub", "Nadia Benali", "Air Freight", Decimal("89.00"), Decimal("20.00"), "EXW", "30 days transfer", "DAP Marseille", [("Industrial Pressure Sensor", 6), ("Temperature Transmitter", 6)]),
    ("2025-07-16", "Istanbul Industrial Parts", "Paris Operations Team", "Karim Haddad", "Road Transport", Decimal("117.00"), Decimal("20.00"), "Reinforced pallet", "50% advance / 50% on shipment", "CPT Paris", [("Shielded Signal Cable 100m", 10), ("Stainless Control Valve", 3)]),
    ("2025-07-28", "Berlin Automation Works", "Lyon Project Office", "Ines Boussaid", "Road Express", Decimal("82.00"), Decimal("20.00"), "Factory sealed", "45 days transfer", "DAP Lyon", [("Industrial Relay Module", 8), ("Temperature Transmitter", 4)]),
    ("2025-08-06", "Shanghai Tech Supplies", "Paris Operations Team", "Yasmine Kaci", "Sea Freight", Decimal("146.00"), Decimal("20.00"), "Export carton", "45 days transfer", "CIF Le Havre", [("Shielded Signal Cable 100m", 14), ("PLC Expansion Module", 3)]),
    ("2025-08-19", "Istanbul Industrial Parts", "Marseille Maintenance Hub", "Sonia Merabet", "Road Transport", Decimal("101.00"), Decimal("20.00"), "Standard packing", "30 days transfer", "DAP Marseille", [("Industrial Pressure Sensor", 10), ("Industrial Relay Module", 4)]),
    ("2025-08-27", "Berlin Automation Works", "Paris Operations Team", "Nora Salem", "Road Express", Decimal("75.00"), Decimal("20.00"), "Protective foam packing", "30 days transfer", "DAP Paris", [("Temperature Transmitter", 9), ("PLC Expansion Module", 2)]),
    ("2025-09-09", "Shanghai Tech Supplies", "Lyon Project Office", "Nadia Benali", "Air Freight", Decimal("93.00"), Decimal("20.00"), "EXW", "30 days transfer", "DAP Lyon", [("Industrial Pressure Sensor", 12), ("PLC Expansion Module", 1)]),
    ("2025-09-18", "Istanbul Industrial Parts", "Paris Operations Team", "Karim Haddad", "Road Transport", Decimal("120.00"), Decimal("20.00"), "Reinforced pallet", "45 days transfer", "CPT Paris", [("Stainless Control Valve", 5), ("Shielded Signal Cable 100m", 4)]),
    ("2025-09-30", "Berlin Automation Works", "Marseille Maintenance Hub", "Ines Boussaid", "Road Express", Decimal("84.00"), Decimal("20.00"), "Factory sealed", "60 days transfer", "FCA Berlin", [("Temperature Transmitter", 6), ("Industrial Relay Module", 7)]),
    ("2025-10-14", "Shanghai Tech Supplies", "Paris Operations Team", "Yasmine Kaci", "Sea Freight", Decimal("138.00"), Decimal("20.00"), "Export carton", "30 days transfer", "CIF Marseille", [("Shielded Signal Cable 100m", 9), ("Industrial Pressure Sensor", 5), ("Temperature Transmitter", 3)]),
    ("2025-11-06", "Istanbul Industrial Parts", "Lyon Project Office", "Sonia Merabet", "Road Transport", Decimal("97.00"), Decimal("20.00"), "Standard export packing", "30 days transfer", "DAP Lyon", [("Industrial Relay Module", 9), ("Stainless Control Valve", 2)]),
    ("2025-12-03", "Berlin Automation Works", "Paris Operations Team", "Nora Salem", "Road Express", Decimal("79.00"), Decimal("20.00"), "Anti-static packing", "30 days transfer", "DAP Paris", [("Temperature Transmitter", 11), ("PLC Expansion Module", 4)]),
]


class Command(BaseCommand):
    help = "Create 30 purchase order examples for the year 2025."

    @transaction.atomic
    def handle(self, *args, **options):
        partners = self._seed_partners()
        products = self._seed_products()
        count = self._seed_purchase_orders(partners, products)
        self.stdout.write(self.style.SUCCESS(f"{count} purchase orders for 2025 created or updated successfully."))

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
                    "unit_price": data["unit_price"],
                    "sale_price": data["sale_price"],
                    "purchase_price": data["purchase_price"],
                },
            )
            products[product.description] = product

        return products

    def _seed_purchase_orders(self, partners, products):
        for index, spec in enumerate(ORDER_SPECS, start=1):
            (
                purchase_date,
                seller,
                requester,
                sent_by,
                shipment,
                freight,
                vat_percent,
                sales_condition,
                payment_condition,
                delivery_terms,
                items,
            ) = spec

            order, _ = PurchaseOrder.objects.update_or_create(
                purchase_number=f"PO/2025-SAMPLE-{index:04d}",
                defaults={
                    "purchase_date": purchase_date,
                    "seller": partners[seller],
                    "requester": partners[requester],
                    "sent_by": sent_by,
                    "shipment": shipment,
                    "freight": freight,
                    "vat_percent": vat_percent,
                    "sales_condition": sales_condition,
                    "payment_condition": payment_condition,
                    "delivery_terms": delivery_terms,
                },
            )

            PurchaseOrderItem.objects.filter(purchase_order=order).delete()

            for product_name, quantity in items:
                product = products[product_name]
                PurchaseOrderItem.objects.create(
                    purchase_order=order,
                    product=product,
                    description=product.description,
                    part_number=product.part_number or "",
                    quantity=quantity,
                    unit_price=product.purchase_price,
                )

        return len(ORDER_SPECS)
