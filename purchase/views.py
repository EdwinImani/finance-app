from django.http import JsonResponse
from products.models import Product


def product_info(request, product_id):

    try:
        product = Product.objects.get(id=product_id)

        data = {
            "description": product.description,
            "part_number": product.part_number,
            "hs_code": product.hs_code,
            "note": product.note,
            "unit_qty": str(product.unit_qty),
            "sale_price": str(product.sale_price),
            "purchase_price": str(product.purchase_price),
        }

        return JsonResponse(data)

    except Product.DoesNotExist:
        return JsonResponse({})
