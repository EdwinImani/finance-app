(function () {
    function toNumber(value) {
        const normalized = String(value || "0").replace(",", ".");
        const parsed = parseFloat(normalized);
        return Number.isNaN(parsed) ? 0 : parsed;
    }

    function formatMoney(value) {
        return toNumber(value).toFixed(2);
    }

    function getInvoiceRows() {
        return Array.from(document.querySelectorAll("tr.form-row")).filter(function (row) {
            return row.querySelector('select[name$="-product"], input.vForeignKeyRawIdAdminField[name$="-product"], input[name$="-quantity"], input[name$="-unit_price"]');
        });
    }

    function updateText(row, fieldName, value) {
        const cell = row.querySelector('[data-product-field="' + fieldName + '"]');

        if (cell) {
            cell.textContent = value || "-";
        }
    }

    function updateRowTotal(row) {
        if (!row) {
            return 0;
        }

        const quantityInput = row.querySelector('input[name$="-quantity"]');
        const unitPriceInput = row.querySelector('input[name$="-unit_price"]');
        const total = toNumber(quantityInput && quantityInput.value) * toNumber(unitPriceInput && unitPriceInput.value);
        const totalCell = row.querySelector("td.field-total_line .readonly, td.field-total_line, [data-product-field='total_line']");

        if (totalCell) {
            totalCell.textContent = formatMoney(total);
        }

        return total;
    }

    function defaultQuantityToOne(row) {
        const quantityInput = row && row.querySelector('input[name$="-quantity"]');

        if (quantityInput && (!quantityInput.value || toNumber(quantityInput.value) === 0)) {
            quantityInput.value = "1";
            quantityInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function getSummaryRate() {
        const vatRateInput = document.querySelector("#id_vat_percent");
        return vatRateInput ? toNumber(vatRateInput.value) : 0;
    }

    function updateSummary() {
        const rows = getInvoiceRows();
        let subtotal = 0;

        rows.forEach(function (row) {
            const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
            if (deleteCheckbox && deleteCheckbox.checked) {
                return;
            }

            subtotal += updateRowTotal(row);
        });

        const freight = toNumber(document.querySelector("#id_freight") && document.querySelector("#id_freight").value);
        const discount = toNumber(document.querySelector("#id_discount") && document.querySelector("#id_discount").value);
        const vatRate = getSummaryRate();
        const vatAmount = subtotal * vatRate / 100;
        const total = subtotal + vatAmount + freight - discount;

        const summaryValues = {
            subtotal: formatMoney(subtotal),
            vat: formatMoney(vatAmount),
            total: formatMoney(total),
            "vat-rate": formatMoney(vatRate) + "%",
        };

        Object.keys(summaryValues).forEach(function (key) {
            document.querySelectorAll('[data-invoice-summary="' + key + '"]').forEach(function (node) {
                node.textContent = summaryValues[key];
            });
        });
    }

    function shouldUseDefaultUnitPrice(input, forceDefaultPrice) {
        if (!input) {
            return false;
        }

        if (forceDefaultPrice) {
            return true;
        }

        return !input.value || toNumber(input.value) === 0;
    }

    function updateInvoiceRow(row, data, options) {
        if (!row) {
            return;
        }

        const settings = options || {};
        const unitPriceInput = row.querySelector('input[name$="-unit_price"]');
        const hsCodeInput = row.querySelector('input[name$="-hs_code"]');
        const partNumberInput = row.querySelector('input[name$="-part_number"]');

        if (data && Object.keys(data).length) {
            defaultQuantityToOne(row);
        }

        updateText(row, "description", data.description);
        updateText(row, "part_number", data.part_number);
        updateText(row, "stock", data.unit_qty);
        updateText(row, "sale_price", data.sale_price);
        updateText(row, "purchase_price", data.purchase_price);
        updateText(row, "note", data.note);

        if (shouldUseDefaultUnitPrice(unitPriceInput, settings.forceDefaultPrice)) {
            unitPriceInput.value = data.sale_price || "0";
        }

        if (hsCodeInput) {
            hsCodeInput.value = data.hs_code || "";
        }

        if (partNumberInput) {
            partNumberInput.value = data.part_number || "";
        }

        updateRowTotal(row);
        updateSummary();
    }

    function getRowFromElement(element) {
        return element ? element.closest("tr") : null;
    }

    function fetchProductInfoForField(field, options) {
        const row = getRowFromElement(field);
        const productId = field ? field.value : "";
        const previousProductId = field ? field.dataset.invoiceLastProductId || "" : "";
        const productChanged = Boolean(productId) && previousProductId !== productId;
        const settings = options || {};

        if (!row) {
            return;
        }

        if (!productId) {
            updateInvoiceRow(row, {});
            if (field) {
                field.dataset.invoiceLastProductId = "";
            }
            return;
        }

        fetch("/purchase/product-info/" + productId + "/")
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                updateInvoiceRow(row, data, {
                    forceDefaultPrice: settings.forceDefaultPrice === true || (productChanged && settings.preserveUnitPrice !== true),
                });
                field.dataset.invoiceLastProductId = productId;
                document.dispatchEvent(new CustomEvent("invoice:inline-product-updated"));
            })
            .catch(function () {
                updateInvoiceRow(row, {});
            });
    }

    function isProductField(element) {
        return (
            element &&
            element.name &&
            element.name.endsWith("-product") &&
            (element.tagName === "SELECT" || element.classList.contains("vForeignKeyRawIdAdminField"))
        );
    }

    function bindProductField(field) {
        if (!isProductField(field) || field.dataset.invoiceProductBound === "true") {
            return;
        }

        field.dataset.invoiceProductBound = "true";

        field.addEventListener("change", function () {
            fetchProductInfoForField(field, { preserveUnitPrice: true });
        });

        field.addEventListener("input", function () {
            fetchProductInfoForField(field, { preserveUnitPrice: true });
        });

        if (field.value) {
            field.dataset.invoiceLastProductId = field.value;
            fetchProductInfoForField(field, { preserveUnitPrice: true });
        }
    }

    function bindMoneyField(field) {
        if (!field || field.dataset.invoiceMoneyBound === "true") {
            return;
        }

        field.dataset.invoiceMoneyBound = "true";

        field.addEventListener("input", updateSummary);
        field.addEventListener("change", updateSummary);
    }

    function bindAllFields(root) {
        (root || document)
            .querySelectorAll('select[name$="-product"]')
            .forEach(function (field) {
                bindProductField(field);
            });

        (root || document)
            .querySelectorAll('input.vForeignKeyRawIdAdminField[name$="-product"]')
            .forEach(function (field) {
                bindProductField(field);
            });

        (root || document)
            .querySelectorAll('input[name$="-quantity"], input[name$="-unit_price"], #id_freight, #id_discount, #id_vat_percent, input[name$="-DELETE"]')
            .forEach(function (field) {
                bindMoneyField(field);
            });

    }

    document.addEventListener("DOMContentLoaded", function () {
        bindAllFields(document);
        updateSummary();

        document.addEventListener("change", function (event) {
            const target = event.target;

            if (isProductField(target)) {
                fetchProductInfoForField(target);
                return;
            }

            if (
                target.matches('input[name$="-quantity"], input[name$="-unit_price"], #id_freight, #id_discount, #id_vat_percent, input[name$="-DELETE"]')
            ) {
                updateSummary();
            }
        });

        document.addEventListener("input", function (event) {
            if (
                event.target.matches('input[name$="-quantity"], input[name$="-unit_price"], #id_freight, #id_discount, #id_vat_percent')
            ) {
                updateSummary();
            }
        });

        if (window.django && window.django.jQuery) {
            const $ = window.django.jQuery;

            $(document).on("select2:select", 'select[name$="-product"]', function () {
                const field = this;

                window.setTimeout(function () {
                    fetchProductInfoForField(field, { forceDefaultPrice: true });
                }, 0);
            });

            $(document).on("select2:close", 'select[name$="-product"]', function () {
                const field = this;

                window.setTimeout(function () {
                    fetchProductInfoForField(field, { preserveUnitPrice: true });
                }, 0);
            });

            $(document).on("formset:added", function (_event, row) {
                const root = row.get ? row.get(0) : row;
                bindAllFields(root);
                updateSummary();
            });
        }

        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) {
                        bindAllFields(node);
                        updateSummary();
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    });
})();
