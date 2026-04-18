/**
 * Dashboard full-page loader — shows on same-origin navigations and form posts.
 * Opt out: data-sf-no-loader on <a> or <form>.
 */
(function () {
  var loader = document.getElementById("sf-dashboard-loader");
  if (!loader) return;

  function show() {
    loader.classList.add("is-visible");
    loader.setAttribute("aria-hidden", "false");
    loader.setAttribute("aria-busy", "true");
    document.body.classList.add("sf-dashboard-loading");
  }

  function hide() {
    loader.classList.remove("is-visible");
    loader.setAttribute("aria-hidden", "true");
    loader.removeAttribute("aria-busy");
    document.body.classList.remove("sf-dashboard-loading");
  }

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

  window.addEventListener("pageshow", function (e) {
    if (e.persisted) hide();
  });

  window.addEventListener("popstate", hide);
})();
