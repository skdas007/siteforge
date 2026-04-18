/**
 * "What We Offer": 3 cards — random slot swap with layered motion (fade, move, scale, tilt, blur).
 * Full grid only when prefers-reduced-motion.
 */
(function () {
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function initRoot(root) {
    var pool = root.querySelectorAll(".sf-offer-pool [data-offer-index]");
    var n = pool.length;
    if (n < 4) return;

    var staticRow = root.querySelector(".sf-offer-static-all");
    var animatedRow = root.querySelector(".sf-offer-animated-slots");
    if (!staticRow || !animatedRow) return;

    var intervalMs = parseInt(root.getAttribute("data-interval-ms"), 10) || 2800;
    var fadeMs = parseInt(root.getAttribute("data-fade-ms"), 10) || 650;
    var timer = null;
    var busy = false;
    var slotIndices = [];
    var slotInners = [];

    function syncDur(el) {
      el.style.transitionDuration = fadeMs + "ms";
      /* Match features-offer.css — smooth deceleration with slight overshoot feel */
      el.style.transitionTimingFunction = "cubic-bezier(0.33, 0.82, 0.32, 1)";
    }

    function fillStaticSix() {
      staticRow.innerHTML = "";
      for (var i = 0; i < n; i++) {
        var col = document.createElement("div");
        col.className = "col-12 col-sm-6 col-lg-4 sf-offer-static-cell";
        var node = pool[i].cloneNode(true);
        node.removeAttribute("data-offer-index");
        col.appendChild(node);
        staticRow.appendChild(col);
      }
      if (window.initCard3dTilt) window.initCard3dTilt(staticRow);
    }

    function buildSlots() {
      animatedRow.innerHTML = "";
      slotInners = [];
      slotIndices = [];
      for (var s = 0; s < 3; s++) {
        var col = document.createElement("div");
        col.className = "col-12 col-md-4 sf-offer-slot";
        var inner = document.createElement("div");
        inner.className = "sf-offer-slot__inner";
        syncDur(inner);
        col.appendChild(inner);
        animatedRow.appendChild(col);
        slotInners.push(inner);
        slotIndices.push(s);
        inner.appendChild(pool[s].cloneNode(true));
      }
      if (window.initCard3dTilt) window.initCard3dTilt(animatedRow);
    }

    function allowedIndices(slot) {
      var forbidden = [];
      for (var k = 0; k < 3; k++) {
        if (k !== slot) forbidden.push(slotIndices[k]);
      }
      var out = [];
      for (var i = 0; i < n; i++) {
        if (forbidden.indexOf(i) === -1) out.push(i);
      }
      return out;
    }

    function swapRandom() {
      if (busy || reduceMotion.matches) return;
      busy = true;

      var slot = Math.floor(Math.random() * 3);
      var choices = allowedIndices(slot);
      if (choices.length === 0) {
        busy = false;
        return;
      }
      var newIdx = pickRandom(choices);

      var inner = slotInners[slot];
      syncDur(inner);
      inner.classList.add("sf-offer-slot__inner--hide");

      window.setTimeout(function () {
        inner.innerHTML = "";
        inner.classList.remove("sf-offer-slot__inner--hide");
        var fresh = pool[newIdx].cloneNode(true);
        fresh.removeAttribute("data-offer-index");
        inner.appendChild(fresh);
        slotIndices[slot] = newIdx;

        inner.classList.add("sf-offer-slot__inner--enter");
        window.requestAnimationFrame(function () {
          window.requestAnimationFrame(function () {
            inner.classList.remove("sf-offer-slot__inner--enter");
            if (window.initCard3dTilt) window.initCard3dTilt(inner);
            busy = false;
          });
        });
      }, fadeMs + 50);
    }

    function start() {
      stop();
      if (reduceMotion.matches) return;
      timer = setInterval(swapRandom, intervalMs);
    }

    function stop() {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    function layout() {
      stop();
      if (reduceMotion.matches) {
        animatedRow.classList.add("d-none");
        animatedRow.classList.remove("d-flex");
        animatedRow.innerHTML = "";
        staticRow.classList.remove("d-none");
        staticRow.classList.add("d-flex");
        fillStaticSix();
        return;
      }
      staticRow.classList.add("d-none");
      staticRow.classList.remove("d-flex");
      staticRow.innerHTML = "";
      animatedRow.classList.remove("d-none");
      animatedRow.classList.add("d-flex");
      buildSlots();
      start();
    }

    var ioVisible = false;
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          ioVisible = e.isIntersecting;
          if (ioVisible && !reduceMotion.matches) start();
          else stop();
        });
      },
      { threshold: 0.06 }
    );
    io.observe(root);

    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", function () {
      if (ioVisible && !reduceMotion.matches) start();
    });

    if (reduceMotion.addEventListener) reduceMotion.addEventListener("change", layout);
    else if (reduceMotion.addListener) reduceMotion.addListener(layout);

    layout();
  }

  function boot() {
    document.querySelectorAll(".sf-offer-fade-carousel").forEach(function (root) {
      if (root.dataset.sfOfferFadeInit === "1") return;
      root.dataset.sfOfferFadeInit = "1";
      initRoot(root);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
