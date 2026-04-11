/**
 * Mouse-follow 3D tilt effect for .card-3d-tilt elements.
 * Adds subtle rotateX/rotateY based on mouse position over the card.
 * Call window.initCard3dTilt(container) after injecting new cards (infinite scroll).
 */
(function () {
  function bindCard(card) {
    if (card.dataset.tiltBound === "1") return;
    card.dataset.tiltBound = "1";
    card.addEventListener("mousemove", function (e) {
      var rect = card.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      var centerX = rect.width / 2;
      var centerY = rect.height / 2;
      var rotateX = (y - centerY) / 20;
      var rotateY = (centerX - x) / 20;
      card.style.transform =
        "perspective(1000px) rotateX(" +
        rotateX +
        "deg) rotateY(" +
        rotateY +
        "deg) translateY(-8px) scale(1.02)";
      card.style.boxShadow = "0 20px 40px rgba(0,0,0,0.15)";
    });
    card.addEventListener("mouseleave", function () {
      card.style.transform = "";
      card.style.boxShadow = "";
    });
  }

  window.initCard3dTilt = function (root) {
    root = root || document;
    root.querySelectorAll(".card-3d-tilt").forEach(bindCard);
  };

  function init() {
    window.initCard3dTilt(document);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
