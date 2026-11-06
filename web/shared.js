export const kinds = ["网页", "工具", "Skill", "MCP", "文章", "教程", "文档", "资源合集"];
export const state = {
  resources: [], collections: [], selected: new Set(), route: "all",
  query: "", kind: "", category: "", status: "", limit: 100,
  resourceDirty: false, shareDirty: false,
};
export const $ = id => document.getElementById(id);
export function element(tag, className = "", text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
export function action(text, handler, className = "text-btn") {
  const button = element("button", className, text);
  button.type = "button";
  button.addEventListener("click", handler);
  return button;
}
export function originalLink(url) {
  const link = element("a", "resource-url", url);
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.setAttribute("aria-label", "打开原始链接（新标签页）：" + url);
  return link;
}
export function notify(message, error = false) {
  const box = $("feedback");
  box.textContent = message;
  box.classList.toggle("error", error);
  box.setAttribute("role", error ? "alert" : "status");
  box.hidden = false;
}
export function navigate(route) {
  state.route = route;
  document.dispatchEvent(new Event("route-change"));
}
export async function api(path, method = "GET", data) {
  let response;
  try {
    response = await fetch(path, {
      method, headers: { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch {
    throw new Error("无法连接本地服务，请重新运行“启动工具箱.cmd”。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "操作失败，请稍后重试。");
  }
  return response.json();
}
export async function refresh() {
  const snapshot = await api("/api/state");
  state.resources = snapshot.resources;
  state.collections = snapshot.collections;
  document.dispatchEvent(new Event("library-updated"));
}
export async function run(work, button) {
  if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
  try { await work(); }
  catch (error) { notify(error instanceof Error ? error.message : "操作没有完成，请重试。", true); }
  finally { if (button) { button.disabled = false; button.removeAttribute("aria-busy"); } }
}
export function formatTime(value) {
  return new Date(value).toLocaleString("zh-CN", {timeZone: "Asia/Shanghai", dateStyle: "medium", timeStyle: "short"});
}
