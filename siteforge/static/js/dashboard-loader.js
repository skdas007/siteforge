/**
 * Dashboard full-page loader — shows on same-origin navigations and form posts.
 * Opt out: data-sf-no-loader on <a> or <form>.
 *
 * The overlay is cleared when the browser finishes loading the document
 * (document.readyState === "complete" / window "load") — aligned with the tab
 * loading indicator. Safety timeout clears the overlay if navigation is cancelled.
 */
(function () {
  var loader = document.getElementById("sf-dashboard-loader");
  if (!loader) return;

  var stuckTimer = null;
  /** If show() runs but navigation never completes (preventDefault, etc.) */
  var STUCK_MS = 12000;

  function show() {
    if (stuckTimer) {
      clearTimeout(stuckTimer);
      stuckTimer = null;
    }
    loader.classList.add("is-visible");
    loader.setAttribute("aria-hidden", "false");
    loader.setAttribute("aria-busy", "true");
    document.body.classList.add("sf-dashboard-loading");
    stuckTimer = window.setTimeout(function () {
      stuckTimer = null;
      hide();
    }, STUCK_MS);
  }

  function hide() {
    if (stuckTimer) {
      clearTimeout(stuckTimer);
      stuckTimer = null;
    }
    loader.classList.remove("is-visible");
    loader.setAttribute("aria-hidden", "true");
    loader.removeAttribute("aria-busy");
    document.body.classList.remove("sf-dashboard-loading");
  }

  /**
   * Hide once the browser has finished loading resources for this document
   * (same lifecycle as the address bar / tab loading state ending).
   */
  function hideWhenDocumentComplete() {
    if (document.readyState === "complete") {
      hide();
      return;
    }
    window.addEventListener(
      "load",
      function () {
        hide();
      },
      { once: true }
    );
  }

  hideWhenDocumentComplete();

  window.addEventListener("pageshow", function () {
    hideWhenDocumentComplete();
  });

  document.addEventListener(
    "click",
    function (e) {
      var a = e.target.closest("a[href]");
      if (!a) return;
      if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.hasAttribute("data-sf-no-loader")) return;
      var href = a.getAttribute("href");
      if (!href || href.trim().charAt(0) === "#") return;
      if (href.indexOf("mailto:") === 0 || href.indexOf("tel:") === 0 || href.indexOf("javascript:") === 0)
        return;
      if (a.getAttribute("target") === "_blank" || a.hasAttribute("download")) return;
      try {
        var u = new URL(a.href, window.location.href);
        if (u.origin !== window.location.origin) return;
        if (
          u.pathname === window.location.pathname &&
          u.search === window.location.search
        ) {
          return;
        }
      } catch (_) {
        return;
      }
      show();
    },
    true
  );

  document.addEventListener(
    "submit",
    function (e) {
      var form = e.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (form.hasAttribute("data-sf-no-loader")) return;
      if (form.getAttribute("target") === "_blank") return;
      show();
    },
    true
  );

  window.addEventListener("popstate", hide);
})();
