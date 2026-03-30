document.addEventListener("DOMContentLoaded", function () {
    function addPartnerTypeToLink(linkId, partnerType) {
        const link = document.getElementById(linkId);

        if (!link) return;

        const url = new URL(link.href, window.location.origin);
        url.searchParams.set("partner_type", partnerType);
        link.href = url.toString();
    }

    addPartnerTypeToLink("add_id_seller", "seller");
    addPartnerTypeToLink("add_id_requester", "requester");
});