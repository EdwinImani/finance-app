import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product


class Command(BaseCommand):
    help = "Import products from a semicolon CSV without merging duplicate descriptions."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the products CSV file.")
        parser.add_argument(
            "--encoding",
            default="utf-8-sig",
            help="CSV file encoding. Defaults to utf-8-sig.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        rows = self.read_rows(csv_path, options["encoding"])
        generated_part_numbers = set(
            Product.objects.exclude(part_number__isnull=True)
            .exclude(part_number="")
            .values_list("part_number", flat=True)
        )

        created = 0
        generated_missing = 0

        with transaction.atomic():
            for line_number, row in rows:
                description = self.clean(row.get("product_name")) or self.clean(row.get("description"))
                if not description:
                    self.stdout.write(self.style.WARNING(f"Skipping line {line_number}: missing product_name"))
                    continue

                raw_part_number = self.clean(row.get("part_number"))
                part_number = raw_part_number

                if not part_number:
                    part_number = self.next_part_number("LEGACY", generated_part_numbers)
                    generated_missing += 1

                Product.objects.create(
                    description=description[:255],
                    part_number=part_number[:100],
                    hs_code=self.clean(row.get("hs_code"))[:20],
                    note=self.clean(row.get("note"))[:255],
                    unit_qty=self.parse_quantity(row.get("quantity")),
                    purchase_price=self.parse_decimal(row.get("purchase_price")),
                    sale_price=self.parse_decimal(row.get("sale_price")),
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported products: {created}"))
        self.stdout.write(f"Generated missing part numbers: {generated_missing}")

    def read_rows(self, csv_path, encoding):
        with csv_path.open("r", encoding=encoding, newline="") as handle:
            first_line = handle.readline()
            if not first_line.startswith("sep="):
                handle.seek(0)

            reader = csv.DictReader(handle, delimiter=";")
            return list(enumerate(reader, start=2))

    def next_part_number(self, prefix, generated_part_numbers):
        index = 1
        while True:
            candidate = f"{prefix}-{index:04d}"
            if candidate not in generated_part_numbers:
                generated_part_numbers.add(candidate)
                return candidate
            index += 1

    def clean(self, value):
        return (value or "").strip()

    def parse_decimal(self, value):
        value = self.clean(value).replace(",", ".")
        if not value:
            return Decimal("0")
        try:
            return Decimal(value)
        except InvalidOperation:
            return Decimal("0")

    def parse_quantity(self, value):
        value = self.clean(value).replace(",", ".")
        if not value:
            return 0
        try:
            return int(Decimal(value))
        except (InvalidOperation, ValueError):
            return 0
