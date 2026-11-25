// Stamp the appearance before first paint, so there is no flash. Choices: "system" (Jami's blue night, by the
// owner's choice), "light" and "dark" (black). ?theme= (screenshots) wins; then the saved choice. Stars can be off.
(function () {
  var q = new URLSearchParams(location.search);
  var c = q.get("theme");
  if (c !== "light" && c !== "dark" && c !== "system" && c !== "blue") {
    try { c = JSON.parse(localStorage.getItem("ss-theme-choice") || '"system"'); } catch (e) { c = "system"; }
  }
  document.documentElement.setAttribute("data-theme", c === "light" || c === "dark" ? c : "blue");
  var stars = q.get("stars");
  if (stars == null) { try { stars = localStorage.getItem("ss-stars"); } catch (e) {} }
  if (stars === "false" || stars === "0") document.documentElement.classList.add("no-stars");
})();
