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

    function isMeaningfulValue(value) {
        const normalized = String(value || "").trim();
        return normalized !== "" && !["0", "0.00", "0,00", "-"].includes(normalized);
    }

    function hasPendingNewInlineRows(form) {
        const inlineRows = form.querySelectorAll(".inline-related");

        return Array.from(inlineRows).some(function (row) {
            const inlineIdField = row.querySelector('input[type="hidden"][name$="-id"]');

            if (!inlineIdField || inlineIdField.value) {
                return false;
            }

            const deleteField = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
            if (deleteField && deleteField.checked) {
                return false;
            }

            const fields = row.querySelectorAll("input, select, textarea");
            return Array.from(fields).some(function (field) {
                if (!field.name || field.disabled) {
                    return false;
                }
                if (field.type === "hidden" || field.type === "checkbox" || field.name.endsWith("-DELETE")) {
                    return false;
                }
                if (field.tagName === "SELECT") {
                    return Boolean(field.value);
                }
                return isMeaningfulValue(field.value);
            });
        });
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
        let hasDirtyInlineChanges = false;

        function autosave() {
            if (isSaving || isSubmitting) {
                return;
            }

            if (hasDirtyInlineChanges) {
                setStatus("Click Save to save item lines", "");
                return;
            }

            if (hasPendingNewInlineRows(form)) {
                setStatus("Click Save once to create the new line", "");
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

        function markInlineDirty(event) {
            if (!event.target.closest(".inline-related")) {
                return false;
            }
            hasDirtyInlineChanges = true;
            window.clearTimeout(timer);
            setStatus("Click Save to save item lines", "");
            return true;
        }

        form.addEventListener("submit", function () {
            isSubmitting = true;
            window.clearTimeout(timer);
        });
        form.addEventListener("input", function (event) {
            if (markInlineDirty(event)) {
                return;
            }
            scheduleAutosave();
        }, true);
        form.addEventListener("change", function (event) {
            if (markInlineDirty(event)) {
                return;
            }
            scheduleAutosave();
        }, true);
    });
})();
