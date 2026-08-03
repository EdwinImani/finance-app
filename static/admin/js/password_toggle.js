(function () {
    "use strict";

    function addPasswordToggle(input) {
        if (!input || input.dataset.passwordToggleReady === "1") {
            return;
        }

        input.dataset.passwordToggleReady = "1";
        var wrapper = input.parentElement;
        if (!wrapper.classList.contains("password-field-wrapper")) {
            wrapper = document.createElement("span");
            wrapper.className = "password-field-wrapper";
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
        }

        var button = document.createElement("button");
        button.type = "button";
        button.className = "password-toggle";
        button.dataset.passwordToggle = input.id;
        button.setAttribute("aria-label", "Afficher le mot de passe");
        button.setAttribute("title", "Afficher le mot de passe");
        button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5c-5.5 0-9.5 5.1-9.7 5.3a2.7 2.7 0 0 0 0 3.4C2.5 13.9 6.5 19 12 19s9.5-5.1 9.7-5.3a2.7 2.7 0 0 0 0-3.4C21.5 10.1 17.5 5 12 5Zm0 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-6a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/></svg>';
        wrapper.appendChild(button);
    }

    function initialize(root) {
        (root || document).querySelectorAll('input[type="password"]').forEach(addPasswordToggle);
    }

    document.addEventListener("DOMContentLoaded", function () {
        initialize(document);
        new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) {
                        initialize(node.matches && node.matches('input[type="password"]') ? node.parentElement : node);
                    }
                });
            });
        }).observe(document.body, { childList: true, subtree: true });
    });

    document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-password-toggle]");
        if (!button) {
            return;
        }
        var input = document.getElementById(button.dataset.passwordToggle);
        if (!input) {
            return;
        }
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        var label = show ? "Masquer le mot de passe" : "Afficher le mot de passe";
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
        input.focus({ preventScroll: true });
    });
})();
