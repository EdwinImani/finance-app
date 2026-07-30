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
        const formData = new FormData(form);
        if (window.financeNumberFormatting && window.financeNumberFormatting.normalizeFormData) {
            return window.financeNumberFormatting.normalizeFormData(formData);
        }
        return formData;
    }

    function hasCheckedDelete(form) {
        return Boolean(form.querySelector('input[name$="-DELETE"]:checked'));
    }

    function syncSavedInlineIds(form, inlineObjects) {
        const highestSavedIndexByPrefix = {};

        (inlineObjects || []).forEach(function (item) {
            if (!item || !item.form_prefix || !item.id) {
                return;
            }

            Array.from(form.elements).forEach(function (field) {
                if (field.name === item.form_prefix + "-id" && !field.value) {
                    field.value = item.id;
                }
            });

            const prefix = item.prefix;
            const index = parseInt(item.form_prefix.slice(prefix.length + 1), 10);
            if (!Number.isNaN(index)) {
                highestSavedIndexByPrefix[prefix] = Math.max(highestSavedIndexByPrefix[prefix] || 0, index + 1);
            }
        });

        Object.keys(highestSavedIndexByPrefix).forEach(function (prefix) {
            Array.from(form.elements).forEach(function (field) {
                if (field.name !== prefix + "-INITIAL_FORMS") {
                    return;
                }

                const current = parseInt(field.value || "0", 10);
                field.value = String(Math.max(current || 0, highestSavedIndexByPrefix[prefix]));
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
        let saveAgain = false;
        let activeSavePromise = null;

        function autosave(options) {
            const settings = options || {};

            if (isSubmitting && !settings.force) {
                return Promise.resolve(false);
            }

            if (isSaving) {
                saveAgain = true;
                return activeSavePromise ? activeSavePromise.then(function () {
                    return settings.force ? autosave(settings) : true;
                }) : Promise.resolve(false);
            }

            isSaving = true;
            saveAgain = false;
            const reloadAfterSave = hasCheckedDelete(form) && !settings.suppressReload;
            setStatus("Autosaving...", "is-saving");

            activeSavePromise = fetch(config.url, {
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
                    syncSavedInlineIds(form, result.data.inline_objects);
                    setStatus("Saved " + (result.data.saved_at || ""), "");
                    if (reloadAfterSave) {
                        window.location.reload();
                    }
                })
                .catch(function () {
                    setStatus("Autosave needs a valid form", "is-error");
                    if (settings.force) {
                        throw new Error("Autosave failed");
                    }
                    return false;
                })
                .finally(function () {
                    isSaving = false;
                    activeSavePromise = null;
                    if (saveAgain && !isSubmitting) {
                        scheduleAutosave(250);
                    }
                });

            return activeSavePromise;
        }

        window.invoiceAutosaveNow = function () {
            window.clearTimeout(timer);
            return autosave({ force: true, suppressReload: true });
        };

        function autosaveOnPageExit() {
            if (isSubmitting) {
                return;
            }

            window.clearTimeout(timer);
            const payload = serializeForm(form);

            if (navigator.sendBeacon && navigator.sendBeacon(config.url, payload)) {
                return;
            }

            try {
                fetch(config.url, {
                    method: "POST",
                    body: payload,
                    credentials: "same-origin",
                    keepalive: true,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
            } catch (error) {
                // The browser may reject keepalive for large forms; the regular autosave still covers normal editing.
            }
        }

        function scheduleAutosave(delay) {
            if (isSubmitting) {
                return;
            }
            window.clearTimeout(timer);
            timer = window.setTimeout(autosave, delay == null ? 180 : delay);
        }

        function scheduleAutosaveSoon() {
            scheduleAutosave(80);
        }

        window.invoiceAutosaveTouch = scheduleAutosaveSoon;

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

        document.addEventListener("click", function (event) {
            const saveButton = event.target && event.target.closest(
                "input[type='submit'][name='_save'], button[type='submit'][name='_save']"
            );

            if (!saveButton || saveButton.form !== form) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            window.clearTimeout(timer);

            autosave({ force: true, suppressReload: true })
                .then(function () {
                    isSubmitting = true;
                    if (
                        window.financeNumberFormatting &&
                        window.financeNumberFormatting.normalizeForm
                    ) {
                        window.financeNumberFormatting.normalizeForm(form);
                    }
                    let saveMarker = form.querySelector(
                        "input[type='hidden'][name='_save'][data-autosave-save-marker]"
                    );
                    if (!saveMarker) {
                        saveMarker = document.createElement("input");
                        saveMarker.type = "hidden";
                        saveMarker.name = "_save";
                        saveMarker.dataset.autosaveSaveMarker = "true";
                        form.appendChild(saveMarker);
                    }
                    saveMarker.value = saveButton.value || "Save";
                    HTMLFormElement.prototype.submit.call(form);
                })
                .catch(function () {
                    setStatus("Autosave needs a valid form", "is-error");
                });
        }, true);

        form.addEventListener("submit", function () {
            isSubmitting = true;
            window.clearTimeout(timer);
        });
        document.addEventListener("click", function (event) {
            const link = event.target && event.target.closest("[data-autosave-before-open]");
            if (!link) {
                return;
            }

            event.preventDefault();
            window.clearTimeout(timer);

            autosave({ force: true, suppressReload: true })
                .then(function () {
                    window.open(link.href, link.target || "_blank");
                })
                .catch(function () {
                    window.alert("Autosave needs a valid form before opening the PDF.");
                });
        }, true);
        form.addEventListener("input", function (event) {
            scheduleAutosaveSoon();
        }, true);
        form.addEventListener("change", function (event) {
            scheduleAutosaveSoon();
        }, true);
        form.addEventListener("blur", function (event) {
            scheduleAutosaveSoon();
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
        document.addEventListener("invoice:inline-product-updated", scheduleAutosaveAfterDomUpdate);

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
                autosaveOnPageExit();
            }
        });
        window.addEventListener("pagehide", autosaveOnPageExit);
        window.addEventListener("beforeunload", autosaveOnPageExit);
    });
})();
