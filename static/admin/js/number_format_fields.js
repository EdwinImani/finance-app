(function () {
    "use strict";

    var decimalFormatter = new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    var decimalNamePattern = /(amount|balance|cost|debit|credit|dimension|discount|freight|gross_weight|net_weight|percent|price|rate|subtotal|total|vat|weight)/i;
    var excludedNamePattern = /(date|day|email|hs_code|id$|invoice_number|month|no_packing|number|part_number|phone|purchase_number|quantity|unit_qty|year|zip)/i;

    function fieldKey(field) {
        return [field.name, field.id, field.getAttribute("aria-label")].filter(Boolean).join(" ");
    }

    function isDecimalField(field) {
        if (!field || field.disabled || field.readOnly) {
            return false;
        }

        var tag = field.tagName;
        var type = (field.type || "text").toLowerCase();

        if (tag !== "INPUT" || !["text", "number"].includes(type)) {
            return false;
        }

        var key = fieldKey(field);
        return decimalNamePattern.test(key) && !excludedNamePattern.test(key);
    }

    function normalizeValue(value) {
        var raw = String(value == null ? "" : value).trim();

        if (!raw) {
            return "";
        }

        raw = raw.replace(/\s+/g, "");

        var hasComma = raw.indexOf(",") !== -1;
        var hasDot = raw.indexOf(".") !== -1;

        if (hasComma && hasDot) {
            raw = raw.replace(/,/g, "");
        } else if (hasComma) {
            raw = raw.replace(",", ".");
        }

        raw = raw.replace(/[^0-9.-]/g, "");

        var minus = raw.charAt(0) === "-" ? "-" : "";
        raw = raw.replace(/-/g, "");

        var firstDot = raw.indexOf(".");
        if (firstDot !== -1) {
            raw = raw.slice(0, firstDot + 1) + raw.slice(firstDot + 1).replace(/\./g, "");
        }

        return minus + raw;
    }

    function toNumber(value) {
        var normalized = normalizeValue(value);
        var parsed = parseFloat(normalized || "0");
        return Number.isNaN(parsed) ? 0 : parsed;
    }

    function formatValue(value) {
        var normalized = normalizeValue(value);

        if (!normalized || normalized === "-" || normalized === "." || normalized === "-.") {
            return "";
        }

        return decimalFormatter.format(toNumber(normalized));
    }

    function normalizeField(field) {
        if (!isDecimalField(field)) {
            return;
        }

        field.value = normalizeValue(field.value);
    }

    function formatField(field) {
        if (!isDecimalField(field) || !field.value) {
            return;
        }

        field.value = formatValue(field.value);
    }

    function isSkippableTextParent(element) {
        if (!element) {
            return true;
        }

        return Boolean(element.closest("script, style, textarea, input, select, option, code, pre, [data-no-number-format]"));
    }

    function isStandaloneDecimalText(value) {
        return /^\s*-?(?:\d{1,3}(?:,\d{3})+|\d+)[.,]\d+\s*$/.test(value || "");
    }

    function formatTextNode(node) {
        if (!node || isSkippableTextParent(node.parentElement) || !isStandaloneDecimalText(node.nodeValue)) {
            return;
        }

        node.nodeValue = formatValue(node.nodeValue);
    }

    function formatDisplayNumbers(root) {
        var base = root || document.body;

        if (base.nodeType === Node.TEXT_NODE) {
            formatTextNode(base);
            return;
        }

        if (!base.querySelectorAll) {
            return;
        }

        var walker = document.createTreeWalker(base, NodeFilter.SHOW_TEXT);
        var textNodes = [];
        var node = walker.nextNode();

        while (node) {
            textNodes.push(node);
            node = walker.nextNode();
        }

        textNodes.forEach(formatTextNode);
    }

    function prepareField(field) {
        if (!isDecimalField(field) || field.dataset.numberFormatBound === "true") {
            return;
        }

        field.dataset.numberFormatBound = "true";
        field.setAttribute("inputmode", "decimal");

        if ((field.type || "").toLowerCase() === "number") {
            field.type = "text";
        }

        formatField(field);

        field.addEventListener("focus", function () {
            normalizeField(field);
        });

        field.addEventListener("blur", function () {
            formatField(field);
        });

        field.addEventListener("change", function () {
            window.setTimeout(function () {
                formatField(field);
            }, 0);
        });
    }

    function eachDecimalField(root, callback) {
        Array.from((root || document).querySelectorAll("input[type='text'], input[type='number'], input:not([type])"))
            .forEach(function (field) {
                if (isDecimalField(field)) {
                    callback(field);
                }
            });
    }

    function setup(root) {
        eachDecimalField(root || document, prepareField);
        formatDisplayNumbers(root || document.body);
    }

    function normalizeForm(form) {
        eachDecimalField(form, normalizeField);
    }

    function normalizeFormData(formData) {
        Array.from(formData.keys()).forEach(function (name) {
            var probe = document.createElement("input");
            probe.name = name;

            if (!isDecimalField(probe)) {
                return;
            }

            formData.set(name, normalizeValue(formData.get(name)));
        });

        return formData;
    }

    window.financeNumberFormatting = {
        formatValue: formatValue,
        formatDisplayNumbers: formatDisplayNumbers,
        normalizeValue: normalizeValue,
        toNumber: toNumber,
        setup: setup,
        normalizeForm: normalizeForm,
        normalizeFormData: normalizeFormData
    };

    document.addEventListener("DOMContentLoaded", function () {
        setup(document);

        document.addEventListener("focusin", function (event) {
            if (isDecimalField(event.target)) {
                normalizeField(event.target);
            }
        });

        document.addEventListener("focusout", function (event) {
            if (isDecimalField(event.target)) {
                formatField(event.target);
            }
        });

        document.addEventListener("submit", function (event) {
            normalizeForm(event.target);
        }, true);

        document.addEventListener("formset:added", function (event) {
            window.setTimeout(function () {
                setup(event.target || document);
            }, 0);
        });

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) {
                        setup(node);
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
})();
