document.addEventListener("DOMContentLoaded", function () {

    function setPartnerType(linkId, type) {

        const link = document.getElementById(linkId);

        if (!link) return;

        const url = new URL(link.href, window.location.origin);

        url.searchParams.set("partner_type", type);

        link.href = url.toString();
    }

    setPartnerType("add_id_importer", "importer");
    setPartnerType("add_id_end_user", "enduser");

});