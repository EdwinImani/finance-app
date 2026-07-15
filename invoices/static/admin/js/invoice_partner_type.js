document.addEventListener("DOMContentLoaded", function () {
    function currentReturnUrl() {
        return window.location.pathname + window.location.search;
    }

    function preparePartnerLink(link, partnerType) {
        if (!link) {
            return;
        }

        const url = new URL(link.href, window.location.origin);
        url.searchParams.delete("_popup");
        url.searchParams.set("_return_to", currentReturnUrl());

        if (partnerType) {
            url.searchParams.set("partner_type", partnerType);
        }

        link.href = url.toString();
    }

    function preparePartnerField(fieldId, type) {
        const addLink = document.getElementById(`add_${fieldId}`);
        const changeLink = document.getElementById(`change_${fieldId}`);

        preparePartnerLink(addLink, type);
        preparePartnerLink(changeLink, "");

        document.getElementById(`view_${fieldId}`)?.remove();
        document.getElementById(`delete_${fieldId}`)?.remove();

        [addLink, changeLink].forEach(function(link) {
            if (!link || link.dataset.partnerSamePageBound === "true") {
                return;
            }

            link.dataset.partnerSamePageBound = "true";
            link.addEventListener("click", function(event) {
                preparePartnerLink(link, link === addLink ? type : "");
                event.preventDefault();
                event.stopImmediatePropagation();
                window.location.href = link.href;
            }, true);
        });
    }

    function setPartnerType(linkId, type) {

        const link = document.getElementById(linkId);

        if (!link) return;

        const url = new URL(link.href, window.location.origin);

        url.searchParams.set("partner_type", type);

        link.href = url.toString();
    }

    setPartnerType("add_id_importer", "importer");
    setPartnerType("add_id_end_user", "enduser");
    preparePartnerField("id_importer", "importer");
    preparePartnerField("id_end_user", "enduser");

});
