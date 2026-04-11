/**
 * Replace broken remote images (e.g. DB path exists but file missing on S3) with a local placeholder.
 * Covers: error event, decode failure (naturalWidth 0), lazy-loaded imgs, DOM injected later.
 * Body: data-sf-no-image="{% static 'img/no-image.svg' %}"
 * Skip: data-no-img-fallback="1"
 */
(function () {
  function fallbackUrl() {
    var b = document.body;
    return (b && b.getAttribute("data-sf-no-image")) || "";
  }

  function shouldSkip(el) {
    if (!el || el.tagName !== "IMG") return true;
    if (el.getAttribute("data-no-img-fallback") === "1") return true;
    if (el.dataset.sfFallbackDone === "1") return true;
    var cur = el.getAttribute("src") || "";
    if (!cur || cur === "") return true;
    if (cur.indexOf("no-image") !== -1) return true;
    return false;
  }

  function applyFallback(el) {
    if (shouldSkip(el)) return;
    var url = fallbackUrl();
    if (!url) return;
    el.dataset.sfFallbackDone = "1";
    el.removeAttribute("srcset");
    el.removeAttribute("sizes");
    el.src = url;
    el.classList.add("sf-img-fallback-applied");
    if (!el.getAttribute("alt")) {
      el.setAttribute("alt", "No image available");
    }
  }

  /** S3 sometimes returns 200 + non-image body: load fires, dimensions stay 0 */
  function checkDecoded(el) {
    if (shouldSkip(el)) return;
    if (!el.complete || !el.src) return;
    try {
      if (el.naturalWidth === 0 && el.naturalHeight === 0) {
        applyFallback(el);
      }
    } catch (e) {
      applyFallback(el);
    }
  }

  function scanAll() {
    document.querySelectorAll("img").forEach(function (img) {
      checkDecoded(img);
    });
  }

  document.addEventListener(
    "error",
    function (ev) {
      if (ev.target && ev.target.tagName === "IMG") {
        applyFallback(ev.target);
      }
    },
    true
  );

  document.addEventListener(
    "load",
    function (ev) {
      if (ev.target && ev.target.tagName === "IMG") {
        checkDecoded(ev.target);
      }
    },
    true
  );

  function observeNew() {
    if (!window.MutationObserver) return;
    var obs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (n) {
          if (n.nodeType !== 1) return;
          if (n.tagName === "IMG") {
            checkDecoded(n);
            n.addEventListener("load", function () {
              checkDecoded(n);
            });
          }
          try {
            if (n.querySelectorAll) {
              n.querySelectorAll("img").forEach(function (img) {
                checkDecoded(img);
              });
            }
          } catch (e) {}
        });
      });
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
  }

  function boot() {
    scanAll();
    observeNew();
    window.addEventListener("load", scanAll);
    setTimeout(scanAll, 400);
    setTimeout(scanAll, 2000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
