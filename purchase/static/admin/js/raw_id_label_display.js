(function () {
    const FIELD_MODELS = {
        product: { app: "products", model: "product", placeholder: "Choose product" },
        seller: { app: "partners", model: "partner", placeholder: "Choose partner" },
        importer: { app: "partners", model: "partner", placeholder: "Choose partner" },
        end_user: { app: "partners", model: "partner", placeholder: "Choose partner" },
    };

    function installStyle() {
        if (document.getElementById("raw-id-label-display-style")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "raw-id-label-display-style";
        style.textContent = `
            .raw-id-label-display {
                box-sizing: border-box;
                min-width: 240px;
                width: min(100%, 520px);
                min-height: 36px;
                padding: 8px 12px;
                border: 1px solid #f0cda8;
                border-radius: 12px;
                background: #fff;
                color: #273241;
                font-size: 14px;
                line-height: 1.25;
                cursor: pointer;
                box-shadow: 0 1px 5px rgba(234, 142, 44, 0.12);
            }
            .raw-id-label-display:focus {
                outline: 2px solid rgba(234, 142, 44, 0.22);
                border-color: #e58a24;
            }
            .raw-id-label-display.is-empty {
                color: #7d8794;
            }
            .raw-id-label-wrapper {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                max-width: 100%;
            }
            .raw-id-label-wrapper .related-lookup {
                flex: 0 0 auto;
            }
        `;
        document.head.appendChild(style);
    }

    function fieldName(input) {
        const name = input.name || input.id || "";

        return Object.keys(FIELD_MODELS).find(function (key) {
            return name === key || name.endsWith("-" + key) || name.endsWith("_" + key);
        });
    }

    function lookupLink(input) {
        const id = input.id ? "lookup_" + input.id : "";
        return (
            (id && document.getElementById(id)) ||
            input.parentElement.querySelector(".related-lookup")
        );
    }

    function labelFromDjango(input) {
        const parent = input.parentElement;
        if (!parent) {
            return "";
        }

        const labelNode = parent.querySelector("strong a, strong");
        return labelNode ? labelNode.textContent.trim() : "";
    }

    function setVisibleValue(input, visible, value) {
        visible.value = value || "";
        visible.classList.toggle("is-empty", !visible.value);
    }

    function fetchLabel(input, visible, config) {
        const objectId = input.value;

        if (!objectId) {
            setVisibleValue(input, visible, "");
            return;
        }

        const existingLabel = config.app === "products" ? "" : labelFromDjango(input);
        if (existingLabel && existingLabel !== objectId) {
            setVisibleValue(input, visible, existingLabel);
            return;
        }

        fetch(`/admin/related-object-label/${config.app}/${config.model}/${encodeURIComponent(objectId)}/`)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Label not found");
                }
                return response.json();
            })
            .then(function (data) {
                setVisibleValue(input, visible, data.label || "");
            })
            .catch(function () {
                setVisibleValue(input, visible, "");
            });
    }

    function wrapInput(input, visible, link) {
        if (input.parentElement.classList.contains("raw-id-label-wrapper")) {
            return;
        }

        const wrapper = document.createElement("span");
        wrapper.className = "raw-id-label-wrapper";
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(visible);
        if (link) {
            wrapper.appendChild(link);
        }
    }

    function hideDjangoRawIdLabel(input) {
        const container = input.closest(".related-widget-wrapper") || input.parentElement.parentElement;
        if (!container) {
            return;
        }

        container.querySelectorAll("strong").forEach(function (label) {
            label.style.display = "none";
        });
    }

    function setupInput(input) {
        if (!input || input.dataset.rawIdLabelReady === "true") {
            return;
        }

        const key = fieldName(input);
        const config = FIELD_MODELS[key];
        if (!config) {
            return;
        }

        const visible = document.createElement("input");
        visible.type = "text";
        visible.readOnly = true;
        visible.placeholder = config.placeholder;
        visible.className = "raw-id-label-display is-empty";

        const link = lookupLink(input);
        input.dataset.rawIdLabelReady = "true";
        input.type = "hidden";
        wrapInput(input, visible, link);
        hideDjangoRawIdLabel(input);

        visible.addEventListener("click", function () {
            const currentLink = lookupLink(input);
            if (currentLink) {
                currentLink.click();
            }
        });

        visible.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                const currentLink = lookupLink(input);
                if (currentLink) {
                    currentLink.click();
                }
            }
        });

        input.addEventListener("change", function () {
            fetchLabel(input, visible, config);
        });

        input.addEventListener("input", function () {
            fetchLabel(input, visible, config);
        });

        fetchLabel(input, visible, config);
    }

    function setupAll(root) {
        installStyle();
        (root || document)
            .querySelectorAll("input.vForeignKeyRawIdAdminField, input[data-raw-id-field]")
            .forEach(setupInput);
    }

    function refreshAllLabels() {
        document.querySelectorAll("input.vForeignKeyRawIdAdminField[data-raw-id-label-ready='true']").forEach(function (input) {
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupAll(document);
    });

    document.addEventListener("formset:added", function (event) {
        setupAll(event.target);
    });

    if (window.django && window.django.jQuery) {
        window.django.jQuery(document).on("formset:added", function (_event, row) {
            setupAll(row && row.get ? row.get(0) : row);
        });
    }

    const originalDismissRelatedLookupPopup = window.dismissRelatedLookupPopup;
    window.dismissRelatedLookupPopup = function () {
        const result = typeof originalDismissRelatedLookupPopup === "function"
            ? originalDismissRelatedLookupPopup.apply(this, arguments)
            : undefined;
        window.setTimeout(refreshAllLabels, 0);
        return result;
    };

    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType === 1) {
                    setupAll(node);
                }
            });
        });
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
})();
