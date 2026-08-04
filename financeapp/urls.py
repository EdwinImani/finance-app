"""
URL configuration for financeapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from django.conf import settings
from django.conf.urls.static import static
from financeapp import views

admin.site.site_header = "VERTEA S.A.S"
admin.site.site_title = "VERTEA S.A.S"
admin.site.index_title = "Administration"

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/login/', permanent=False), name='home'),
    path(
        'admin/related-object-label/<str:app_label>/<str:model_name>/<str:object_id>/',
        views.related_object_label,
        name='related_object_label',
    ),
    path('admin/', admin.site.urls),
    path('purchase/', include('purchase.urls')),
    path('invoices/', include('invoices.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('__server_check__/', views.server_check, name='server_check'),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




