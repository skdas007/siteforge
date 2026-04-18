/**
 * Immediate client-side checks on dashboard file inputs (size + pixel dimensions).
 * Inputs must include data-sf-upload and data-sf-max-bytes (see templates).
 */
(function () {
  "use strict";

  function parsePositiveInt(el, attr, fallback) {
    var raw = el.getAttribute(attr);
    if (raw === null || raw === "") return fallback;
    var n = parseInt(raw, 10);
    return !isFinite(n) || n < 0 ? fallback : n;
  }

  function formatBytes(n) {
    if (n >= 1048576 && n % 1048576 === 0) return n / 1048576 + " MB";
    if (n >= 1048576) return (n / 1048576).toFixed(1) + " MB";
    if (n >= 1024) return Math.round(n / 1024) + " KB";
    return n + " bytes";
  }

  function readImageDims(file) {
    return new Promise(function (resolve) {
      if (file.type === "image/svg+xml") {
        resolve({ skip: true, width: 0, height: 0, maxSide: 0 });
        return;
      }
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        URL.revokeObjectURL(url);
        var w = img.naturalWidth || 0;
        var h = img.naturalHeight || 0;
        resolve({
          skip: false,
          width: w,
          height: h,
          maxSide: Math.max(w, h),
        });
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        resolve({ skip: true, width: 0, height: 0, maxSide: 0 });
      };
      img.src = url;
    });
  }

  function readVideoDims(file) {
    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file);
      var v = document.createElement("video");
      v.muted = true;
      v.preload = "metadata";
      var done = false;
      function finish() {
        if (done) return;
        done = true;
        URL.revokeObjectURL(url);
        var w = v.videoWidth || 0;
        var h = v.videoHeight || 0;
        resolve({
          skip: !(w || h),
          width: w,
          height: h,
          maxSide: Math.max(w, h),
        });
      }
      v.onloadedmetadata = finish;
      v.onerror = function () {
        if (!done) {
          done = true;
          URL.revokeObjectURL(url);
          resolve({ skip: true, width: 0, height: 0, maxSide: 0 });
        }
      };
      v.src = url;
      try {
        v.load();
      } catch (e) {}
      window.setTimeout(finish, 6000);
    });
  }

  function dimsForFile(input, file) {
    var kind = (input.getAttribute("data-sf-kind") || "").toLowerCase();
    var isVid = file.type.indexOf("video/") === 0;
    if (kind === "image") {
      if (isVid) {
        return Promise.resolve({ rejectKind: true });
      }
      return readImageDims(file);
    }
    if (kind === "video") {
      if (!isVid) {
        return Promise.resolve({ rejectKind: true });
      }
      return readVideoDims(file);
    }
    if (isVid) {
      return readVideoDims(file);
    }
    return readImageDims(file);
  }

  function softLimitForFile(input, file) {
    var isVid = file.type.indexOf("video/") === 0;
    var imgLim = parsePositiveInt(input, "data-sf-soft-max-side", 0);
    var vidLim = parsePositiveInt(input, "data-sf-soft-max-side-video", 0);
    if (isVid && vidLim > 0) return vidLim;
    return imgLim;
  }

  function buildSoftMessage(recLabel, dims, limit) {
    return (
      "Recommended size: " +
      recLabel +
      "\n\n" +
      "This file: " +
      dims.width +
      " × " +
      dims.height +
      " px (longest side " +
      dims.maxSide +
      " px; we suggest about " +
      limit +
      " px or less on the longest side).\n\n" +
      "Very large files are scaled down on the site and may look softer, load slowly, or use more data. Keep this file anyway?"
    );
  }

  function clearInput(input) {
    input.value = "";
  }

  async function validateOne(input, file, softLimit, recLabel) {
    var maxImg = parsePositiveInt(input, "data-sf-max-bytes", 0);
    var maxVid = parsePositiveInt(input, "data-sf-max-bytes-video", maxImg);
    var isVid = file.type.indexOf("video/") === 0;
    var byteCap = isVid ? maxVid : maxImg;

    if (byteCap && file.size > byteCap) {
      window.alert(
        "This file is too large (" +
          formatBytes(file.size) +
          "). Maximum allowed here is " +
          formatBytes(byteCap) +
          "."
      );
      return false;
    }

    var meta = await dimsForFile(input, file);
    if (meta.rejectKind) {
      window.alert(
        "Please choose a different file type for this field (see accepted formats below)."
      );
      return false;
    }
    if (meta.skip || !softLimit) {
      return true;
    }
    if (meta.maxSide > softLimit) {
      var ok = window.confirm(buildSoftMessage(recLabel, meta, softLimit));
      return ok;
    }
    return true;
  }

  async function handleChange(ev) {
    var input = ev.target;
    if (
      !input ||
      input.tagName !== "INPUT" ||
      input.type !== "file" ||
      !input.hasAttribute("data-sf-upload")
    ) {
      return;
    }

    var files = input.files;
    if (!files || !files.length) return;

    var recLabel =
      input.getAttribute("data-sf-rec-label") ||
      "the size described in the help text for this field";

    var list = Array.prototype.slice.call(files);
    for (var i = 0; i < list.length; i++) {
      var file = list[i];
      var soft = softLimitForFile(input, file);
      var ok = await validateOne(input, file, soft, recLabel);
      if (!ok) {
        clearInput(input);
        return;
      }
    }
  }

  document.addEventListener("change", handleChange);

  window.SfDashboardUploadValidation = {
    /** For tests or manual bind if needed */
    handleChange: handleChange,
  };
})();
