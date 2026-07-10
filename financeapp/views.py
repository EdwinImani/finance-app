from django.apps import apps
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse


ALLOWED_RELATED_LABELS = {
    ("partners", "partner"),
    ("products", "product"),
}


@staff_member_required
def related_object_label(request, app_label, model_name, object_id):
    model_key = (app_label, model_name)

    if model_key not in ALLOWED_RELATED_LABELS:
        return JsonResponse({"ok": False, "label": ""}, status=404)

    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return JsonResponse({"ok": False, "label": ""}, status=404)

    try:
        obj = model._default_manager.get(pk=object_id)
    except model.DoesNotExist:
        return JsonResponse({"ok": False, "label": ""}, status=404)

    label = str(obj)

    return JsonResponse({"ok": True, "label": label})


def server_check(request):
    return JsonResponse(
        {
            "ok": True,
            "host": request.get_host(),
            "base_dir": str(settings.BASE_DIR),
            "database_engine": settings.DATABASES["default"]["ENGINE"],
            "database_name": str(settings.DATABASES["default"]["NAME"]),
            "marker": "finance-app-server-check-2026-07-10",
        }
    )
