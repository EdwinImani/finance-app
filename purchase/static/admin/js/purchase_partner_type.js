document.addEventListener("DOMContentLoaded", function () {
    function currentReturnUrl() {
        const url = new URL(window.location.href);
        [
            "_selected_partner_field",
            "_selected_partner_id",
            "_selected_partner_label",
            "_selected_product_field",
            "_selected_product_id",
            "_selected_product_label",
        ].forEach(function(key) {
            url.searchParams.delete(key);
        });
        const adminReturnInput = document.querySelector('input[name="admin_return_url"]');
        if (adminReturnInput && adminReturnInput.value) {
            url.searchParams.set("admin_return_url", adminReturnInput.value);
        }
        return url.pathname + url.search;
    }

    function preparePartnerLink(link, partnerType, fieldId) {
        if (!link) {
            return;
        }

        const url = new URL(link.href, window.location.origin);
        url.searchParams.delete("_popup");
        url.searchParams.set("_return_to", currentReturnUrl());
        url.searchParams.set("_return_field", fieldId);

        if (partnerType) {
            url.searchParams.set("partner_type", partnerType);
        }

        link.href = url.toString();
    }

    function preparePartnerField(fieldId, partnerType) {
        const addLink = document.getElementById(`add_${fieldId}`);
        const changeLink = document.getElementById(`change_${fieldId}`);

        preparePartnerLink(addLink, partnerType, fieldId);
        preparePartnerLink(changeLink, "", fieldId);

        document.getElementById(`view_${fieldId}`)?.remove();
        document.getElementById(`delete_${fieldId}`)?.remove();

        [addLink, changeLink].forEach(function(link) {
            if (!link || link.dataset.partnerSamePageBound === "true") {
                return;
            }

            link.dataset.partnerSamePageBound = "true";
            link.addEventListener("click", function(event) {
                preparePartnerLink(link, link === addLink ? partnerType : "", fieldId);
                event.preventDefault();
                event.stopImmediatePropagation();
                const targetHref = link.href;
                const autosave = window.invoiceAutosaveNow ? window.invoiceAutosaveNow() : Promise.resolve();
                autosave
                    .catch(function () {})
                    .finally(function () {
                        window.location.href = targetHref;
                    });
            }, true);
        });
    }

    function addPartnerTypeToLink(linkId, partnerType) {
        const link = document.getElementById(linkId);

        if (!link) return;

        const url = new URL(link.href, window.location.origin);
        url.searchParams.set("partner_type", partnerType);
        link.href = url.toString();
    }

    addPartnerTypeToLink("add_id_seller", "seller");
    addPartnerTypeToLink("add_id_requester", "requester");
    preparePartnerField("id_seller", "seller");
    preparePartnerField("id_requester", "requester");

    const params = new URLSearchParams(window.location.search);
    const selectedFieldId = params.get("_selected_partner_field");
    const selectedPartnerId = params.get("_selected_partner_id");
    const selectedPartnerLabel = params.get("_selected_partner_label");
    if (selectedFieldId && selectedPartnerId) {
        const field = document.getElementById(selectedFieldId);
        if (field && field.tagName === "SELECT") {
            let option = Array.from(field.options).find(function(item) {
                return item.value === selectedPartnerId;
            });
            if (!option) {
                option = new Option(selectedPartnerLabel || selectedPartnerId, selectedPartnerId, true, true);
                field.appendChild(option);
            }
            field.value = selectedPartnerId;
            if (window.django && window.django.jQuery) {
                window.django.jQuery(field).trigger("change");
            } else {
                field.dispatchEvent(new Event("change", { bubbles: true }));
            }
        }
    }
});
