from django.urls import path
from . import views

urlpatterns = [
    path('new/proforma/', views.create_proforma_invoice, name='create_proforma_invoice'),
    path('new/commercial/', views.create_commercial_invoice, name='create_commercial_invoice'),
]
