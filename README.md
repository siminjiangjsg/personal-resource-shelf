# 我的工具箱 · Personal Resource Shelf

一个在本机运行的个人资源库：把好用的工具、GitHub 项目、Skill、MCP、文章或教程链接先收下，需要时搜索整理，再挑选其中一部分分享。

Local URL library with SQLite persistence, search, categories, private notes, and selective HTML/Markdown exports. No account, API key, frontend build, or cloud service is required.

## 功能

- 单条或批量收藏链接，保留查询参数与页面锚点，重复链接不会覆盖原记录。
- 搜索名称、链接、用途、分类、标签和私人笔记；按类型、分类、使用状态筛选。
- 待整理、私人笔记、归档与恢复。
- 勾选资源创建独立分享清单，填写推荐语、调整顺序、选择是否展示标签。
- 导出可独立打开的 HTML 分享页或 Markdown；私人笔记、使用状态和未选资源不进入分享文件。
- 完整 JSON 备份与合并恢复；导入前自动备份当前数据。
- 跟随系统明暗主题，支持窄窗口布局。

## Windows 便携版（无需安装 Python）

在 [GitHub Releases](https://github.com/siminjiangjsg/personal-resource-shelf/releases/latest) 下载 `personal-resource-shelf-v1.0.0-windows-x64.zip`，适用于 Windows 10 / 11 x64。

1. **完整解压**到有写入权限的目录。
2. 双击 **启动工具箱.cmd**，浏览器自动打开。
3. 用完后双击 **停止工具箱.cmd**；关闭浏览器不会停止后台服务。

包内已包含 Python 和依赖，无需安装 Git、uv 或 Python。请保留整个 `runtime` 文件夹。首次启动为空库，数据保存在解压目录的 `data/`。升级时先备份并停止旧版，再将整个 `data/` 复制到新版本目录，或在新版导入 JSON 备份。

发布包尚未进行代码签名；可用 Release 附带的 SHA256 文件核对下载完整性。下载时选择上述 ZIP，GitHub 自动生成的 **Source code** 是需要自行安装环境的源码。

## 从源码部署

### 1. 获取代码

先安装 [Git](https://git-scm.com/downloads) 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，再运行：

```sh
git clone https://github.com/siminjiangjsg/personal-resource-shelf.git
cd personal-resource-shelf
```

也可以在仓库页面选择 **Code → Download ZIP**，解压后在该目录打开终端。使用 ZIP 时不需要安装 Git。

### 2. 安装依赖并启动

以下命令可用于 Windows、macOS 和 Linux：

```sh
uv sync --frozen --no-dev
uv run --frozen --no-dev python -m toolbox
```

浏览器打开 **http://127.0.0.1:8765**。保持终端运行，按 `Ctrl+C` 停止服务。

需要 Python 3.13 或更高版本；uv 会选择兼容版本，必要时下载 Python。首次安装需要联网下载运行环境与依赖，日常保存、查找和导出可在离线状态使用。安装过程参考 [uv 项目文档](https://docs.astral.sh/uv/guides/projects/)。

首次启动是空库，无示例收藏，也不会读取他人的收藏数据。

### Windows 双击入口

完成一次 `uv sync --frozen --no-dev` 后，可以直接使用：

- **启动工具箱.cmd**：后台启动服务并打开浏览器；重复启动会连接已有实例。
- **停止工具箱.cmd**：停止由启动器记录的服务，保留收藏数据。

如果是用终端命令启动的服务，请在原终端按 `Ctrl+C` 停止。

核心服务使用 Python 和浏览器，Windows 提供额外的双击入口。仓库的自动检查覆盖 Windows 和 Linux；macOS 的启动命令相同，但尚未进行独立平台验证。

## 日常使用

1. 粘贴一条或多条链接，每行一个，点击“收下链接”。
2. 点击资源名称，编辑标题、类型、分类、标签、用途和私人笔记。
3. 新收藏进入“待整理”；勾选“已整理”即可移出该列表。
4. 勾选想分享的资源 → 整理分享清单 → 填写推荐语 → 保存清单。
5. 用“本机预览”检查对方能看到的内容，再下载 HTML 或 Markdown 文件发送。

标题初值来自链接路径或域名，可手动修改；本版不自动抓取网页标题、正文或摘要。Skill、MCP 等类型用于分类，不会安装或执行链接指向的工具。

## 分享内容与边界

分享文件只包含选中资源的名称、原始链接、本清单的推荐语，以及主动开启展示的标签。私人笔记、使用状态、主题分类和未选资源留在个人库中。

每份清单保存独立快照。修改个人库不会自动改变旧清单；编辑清单后需要重新导出。HTML 文件自带样式，无脚本和外部字体依赖，对方无需安装工具箱即可打开。

**本机预览地址不能当作公网分享链接。** 当前分享采用文件导出，不提供公网托管；已发送的文件无法远程撤回。

## 数据、备份与升级

默认数据保存在项目目录：

| 位置 | 内容 |
| --- | --- |
| `data/library.sqlite3` | 收藏、私人笔记和分享清单 |
| `data/backups/` | 合并导入前生成的完整备份 |
| `.runtime/` | Windows 启动器的运行记录和日志 |

关闭浏览器不会删除数据。在“数据与备份”中可以下载完整 JSON 备份；**完整备份包含私人笔记，请自行保管**。

恢复采用合并方式：已有链接保留当前内容，只新增缺少的资源；同 ID 的分享清单保留现状。迁移到其他电脑时，可在新安装中导入完整备份，或停止服务后复制 `data/` 文件夹。

升级前建议导出备份并停止服务，然后在项目目录运行：

```sh
git pull --ff-only
uv sync --frozen --no-dev
```

再按前述方式启动。数据、日志、虚拟环境和本地测试产物已通过 `.gitignore` 排除，不会随正常 Git 提交上传。

## 可选设置

默认只监听 `127.0.0.1:8765`，适合单人在自己的电脑上使用，没有远程访问所需的账号系统。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `TOOLBOX_PORT` | `8765` | 本机端口；被其他程序占用时可修改 |
| `TOOLBOX_DATA_DIR` | 项目下的 `data/` | 数据目录；建议使用绝对路径 |

PowerShell 示例：

```powershell
$env:TOOLBOX_PORT = '8767'
uv run --frozen --no-dev python -m toolbox
```

macOS / Linux 示例：

```sh
TOOLBOX_PORT=8767 uv run --frozen --no-dev python -m toolbox
```

此时访问 `http://127.0.0.1:8767`。Windows 双击入口也会读取其启动环境中的这些变量。

## 开发与验证

后端：FastAPI、Pydantic、SQLite。前端：原生 HTML、CSS、JavaScript，无需 Node.js 构建步骤。

```sh
uv sync --frozen
uv run --frozen pytest
uv run --frozen ruff check toolbox tests
uv run --frozen basedpyright
```

测试使用隔离临时数据库。GitHub Actions 在 Windows 和 Linux 上执行这些检查；首次发布前另外执行过保存、重启读取、搜索分类、分享下载和备份恢复的真实浏览器验证。

### 构建 Windows 便携包

维护者在 Windows x64 上安装 uv 和 PowerShell 7 后运行：

```powershell
pwsh -File scripts/build-windows.ps1
pwsh -File scripts/test-windows-package.ps1 -Archive dist/personal-resource-shelf-v1.0.0-windows-x64.zip
```

构建使用独立的 `.runtime/windows-build-venv`、Python 3.13 和锁定的 PyInstaller，不改变开发环境；输出 ZIP 和 SHA256 到 `dist/`，已有输出不会被覆盖。重复构建可传 `-OutputDirectory dist/new-build`。压缩包仅包含运行时、网页资源、启动入口和许可文件，不包含开发者的收藏。验证脚本从 ZIP 解压到含空格和中文的临时路径，移除 PATH 中的 Python/uv，检查内置解释器、首次空库、保存重启、选择性分享及端口冲突。

```text
toolbox/       本地接口、数据模型、SQLite 存储、分享导出
web/           浏览器界面
tests/         接口与分享隔离测试
start.ps1      Windows 后台启动器
stop.ps1       Windows 停止入口
pyproject.toml 依赖与检查配置
uv.lock        锁定的依赖版本
DESIGN.md      界面设计约定
```

欢迎通过 [Issues](https://github.com/siminjiangjsg/personal-resource-shelf/issues) 提交问题和改进建议。报告问题时请勿附上私人数据库、完整备份或含私人笔记的截图。

## 许可证

[MIT License](LICENSE) · Copyright (c) 2026 siminjiangjsg。
