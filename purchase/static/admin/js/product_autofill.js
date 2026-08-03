function updatePurchaseOrderItemRow(row, refreshProduct, options) {
    if (!row) return;
    const settings = options || {};

    function toNumber(value) {
        const normalized = window.financeNumberFormatting && window.financeNumberFormatting.normalizeValue
            ? window.financeNumberFormatting.normalizeValue(value)
            : String(value || "0").replace(/,/g, "");
        const parsed = parseFloat(normalized || "0");
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
        const formattedTotal = window.financeNumberFormatting && window.financeNumberFormatting.formatValue
            ? window.financeNumberFormatting.formatValue(total)
            : total.toFixed(2);

        const totalField = row.querySelector("input[name$='total_line']") || row.querySelector("td.field-total_line") || row.querySelector("div.field-total_line");
        if (totalField) {
            if (totalField.tagName === "INPUT") {
                totalField.value = formattedTotal;
            } else {
                totalField.textContent = formattedTotal;
            }
        }
    }

    function hasEditedUnitPrice(input) {
        return Boolean(input && input.dataset.purchaseUnitPriceEdited === "true");
    }

    function clearUnitPriceEdited(input) {
        if (input) {
            input.dataset.purchaseUnitPriceEdited = "";
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

    fetch(`/purchase/product-info/${productId}/`, {
        cache: "no-store",
        credentials: "same-origin"
    })
        .then(response => response.json())
        .then(data => {
            const descriptionInput = row.querySelector("input[name$='description']") || row.querySelector("input[name$='-description']");
            const partNumberInput = row.querySelector("input[name$='part_number']") || row.querySelector("input[name$='-part_number']");
            const hsCodeInput = row.querySelector("input[name$='hs_code']") || row.querySelector("input[name$='-hs_code']");
            const hsCodeDisplay = row.querySelector('[data-product-field="hs_code"]');
            const partNumberDisplay = row.querySelector('[data-product-field="part_number"]');
            const unitPriceInput = row.querySelector("input[name$='unit_price']") || row.querySelector("input[name$='-unit_price']");

            if (
                descriptionInput &&
                (productChanged || !descriptionInput.value.trim())
            ) {
                descriptionInput.value = data.description || "";
            }
            if (
                partNumberInput &&
                (productChanged || !partNumberInput.value.trim())
            ) {
                partNumberInput.value = data.part_number || "";
            }
            if (
                hsCodeInput &&
                (productChanged || !hsCodeInput.value.trim() || hsCodeInput.value.trim() === "-")
            ) {
                hsCodeInput.value = data.hs_code || "";
                hsCodeInput.dispatchEvent(new Event("input", { bubbles: true }));
                hsCodeInput.dispatchEvent(new Event("change", { bubbles: true }));
            }
            if (hsCodeDisplay) {
                hsCodeDisplay.textContent =
                    (hsCodeInput && hsCodeInput.value.trim()) || data.hs_code || "-";
            }
            if (partNumberDisplay) {
                partNumberDisplay.textContent = data.part_number || "-";
            }
            if (unitPriceInput && (
                (settings.forceDefaultPrice === true && !hasEditedUnitPrice(unitPriceInput)) ||
                (productChanged && settings.preserveUnitPrice !== true && !hasEditedUnitPrice(unitPriceInput)) ||
                !unitPriceInput.value ||
                toNumber(unitPriceInput.value) === 0
            )) {
                unitPriceInput.value = data.purchase_price || "0";
                clearUnitPriceEdited(unitPriceInput);
            }
            if (productField) {
                productField.dataset.purchaseLastProductId = productId;
            }
            updateTotal();
            document.dispatchEvent(new CustomEvent("invoice:inline-product-updated"));
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

    fetch(`/purchase/product-info/${productId}/`, {
        cache: "no-store",
        credentials: "same-origin"
    })
        .then(response => response.json())
        .then(data => {
            hsCodeInput.value = data.hs_code || "-";
            hsCodeInput.dispatchEvent(new Event("input", { bubbles: true }));
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
        if (target.name.includes("unit_price")) {
            target.dataset.purchaseUnitPriceEdited = "true";
        }
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

function currentReturnUrl() {
    const url = new URL(window.location.href);
    [
        "_selected_product_field",
        "_selected_product_id",
        "_selected_product_label",
        "_selected_partner_field",
        "_selected_partner_id",
        "_selected_partner_label",
    ].forEach(function(key) {
        url.searchParams.delete(key);
    });
    const adminReturnInput = document.querySelector('input[name="admin_return_url"]');
    if (adminReturnInput && adminReturnInput.value) {
        url.searchParams.set("admin_return_url", adminReturnInput.value);
    }
    return url.pathname + url.search;
}

function prepareProductLink(link, fieldName, itemId, action) {
    if (!link) {
        return;
    }

    const url = new URL(link.href, window.location.origin);
    url.searchParams.delete("_popup");
    url.searchParams.set("_return_to", currentReturnUrl());
    url.searchParams.set("_return_product_action", action || "edit");
    if (fieldName) {
        url.searchParams.set("_return_field", fieldName);
    }
    if (itemId && action !== "add") {
        url.searchParams.set("_return_item_id", itemId);
    } else {
        url.searchParams.delete("_return_item_id");
    }
    link.href = url.toString();
}

function getProductFieldName(wrapper) {
    const field = wrapper.querySelector('select[name$="-product"], input[name$="-product"]');
    return field ? field.name : "";
}

function getItemId(wrapper, fieldName) {
    if (!fieldName) {
        return "";
    }
    const row = wrapper.closest("tr");
    const prefix = fieldName.replace(/-product$/, "");
    const idField = row ? row.querySelector(`[name="${CSS.escape(prefix + "-id")}"]`) : null;
    return idField ? idField.value : "";
}

function prepareProductButtons(root) {
    (root || document).querySelectorAll(".inline-group .field-product .related-widget-wrapper").forEach(function(wrapper) {
        const addLink = wrapper.querySelector(".add-related");
        const changeLink = wrapper.querySelector(".change-related");
        const fieldName = getProductFieldName(wrapper);
        const itemId = getItemId(wrapper, fieldName);

        wrapper.querySelector(".view-related")?.remove();
        wrapper.querySelector(".delete-related")?.remove();

        prepareProductLink(addLink, fieldName, "", "add");
        prepareProductLink(changeLink, fieldName, itemId, "edit");

        [addLink, changeLink].forEach(function(link) {
            if (!link || link.dataset.productSamePageBound === "true") {
                return;
            }

            link.dataset.productSamePageBound = "true";
            link.addEventListener("click", function(event) {
                const action = link.classList.contains("add-related") ? "add" : "edit";
                event.preventDefault();
                event.stopImmediatePropagation();
                const autosave = window.invoiceAutosaveNow ? window.invoiceAutosaveNow() : Promise.resolve();
                autosave
                    .then(function () {
                        const currentItemId = action === "add" ? "" : getItemId(wrapper, fieldName);
                        prepareProductLink(link, fieldName, currentItemId, action);
                        window.location.href = link.href;
                    })
                    .catch(function () {
                        window.alert(
                            "Please correct the form errors before editing the product. " +
                            "Your purchase order information has not been discarded."
                        );
                    });
            }, true);
        });
    });
}

function applyReturnedProductSelection() {
    const params = new URLSearchParams(window.location.search);
    const fieldName = params.get("_selected_product_field");
    const productId = params.get("_selected_product_id");
    const productLabel = params.get("_selected_product_label");

    if (!fieldName || !productId) {
        return;
    }

    const field = document.querySelector(`[name="${CSS.escape(fieldName)}"]`);
    if (!field) {
        return;
    }

    if (field.tagName === "SELECT") {
        let option = Array.from(field.options).find(function(item) {
            return item.value === productId;
        });
        if (!option) {
            option = new Option(productLabel || productId, productId, true, true);
            field.appendChild(option);
        }
        if (productLabel) {
            option.textContent = productLabel;
            option.text = productLabel;
        }
        field.value = productId;
        if (window.django && window.django.jQuery) {
            window.django.jQuery(field).trigger("change");
        } else {
            field.dispatchEvent(new Event("change", { bubbles: true }));
        }
    } else {
        field.value = productId;
        field.dispatchEvent(new Event("change", { bubbles: true }));
    }

    updatePurchaseOrderItemRow(field.closest("tr"), true, { preserveUnitPrice: true });
}

document.addEventListener("DOMContentLoaded", function() {
    prepareProductButtons(document);
    applyReturnedProductSelection();
    document.querySelectorAll(".inline-group tr").forEach(fillMissingPurchaseHsCode);
    document.querySelectorAll("select[name$='product'], select[name$='-product'], input.vForeignKeyRawIdAdminField[name$='product'], input[name$='-product']").forEach(function(field) {
        if (field.value) {
            field.dataset.purchaseLastProductId = field.value;
        }
    });
});

document.body.addEventListener("formset:added", function(event) {
    prepareProductButtons(event.target);
    event.target.querySelectorAll(".inline-group tr, tr").forEach(fillMissingPurchaseHsCode);
});
