// Stamp the theme before first paint so there is no flash: ?theme= (screenshots), saved choice, else the system setting.
(function () {
  var t = new URLSearchParams(location.search).get("theme");
  if (t !== "light" && t !== "dark") {
    try { t = localStorage.getItem("ss-theme"); } catch (e) {}
  }
  if (t !== "light" && t !== "dark") t = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
})();
