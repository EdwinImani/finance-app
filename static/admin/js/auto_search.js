(function() {
    "use strict";

    const SEARCH_DELAY_MS = 350;
    const AJAX_HEADER = "XMLHttpRequest";
    let activeController = null;

    function findSearchForm(input) {
        const form = input.closest("form");
        return form && form.id === "changelist-search" ? form : null;
    }

    function buildUrlFromForm(form) {
        const url = new URL(window.location.href);
        const formData = new FormData(form);

        url.searchParams.delete("p");

        formData.forEach(function(value, key) {
            url.searchParams.delete(key);
            if (String(value || "").trim() !== "") {
                url.searchParams.append(key, value);
            }
        });

        return url;
    }

    function replaceNode(selector, newDocument) {
        const currentNode = document.querySelector(selector);
        const nextNode = newDocument.querySelector(selector);

        if (currentNode && nextNode) {
            currentNode.replaceWith(nextNode);
            return nextNode;
        }

        if (currentNode && !nextNode) {
            currentNode.remove();
        }

        return null;
    }

    function syncChangelistClasses(newDocument) {
        const currentChangelist = document.querySelector("#changelist");
        const nextChangelist = newDocument.querySelector("#changelist");

        if (currentChangelist && nextChangelist) {
            currentChangelist.className = nextChangelist.className;
        }
    }

    function syncPageSizeForm(url) {
        const toolbar = document.querySelector(".page-size-toolbar form");

        if (!toolbar) {
            return;
        }

        toolbar.querySelectorAll('input[type="hidden"]').forEach(function(input) {
            input.remove();
        });

        url.searchParams.forEach(function(value, key) {
            if (key === "per_page" || key === "p") {
                return;
            }

            const input = document.createElement("input");
            input.type = "hidden";
            input.name = key;
            input.value = value;
            toolbar.insertBefore(input, toolbar.firstChild);
        });
    }

    function installClickableRows(root) {
        (root || document).querySelectorAll(".change-list #result_list tbody tr").forEach(function(row) {
            if (row.dataset.ajaxSearchClickableReady === "1") {
                return;
            }

            const primaryLink = row.querySelector("th a[href], td a[href]");

            if (!primaryLink) {
                return;
            }

            row.dataset.ajaxSearchClickableReady = "1";
            row.classList.add("row-clickable");

            row.addEventListener("click", function(event) {
                if (
                    event.target.closest("a, button, input, select, textarea, label") ||
                    event.target.closest(".action-checkbox, .action-checkbox-column")
                ) {
                    return;
                }

                if (event.ctrlKey || event.metaKey) {
                    window.open(primaryLink.href, "_blank", "noopener");
                    return;
                }

                window.location.href = primaryLink.href;
            });
        });
    }

    function installDeleteConfirmation(root) {
        const form = (root || document).querySelector("#changelist-form");

        if (!form || form.dataset.ajaxSearchDeleteConfirmReady === "1") {
            return;
        }

        form.dataset.ajaxSearchDeleteConfirmReady = "1";
        form.addEventListener("submit", function(event) {
            const action = form.querySelector('select[name="action"]');

            if (!action || action.value !== "delete_selected") {
                return;
            }

            const selectedRows = form.querySelectorAll("input.action-select:checked");
            const selectAcross = form.querySelector('input[name="select_across"]');
            const selectedAcross = selectAcross && selectAcross.value === "1";

            if (!selectedRows.length && !selectedAcross) {
                return;
            }

            if (!window.confirm("Are you sure you want to delete the selected items?")) {
                event.preventDefault();
                return;
            }

            if (!form.querySelector('input[name="post"]')) {
                const postInput = document.createElement("input");
                postInput.type = "hidden";
                postInput.name = "post";
                postInput.value = "yes";
                form.appendChild(postInput);
            }
        });
    }

    function afterListUpdate(url) {
        syncPageSizeForm(url);
        installClickableRows(document);
        installDeleteConfirmation(document);
        document.dispatchEvent(new CustomEvent("admin:ajax-search-updated"));

        if (window.financeNumberFormatting && window.financeNumberFormatting.setup) {
            window.financeNumberFormatting.setup(document);
        }
    }

    function updateListFromHtml(html, url) {
        const newDocument = new DOMParser().parseFromString(html, "text/html");

        syncChangelistClasses(newDocument);
        replaceNode("#changelist-form", newDocument);
        replaceNode("#changelist-filter", newDocument);

        window.history.replaceState({}, "", url.pathname + url.search + url.hash);
        afterListUpdate(url);
    }

    function runAjaxSearch(form, options) {
        const settings = options || {};
        const input = form.querySelector('input[name="q"]');
        const url = settings.url ? new URL(settings.url, window.location.origin) : buildUrlFromForm(form);

        if (activeController) {
            activeController.abort();
        }

        activeController = new AbortController();

        if (input) {
            input.classList.add("ajax-search-loading");
        }

        return fetch(url.toString(), {
            method: "GET",
            credentials: "same-origin",
            signal: activeController.signal,
            headers: {
                "X-Requested-With": AJAX_HEADER
            }
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error("Search failed");
                }
                return response.text();
            })
            .then(function(html) {
                updateListFromHtml(html, url);
            })
            .catch(function(error) {
                if (error.name === "AbortError") {
                    return;
                }
                form.submit();
            })
            .finally(function() {
                if (input) {
                    input.classList.remove("ajax-search-loading");
                }
                activeController = null;
            });
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
                runAjaxSearch(form);
            }, SEARCH_DELAY_MS);
        }

        input.addEventListener("input", scheduleSearch);

        form.addEventListener("submit", function(event) {
            event.preventDefault();
            window.clearTimeout(timerId);
            lastSubmittedValue = input.value;
            runAjaxSearch(form);
        });
    }

    function installAjaxNavigation() {
        document.addEventListener("click", function(event) {
            const link = event.target.closest(".change-list .paginator a, .change-list #changelist-filter a");
            const form = document.getElementById("changelist-search");

            if (!link || !form || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
                return;
            }

            event.preventDefault();
            runAjaxSearch(form, { url: link.href });
        });
    }

    function installAllAutoSearchFields() {
        document.querySelectorAll('input[name="q"]').forEach(installAutoSearch);
        installClickableRows(document);
        installDeleteConfirmation(document);
        installAjaxNavigation();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installAllAutoSearchFields);
    } else {
        installAllAutoSearchFields();
    }
})();
