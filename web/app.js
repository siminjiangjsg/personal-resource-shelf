import {$, state, navigate, refresh, run} from "./shared.js";
import {renderLibrary, setupLibrary} from "./library.js";
import {setupEditor} from "./resource-editor.js";
import {renderCollections, renderShare, setupSharing} from "./sharing.js";
import {loadInfo, setupBackup} from "./backup.js";

function showRoute() {
  const library = ["all", "inbox", "archive"].includes(state.route);
  const view = library ? "library" : state.route;
  for (const name of ["library", "collections", "share", "backup"]) $(name + "-view").hidden = name !== view;
  document.querySelectorAll(".nav-button").forEach(button => {
    const active = button.dataset.route === (state.route === "share" ? "collections" : state.route);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  if (library) renderLibrary();
  if (view === "collections") renderCollections();
  if (view === "share") renderShare();
}
function updated() {
  $("all-count").textContent = state.resources.filter(item => !item.archived).length;
  $("inbox-count").textContent = state.resources.filter(item => item.inbox && !item.archived).length;
  showRoute();
}
setupEditor();
setupLibrary();
setupSharing();
setupBackup();
document.addEventListener("click", event => {
  const button = event.target.closest("[data-route]");
  if (button) { $("feedback").hidden = true; navigate(button.dataset.route); }
});
document.addEventListener("route-change", showRoute);
document.addEventListener("library-updated", updated);
window.addEventListener("beforeunload", event => {
  if (state.resourceDirty || state.shareDirty) { event.preventDefault(); event.returnValue = ""; }
});
run(async () => { await refresh(); await loadInfo(); });
