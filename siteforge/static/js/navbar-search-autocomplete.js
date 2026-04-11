/**
 * Navbar product search: debounced JSON autocomplete + keyboard-friendly list.
 */
(function () {
  var input = document.getElementById("navbarProductSearch");
  if (!input || !input.dataset.suggestUrl) return;

  var wrap = input.closest(".navbar-search-combo");
  if (!wrap) return;

  var panel = document.getElementById("navbarSearchSuggestions");
  if (!panel) return;

  var urlBase = input.dataset.suggestUrl;
  var debounceMs = 220;
  var minChars = 2;
  var timer = null;
  var activeIndex = -1;
  var items = [];

  function hidePanel() {
    panel.hidden = true;
    panel.innerHTML = "";
    items = [];
    activeIndex = -1;
    panel.removeAttribute("role");
  }

  function render(results) {
    panel.innerHTML = "";
    items = [];
    if (!results || !results.length) {
      hidePanel();
      return;
    }
    panel.hidden = false;
    panel.setAttribute("role", "listbox");
    panel.setAttribute("aria-label", "Product suggestions");

    results.forEach(function (row, i) {
      var a = document.createElement("a");
      a.href = row.url;
      a.className = "navbar-search-suggest-item";
      a.setAttribute("role", "option");
      a.id = "nav-suggest-" + i;
      var main = document.createElement("span");
      main.className = "navbar-search-suggest-name";
      main.textContent = row.name;
      a.appendChild(main);
      if (row.category) {
        var sub = document.createElement("span");
        sub.className = "navbar-search-suggest-cat";
        sub.textContent = row.category;
        a.appendChild(sub);
      }
      a.addEventListener("mousedown", function (e) {
        e.preventDefault();
      });
      panel.appendChild(a);
      items.push(a);
    });
  }

  function setActive(i) {
    items.forEach(function (el, j) {
      el.classList.toggle("active", j === i);
      el.setAttribute("aria-selected", j === i ? "true" : "false");
    });
    activeIndex = i;
  }

  function fetchSuggest(q) {
    var url = urlBase + "?q=" + encodeURIComponent(q);
    fetch(url, {
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (input.value.trim() !== q) return;
        render(data.results || []);
      })
      .catch(function () {
        hidePanel();
      });
  }

  input.addEventListener("input", function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < minChars) {
      hidePanel();
      return;
    }
    timer = setTimeout(function () {
      fetchSuggest(q);
    }, debounceMs);
  });

  input.addEventListener("keydown", function (e) {
    if (panel.hidden || !items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(Math.min(activeIndex + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(Math.max(activeIndex - 1, -1));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      window.location.href = items[activeIndex].href;
    } else if (e.key === "Escape") {
      hidePanel();
    }
  });

  document.addEventListener("click", function (e) {
    if (!wrap.contains(e.target)) hidePanel();
  });

  input.addEventListener("focus", function () {
    var q = input.value.trim();
    if (q.length >= minChars && !panel.innerHTML) fetchSuggest(q);
  });
})();
