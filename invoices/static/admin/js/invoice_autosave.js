(function () {
    function getConfig() {
        return window.invoiceAutosaveConfig || null;
    }

    function getForm() {
        return (
            document.querySelector("form#proformainvoice_form") ||
            document.querySelector("form#commercialinvoice_form") ||
            document.querySelector("#content-main form")
        );
    }

    function getStatusNode() {
        return document.querySelector("[data-invoice-autosave-status]");
    }

    function setStatus(message, className) {
        const node = getStatusNode();
        if (!node) {
            return;
        }
        node.textContent = message;
        node.classList.remove("is-saving", "is-error");
        if (className) {
            node.classList.add(className);
        }
    }

    function serializeForm(form) {
        return new FormData(form);
    }

    document.addEventListener("DOMContentLoaded", function () {
        const config = getConfig();
        const form = getForm();

        if (!config || !config.url || !form) {
            return;
        }

        let timer = null;
        let isSaving = false;
        let isSubmitting = false;

        function autosave() {
            if (isSaving || isSubmitting) {
                return;
            }

            isSaving = true;
            setStatus("Autosaving...", "is-saving");

            fetch(config.url, {
                method: "POST",
                body: serializeForm(form),
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { ok: response.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (!result.ok || !result.data.ok) {
                        throw new Error("Autosave failed");
                    }
                    setStatus("Saved " + (result.data.saved_at || ""), "");
                })
                .catch(function () {
                    setStatus("Autosave needs a valid form", "is-error");
                })
                .finally(function () {
                    isSaving = false;
                });
        }

        function scheduleAutosave() {
            if (isSubmitting) {
                return;
            }
            window.clearTimeout(timer);
            timer = window.setTimeout(autosave, 1200);
        }

        form.addEventListener("submit", function () {
            isSubmitting = true;
            window.clearTimeout(timer);
        });
        form.addEventListener("input", function (event) {
            scheduleAutosave();
        }, true);
        form.addEventListener("change", function (event) {
            scheduleAutosave();
        }, true);
    });
})();
