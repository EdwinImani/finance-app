from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from partners.models import Partner, PartnerAddress, PartnerPhone
from products.models import Product


PARTNERS = [
    ("Aster Import Group", "importer"),
    ("Blue Harbor Trading", "seller"),
    ("Cedar Supply Partners", "requester"),
    ("Delta Medical Buyer", "enduser"),
    ("Euro Bridge Logistics", "importer"),
    ("Falcon Industrial Sales", "seller"),
    ("Greenline Procurement", "requester"),
    ("Helios End Client", "enduser"),
    ("Iris Components", "importer"),
    ("Juno Distribution", "seller"),
    ("Kappa Request Office", "requester"),
    ("Lumen Global Import", "enduser"),
    ("Mistral Seller Hub", "importer"),
    ("Nova End User Services", "seller"),
    ("Orion Purchase Desk", "requester"),
    ("Polar Trade House", "enduser"),
    ("Quartz Equipment", "importer"),
    ("Riviera Import Export", "seller"),
    ("Solstice Client Group", "requester"),
    ("Terra Supplier Network", "enduser"),
]


PRODUCTS = [
    ("Precision Sensor Module", "853710"),
    ("Industrial Control Board", "903180"),
    ("Hydraulic Valve Assembly", "848180"),
    ("Thermal Printer Unit", "844332"),
    ("Optical Cable Harness", "854442"),
    ("Compact Power Inverter", "850440"),
    ("Medical Grade Filter", "842199"),
    ("Stainless Pump Rotor", "841391"),
    ("Network Relay Gateway", "851762"),
    ("Safety Switch Module", "853650"),
    ("Laboratory Mixing Head", "847982"),
    ("Servo Motor Encoder", "903289"),
    ("Battery Protection PCB", "853690"),
    ("Digital Flow Meter", "902610"),
    ("Pressure Regulator Kit", "848110"),
    ("RF Antenna Coupler", "852910"),
    ("Packaging Seal Roller", "842290"),
    ("Cooling Fan Cartridge", "841459"),
    ("Laser Alignment Lens", "900190"),
    ("Smart Meter Terminal", "902830"),
]


class Command(BaseCommand):
    help = "Seed 20 demo partners and 20 demo products with 20-digit part numbers."

    @transaction.atomic
    def handle(self, *args, **options):
        partners_created = self._seed_partners()
        products_created = self._seed_products()

        self.stdout.write(
            self.style.SUCCESS(
                "Demo catalog ready: "
                f"{partners_created} partners created, "
                f"{products_created} products created."
            )
        )

    def _seed_partners(self):
        created_count = 0

        for index, (description, partner_type) in enumerate(PARTNERS, start=1):
            partner, created = Partner.objects.update_or_create(
                description=description,
                defaults={
                    "partner_type": partner_type,
                    "email": f"contact{index:02d}@demo-finance.local",
                    "fax": f"+33 1 45 00 {index:02d} {index:02d}",
                    "website": f"https://partner{index:02d}.demo-finance.local",
                },
            )
            created_count += int(created)

            PartnerAddress.objects.update_or_create(
                partner=partner,
                address=f"{10 + index} Avenue des Affaires, 750{index % 10}0 Paris, France",
            )
            PartnerPhone.objects.update_or_create(
                partner=partner,
                phone_number=f"+33 6 20 30 {index:02d} {index:02d}",
            )

        return created_count

    def _seed_products(self):
        created_count = 0

        for index, (name, hs_code) in enumerate(PRODUCTS, start=1):
            part_number = f"20260615{index:012d}"
            _, created = Product.objects.update_or_create(
                part_number=part_number,
                defaults={
                    "description": f"Demo {name}",
                    "hs_code": hs_code,
                    "note": "Generated demo product data",
                    "unit_qty": 10 + index,
                    "sale_price": Decimal("100.00") + Decimal(index * 17),
                    "purchase_price": Decimal("60.00") + Decimal(index * 11),
                },
            )
            created_count += int(created)

        return created_count
