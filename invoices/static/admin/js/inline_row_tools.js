(function () {
    "use strict";

    function getInlineGroups(root) {
        return Array.from((root || document).querySelectorAll(".inline-group"));
    }

    function getRows(group) {
        return Array.from(group.querySelectorAll(".tabular tbody tr")).filter(function (row) {
            return !row.classList.contains("empty-form") && !row.id.endsWith("-empty");
        });
    }

    function isDeleted(row) {
        var deleteInput = row.querySelector('input[name$="-DELETE"]');
        return Boolean(deleteInput && deleteInput.checked);
    }

    function hasProductRowData(row) {
        var product = row.querySelector('[name$="-product"]');
        var hsCode = row.querySelector('[name$="-hs_code"]');
        var partNumber = row.querySelector('[name$="-part_number"]');
        var unitPrice = row.querySelector('[name$="-unit_price"]');

        return Boolean(
            valueOf(product) ||
            realTextValue(hsCode) ||
            realTextValue(partNumber) ||
            realMoneyValue(unitPrice)
        );
    }

    function hasPackingRowData(row) {
        var noPacking = row.querySelector('[name$="-no_packing"]');
        var grossWeight = row.querySelector('[name$="-gross_weight"]');
        var netWeight = row.querySelector('[name$="-net_weight"]');
        var dimensionLength = row.querySelector('[name$="-dimension_length"]');
        var dimensionWidth = row.querySelector('[name$="-dimension_width"]');
        var dimensionHeight = row.querySelector('[name$="-dimension_height"]');

        return Boolean(
            realTextValue(noPacking) ||
            realMoneyValue(grossWeight) ||
            realMoneyValue(netWeight) ||
            realMoneyValue(dimensionLength) ||
            realMoneyValue(dimensionWidth) ||
            realMoneyValue(dimensionHeight)
        );
    }

    function hasUserData(row) {
        if (row.querySelector(".field-no_packing")) {
            return hasPackingRowData(row);
        }
        if (row.querySelector(".field-product")) {
            return hasProductRowData(row);
        }
        return false;
    }

    function getLastCopyableRow(group) {
        var activeRows = getRows(group).filter(function (row) {
            return !isDeleted(row);
        });
        var rowsWithData = activeRows.filter(hasUserData);

        return rowsWithData[rowsWithData.length - 1] || activeRows[activeRows.length - 1] || null;
    }

    function valueOf(field) {
        return field ? String(field.value || "").trim() : "";
    }

    function realTextValue(field) {
        var value = valueOf(field);
        return value && value !== "-";
    }

    function realMoneyValue(field) {
        var value = window.financeNumberFormatting && window.financeNumberFormatting.normalizeValue
            ? window.financeNumberFormatting.normalizeValue(valueOf(field))
            : valueOf(field).replace(/,/g, "");
        return value && !["0", "0.0", "0.00"].includes(value);
    }

    function ensureNumberHeader(group) {
        var headerRow = group.querySelector(".tabular thead tr");
        if (!headerRow || headerRow.querySelector(".inline-row-number-header")) {
            return;
        }

        var header = document.createElement("th");
        header.className = "inline-row-number-header";
        header.scope = "col";
        header.textContent = "";
        headerRow.insertBefore(header, headerRow.firstElementChild);
    }

    function ensureNumberCell(row) {
        var cell = row.querySelector(".inline-row-number-cell");
        if (cell) {
            return cell;
        }

        cell = document.createElement("td");
        cell.className = "inline-row-number-cell";
        row.insertBefore(cell, row.firstElementChild);
        return cell;
    }

    function normalizeInvoiceLineClasses(group) {
        if (!isInvoicePage() || !group.querySelector(".field-product")) {
            return;
        }

        var headerRow = group.querySelector(".tabular thead tr");
        if (headerRow) {
            headerRow.classList.add("invoice-lines-header");
        }

        group.querySelectorAll(".tabular tbody tr.form-row").forEach(function(row) {
            row.classList.add("invoice-line-row");
        });
    }

    function updateRowNumbers(root) {
        getInlineGroups(root).forEach(function (group) {
            // Product lines already have seven meaningful columns. Do not add
            // an artificial numbering column that shifts their shared grid.
            if (group.querySelector(".field-product")) {
                group.querySelectorAll(
                    ".inline-row-number-header, .inline-row-number-cell"
                ).forEach(function(cell) {
                    cell.remove();
                });
                return;
            }

            var rows = getRows(group);
            var allFormRows = Array.from(group.querySelectorAll(".tabular tbody tr.form-row"));
            if (!allFormRows.length) {
                return;
            }

            ensureNumberHeader(group);
            // Keep the hidden __prefix__ template structurally identical to
            // saved and dynamically-added rows. Its cell remains blank until
            // the row becomes a real form row.
            allFormRows.forEach(ensureNumberCell);

            var countedRows = rows.filter(function (row) {
                return !isDeleted(row) && hasUserData(row);
            });
            var total = countedRows.length;

            rows.forEach(function (row) {
                var cell = ensureNumberCell(row);
                var index = countedRows.indexOf(row);
                var label = index === -1 ? "" : String(index + 1);
                if (cell.textContent !== label) {
                    cell.textContent = label;
                }
            });
        });
    }

    function isInvoicePage() {
        return Boolean(document.body && document.body.classList.contains("app-invoices"));
    }

    function isCloneableInvoiceGroup(group) {
        return isInvoicePage() && Boolean(group.querySelector(".field-no_packing"));
    }

    function fieldSuffix(field) {
        return field.name ? field.name.split("-").slice(2).join("-") : "";
    }

    function copyFieldValue(sourceField, targetRow) {
        var suffix = fieldSuffix(sourceField);
        if (!suffix || sourceField.type === "hidden" || suffix === "id" || suffix === "DELETE") {
            return;
        }

        var escapedSuffix = window.CSS && CSS.escape ? CSS.escape(suffix) : suffix.replace(/"/g, '\\"');
        var targetField = targetRow.querySelector('[name$="-' + escapedSuffix + '"]');
        if (!targetField || targetField.type === "hidden" || targetField.name.endsWith("-id")) {
            return;
        }

        if (sourceField.tagName === "SELECT") {
            Array.from(sourceField.selectedOptions || []).forEach(function (option) {
                if (!option.value || targetField.querySelector('option[value="' + option.value.replace(/"/g, '\\"') + '"]')) {
                    return;
                }
                targetField.appendChild(option.cloneNode(true));
            });
        }

        if (targetField.type === "checkbox" || targetField.type === "radio") {
            targetField.checked = sourceField.checked;
        } else {
            targetField.value = sourceField.value;
        }

        if (targetField.tagName === "SELECT" && window.django && window.django.jQuery) {
            window.django.jQuery(targetField).trigger("change");
        }

        targetField.dispatchEvent(new Event("input", { bubbles: true }));
        targetField.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function notifyAutosave() {
        document.dispatchEvent(new CustomEvent("invoice:inline-product-updated"));
        if (window.invoiceAutosaveTouch) {
            window.invoiceAutosaveTouch();
        }
    }

    function getRealAddLink(group) {
        return group.querySelector(".add-row a.addlink, .add-row a:not(.add-same-inline-row):not(.add-same-commercial-packing)");
    }

    function clickAddLink(addLink) {
        if (addLink && typeof addLink.click === "function") {
            addLink.click();
        }
    }

    function replaceFormIndex(root, prefix, index) {
        var pattern = new RegExp(prefix + "-(?:__prefix__|empty)", "g");
        Array.from(root.querySelectorAll("*")).concat(root).forEach(function (element) {
            ["for", "id", "name"].forEach(function (attribute) {
                var value = element.getAttribute && element.getAttribute(attribute);
                if (value) {
                    element.setAttribute(attribute, value.replace(pattern, prefix + "-" + index));
                }
            });
        });
    }

    function addDeleteLink(row) {
        var deleteCell = row.querySelector("td.delete");
        if (!deleteCell || deleteCell.querySelector(".inline-deletelink")) {
            return;
        }

        var wrapper = document.createElement("div");
        var link = document.createElement("a");
        link.href = "#";
        link.className = "inline-deletelink";
        link.textContent = "Remove";
        link.addEventListener("click", function (event) {
            event.preventDefault();
            row.remove();
            notifyAutosave();
        });
        wrapper.appendChild(link);
        deleteCell.appendChild(wrapper);
    }

    function fallbackAddRow(group) {
        var totalInput = group.querySelector('input[id$="-TOTAL_FORMS"]');
        var template = group.querySelector("tr.empty-form, tr[id$='-empty']");
        if (!totalInput || !template) {
            return null;
        }

        var prefix = totalInput.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
        var index = parseInt(totalInput.value || "0", 10);
        if (Number.isNaN(index)) {
            return null;
        }

        var row = template.cloneNode(true);
        row.classList.remove("empty-form", "empty-row");
        row.classList.add("dynamic-" + prefix);
        row.id = prefix + "-" + index;
        replaceFormIndex(row, prefix, index);
        addDeleteLink(row);

        template.parentNode.insertBefore(row, template);
        totalInput.value = String(index + 1);
        row.dispatchEvent(new CustomEvent("formset:added", {
            bubbles: true,
            detail: { formsetName: prefix }
        }));
        return row;
    }

    function addSameCommercialPackingLine(group) {
        var addLink = getRealAddLink(group);
        if (!addLink) {
            return;
        }

        var sourceRow = getLastCopyableRow(group);
        var beforeRows = getRows(group);

        clickAddLink(addLink);

        window.setTimeout(function () {
            var afterRows = getRows(group);
            var newRow = afterRows.find(function (row) {
                return beforeRows.indexOf(row) === -1;
            });

            if (!newRow) {
                newRow = fallbackAddRow(group);
            }

            if (sourceRow && newRow && newRow !== sourceRow) {
                Array.from(sourceRow.querySelectorAll("input, select, textarea")).forEach(function (sourceField) {
                    copyFieldValue(sourceField, newRow);
                });
                notifyAutosave();
            }
            updateRowNumbers(group);
        }, 0);
    }

    function ensureSamePackingButton(group) {
        if (!isCloneableInvoiceGroup(group) || group.querySelector(".add-same-inline-row, .add-same-commercial-packing")) {
            return;
        }

        var addLink = getRealAddLink(group);
        if (!addLink) {
            return;
        }
        var sameLink = document.createElement("a");
        sameLink.href = "#";
        sameLink.className = "add-same-inline-row add-same-commercial-packing";
        sameLink.textContent = "Add another same item";
        sameLink.addEventListener("click", function (event) {
            event.preventDefault();
            addSameCommercialPackingLine(group);
        });

        addLink.insertAdjacentElement("afterend", sameLink);
    }

    function setup(root) {
        getInlineGroups(root || document).forEach(normalizeInvoiceLineClasses);
        updateRowNumbers(root || document);
        getInlineGroups(root || document).forEach(ensureSamePackingButton);
    }

    document.addEventListener("DOMContentLoaded", function () {
        setup(document);
        [50, 200, 600, 1200].forEach(function (delay) {
            window.setTimeout(function () {
                setup(document);
            }, delay);
        });

        if (window.MutationObserver) {
            var observer = new MutationObserver(function (mutations) {
                if (mutations.some(function (mutation) { return mutation.addedNodes && mutation.addedNodes.length; })) {
                    setup(document);
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }

        document.body.addEventListener("formset:added", function () {
            window.setTimeout(function () {
                setup(document);
            }, 0);
        });

        document.addEventListener("input", function (event) {
            if (event.target.closest(".inline-group")) {
                window.setTimeout(function () {
                    updateRowNumbers(document);
                }, 0);
            }
        }, true);

        document.addEventListener("change", function (event) {
            if (event.target.closest(".inline-group")) {
                window.setTimeout(function () {
                    updateRowNumbers(document);
                }, 0);
            }
        }, true);

    });
})();
