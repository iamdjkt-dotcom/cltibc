// CLTIBC — quiet motion only: scroll reveals, masthead shadow,
// image load fades, soft page transitions. All skipped under
// prefers-reduced-motion.
(function () {
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- scroll reveals ---- */
  var items = document.querySelectorAll("[data-reveal]");
  if (reduced || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("revealed"); });
  } else {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    items.forEach(function (el) { observer.observe(el); });
  }

  /* ---- masthead shadow ---- */
  var topbar = document.getElementById("topbar");
  if (topbar) {
    var onScroll = function () {
      topbar.classList.toggle("scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---- mobile menu ---- */
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav && topbar) {
    var setMenu = function (open) {
      topbar.classList.toggle("menu-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    };
    toggle.addEventListener("click", function () {
      setMenu(!topbar.classList.contains("menu-open"));
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setMenu(false);
    });
  }

  /* ---- images appear only once loaded (no blank flashes) ---- */
  document.querySelectorAll(".photo-grid img, .logo-badge img, .member img").forEach(function (img) {
    if (img.complete) return;
    img.classList.add("img-pending");
    img.addEventListener("load", function () {
      img.classList.remove("img-pending");
    }, { once: true });
  });

  /* ---- soft page-to-page fade ---- */
  if (!reduced) {
    document.addEventListener("click", function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      var a = e.target.closest && e.target.closest("a");
      if (!a || a.target || a.hasAttribute("download")) return;
      var url;
      try { url = new URL(a.href, location.href); } catch (err) { return; }
      if (url.origin !== location.origin) return;
      if (url.pathname === location.pathname && url.hash) return; // same-page anchor
      if (url.pathname.startsWith("/uploads/")) return;           // let files open plainly
      e.preventDefault();
      document.documentElement.classList.add("leaving");
      setTimeout(function () { location.href = url.href; }, 180);
    });
    window.addEventListener("pageshow", function () {
      document.documentElement.classList.remove("leaving");
    });
  }
})();

/* ---- likes: one per browser, live count from the server ---- */
(function () {
  document.querySelectorAll(".like-btn").forEach(function (btn) {
    var id = btn.getAttribute("data-id");
    if (!id) return;
    var key = "cltibc-liked-" + id;
    try { if (localStorage.getItem(key)) btn.classList.add("liked"); } catch (e) {}
    btn.addEventListener("click", function () {
      var liked = btn.classList.contains("liked");
      btn.disabled = true;
      fetch("/api/like", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "id=" + encodeURIComponent(id) + "&action=" + (liked ? "unlike" : "like")
      }).then(function (r) { return r.json(); }).then(function (data) {
        var count = btn.querySelector(".like-count");
        if (count && typeof data.likes === "number") count.textContent = data.likes;
        btn.classList.toggle("liked", !liked);
        try {
          if (liked) localStorage.removeItem(key);
          else localStorage.setItem(key, "1");
        } catch (e) {}
      }).finally(function () { btn.disabled = false; });
    });
  });
})();
