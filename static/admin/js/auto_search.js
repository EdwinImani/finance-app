(function() {
    "use strict";

    const SEARCH_DELAY_MS = 500;

    function findSearchForm(input) {
        const form = input.closest("form");

        return form && form.id === "changelist-search" ? form : null;
    }

    function submitForm(form) {
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
            return;
        }

        form.submit();
    }

    function installAutoSearch(input) {
        if (input.dataset.autoSearchReady === "1") {
            return;
        }

        const form = findSearchForm(input);

        if (!form) {
            return;
        }

        input.dataset.autoSearchReady = "1";
        let lastSubmittedValue = input.value;
        let timerId = null;

        function scheduleSearch() {
            window.clearTimeout(timerId);
            timerId = window.setTimeout(function() {
                const currentValue = input.value;

                if (currentValue === lastSubmittedValue) {
                    return;
                }

                lastSubmittedValue = currentValue;
                submitForm(form);
            }, SEARCH_DELAY_MS);
        }

        input.addEventListener("input", scheduleSearch);

        input.addEventListener("keydown", function(event) {
            if (event.key !== "Enter") {
                return;
            }

            window.clearTimeout(timerId);
            lastSubmittedValue = input.value;
        });
    }

    function installAllAutoSearchFields() {
        document.querySelectorAll('input[name="q"]').forEach(installAutoSearch);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installAllAutoSearchFields);
    } else {
        installAllAutoSearchFields();
    }
})();
