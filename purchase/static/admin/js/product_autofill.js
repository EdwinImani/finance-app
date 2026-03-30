document.addEventListener("change", function(e) {
    const target = e.target;
    const row = target.closest("tr");
    if (!row) return;

    function updateTotal() {
        const qtyInput = row.querySelector("input[name$='quantity']");
        const unitPriceInput = row.querySelector("input[name$='unit_price']");
        if (!qtyInput || !unitPriceInput) return;

        const qty = parseFloat(qtyInput.value || "0");
        const price = parseFloat(unitPriceInput.value || "0");
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

    if (target.name.includes("product")) {
        const select = target;
        const productId = select.value;
        if (!productId) return;

        fetch(`/purchase/product-info/${productId}/`)
            .then(response => response.json())
            .then(data => {
                const descriptionInput = row.querySelector("input[name$='description']") || row.querySelector("input[name$='-description']");
                const partNumberInput = row.querySelector("input[name$='part_number']") || row.querySelector("input[name$='-part_number']");
                const unitPriceInput = row.querySelector("input[name$='unit_price']") || row.querySelector("input[name$='-unit_price']");

                if (descriptionInput) {
                    descriptionInput.value = data.description || "";
                }
                if (partNumberInput) {
                    partNumberInput.value = data.part_number || "";
                }
                if (unitPriceInput) {
                    unitPriceInput.value = data.unit_price || "0";
                }
                updateTotal();
            })
            .catch(() => {
                updateTotal();
            });
    }

    if (target.name.includes("quantity") || target.name.includes("unit_price")) {
        updateTotal();
    }
});