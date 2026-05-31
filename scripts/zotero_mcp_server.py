"""Zotero MCP Server — AI-powered reference management via the Model Context Protocol.

This MCP server connects AI coding assistants to a Zotero library, enabling:
  - Query and search references
  - Generate formatted bibliographies (GB/T 7714, IEEE, APA, etc.)
  - Insert references into Word documents
  - Manage Zotero collections and items

Protocol: Model Context Protocol (MCP) via JSON-RPC 2.0 over stdio.

Usage:
  # Install dependencies
  pip install pyzotero httpx

  # Run as MCP server (for AI assistants)
  python scripts/zotero_mcp_server.py

  # Test CLI mode
  python scripts/zotero_mcp_server.py --api-key YOUR_KEY --user-id YOUR_ID list
  python scripts/zotero_mcp_server.py --api-key YOUR_KEY --user-id YOUR_ID search --query "time series"
"""
import sys, os, json, re, logging, traceback
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger("zotero-mcp")


# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

def load_config():
    """Load Zotero API credentials from config file or environment."""
    config = {}

    # Try config file
    config_paths = [
        Path.home() / ".zotero-mcp.json",
        Path.cwd() / ".zotero-mcp.json",
        Path.cwd() / ".trae" / "zotero-mcp.json",
    ]
    for cp in config_paths:
        if cp.exists():
            try:
                with open(cp) as f:
                    config.update(json.load(f))
                log.info("Loaded config from %s", cp)
                break
            except Exception as e:
                log.warning("Config load error: %s", e)

    # Environment variables override
    config["api_key"] = os.environ.get("ZOTERO_API_KEY") or config.get("api_key")
    config["user_id"] = os.environ.get("ZOTERO_USER_ID") or config.get("user_id")

    return config


# ──────────────────────────────────────────────
#  Zotero Client
# ──────────────────────────────────────────────

class ZoteroClient:
    """Wrapper around pyzotero for Zotero web API access."""

    def __init__(self, api_key, user_id):
        self.api_key = api_key
        self.user_id = user_id
        self._zot = None
        self._httpx = None

    def _ensure_client(self):
        if self._zot is None:
            from pyzotero import zotero
            self._zot = zotero.Zotero(self.user_id, "user", self.api_key)
        return self._zot

    def _ensure_httpx(self):
        if self._httpx is None:
            import httpx
            self._httpx = httpx
        return self._httpx

    def check_connection(self):
        """Verify API key works and return user info."""
        import httpx
        try:
            resp = httpx.get(
                "https://api.zotero.org/keys/current",
                headers={"Zotero-API-Key": self.api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "ok": True,
                    "username": data.get("username", "?"),
                    "user_id": data.get("userID"),
                }
            return {"ok": False, "error": resp.text[:100]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_total_items(self):
        """Get total item count in library."""
        h = self._ensure_httpx()
        try:
            resp = h.get(
                "https://api.zotero.org/users/%s/items/top" % self.user_id,
                headers={"Zotero-API-Key": self.api_key},
            )
            return int(resp.headers.get("Total-Results", 0))
        except Exception:
            return 0

    def list_collections(self):
        """List all collections with item counts."""
        zot = self._ensure_client()
        cols = zot.collections()
        h = self._ensure_httpx()
        result = []
        for c in cols:
            data = c.get("data", {})
            key = data.get("key", "")
            name = data.get("name", "?")
            try:
                resp = h.get(
                    "https://api.zotero.org/users/%s/collections/%s/items/top" % (
                        self.user_id, key),
                    headers={"Zotero-API-Key": self.api_key},
                    timeout=5,
                )
                count = int(resp.headers.get("Total-Results", 0))
                result.append({"key": key, "name": name, "item_count": count})
            except Exception:
                result.append({"key": key, "name": name, "item_count": 0})
        return result

    def search_items(self, query=None, collection=None, limit=20, offset=0):
        """Search for items in the library."""
        zot = self._ensure_client()
        try:
            if collection:
                items = zot.collection_items(collection, limit=limit, offset=offset)
            elif query:
                items = zot.items(q=query, limit=limit, offset=offset,
                                  itemType="-attachment -note")
            else:
                items = zot.items(limit=limit, offset=offset,
                                  itemType="-attachment -note")
        except Exception as e:
            log.error("Search error: %s", e)
            return []

        result = []
        for item in items:
            data = item.get("data", {})
            creators = data.get("creators", [])
            authors = [("%s %s" % (c.get("firstName", ""), c.get("lastName", ""))).strip()
                       for c in creators[:3]]
            result.append({
                "key": data.get("key", ""),
                "title": data.get("title", "(no title)"),
                "date": data.get("date", ""),
                "item_type": data.get("itemType", ""),
                "authors": authors,
                "publication": data.get("publicationTitle", data.get("publisher", "")),
                "doi": data.get("DOI", ""),
            })
        return result

    def get_item(self, key):
        """Get detailed item info by key."""
        zot = self._ensure_client()
        try:
            item = zot.item(key)
        except Exception as e:
            return {"error": str(e)}
        data = item.get("data", {})
        creators = data.get("creators", [])
        authors = [("%s %s" % (c.get("firstName", ""), c.get("lastName", ""))).strip()
                   for c in creators]
        return {
            "key": data.get("key"),
            "title": data.get("title"),
            "item_type": data.get("itemType"),
            "authors": authors,
            "date": data.get("date"),
            "publication": data.get("publicationTitle") or data.get("publisher", ""),
            "volume": data.get("volume"),
            "issue": data.get("issue"),
            "pages": data.get("pages"),
            "doi": data.get("DOI"),
            "isbn": data.get("ISBN"),
            "issn": data.get("ISSN"),
            "abstract": data.get("abstractNote", "")[:500],
            "url": data.get("url"),
            "tags": [t.get("tag", "") for t in data.get("tags", [])],
        }

    def generate_bibliography(self, item_keys, style="chinese-gb7714-2005-numeric"):
        """Generate formatted bibliography for selected items."""
        if not item_keys:
            return {"error": "No items selected"}
        h = self._ensure_httpx()
        try:
            resp = h.post(
                "https://api.zotero.org/users/%s/items/bibliography" % self.user_id,
                headers={
                    "Zotero-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                params={"csl": style},
                json=item_keys,
                timeout=15,
            )
            if resp.status_code == 200:
                entries = resp.json()
                bib = []
                for entry in entries:
                    bib.append({
                        "key": entry.get("data", {}).get("key", ""),
                        "html": entry.get("bib", ""),
                        "text": re.sub(r"<[^>]+>", "", entry.get("bib", "")),
                    })
                return {"entries": bib, "count": len(bib)}
            else:
                return {"error": "HTTP %d: %s" % (resp.status_code, resp.text[:200])}
        except Exception as e:
            return {"error": str(e)}

    def get_citation_style_options(self):
        """Return available citation style options."""
        return [
            {"id": "chinese-gb7714-2005-numeric", "name": "GB/T 7714 (中文核心)"},
            {"id": "ieee", "name": "IEEE"},
            {"id": "apa", "name": "APA 7th"},
            {"id": "chicago-note-bibliography", "name": "Chicago"},
            {"id": "modern-language-association", "name": "MLA"},
            {"id": "elsevier-harvard", "name": "Harvard"},
            {"id": "nature", "name": "Nature"},
            {"id": "science", "name": "Science"},
        ]


# ──────────────────────────────────────────────
#  MCP Protocol Implementation
# ──────────────────────────────────────────────

class MCPServer:
    """Model Context Protocol server — JSON-RPC 2.0 over stdio."""

    def __init__(self, api_key, user_id):
        self.client = ZoteroClient(api_key, user_id)
        self.tools = self._register_tools()
        self.request_id = 0

    def _register_tools(self):
        """Define MCP tools that the AI assistant can call."""
        return {
            "check_connection": {
                "description": "验证 Zotero API 连接是否正常，返回用户名和用户 ID",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": lambda args: self.client.check_connection(),
            },
            "list_collections": {
                "description": "列出 Zotero 中的所有集合（文件夹）及其包含的文献数量",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": lambda args: self.client.list_collections(),
            },
            "search_items": {
                "description": "搜索 Zotero 文献库中的条目，支持关键词搜索和按集合筛选",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词（标题/作者）"},
                        "collection": {"type": "string", "description": "集合 key（可选）"},
                        "limit": {"type": "number", "description": "返回条数上限（默认 20）"},
                    },
                    "required": [],
                },
                "handler": lambda args: self.client.search_items(
                    query=args.get("query"),
                    collection=args.get("collection"),
                    limit=args.get("limit", 20),
                ),
            },
            "get_item": {
                "description": "获取单篇文献的详细信息，包括作者、摘要、DOI、标签等",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Zotero 条目 key"},
                    },
                    "required": ["key"],
                },
                "handler": lambda args: self.client.get_item(args["key"]),
            },
            "generate_bibliography": {
                "description": "生成格式化参考文献列表，支持 GB/T 7714、IEEE、APA 等多种格式",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Zotero 条目 key 列表",
                        },
                        "style": {
                            "type": "string",
                            "description": "引文格式（默认: chinese-gb7714-2005-numeric）",
                            "enum": [
                                "chinese-gb7714-2005-numeric",
                                "ieee",
                                "apa",
                                "chicago-note-bibliography",
                                "modern-language-association",
                                "elsevier-harvard",
                                "nature",
                                "science",
                            ],
                        },
                    },
                    "required": ["item_keys"],
                },
                "handler": lambda args: self.client.generate_bibliography(
                    args["item_keys"],
                    style=args.get("style", "chinese-gb7714-2005-numeric"),
                ),
            },
            "list_styles": {
                "description": "列出所有支持的参考文献格式选项",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": lambda args: self.client.get_citation_style_options(),
            },
            "get_library_stats": {
                "description": "获取 Zotero 文献库统计信息（总文献数、集合数等）",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": lambda args: {
                    "total_items": self.client.get_total_items(),
                    "collections": len(self.client.list_collections()),
                },
            },
        }

    def handle_message(self, message):
        """Process a single JSON-RPC message and return response."""
        req_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        if method == "resources/list":
            return self._make_result(req_id, [])
        elif method == "resources/read":
            return self._make_error(req_id, -32601, "Resource reading not supported")
        elif method == "tools/list":
            tools_list = [
                {
                    "name": name,
                    "description": info["description"],
                    "inputSchema": info["input_schema"],
                }
                for name, info in self.tools.items()
            ]
            return self._make_result(req_id, {"tools": tools_list})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            if tool_name not in self.tools:
                return self._make_error(req_id, -32602,
                                        "Unknown tool: %s" % tool_name)
            try:
                result = self.tools[tool_name]["handler"](tool_args)
                return self._make_result(req_id, {"content": [
                    {"type": "text", "text": json.dumps(
                        result, ensure_ascii=False, indent=2)}
                ]})
            except Exception as e:
                log.error("Tool execution error: %s", traceback.format_exc())
                return self._make_error(req_id, -32603, str(e))
        elif method == "initialize":
            return self._make_result(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "zotero-mcp",
                    "version": "1.0.0",
                },
            })
        else:
            return self._make_error(req_id, -32601,
                                    "Method not found: %s" % method)

    def _make_result(self, req_id, result):
        resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        return json.dumps(resp, ensure_ascii=False) + "\n"

    def _make_error(self, req_id, code, message):
        resp = {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": code, "message": message}}
        return json.dumps(resp, ensure_ascii=False) + "\n"

    def run_stdio(self):
        """Run MCP server reading JSON-RPC from stdin, writing to stdout."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                message = json.loads(line)
                response = self.handle_message(message)
                sys.stdout.write(response)
                sys.stdout.flush()
            except json.JSONDecodeError:
                continue
            except EOFError:
                break
            except Exception as e:
                log.error("Fatal error: %s", traceback.format_exc())
                break


# ──────────────────────────────────────────────
#  CLI Mode
# ──────────────────────────────────────────────

def run_cli(args, config):
    """Run in CLI mode for testing."""
    api_key = args.api_key or config.get("api_key")
    user_id = args.user_id or config.get("user_id")
    
    if not api_key or not user_id:
        print("Error: --api-key and --user-id are required (or set ZOTERO_API_KEY/ZOTERO_USER_ID env)")
        print("Usage: python scripts/zotero_mcp_server.py --api-key KEY --user-id ID <command>")
        sys.exit(1)

    client = ZoteroClient(api_key, user_id)

    if args.command == "list":
        cols = client.list_collections()
        for c in cols:
            print("  [%s] %s" % (c["key"][:8], c["name"]))

    elif args.command == "search":
        items = client.search_items(query=args.query or "",
                                    collection=args.collection,
                                    limit=args.limit or 20)
        for item in items:
            authors = ", ".join(item["authors"][:2])
            print("[%s] %s" % (item["key"][:8], item["title"][:60]))
            print("      %s | %s" % (authors[:30], item["date"]))

    elif args.command == "get":
        item = client.get_item(args.key)
        for k, v in item.items():
            print("  %s: %s" % (k, v))

    elif args.command == "bib":
        bib = client.generate_bibliography(args.keys.split(","), args.style or "chinese-gb7714-2005-numeric")
        for entry in bib.get("entries", []):
            print("%s" % entry["text"])

    elif args.command == "check":
        result = client.check_connection()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("total_items") is not None:
            print("Total items:", result["total_items"])

    elif args.command == "styles":
        styles = client.get_citation_style_options()
        for s in styles:
            print("  %s — %s" % (s["id"], s["name"]))

    else:
        print("Available commands: list, search, get, bib, check, styles")


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

def main():
    import argparse
    config = load_config()

    parser = argparse.ArgumentParser(
        description="Zotero MCP Server — AI-powered reference management",
        epilog="Run without arguments to start MCP server (for AI assistants).")

    parser.add_argument("--api-key", help="Zotero API key")
    parser.add_argument("--user-id", help="Zotero user ID")
    parser.add_argument("--config", help="Config file path")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List collections")
    p_search = sub.add_parser("search", help="Search items")
    p_search.add_argument("--query")
    p_search.add_argument("--collection")
    p_search.add_argument("--limit", type=int, default=20)

    p_get = sub.add_parser("get", help="Get item details")
    p_get.add_argument("key")

    p_bib = sub.add_parser("bib", help="Generate bibliography")
    p_bib.add_argument("keys", help="Comma-separated item keys")
    p_bib.add_argument("--style", default="chinese-gb7714-2005-numeric")

    sub.add_parser("check", help="Check API connection")
    sub.add_parser("styles", help="List citation styles")

    args = parser.parse_args()

    if args.command:
        run_cli(args, config)
    else:
        # MCP server mode
        api_key = config.get("api_key") or os.environ.get("ZOTERO_API_KEY")
        user_id = config.get("user_id") or os.environ.get("ZOTERO_USER_ID")
        if not api_key or not user_id:
            print("Error: ZOTERO_API_KEY and ZOTERO_USER_ID must be set", file=sys.stderr)
            print("Create ~/.zotero-mcp.json or set environment variables", file=sys.stderr)
            sys.exit(1)
        server = MCPServer(api_key, user_id)
        server.run_stdio()


if __name__ == "__main__":
    main()
