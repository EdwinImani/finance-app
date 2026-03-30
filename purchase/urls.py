from django.urls import path
from .views import product_info
from .views_report import purchase_home, purchase_report_filter, purchase_report_result


urlpatterns = [
    path("", purchase_home, name="purchase_home"),

    # product info
    path(
        "product-info/<int:product_id>/",
        product_info,
        name="product_info"
    ),

    # page filtre report
    path(
        "report/",
        purchase_report_filter,
        name="purchase_report_filter"
    ),

    # page résultat report
    path(
        "report/result/",
        purchase_report_result,
        name="purchase_report_result"
    ),
]