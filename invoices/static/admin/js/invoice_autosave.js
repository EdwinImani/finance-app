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
        let saveAgain = false;

        function autosave() {
            if (isSubmitting) {
                return;
            }

            if (isSaving) {
                saveAgain = true;
                return;
            }

            isSaving = true;
            saveAgain = false;
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
                    if (saveAgain && !isSubmitting) {
                        scheduleAutosave(250);
                    }
                });
        }

        function scheduleAutosave(delay) {
            if (isSubmitting) {
                return;
            }
            window.clearTimeout(timer);
            timer = window.setTimeout(autosave, delay == null ? 1200 : delay);
        }

        function scheduleAutosaveSoon() {
            scheduleAutosave(250);
        }

        function scheduleAutosaveAfterDomUpdate() {
            window.setTimeout(scheduleAutosaveSoon, 0);
        }

        function shouldIgnoreClick(target) {
            return (
                target.closest(".related-widget-wrapper-link") ||
                target.closest(".select2-selection") ||
                target.closest(".select2-results__option")
            );
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
        form.addEventListener("click", function (event) {
            const target = event.target;
            if (!target || shouldIgnoreClick(target)) {
                return;
            }

            if (
                target.matches("input[type='checkbox'], input[type='radio'], button, input[type='button']") ||
                target.closest(".invoice-line-delete") ||
                target.closest(".po-inline-delete") ||
                target.closest(".deletelink") ||
                target.closest(".inline-deletelink")
            ) {
                scheduleAutosaveAfterDomUpdate();
            }
        }, true);

        document.addEventListener("formset:added", scheduleAutosaveAfterDomUpdate);
        document.addEventListener("formset:removed", scheduleAutosaveAfterDomUpdate);

        if (window.django && window.django.jQuery) {
            const $ = window.django.jQuery;
            $(document).on(
                "select2:select select2:unselect select2:clear select2:close",
                "select",
                function () {
                    scheduleAutosaveAfterDomUpdate();
                }
            );
            $(document).on("formset:added formset:removed", function () {
                scheduleAutosaveAfterDomUpdate();
            });
        }

        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "hidden") {
                window.clearTimeout(timer);
                autosave();
            }
        });
    });
})();
