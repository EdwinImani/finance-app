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

    function updateRowNumbers(root) {
        getInlineGroups(root).forEach(function (group) {
            var rows = getRows(group);
            if (!rows.length) {
                return;
            }

            ensureNumberHeader(group);

            var countedRows = rows.filter(function (row) {
                return !isDeleted(row) && hasUserData(row);
            });
            var total = countedRows.length;

            rows.forEach(function (row) {
                var cell = ensureNumberCell(row);
                var index = countedRows.indexOf(row);
                cell.textContent = index === -1 ? "" : String(index + 1) + "/" + String(total);
            });
        });
    }

    function isCommercialPackingGroup(group) {
        var addLink = group.querySelector(".add-row a");
        return Boolean(addLink && (addLink.textContent || "").toLowerCase().includes("commercial invoice packing"));
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

        if (targetField.type === "checkbox" || targetField.type === "radio") {
            targetField.checked = sourceField.checked;
        } else {
            targetField.value = sourceField.value;
        }
        targetField.dispatchEvent(new Event("input", { bubbles: true }));
        targetField.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function addSameCommercialPackingLine(group) {
        var addLink = group.querySelector(".add-row a");
        if (!addLink) {
            return;
        }

        var sourceRows = getRows(group).filter(function (row) {
            return !isDeleted(row);
        });
        var sourceRow = sourceRows[sourceRows.length - 1];
        var beforeRows = getRows(group);

        addLink.click();

        window.setTimeout(function () {
            var afterRows = getRows(group);
            var newRow = afterRows.find(function (row) {
                return beforeRows.indexOf(row) === -1;
            }) || afterRows[afterRows.length - 1];

            if (sourceRow && newRow && newRow !== sourceRow) {
                Array.from(sourceRow.querySelectorAll("input, select, textarea")).forEach(function (sourceField) {
                    copyFieldValue(sourceField, newRow);
                });
            }
            updateRowNumbers(group);
        }, 0);
    }

    function ensureSamePackingButton(group) {
        if (!isCommercialPackingGroup(group) || group.querySelector(".add-same-commercial-packing")) {
            return;
        }

        var addLink = group.querySelector(".add-row a");
        var sameLink = document.createElement("a");
        sameLink.href = "#";
        sameLink.className = "add-same-commercial-packing";
        sameLink.textContent = "Add another same item";
        sameLink.addEventListener("click", function (event) {
            event.preventDefault();
            addSameCommercialPackingLine(group);
        });

        addLink.insertAdjacentElement("afterend", sameLink);
    }

    function setup(root) {
        updateRowNumbers(root || document);
        getInlineGroups(root || document).forEach(ensureSamePackingButton);
    }

    document.addEventListener("DOMContentLoaded", function () {
        setup(document);

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
