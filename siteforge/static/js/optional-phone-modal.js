/**
 * Optional phone capture modal: appears after delay or scroll; remembers choice in localStorage.
 */
(function () {
  "use strict";

  /* v2: do not persist if the tab is closed/refreshed while the modal is open (see pagehide). */
  var STORAGE_PREFIX = "sf_opt_phone_done_v2_";
  var DELAY_MS = 4800;
  var DELAY_REDUCED_MS = 900;
  var SCROLL_THRESHOLD = 140;
  var CAMPAIGN_FALLBACK_MS = 3200;

  function storageKey() {
    return STORAGE_PREFIX + (location.hostname || "default");
  }

  function isDone() {
    try {
      return localStorage.getItem(storageKey()) === "1";
    } catch (e) {
      return false;
    }
  }

  function markDone() {
    try {
      localStorage.setItem(storageKey(), "1");
    } catch (e) {}
  }

  function readJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function getCookie(name) {
    var m = document.cookie.match(new RegExp("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"));
    return m ? decodeURIComponent(m.pop()) : "";
  }

  function prefersReducedMotion() {
    return (
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  /** Start phone flow only after campaign modal is gone or was never shown. */
  function afterCampaignGate(done) {
    var m = document.getElementById("sfCampaignModal");
    if (!m) {
      done();
      return;
    }
    var finished = false;
    function finish() {
      if (finished) return;
      finished = true;
      done();
    }
    m.addEventListener("hidden.bs.modal", finish);
    window.setTimeout(function () {
      if (!m.classList.contains("show")) finish();
    }, CAMPAIGN_FALLBACK_MS);
  }

  function init() {
    if (!window.bootstrap) return;
    var submitPath = readJsonScript("sf-optional-phone-url");
    if (!submitPath || typeof submitPath !== "string") return;
    if (isDone()) return;

    var modalEl = document.getElementById("sfOptionalPhoneModal");
    if (!modalEl) return;

    var brand = readJsonScript("sf-optional-phone-brand");
    var brandSpan = modalEl.querySelector("[data-sf-opt-brand]");
    if (brandSpan && typeof brand === "string" && brand.trim()) {
      brandSpan.textContent = brand.trim();
    } else if (brandSpan && !brandSpan.textContent.trim()) {
      brandSpan.textContent = "us";
    }

    var modal = new bootstrap.Modal(modalEl, {
      backdrop: true,
      keyboard: true,
    });

    var delayMs = prefersReducedMotion() ? DELAY_REDUCED_MS : DELAY_MS;

    function wireForm() {
      var form = document.getElementById("sfOptionalPhoneForm");
      var input = document.getElementById("sfOptionalPhoneInput");
      var errEl = document.getElementById("sfOptionalPhoneError");
      var thanks = document.getElementById("sfOptionalPhoneThanks");
      var submitBtn = form ? form.querySelector('[type="submit"]') : null;

      if (!form || !input) return;

      function showErr(msg) {
        if (!errEl) return;
        errEl.textContent = msg || "";
        errEl.classList.toggle("visually-hidden", !msg);
        input.classList.toggle("is-invalid", !!msg);
      }

      /** Keep only digits; max 10 (no letters or symbols). */
      input.addEventListener("input", function () {
        var digits = input.value.replace(/\D/g, "").slice(0, 10);
        if (input.value !== digits) input.value = digits;
      });

      function validatePhoneDigits(raw) {
        var s = (raw || "").trim();
        if (/[a-zA-Z]/.test(s)) {
          return "Letters are not allowed. Enter only 10 digits.";
        }
        var d = s.replace(/\D/g, "");
        if (d.length !== 10) {
          return "Enter exactly 10 digits.";
        }
        return null;
      }

      form.addEventListener("submit", function (e) {
        e.preventDefault();
        showErr("");
        var phone = (input.value || "").trim();
        if (!phone) {
          showErr("Please enter your 10-digit mobile number.");
          input.focus();
          return;
        }
        var clientErr = validatePhoneDigits(input.value || "");
        if (clientErr) {
          showErr(clientErr);
          input.focus();
          return;
        }
        phone = phone.replace(/\D/g, "");
        if (submitBtn) submitBtn.disabled = true;
        var fd = new FormData();
        fd.append("phone", phone);
        var csrfIn = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfIn) fd.append("csrfmiddlewaretoken", csrfIn.value);
        else {
          var c = getCookie("csrftoken");
          if (c) fd.append("csrfmiddlewaretoken", c);
        }

        fetch(submitPath, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, status: res.status, data: data };
            });
          })
          .then(function (pack) {
            if (pack.ok && pack.data && pack.data.success) {
              markDone();
              form.classList.add("d-none");
              if (thanks) {
                thanks.classList.remove("d-none");
                thanks.removeAttribute("hidden");
              }
              return;
            }
            var msg = "Something went wrong. Please try again.";
            if (
              pack.data &&
              pack.data.errors &&
              pack.data.errors.phone &&
              pack.data.errors.phone[0]
            ) {
              msg = pack.data.errors.phone[0];
            } else if (pack.data && pack.data.message) {
              msg = pack.data.message;
            }
            showErr(msg);
          })
          .catch(function () {
            showErr("Network error. Check your connection and try again.");
          })
          .finally(function () {
            if (submitBtn) submitBtn.disabled = false;
          });
      });
    }

    wireForm();

    /**
     * Do not save “never show again” when the page is unloading (refresh / close tab)
     * while the modal was still open — user should see the modal again next visit.
     */
    var unloadWhileModalRelevant = false;
    window.addEventListener(
      "pagehide",
      function (ev) {
        if (!ev.persisted && modalEl.classList.contains("show")) {
          unloadWhileModalRelevant = true;
        }
      },
      false
    );

    modalEl.addEventListener("shown.bs.modal", function () {
      document.body.classList.add("sf-opt-phone-prompt-active");
    });

    modalEl.addEventListener("hidden.bs.modal", function () {
      document.body.classList.remove("sf-opt-phone-prompt-active");
      var vs = typeof document.visibilityState === "string" ? document.visibilityState : "visible";
      if (unloadWhileModalRelevant || vs !== "visible") {
        unloadWhileModalRelevant = false;
        return;
      }
      markDone();
    });

    var fired = false;

    function tryShow() {
      if (fired || isDone()) return;
      fired = true;
      if (timer) window.clearTimeout(timer);
      window.removeEventListener("scroll", onScroll, opts);
      modal.show();
    }

    var timer = null;
    var opts = { passive: true };

    function onScroll() {
      if (window.scrollY >= SCROLL_THRESHOLD) tryShow();
    }

    function arm() {
      if (isDone()) return;
      timer = window.setTimeout(tryShow, delayMs);
      window.addEventListener("scroll", onScroll, opts);
    }

    afterCampaignGate(arm);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
