import {$, state, element, action, originalLink, navigate, api, refresh, notify, run, formatTime} from "./shared.js";

let draft = null;
let saving = false;
function publicItems() {
  const byId = new Map(state.resources.map(resource => [resource.id, resource]));
  return [...state.selected].map(id => byId.get(id)).filter(Boolean).map(resource => ({
    resource_id: resource.id, title: resource.title, url: resource.url,
    recommendation: "", tags: [...resource.tags],
  }));
}
function updateDraftStatus() {
  $("share-status").textContent = state.shareDirty ? "有未保存的更改" : "已保存到本机";
  $("share-exports").hidden = state.shareDirty || !draft?.id;
  $("save-share").disabled = saving || !draft?.title.trim() || !draft.items.length;
  if (draft?.id && !state.shareDirty) {
    $("preview-share").href = "/share/" + draft.id;
    $("download-html").href = "/api/collections/" + draft.id + "/html";
    $("download-md").href = "/api/collections/" + draft.id + "/markdown";
  }
}
function markDirty() { state.shareDirty = true; updateDraftStatus(); }
export function newShare() {
  if (saving) { notify("正在保存清单，请稍候。"); return; }
  const items = publicItems();
  if (!items.length) { notify("请先选择想分享的资源。"); navigate("all"); return; }
  if (items.length > 500) { notify("一份清单最多支持 500 项，请减少选择。", true); return; }
  if (state.shareDirty && !window.confirm("当前清单还有未保存的修改，改为新建清单？")) return;
  draft = {title: "我的精选资源", show_tags: false, items};
  state.shareDirty = true;
  navigate("share");
}
function openCollection(collection) {
  if (saving) { notify("正在保存清单，请稍候。"); return; }
  if (state.shareDirty && !window.confirm("当前清单还有未保存的修改，放弃后打开另一份清单？")) return;
  draft = structuredClone(collection);
  state.shareDirty = false;
  navigate("share");
}
export function renderCollections() {
  $("continue-share").hidden = !draft;
  $("collection-list").replaceChildren();
  if (!state.collections.length) {
    const empty = element("div", "empty");
    empty.append(element("h2", "", "还没有分享清单"), element("p", "", "勾选资源，创建分享清单。"));
    $("collection-list").append(empty);
  }
  for (const collection of [...state.collections].sort((a,b) => b.updated_at.localeCompare(a.updated_at))) {
    const row = element("article", "collection-row between");
    const info = element("div", "stack");
    info.append(action(collection.title, () => openCollection(collection), "resource-title"),
      element("p", "small muted", collection.items.length + " 项 · 更新于 " + formatTime(collection.updated_at)));
    row.append(info, action("编辑清单", () => openCollection(collection), "btn"));
    $("collection-list").append(row);
  }
}
export function renderShare() {
  if (!draft) { navigate("collections"); return; }
  $("collection-title").value = draft.title;
  $("share-tags").checked = draft.show_tags;
  $("share-count").textContent = draft.items.length + " 项";
  $("append-selected").disabled = state.selected.size === 0;
  $("share-items").replaceChildren();
  if (!draft.items.length) $("share-items").append(element("p", "empty", "清单为空，可以追加资源或重新选择。"));
  draft.items.forEach((item, index) => {
    const entry = element("section", "share-entry stack");
    const heading = element("div", "between");
    heading.append(element("h3", "", (index + 1) + ". " + item.title));
    const controls = element("div", "cluster");
    for (const [label, delta] of [["上移", -1], ["下移", 1]]) {
      const button = action(label, () => {
        const target = index + delta;
        [draft.items[index], draft.items[target]] = [draft.items[target], draft.items[index]];
        markDirty(); renderShare();
      });
      button.disabled = index + delta < 0 || index + delta >= draft.items.length;
      button.setAttribute("aria-label", label + "：" + item.title);
      controls.append(button);
    }
    const remove = action("移出", () => { draft.items.splice(index, 1); markDirty(); renderShare(); });
    remove.setAttribute("aria-label", "移出清单：" + item.title);
    controls.append(remove);
    heading.append(controls);
    const label = element("label", "field");
    label.htmlFor = "recommend-" + index;
    label.append(element("span", "small muted", "本清单的推荐语（可留空）"));
    const input = element("textarea", "input");
    input.id = label.htmlFor; input.rows = 2; input.maxLength = 4000;
    input.value = item.recommendation;
    input.placeholder = "写给对方看的用途或推荐理由";
    input.addEventListener("input", () => { item.recommendation = input.value; markDirty(); });
    label.append(input);
    entry.append(heading, originalLink(item.url), label);
    if (draft.show_tags && item.tags.length) entry.append(element("p", "small muted", item.tags.join(" · ")));
    $("share-items").append(entry);
  });
  updateDraftStatus();
}
export function setupSharing() {
  $("continue-share").addEventListener("click", () => navigate("share"));
  $("collection-title").addEventListener("input", event => { draft.title = event.target.value; markDirty(); });
  $("share-tags").addEventListener("change", event => { draft.show_tags = event.target.checked; markDirty(); renderShare(); });
  $("append-selected").addEventListener("click", () => {
    const existing = new Set(draft.items.map(item => item.resource_id));
    const additions = publicItems().filter(item => !existing.has(item.resource_id));
    if (draft.items.length + additions.length > 500) { notify("一份清单最多支持 500 项。", true); return; }
    draft.items.push(...additions); markDirty(); renderShare();
    notify(additions.length ? "已追加 " + additions.length + " 项，保存后生效。" : "已选资源都在这份清单中。");
  });
  $("save-share").addEventListener("click", () => run(async () => {
    saving = true;
    $("share-view").inert = true;
    try {
      const {title, show_tags, items} = draft;
      draft = await api("/api/collections" + (draft.id ? "/" + draft.id : ""), draft.id ? "PUT" : "POST",
        {title: title.trim(), show_tags, items});
      state.shareDirty = false;
      await refresh();
      renderShare();
      notify("清单已保存。先预览，再导出。");
    } finally { saving = false; $("share-view").inert = false; }
  }, $("save-share")).then(updateDraftStatus));
  $("copy-md").addEventListener("click", () => run(async () => {
    const response = await fetch("/api/collections/" + draft.id + "/markdown");
    if (!response.ok) throw new Error("读取分享内容失败，请重试。");
    const text = await response.text();
    try { await navigator.clipboard.writeText(text); }
    catch { throw new Error("浏览器未允许复制，请使用“下载 Markdown”。"); }
    notify("已复制 Markdown，只包含这份清单的公开内容。");
  }, $("copy-md")));
}
