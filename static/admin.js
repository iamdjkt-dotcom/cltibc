// CLTIBC admin — team photo cropper.
// Pick a photo, drag it to centre the face, zoom with the slider.
// On save, the visible circle is baked into a square JPEG and uploaded.
(function () {
  var input = document.getElementById("team-photo");
  var box = document.getElementById("crop-box");
  var canvas = document.getElementById("crop-canvas");
  var zoomCtl = document.getElementById("crop-zoom");
  var form = document.getElementById("team-form");
  if (!input || !box || !canvas || !zoomCtl || !form || !window.DataTransfer) return;

  var SIZE = 600;
  var ctx = canvas.getContext("2d");
  var img = null, zoom = 1, ox = 0, oy = 0;
  var dragging = false, lastX = 0, lastY = 0;

  function baseScale() {
    return Math.max(SIZE / img.width, SIZE / img.height);
  }

  function draw() {
    if (!img) return;
    var s = baseScale() * zoom;
    var w = img.width * s, h = img.height * s;
    // keep the photo covering the whole crop area
    ox = Math.min(0, Math.max(SIZE - w, ox));
    oy = Math.min(0, Math.max(SIZE - h, oy));
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, SIZE, SIZE);
    ctx.drawImage(img, ox, oy, w, h);
  }

  input.addEventListener("change", function () {
    var file = input.files && input.files[0];
    if (!file) { box.hidden = true; img = null; return; }
    var url = URL.createObjectURL(file);
    var im = new Image();
    im.onload = function () {
      img = im;
      zoom = 1;
      zoomCtl.value = "1";
      var s = baseScale();
      ox = (SIZE - img.width * s) / 2;
      oy = (SIZE - img.height * s) / 2;
      box.hidden = false;
      draw();
      URL.revokeObjectURL(url);
    };
    im.onerror = function () { box.hidden = true; img = null; };
    im.src = url;
  });

  zoomCtl.addEventListener("input", function () {
    if (!img) return;
    var next = parseFloat(zoomCtl.value) || 1;
    // zoom around the centre of the circle
    var s = baseScale() * zoom;
    var cx = (SIZE / 2 - ox) / s, cy = (SIZE / 2 - oy) / s;
    zoom = next;
    var s2 = baseScale() * zoom;
    ox = SIZE / 2 - cx * s2;
    oy = SIZE / 2 - cy * s2;
    draw();
  });

  canvas.addEventListener("pointerdown", function (e) {
    if (!img) return;
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = "grabbing";
    e.preventDefault();
  });
  canvas.addEventListener("pointermove", function (e) {
    if (!dragging) return;
    var scale = SIZE / canvas.getBoundingClientRect().width;
    ox += (e.clientX - lastX) * scale;
    oy += (e.clientY - lastY) * scale;
    lastX = e.clientX;
    lastY = e.clientY;
    draw();
  });
  ["pointerup", "pointercancel"].forEach(function (evt) {
    canvas.addEventListener(evt, function () {
      dragging = false;
      canvas.style.cursor = "grab";
    });
  });

  // Before the form submits, replace the chosen file with the cropped square.
  form.addEventListener("submit", function () {
    if (!img) return;
    draw();
    try {
      var dataURL = canvas.toDataURL("image/jpeg", 0.92);
      var bin = atob(dataURL.split(",")[1]);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      var file = new File([bytes], "team-photo.jpg", { type: "image/jpeg" });
      var dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch (err) {
      // If anything fails, the original file uploads unchanged.
    }
  });
})();
