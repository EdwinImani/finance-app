from django.apps import apps
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

    if model_key == ("products", "product"):
        label = obj.description
    else:
        label = str(obj)

    return JsonResponse({"ok": True, "label": label})
