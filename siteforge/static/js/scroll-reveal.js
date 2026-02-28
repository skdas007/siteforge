/**
 * Minimal scroll-reveal: add .reveal-in when element enters viewport.
 * Use with data-reveal="fade-up" | "fade-down" | "fade-left" | "fade-right" | "fade" | "zoom-in" | "zoom-out"
 */
(function () {
  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-in');
        }
      });
    },
    { rootMargin: '0px 0px -60px 0px', threshold: 0.1 }
  );

  function init() {
    document.querySelectorAll('[data-reveal]').forEach(function (el) {
      observer.observe(el);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
