/**
 * Scroll-driven motion: toggles .reveal-in when [data-reveal] enters/leaves view
 * (bidirectional unless data-reveal-once). Uses IntersectionObserver (GPU-friendly transforms in CSS).
 * Call window.sfRefreshScrollReveal(container) after injecting DOM (e.g. infinite scroll).
 */
(function () {
  var observed = new WeakSet();

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        var el = entry.target;
        var once = el.hasAttribute("data-reveal-once");
        if (entry.isIntersecting) {
          el.classList.add("reveal-in");
        } else if (!once) {
          el.classList.remove("reveal-in");
        }
      });
    },
    {
      root: null,
      rootMargin: "0px 0px -52px 0px",
      threshold: 0.1,
    }
  );

  function observeEl(el) {
    if (!(el instanceof Element)) return;
    if (observed.has(el)) return;
    observed.add(el);
    observer.observe(el);
  }

  function scan(root) {
    root.querySelectorAll("[data-reveal]").forEach(observeEl);
  }

  window.sfRefreshScrollReveal = function (root) {
    scan(root || document);
  };

  function init() {
    scan(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
