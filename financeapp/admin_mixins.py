from django.contrib.admin.views.main import ChangeList


class PageSizeChangeList(ChangeList):

    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params=params)
        lookup_params.pop("per_page", None)
        return lookup_params


class PageSizeAdminMixin:
    list_per_page = 10
    page_size_options = (10, 15, 20, 25, 50, 100)
    max_list_per_page = 500
    changelist_template = "admin/change_list_with_page_size.html"

    def _default_list_per_page(self):
        return getattr(self, "list_per_page", 100)

    def get_list_per_page(self, request):
        value = request.GET.get("per_page")

        if not value:
            return self._default_list_per_page()

        try:
            per_page = int(value)
        except (TypeError, ValueError):
            return self._default_list_per_page()

        if per_page < 1:
            return self._default_list_per_page()

        return min(per_page, self.max_list_per_page)

    def changelist_view(self, request, extra_context=None):
        current_per_page = self.get_list_per_page(request)
        options = []

        for option in self.page_size_options:
            if option not in options:
                options.append(option)

        if current_per_page not in options:
            options.append(current_per_page)

        extra_context = extra_context or {}
        extra_context["page_size_options"] = sorted(options)
        extra_context["current_per_page"] = current_per_page

        preserved_filters = []

        for key, values in request.GET.lists():
            if key in {"per_page", "p"}:
                continue

            for value in values:
                preserved_filters.append((key, value))

        extra_context["page_size_preserved_filters"] = preserved_filters

        return super().changelist_view(request, extra_context=extra_context)

    def get_changelist(self, request, **kwargs):
        return PageSizeChangeList

    def get_changelist_instance(self, request):
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)

        if self.get_actions(request):
            list_display = ["action_checkbox", *list_display]

        sortable_by = self.get_sortable_by(request)
        ChangeList = self.get_changelist(request)

        return ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.get_list_filter(request),
            self.date_hierarchy,
            self.get_search_fields(request),
            self.get_list_select_related(request),
            self.get_list_per_page(request),
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
            self.search_help_text,
        )
