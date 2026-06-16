function updatePurchaseOrderItemRow(row, refreshProduct, options) {
    if (!row) return;
    const settings = options || {};

    function toNumber(value) {
        const normalized = String(value || "0").replace(",", ".");
        const parsed = parseFloat(normalized);
        return Number.isNaN(parsed) ? 0 : parsed;
    }

    function defaultQuantityToOne() {
        const qtyInput = row.querySelector("input[name$='quantity']") || row.querySelector("input[name$='-quantity']");

        if (!qtyInput) return;

        const qty = toNumber(qtyInput.value);
        if (!qtyInput.value || qty === 0) {
            qtyInput.value = "1";
            qtyInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function updateTotal() {
        const qtyInput = row.querySelector("input[name$='quantity']");
        const unitPriceInput = row.querySelector("input[name$='unit_price']");
        if (!qtyInput || !unitPriceInput) return;

        const qty = toNumber(qtyInput.value);
        const price = toNumber(unitPriceInput.value);
        const total = qty * price;

        const totalField = row.querySelector("input[name$='total_line']") || row.querySelector("td.field-total_line") || row.querySelector("div.field-total_line");
        if (totalField) {
            if (totalField.tagName === "INPUT") {
                totalField.value = total.toFixed(2);
            } else {
                totalField.textContent = total.toFixed(2);
            }
        }
    }

    if (!refreshProduct) {
        updateTotal();
        return;
    }

    const productField = row.querySelector("select[name$='product']") ||
        row.querySelector("select[name$='-product']") ||
        row.querySelector("input.vForeignKeyRawIdAdminField[name$='product']") ||
        row.querySelector("input[name$='-product']");
    const productId = productField ? productField.value : "";
    const previousProductId = productField ? productField.dataset.purchaseLastProductId || "" : "";
    const productChanged = Boolean(productId) && previousProductId !== productId;
    if (!productId) {
        if (productField) {
            productField.dataset.purchaseLastProductId = "";
        }
        updateTotal();
        return;
    }

    defaultQuantityToOne();

    fetch(`/purchase/product-info/${productId}/`)
        .then(response => response.json())
        .then(data => {
            const descriptionInput = row.querySelector("input[name$='description']") || row.querySelector("input[name$='-description']");
            const partNumberInput = row.querySelector("input[name$='part_number']") || row.querySelector("input[name$='-part_number']");
            const hsCodeInput = row.querySelector("input[name$='hs_code']") || row.querySelector("input[name$='-hs_code']");
            const hsCodeDisplay = row.querySelector('[data-product-field="hs_code"]');
            const partNumberDisplay = row.querySelector('[data-product-field="part_number"]');
            const unitPriceInput = row.querySelector("input[name$='unit_price']") || row.querySelector("input[name$='-unit_price']");

            if (descriptionInput) {
                descriptionInput.value = data.description || "";
            }
            if (partNumberInput) {
                partNumberInput.value = data.part_number || "";
            }
            if (hsCodeInput) {
                hsCodeInput.value = data.hs_code || "";
                hsCodeInput.dispatchEvent(new Event("change", { bubbles: true }));
            }
            if (hsCodeDisplay) {
                hsCodeDisplay.textContent = data.hs_code || "-";
            }
            if (partNumberDisplay) {
                partNumberDisplay.textContent = data.part_number || "-";
            }
            if (unitPriceInput && (settings.forceDefaultPrice === true || (productChanged && settings.preserveUnitPrice !== true) || !unitPriceInput.value || toNumber(unitPriceInput.value) === 0)) {
                unitPriceInput.value = data.purchase_price || "0";
            }
            if (productField) {
                productField.dataset.purchaseLastProductId = productId;
            }
            updateTotal();
        })
        .catch(() => {
            updateTotal();
        });
}

function fillMissingPurchaseHsCode(row) {
    if (!row) return;

    const select = row.querySelector("select[name$='product']") ||
        row.querySelector("select[name$='-product']") ||
        row.querySelector("input.vForeignKeyRawIdAdminField[name$='product']") ||
        row.querySelector("input[name$='-product']");
    const hsCodeInput = row.querySelector("input[name$='hs_code']") || row.querySelector("input[name$='-hs_code']");
    const productId = select ? select.value : "";
    const currentHsCode = hsCodeInput ? hsCodeInput.value.trim() : "";

    if (!productId || !hsCodeInput || (currentHsCode && currentHsCode !== "-")) {
        return;
    }

    fetch(`/purchase/product-info/${productId}/`)
        .then(response => response.json())
        .then(data => {
            hsCodeInput.value = data.hs_code || "-";
            hsCodeInput.dispatchEvent(new Event("change", { bubbles: true }));
        });
}

document.addEventListener("change", function(e) {
    const target = e.target;
    const row = target.closest("tr");
    if (!row) return;

    if (target.name.includes("product")) {
        updatePurchaseOrderItemRow(row, true, { preserveUnitPrice: true });
    }

    if (target.name.includes("quantity") || target.name.includes("unit_price")) {
        updatePurchaseOrderItemRow(row, false);
    }
});

if (window.django && django.jQuery) {
    django.jQuery(document).on("select2:select", ".inline-group .field-product select", function() {
        const row = this.closest("tr");
        window.setTimeout(function() {
            updatePurchaseOrderItemRow(row, true, { forceDefaultPrice: true });
        }, 0);
    });

    django.jQuery(document).on("select2:close", ".inline-group .field-product select", function() {
        const row = this.closest("tr");
        window.setTimeout(function() {
            updatePurchaseOrderItemRow(row, true, { preserveUnitPrice: true });
        }, 0);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll(".inline-group tr").forEach(fillMissingPurchaseHsCode);
    document.querySelectorAll("select[name$='product'], select[name$='-product'], input.vForeignKeyRawIdAdminField[name$='product'], input[name$='-product']").forEach(function(field) {
        if (field.value) {
            field.dataset.purchaseLastProductId = field.value;
        }
    });
});

document.body.addEventListener("formset:added", function(event) {
    event.target.querySelectorAll(".inline-group tr, tr").forEach(fillMissingPurchaseHsCode);
});
