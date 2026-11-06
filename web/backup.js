import {$, api, refresh, notify, run} from "./shared.js";

export async function loadInfo() {
  const info = await api("/api/info");
  $("data-path").textContent = "数据文件：" + info.data_path;
}
export function setupBackup() {
  $("restore-form").addEventListener("submit", event => {
    event.preventDefault();
    run(async () => {
      const file = $("restore-file").files[0];
      if (!file) return;
      if (file.size > 16 * 1024 * 1024) throw new Error("备份文件不能超过 16 MB。");
      let data;
      try { data = JSON.parse(await file.text()); }
      catch { throw new Error("文件不是有效的 JSON，请选择工具箱导出的完整备份。"); }
      const result = await api("/api/restore", "POST", data);
      await refresh();
      $("restore-form").reset();
      notify("导入完成：新增 " + result.added_resources + " 项资源、" + result.added_collections +
        " 份清单；保留 " + result.skipped_resources + " 项已有资源。");
    }, $("restore-button"));
  });
}
