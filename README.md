# GenericAgent（复刻学习版）

> 一个极简的**自我进化自主 Agent 框架**的完整复刻与深度解析项目。
> 约 3000 行种子代码、9 个原子工具、~100 行 Agent Loop。
> 原项目：[lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) 


---

## ✨ 项目亮点

- **极简内核**：主循环 `agent_loop.py` 不足 150 行，含 `BaseHandler` / `StepOutcome` 抽象，易于快速读懂 Agent 的核心运行机制。
- **自我进化记忆系统**：四级记忆中转（L1 索引 → L2 事实库 → L3 任务记录库 → L4 原始会话），配合 20+ 条 SOP，实现跨会话的知识沉淀与复用。
- **9 个原子工具**：从代码执行、文件读写/修补、Web 浏览扫描到浏览器远程控制，工具协议原生可扩展。
- **多端前端**：CLI、GUI（PyQt5）、TUI（Textual v1/v2）、Web（Streamlit / pywebview 桌面壳）、Hub 管理面板，以及 Telegram / QQ / 飞书 / 企业微信 / 钉钉 / 微信等 IM Bot。
- **插件钩子系统**：基于事件钩子的插件机制，支持项目管理模式与 Langfuse 可观测性追踪。
- **Subagent 协作**：支持 `--func` 纯函数模式与 `--task` 持续协作模式，可实现并行任务分发与多 Agent 通信。

---

## 🧱 项目结构

```
GenericAgentReplicate/
├── agent_loop.py           # ⭐ 核心：Agent Loop（~132 行）+ BaseHandler / StepOutcome
├── llmcore.py              # ⭐ 核心：LLM 交互层（Session、流式解析、工具协议转换）
├── ga.py                   # ⭐ 核心：9 个原子工具 + GenericAgentHandler（~600 行）
├── agentmain.py            # ⭐ 核心：Agent 主入口（~350 行）GenericAgent 类
├── mykey.py                #   API Key 配置（由 configure_mykey.py 自动生成）
├── simphtml.py             #   浏览器 HTML 简化引擎（~500 行）
├── TMWebDriver.py          # ⭐ 浏览器远程控制驱动（~300 行）
├── hub.pyw                 #   Hub 服务启动器（纯 tkinter，零第三方依赖）
├── launch.pyw              #   pywebview 桌面壳（包装 Streamlit Web UI）
├── ga.cmd                  #   Windows 一键启动入口
│
├── ga_cli/                 # CLI 命令分发系统
│   ├── cli.py              #   ga 命令分发器（gui/tui/cli/list/status/update...）
│   ├── __main__.py         #   python -m ga_cli 入口
│   └── ga_cli.cmd          #   Windows CLI 启动脚本
│
├── frontends/              # ⭐ 多端前端（8+ 种）
│   ├── qtapp.py            #   PyQt5 桌面 GUI
│   ├── tuiapp.py / tuiapp_v2.py   #   Textual TUI（v1 / v2 增强版）
│   ├── stapp.py            #   Streamlit Web UI
│   ├── launch.pyw          #   webview 桌面壳
│   ├── chatapp_common.py   #   会话公共命令（/help、/btw、/review、/llm 等）
│   └── ...                 #   IM Bot 前端
│
├── plugins/                # 插件系统
│   ├── hooks.py            #   ⭐ 事件钩子系统（register/trigger/discover）
│   ├── project_mode.py     #   项目管理模式插件
│   └── langfuse_tracing.py #   可观测性追踪插件
│
├── memory/                 # ⭐ 记忆系统（自进化核心）
│   ├── global_mem.txt      #   L2 全局事实库
│   ├── global_mem_insight.txt   # L1/L3 记忆洞察与索引
│   ├── *_sop.md            #   20+ 条任务 SOP（计划/审查/子任务/电脑操作等）
│   ├── subagent.md         #   Subagent 调用与协作 SOP
│   └── L4_raw_sessions/    #   L4 原始会话归档
│
├── assets/                 # 资源文件
│   ├── tools_schema.json   #   ⭐ 工具定义（JSON Schema）
│   ├── sys_prompt.txt      #   ⭐ 系统提示词
│   ├── configure_mykey.py  #   ⭐ 交互式配置向导（生成 mykey.py）
│   └── ...
├── pyproject.toml          #   项目元数据与依赖声明
└── requirements.txt        #   锁定的依赖清单
```

---

## 🚀 快速开始

### 1. 环境准备

要求 Python ≥ 3.10（推荐 3.12）。

```bash
# 创建虚拟环境（推荐使用 uv 或 venv）
python -m venv .venv
# Windows 激活
.venv\Scripts\activate
# 或使用 uv
uv venv && uv pip install -e .

# 安装依赖（按需选择 extras，不建议全量安装）
pip install -e .          # 最小核心
pip install -e ".[ui]"    # 额外安装 GUI/TUI/Web 前端依赖
pip install -e ".[all-frontends]"  # 安装全部 IM Bot 前端依赖
```

> 核心依赖仅需 `requests / beautifulsoup4 / bottle / simple-websocket-server / aiohttp`，其他如 Streamlit、Textual、pywebview 等按所选前端按需安装。

### 2. 配置 API Key

运行配置向导，选择 LLM 厂商并填入 API Key，向导会自动生成 `mykey.py`：

```bash
ga configure
# 或直接 python assets/configure_mykey.py
```

支持 OpenAI Chat Completions / Responses 协议、Claude、任意 OAI 兼容中转或网关；可配置 `apibase`、`model`、`reasoning_effort`、超时与重试等参数。也支持通过 `mykey.json` 或远程 URL 加载密钥。

### 3. 一键启动

Windows 下可用 `ga.cmd` 统一入口：

```bash
ga gui        # 桌面 GUI（PyQt5）
ga tui        # 终端 TUI（Textual v1）
ga tui2       # 终端 TUI v2 增强版
ga cli        # 最轻量的命令行对话
ga hub        # Hub 管理面板（系统托盘 + 浏览器界面）
ga launch     # webview 桌面壳
ga list       # 列出所有可用命令
ga status     # 检查当前运行状态
ga update     # git pull + pip install 更新
```

也可直接用 `python -m ga_cli <命令>` 或 `python agentmain.py` 运行。

---

## 🛠 9 个原子工具

定义见 [assets/tools_schema.json](assets/tools_schema.json)：

| 工具 | 说明 |
|:---|:---|
| `code_run` | 执行 Python 脚本 / PowerShell / Bash 命令，流式回传输出 |
| `file_read` | 读取本地文件内容 |
| `file_patch` | 对文件做增量修补（避免整体 overwrite） |
| `file_write` | 写入/创建文件 |
| `web_scan` | 网页扫描与信息抓取 |
| `web_execute_js` | 在浏览器中执行 JS（配合 TMWebDriver 远程控制） |
| `update_working_checkpoint` | 更新工作检查点（长期任务进度记录） |
| `ask_user` | 向用户提问获取信息 |
| `start_long_term_update` | 触发长期记忆更新流程（自进化核心） |

可传入 `--no-user-tools` 禁用 `ask_user` / `start_long_term_update` 等交互式工具。

---

## 🧠 记忆系统（自进化核心）

遵循「**无行动，不记忆**（No Execution, No Memory）」公理，任何写入记忆的信息必须源于**成功的工具调用结果**。

4 级记忆架构：

```
L1: global_mem_insight.txt    极简索引层（≤30 行，场景关键词 → 记忆定位）
L2: global_mem.txt            全局事实库（路径、凭证、配置等）
L3: ../memory/                任务级记录库（SOP + 高复用脚本）
L4: ../memory/L4_raw_sessions/ 原始会话归档（可定位过往上下文）
```

同步规则：上层只保留能定位下层的「最小充分指针」，L1 有体积硬约束，变更时仅允许少量 patch，不允许整体覆盖。20+ 条 SOP 覆盖计划、代码审查、任务执行、移动设备操控、浏览器远程控制等场景。

---

## 📡 Subagent 协作

参见 [memory/subagent.md](memory/subagent.md)：

- **`--func` 纯函数模式**：读 prompt 文件 → 执行 → 写 `prompt.out.txt` → 退出。适合单次任务、并行 map。
- **`--task` 持续协作模式**：`--input` 建目录并写输入，通过 `output.txt` / `reply.txt` 持续通信，支持 `_stop` / `_keyinfo` / `_intervene` 干预文件与 `_history.json` 上下文继承。

`agentmain.py` 常用参数：

```bash
python agentmain.py --task {name} --input "短文本"      # 持续协作模式
python agentmain.py --func prompt.txt --nobg            # 纯函数前台模式
python agentmain.py --reflect scripts/xxx.py            # 反射/监控脚本模式
python agentmain.py --llm_no 1 --verbose                # 选择模型/查看原始数据
```

---

## 🖥 前端体系

| 前端 | 入口 | 说明 |
|:---|:---|:---|
| 桌面 GUI | `frontends/qtapp.py` | PyQt5 完整界面：气泡代码高亮、文件拖拽、历史搜索 |
| 终端 TUI v1 | `frontends/tuiapp.py` | Textual，适合纯终端/SSH |
| 终端 TUI v2 | `frontends/tuiapp_v2.py` | Textual 增强版 |
| Web UI | `frontends/stapp.py` | Streamlit，支持图片剪贴板粘贴钩子 |
| 桌面壳 | `launch.pyw` | pywebview 原生窗口包装 Web UI |
| Hub 面板 | `hub.pyw` | 纯 tkinter 服务启动器（发现/管理多个服务） |
| IM Bot | `launch.pyw` 相关参数 | Telegram / QQ / 飞书 / 企业微信 / 钉钉 / 微信 |

会话内常用命令（见 `chatapp_common.py`）：`/help`、`/status`、`/stop`、`/new`、`/restore`、`/continue [n]`、`/btw <q>`（临时插问不打断主线）、`/review [scope]`（会话内代码审查）、`/llm [n]`（切换模型）。

---

## 🔌 插件系统

`plugins/hooks.py` 提供事件钩子注册 / 触发 / 自动发现机制。内置插件：

- `project_mode.py`：项目管理模式，约束 Agent 聚焦单一任务上下文。
- `langfuse_tracing.py`：Langfuse 观测追踪，记录与回放 Agent 运行轨迹。


---

## 📄 数据与目录约定

- `memory/`：全局记忆、SOP 与子任务文档。
- `temp/`：Agent 工作目录与模型响应存档（`.ga_rewind` 提供回放）。
- `mykey.py` / `mykey.json`：密钥配置，**请勿提交到 Git**（已在 `.gitignore` 中忽略）。
- `assets/`：工具 schema、系统提示词、模板与配置向导。

---

## 🛡 安全说明

- API Key 由 `mykey.py` / `mykey.json` 保存，默认已被 `.gitignore` 忽略，切勿将密钥提交到公开仓库。
- `code_run` 在执行代码前会注入安全执行头（`assets/code_run_header.py`），为 Agent 代码执行提供沙箱提示。
- 记忆系统公理明确禁止将「未执行的推理/假设」写入记忆，降低幻觉性事实污染。