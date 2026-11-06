import {$, state, kinds, api, refresh, notify} from "./shared.js";

let current = null;
let saving = false;
export function openEditor(resource = null) {
  current = resource;
  $("resource-form").reset();
  const defaults = {url: "", title: "", kind: "网页", category: "", tags: [], description: "", note: "", status: "待看", inbox: true};
  const values = resource || defaults;
  for (const name of ["url", "title", "kind", "category", "description", "note", "status"]) {
    $("edit-" + name).value = values[name];
  }
  $("edit-tags").value = values.tags.join(", ");
  $("edit-organized").checked = !values.inbox;
  $("editor-title").textContent = resource ? "编辑资源" : "添加资源";
  $("archive-resource").hidden = !resource;
  $("archive-resource").textContent = resource?.archived ? "恢复到资源库" : "归档资源";
  $("editor-feedback").hidden = true;
  state.resourceDirty = false;
  $("resource-dialog").showModal();
  (resource ? $("edit-title") : $("edit-url")).focus();
}
function closeEditor() {
  if (saving) return;
  if (state.resourceDirty && !window.confirm("还有未保存的修改，放弃这些修改？")) return;
  state.resourceDirty = false;
  $("resource-dialog").close();
}
function valuesFromForm() {
  return {
    url: $("edit-url").value.trim(), title: $("edit-title").value.trim(),
    kind: $("edit-kind").value, category: $("edit-category").value.trim(),
    tags: [...new Set($("edit-tags").value.split(/[,，;；\n]/).map(tag => tag.trim()).filter(Boolean))],
    description: $("edit-description").value, note: $("edit-note").value,
    status: $("edit-status").value, inbox: !$("edit-organized").checked,
    archived: current?.archived || false,
  };
}
async function saveResource(archive = false) {
  if (!$("resource-form").reportValidity()) return;
  if (saving) return;
  saving = true;
  $("resource-form").inert = true;
  const button = $("save-resource"); button.disabled = true;
  $("archive-resource").disabled = true;
  $("editor-feedback").hidden = true;
  try {
    const draft = valuesFromForm();
    if (archive) draft.archived = !current.archived;
    const result = await api("/api/resources" + (current ? "/" + current.id : ""), current ? "PUT" : "POST", draft);
    if (result.archived) state.selected.delete(result.id);
    state.resourceDirty = false;
    $("resource-dialog").close();
    await refresh();
    notify(archive ? (result.archived ? "已归档，可在归档资源中恢复。" : "已恢复到资源库。") : "资源已保存到本机。");
  } catch (error) {
    $("editor-feedback").textContent = error.message;
    $("editor-feedback").hidden = false;
    if (!$("resource-dialog").open) notify(error.message, true);
  } finally {
    saving = false; $("resource-form").inert = false;
    button.disabled = false; $("archive-resource").disabled = false;
  }
}
export function setupEditor() {
  $("edit-kind").append(...kinds.map(kind => new Option(kind, kind)));
  $("resource-form").addEventListener("input", () => { state.resourceDirty = true; });
  $("resource-form").addEventListener("change", () => { state.resourceDirty = true; });
  $("resource-form").addEventListener("submit", event => { event.preventDefault(); saveResource(); });
  $("close-editor").addEventListener("click", closeEditor);
  $("cancel-editor").addEventListener("click", closeEditor);
  $("resource-dialog").addEventListener("cancel", event => { event.preventDefault(); closeEditor(); });
  $("archive-resource").addEventListener("click", () => saveResource(true));
}
