# Zotero MCP Server

> **AI-driven Zotero reference management via Model Context Protocol (MCP).**  
> Connect AI coding assistants to your Zotero library — search references, generate formatted bibliographies, and manage collections through natural language.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

- **MCP 协议集成** — 基于 Model Context Protocol (JSON-RPC 2.0 over stdio) 的标准协议，兼容所有支持 MCP 的 AI 助手
- **Zotero 全功能访问** — 搜索文献、获取详情、浏览集合、生成参考文献
- **8 种引文格式** — GB/T 7714 (中文核心)、IEEE、APA 7th、Chicago、MLA、Harvard、Nature、Science
- **无配置运行** — 通过 `~/.zotero-mcp.json` 或环境变量配置，即配即用
- **CLI 测试模式** — 无需 AI 助手即可通过命令行测试连接和查询

## Installation

```bash
# Clone the repository
git clone https://github.com/fuwenhao12/zotero-mcp.git
cd zotero-mcp

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### 1. 获取 Zotero API Key

1. 登录 [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys)
2. 创建新的 API Key（勾选 "Allow library access" 权限）
3. 记下 API Key 和 User ID（位于同一页面顶部）

### 2. 配置凭据

**方式 A: 配置文件（推荐）**

```bash
cp .zotero-mcp.json.example ~/.zotero-mcp.json
```

编辑 `~/.zotero-mcp.json`:

```json
{
  "api_key": "你的ZoteroAPIKey",
  "user_id": 1234567
}
```

**方式 B: 环境变量**

```bash
export ZOTERO_API_KEY="你的ZoteroAPIKey"
export ZOTERO_USER_ID="1234567"
```

## Usage

### MCP 服务器模式（AI 助手使用）

启动服务器（无需参数），AI 助手通过 stdio 自动通信：

```bash
python scripts/zotero_mcp_server.py
```

### CLI 测试模式

```bash
# 验证连接
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID check

# 搜索文献
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID search --query "transformer"

# 获取文献详情
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID get ITEM_KEY

# 生成参考文献（GB/T 7714 格式）
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID bib --keys KEY1,KEY2 --style chinese-gb7714-2005-numeric

# 列出所有集合
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID list

# 列出支持的引文格式
python scripts/zotero_mcp_server.py --api-key KEY --user-id ID styles
```

## MCP Tools

AI 助手可通过以下工具操控您的 Zotero 文献库：

| Tool | Description |
|------|-------------|
| `check_connection` | 验证 Zotero API 连接是否正常，返回用户名和用户 ID |
| `list_collections` | 列出 Zotero 中的所有集合（文件夹）及其包含的文献数量 |
| `search_items` | 搜索文献，支持关键词和集合筛选 |
| `get_item` | 获取单篇文献的详细信息（作者、摘要、DOI、标签等） |
| `generate_bibliography` | 生成格式化参考文献，支持 8 种引文格式 |
| `get_library_stats` | 文献库统计（总文献数、集合数） |
| `list_styles` | 列出所有支持的参考文献格式 |

### AI 助手调用示例

```
用户: "帮我查一下我 Zotero 里关于 time series 的文献"
AI 助手: [调用 search_items(query="time series")]
→ 返回文献列表

用户: "把这些文献生成 GB/T 7714 格式的参考文献"
AI 助手: [调用 generate_bibliography(keys=[...], style="chinese-gb7714-2005-numeric")]
→ 返回格式化参考文献
```

## Supported Citation Styles

| Style ID | Name |
|----------|------|
| `chinese-gb7714-2005-numeric` | GB/T 7714 (中文核心) |
| `ieee` | IEEE |
| `apa` | APA 7th |
| `chicago-note-bibliography` | Chicago |
| `modern-language-association` | MLA |
| `elsevier-harvard` | Harvard |
| `nature` | Nature |
| `science` | Science |

## Project Structure

```
zotero-mcp/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── requirements.txt             # Runtime dependencies
├── .zotero-mcp.json.example     # MCP 配置模板
├── scripts/
│   ├── zotero_mcp_server.py     # Zotero MCP 服务器（核心）
│   ├── formats/                 # 引文格式实现（备选）
│   └── utils/                   # 文档工具（备选）
├── .trae/skills/                # Trae AI skill 定义
├── .cursor/                     # Cursor 配置
├── .clinerules                  # Cline 配置
├── CLAUDE.md                    # Claude Code 配置
├── AGENTS.md                    # AI 兼容性指南
└── tests/                       # 测试
```

## Integration with AI Code Assistants

本项目支持所有主流 AI 编程助手：

| Assistant | Config File | Auto-Detected |
|-----------|------------|---------------|
| **Trae** | `.trae/skills/zotero-mcp/SKILL.md` | ✅ |
| **Cursor** | `.cursorrules` + `.cursor/rules/*.mdc` | ✅ |
| **Claude Code** | `CLAUDE.md` | ✅ |
| **GitHub Copilot** | `.github/copilot-instructions.md` | ✅ |
| **Windsurf** | `.windsurfrules` | ✅ |
| **Aider** (v0.73+) | `CONVENTIONS.md` | ✅ |
| **Continue.dev** | `.continue/config.json` | ✅ |
| **OpenAI Codex CLI** | `AGENTS.md` | ✅ |
| **Kimi Code CLI** | `.kimi/skills/*/SKILL.md` | ✅ |
| **Qwen Code** | `.qwen/skills/*/SKILL.md` | ✅ |
| **OpenCode** | `opencode.json` + `AGENTS.md` | ✅ |
| **Gemini CLI** | `GEMINI.md` | 手动指定 |
| **Amazon Q Developer** | `AMAZON_Q.md` | ✅ |
| **Cline** | `.clinerules` | ✅ |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

### v1.2.0 (2026-05-31)

**New features — Zotero MCP 集成:**

- **`scripts/zotero_mcp_server.py`** — Zotero MCP 服务器。遵循 Model Context Protocol (MCP) 协议，通过 JSON-RPC 2.0 提供 AI 助手与 Zotero 文献库的实时交互。支持：
  - `check_connection` — 验证 API 连接
  - `list_collections` — 列出文献集合
  - `search_items` — 搜索文献（关键词/集合筛选）
  - `get_item` — 获取文献详情（摘要、DOI、标签等）
  - `generate_bibliography` — 生成格式化参考文献（GB/T 7714 / IEEE / APA / Nature / Science 等 8 种格式）
  - `get_library_stats` — 文献库统计
  - `list_styles` — 列出支持的引文格式
- **`scripts/zotero_bridge.py`** — Zotero 桥接脚本。提供 CLI 接口查询 Zotero、生成引用、插入论文。
- **`.zotero-mcp.json.example`** — MCP 配置模板。复制为 `~/.zotero-mcp.json` 或设置 `ZOTERO_API_KEY` / `ZOTERO_USER_ID` 环境变量即可启用。
- **依赖** — `pyzotero` 库用于 Zotero 网页 API 访问 (`pip install pyzotero`)。


### v1.2.0 (2026-05-31)

**New features — Zotero MCP 集成:**

- **`scripts/zotero_mcp_server.py`** — Zotero MCP 服务器。遵循 Model Context Protocol (MCP) 协议，通过 JSON-RPC 2.0 提供 AI 助手与 Zotero 文献库的实时交互。支持：
  - `check_connection` — 验证 API 连接
  - `list_collections` — 列出文献集合
  - `search_items` — 搜索文献（关键词/集合筛选）
  - `get_item` — 获取文献详情（摘要、DOI、标签等）
  - `generate_bibliography` — 生成格式化参考文献（GB/T 7714 / IEEE / APA / Nature / Science 等 8 种格式）
  - `get_library_stats` — 文献库统计
  - `list_styles` — 列出支持的引文格式
- **`scripts/zotero_bridge.py`** — Zotero 桥接脚本。提供 CLI 接口查询 Zotero、生成引用、插入论文。
- **`.zotero-mcp.json.example`** — MCP 配置模板。复制为 `~/.zotero-mcp.json` 或设置 `ZOTERO_API_KEY` / `ZOTERO_USER_ID` 环境变量即可启用。
- **依赖** — `pyzotero` 库用于 Zotero 网页 API 访问 (`pip install pyzotero`)。

### v1.0.0 (2026-05-31)

- **`scripts/zotero_mcp_server.py`** — Zotero MCP 服务器。遵循 Model Context Protocol (MCP) 协议，通过 JSON-RPC 2.0 提供 AI 助手与 Zotero 文献库的实时交互。支持 7 个工具：`check_connection`、`list_collections`、`search_items`、`get_item`、`generate_bibliography`、`get_library_stats`、`list_styles`。
- **`.zotero-mcp.json.example`** — MCP 配置模板。复制为 `~/.zotero-mcp.json` 或设置环境变量即可启用。
- **依赖** — `pyzotero` + `httpx`。
