import {$, state, kinds, element, originalLink, api, refresh, notify} from "./shared.js";
import {openEditor} from "./resource-editor.js";
import {newShare} from "./sharing.js";

export function filteredResources() {
  const terms = state.query.normalize("NFKC").toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  return state.resources.filter(resource => {
    const inScope = state.route === "archive" ? resource.archived : !resource.archived;
    const text = [resource.title, resource.url, resource.source, resource.kind, resource.category,
      resource.description, resource.note, ...resource.tags].join(" ").normalize("NFKC").toLocaleLowerCase();
    return inScope && (state.route !== "inbox" || resource.inbox) &&
      (!state.kind || resource.kind === state.kind) &&
      (!state.category || resource.category === state.category) &&
      (!state.status || resource.status === state.status) &&
      terms.every(term => text.includes(term));
  }).sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}
export function updateSelection() {
  $("selection-count").textContent = "已选 " + state.selected.size + " 项";
  $("clear-selection").disabled = state.selected.size === 0;
  $("create-share").disabled = state.selected.size === 0;
}
export function renderLibrary() {
  $("library-title").textContent = ({all: "全部资源", inbox: "待整理", archive: "归档资源"})[state.route] || "全部资源";
  $("capture-form").hidden = state.route === "archive";
  const categories = [...new Set(state.resources.map(resource => resource.category).filter(Boolean))].sort();
  $("category-filter").replaceChildren(new Option("全部分类", ""), ...categories.map(category => new Option(category, category)));
  $("category-filter").value = state.category;
  $("category-options").replaceChildren(...categories.map(category => new Option(category)));
  const filtered = filteredResources();
  $("resource-list").replaceChildren();
  $("result-count").textContent = "找到 " + filtered.length + " 项资源";
  $("select-results").disabled = filtered.length === 0;
  if (!filtered.length) {
    const empty = element("div", "empty");
    empty.append(element("h2", "", state.resources.length ? "没有匹配的资源" : "先收藏一个好发现"),
      element("p", "", state.resources.length ? "调整筛选条件再试试。" : "先收下链接，稍后整理。"));
    $("resource-list").append(empty);
  }
  for (const resource of filtered.slice(0, state.limit)) {
    const row = element("article", "resource");
    const label = element("label", "select-hit");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selected.has(resource.id);
    checkbox.setAttribute("aria-label", "选择分享：" + resource.title);
    checkbox.addEventListener("change", () => {
      checkbox.checked ? state.selected.add(resource.id) : state.selected.delete(resource.id);
      updateSelection();
    });
    label.append(checkbox);
    const body = element("div");
    const title = element("button", "resource-title", resource.title);
    title.type = "button";
    title.addEventListener("click", () => openEditor(resource));
    const meta = element("div", "resource-meta");
    meta.append(element("span", "kind", resource.kind), element("span", "", resource.source),
      element("span", "", resource.status));
    if (resource.inbox) meta.append(element("span", "", "待整理"));
    if (resource.category) meta.append(element("span", "", resource.category));
    resource.tags.forEach(tag => meta.append(element("span", "", "#" + tag)));
    body.append(title, meta);
    if (resource.description) body.append(element("p", "resource-description", resource.description));
    body.append(originalLink(resource.url));
    row.append(label, body);
    $("resource-list").append(row);
  }
  $("load-more").hidden = filtered.length <= state.limit;
  updateSelection();
}
export function setupLibrary() {
  $("kind-filter").append(...kinds.map(kind => new Option(kind, kind)));
  $("new-resource").addEventListener("click", () => openEditor());
  for (const [id, key] of [["search", "query"], ["kind-filter", "kind"], ["category-filter", "category"], ["status-filter", "status"]]) {
    $(id).addEventListener(id === "search" ? "input" : "change", event => {
      state[key] = event.target.value; state.limit = 100; renderLibrary();
    });
  }
  $("reset-filters").addEventListener("click", () => {
    state.query = state.kind = state.category = state.status = ""; state.limit = 100;
    ["search", "kind-filter", "category-filter", "status-filter"].forEach(id => { $(id).value = ""; });
    renderLibrary();
  });
  $("load-more").addEventListener("click", () => { state.limit += 100; renderLibrary(); });
  $("select-results").addEventListener("click", () => { filteredResources().forEach(resource => state.selected.add(resource.id)); renderLibrary(); });
  $("clear-selection").addEventListener("click", () => { state.selected.clear(); renderLibrary(); });
  $("create-share").addEventListener("click", newShare);
  $("capture-form").addEventListener("submit", async event => {
    event.preventDefault();
    const urls = $("capture-urls").value.split(/\r?\n/).map(url => url.trim()).filter(Boolean);
    const button = $("capture-button"); button.disabled = true; button.setAttribute("aria-busy", "true");
    $("capture-urls").disabled = true;
    let added = 0;
    const failures = [];
    for (const url of urls) {
      try { await api("/api/resources", "POST", {url}); added += 1; }
      catch (error) { failures.push({url, message: error.message}); }
    }
    try {
      await refresh();
      $("capture-urls").value = failures.map(item => item.url).join("\n");
      notify("已收下 " + added + " 个链接。" + (failures.length ? "\n" + failures.length + " 个未新增。\n" + failures[0].message : ""), Boolean(failures.length));
    } catch (error) { notify("链接提交已结束，但列表刷新失败：" + error.message, true); }
    finally { button.disabled = false; button.removeAttribute("aria-busy"); $("capture-urls").disabled = false; }
  });
}
