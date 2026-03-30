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
        "description": "Maghreb Import Distribution",
        "partner_type": "importer",
        "email": "contact@mid.example",
        "website": "https://mid.example",
        "addresses": ["102 Route d'Oran, Alger, Algeria"],
        "phones": ["+213 21 45 67 89"],
    },
    {
        "description": "Sahara Energy Services",
        "partner_type": "enduser",
        "email": "procurement@sahara-energy.example",
        "website": "https://sahara-energy.example",
        "addresses": ["Zone Industrielle Sud, Hassi Messaoud, Algeria"],
        "phones": ["+213 29 90 11 22"],
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
]


PURCHASE_ORDERS = [
    {
        "purchase_number": "PO/2026-DEMO-0001",
        "purchase_date": "2026-01-15",
        "seller": "Shanghai Tech Supplies",
        "requester": "Paris Operations Team",
        "sent_by": "Nadia Benali",
        "shipment": "Air Freight",
        "freight": Decimal("85.00"),
        "vat_percent": Decimal("20.00"),
        "sales_condition": "Ex works",
        "payment_condition": "30 days transfer",
        "delivery_terms": "DAP Paris",
        "items": [
            {"product": "Industrial Pressure Sensor", "quantity": 6},
            {"product": "PLC Expansion Module", "quantity": 3},
        ],
    },
    {
        "purchase_number": "PO/2026-DEMO-0002",
        "purchase_date": "2026-02-03",
        "seller": "Istanbul Industrial Parts",
        "requester": "Lyon Project Office",
        "sent_by": "Karim Haddad",
        "shipment": "Road Transport",
        "freight": Decimal("120.00"),
        "vat_percent": Decimal("20.00"),
        "sales_condition": "Standard packing",
        "payment_condition": "50% advance / 50% on shipment",
        "delivery_terms": "CPT Lyon",
        "items": [
            {"product": "Stainless Control Valve", "quantity": 4},
            {"product": "Shielded Signal Cable 100m", "quantity": 10},
        ],
    },
    {
        "purchase_number": "PO/2026-DEMO-0003",
        "purchase_date": "2026-03-10",
        "seller": "Shanghai Tech Supplies",
        "requester": "Paris Operations Team",
        "sent_by": "Ines Boussaid",
        "shipment": "Sea Freight",
        "freight": Decimal("240.00"),
        "vat_percent": Decimal("20.00"),
        "sales_condition": "Export carton",
        "payment_condition": "45 days transfer",
        "delivery_terms": "CIF Marseille",
        "items": [
            {"product": "Industrial Pressure Sensor", "quantity": 12},
            {"product": "Shielded Signal Cable 100m", "quantity": 5},
            {"product": "PLC Expansion Module", "quantity": 2, "unit_price": Decimal("235.00")},
        ],
    },
]

EXTRA_ORDER_SPECS = [
    ("2026-01-08", "Shanghai Tech Supplies", "Paris Operations Team", [("Industrial Pressure Sensor", 4), ("Shielded Signal Cable 100m", 2)], "Yasmine Kaci", "Air Freight", Decimal("65.00")),
    ("2026-01-19", "Istanbul Industrial Parts", "Lyon Project Office", [("Stainless Control Valve", 2), ("PLC Expansion Module", 3)], "Nora Salem", "Road Transport", Decimal("90.00")),
    ("2026-01-28", "Shanghai Tech Supplies", "Paris Operations Team", [("PLC Expansion Module", 5)], "Karim Haddad", "Air Freight", Decimal("70.00")),
    ("2026-02-06", "Istanbul Industrial Parts", "Paris Operations Team", [("Shielded Signal Cable 100m", 8), ("Industrial Pressure Sensor", 3)], "Sonia Merabet", "Road Transport", Decimal("80.00")),
    ("2026-02-12", "Shanghai Tech Supplies", "Lyon Project Office", [("Industrial Pressure Sensor", 10), ("PLC Expansion Module", 1)], "Yasmine Kaci", "Sea Freight", Decimal("130.00")),
    ("2026-02-18", "Istanbul Industrial Parts", "Paris Operations Team", [("Stainless Control Valve", 1), ("Shielded Signal Cable 100m", 6)], "Ines Boussaid", "Road Transport", Decimal("55.00")),
    ("2026-03-04", "Shanghai Tech Supplies", "Lyon Project Office", [("Industrial Pressure Sensor", 7), ("Shielded Signal Cable 100m", 3)], "Nadia Benali", "Air Freight", Decimal("95.00")),
    ("2026-03-16", "Istanbul Industrial Parts", "Paris Operations Team", [("Stainless Control Valve", 5)], "Karim Haddad", "Road Transport", Decimal("145.00")),
    ("2026-03-24", "Shanghai Tech Supplies", "Paris Operations Team", [("PLC Expansion Module", 6), ("Shielded Signal Cable 100m", 4)], "Sonia Merabet", "Sea Freight", Decimal("110.00")),
    ("2026-04-02", "Istanbul Industrial Parts", "Lyon Project Office", [("Industrial Pressure Sensor", 9), ("Stainless Control Valve", 2)], "Nora Salem", "Road Transport", Decimal("115.00")),
    ("2026-04-11", "Shanghai Tech Supplies", "Paris Operations Team", [("Shielded Signal Cable 100m", 12)], "Yasmine Kaci", "Sea Freight", Decimal("150.00")),
    ("2026-04-25", "Istanbul Industrial Parts", "Lyon Project Office", [("PLC Expansion Module", 4), ("Stainless Control Valve", 3)], "Ines Boussaid", "Road Transport", Decimal("125.00")),
    ("2026-05-03", "Shanghai Tech Supplies", "Paris Operations Team", [("Industrial Pressure Sensor", 14)], "Nadia Benali", "Air Freight", Decimal("105.00")),
    ("2026-05-14", "Istanbul Industrial Parts", "Paris Operations Team", [("Shielded Signal Cable 100m", 15), ("PLC Expansion Module", 2)], "Karim Haddad", "Road Transport", Decimal("98.00")),
    ("2026-05-28", "Shanghai Tech Supplies", "Lyon Project Office", [("Industrial Pressure Sensor", 5), ("Stainless Control Valve", 1)], "Sonia Merabet", "Sea Freight", Decimal("88.00")),
    ("2026-06-05", "Istanbul Industrial Parts", "Paris Operations Team", [("Stainless Control Valve", 6), ("Shielded Signal Cable 100m", 2)], "Yasmine Kaci", "Road Transport", Decimal("170.00")),
    ("2026-06-17", "Shanghai Tech Supplies", "Lyon Project Office", [("PLC Expansion Module", 8), ("Industrial Pressure Sensor", 2)], "Nora Salem", "Air Freight", Decimal("92.00")),
    ("2026-06-29", "Istanbul Industrial Parts", "Paris Operations Team", [("Shielded Signal Cable 100m", 20)], "Nadia Benali", "Road Transport", Decimal("140.00")),
    ("2026-07-07", "Shanghai Tech Supplies", "Paris Operations Team", [("Industrial Pressure Sensor", 11), ("PLC Expansion Module", 4)], "Ines Boussaid", "Sea Freight", Decimal("135.00")),
    ("2026-07-21", "Istanbul Industrial Parts", "Lyon Project Office", [("Stainless Control Valve", 2), ("Shielded Signal Cable 100m", 9), ("PLC Expansion Module", 1)], "Sonia Merabet", "Road Transport", Decimal("102.00")),
]


class Command(BaseCommand):
    help = "Create reusable demo data for partners, products and purchase orders."

    @transaction.atomic
    def handle(self, *args, **options):
        partners = self._seed_partners()
        products = self._seed_products()
        self._seed_purchase_orders(partners, products)
        self.stdout.write(self.style.SUCCESS("Demo data created or updated successfully."))

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
        all_orders = PURCHASE_ORDERS + self._build_extra_orders()

        for data in all_orders:
            order, _ = PurchaseOrder.objects.update_or_create(
                purchase_number=data["purchase_number"],
                defaults={
                    "purchase_date": data["purchase_date"],
                    "seller": partners[data["seller"]],
                    "requester": partners[data["requester"]],
                    "sent_by": data["sent_by"],
                    "shipment": data["shipment"],
                    "freight": data["freight"],
                    "vat_percent": data["vat_percent"],
                    "sales_condition": data["sales_condition"],
                    "payment_condition": data["payment_condition"],
                    "delivery_terms": data["delivery_terms"],
                },
            )

            PurchaseOrderItem.objects.filter(purchase_order=order).delete()

            for item_data in data["items"]:
                product = products[item_data["product"]]
                PurchaseOrderItem.objects.create(
                    purchase_order=order,
                    product=product,
                    description=product.description,
                    part_number=product.part_number or "",
                    quantity=item_data["quantity"],
                    unit_price=item_data.get("unit_price", product.purchase_price),
                )

    def _build_extra_orders(self):
        extra_orders = []

        for index, spec in enumerate(EXTRA_ORDER_SPECS, start=4):
            purchase_date, seller, requester, items, sent_by, shipment, freight = spec
            extra_orders.append(
                {
                    "purchase_number": f"PO/2026-DEMO-{index:04d}",
                    "purchase_date": purchase_date,
                    "seller": seller,
                    "requester": requester,
                    "sent_by": sent_by,
                    "shipment": shipment,
                    "freight": freight,
                    "vat_percent": Decimal("20.00"),
                    "sales_condition": "Demo stock replenishment",
                    "payment_condition": "30 days transfer",
                    "delivery_terms": "DAP France",
                    "items": [
                        {"product": product_name, "quantity": quantity}
                        for product_name, quantity in items
                    ],
                }
            )

        return extra_orders
