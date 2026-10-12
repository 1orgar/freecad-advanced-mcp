"""In-process HTTP server hosting the MCP endpoint on loopback."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import FreeCAD

from freecad.mcp_bridge import config, mcp_protocol, paging
from freecad.mcp_bridge import ops_view, ops_inspect, ops_export, ops_doc
from freecad.mcp_bridge import ops_dfam, ops_diagnostics, ops_viewer_html, ops_dummies
from freecad.mcp_bridge.constants import ENDPOINT_PATH, LOG_PREFIX
from freecad.mcp_bridge.executor import Executor

_LOOPBACK_HOSTS = ("localhost", "127.0.0.1")
PARSE_ERROR = -32700
INVALID_PARAMS = -32602


class McpRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return urlparse(origin).hostname in _LOOPBACK_HOSTS

    def do_GET(self):
        self.send_error(405, "Method Not Allowed")

    def do_POST(self):
        if not self._origin_ok():
            self.send_error(403, "Forbidden Origin")
            return
        if self.path != ENDPOINT_PATH:
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, _parse_error())
            return

        if request.get("method") == "tools/call":
            self._handle_tool_call(request)
            return

        response = mcp_protocol.handle_request(request)
        if response is None:
            self.send_response(202)
            self.end_headers()
            return
        self._send_json(200, response)

    def _handle_tool_call(self, request):
        req_id = request.get("id")
        params = request.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        drain_args = (
            config.max_response_timeout_ms(),
            config.max_page_size_chars(),
            config.max_history_retention_ms(),
        )

        if name == "execute_python":
            use_tx = args.get("use_transaction", True)
            self._run_code(req_id, args.get("code", ""), drain_args, None, use_tx)
        elif name == "execute_python_file":
            filepath = args.get("filepath", "")
            use_tx = args.get("use_transaction", True)
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    code = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                self._send_sse(
                    mcp_protocol.tool_call_response(
                        req_id,
                        {
                            "page": [],
                            "has_more": False,
                            "error": f"Error reading file '{filepath}': {exc}",
                        },
                    )
                )
                return
            self._run_code(req_id, code, drain_args, os.path.abspath(filepath), use_tx)
        elif name == "get_output_page":
            page_no = _as_page_no(args.get("page_no"))
            if page_no is None:
                result = {
                    "page": [],
                    "has_more": False,
                    "error": "page_no out of range",
                }
            else:
                result = paging.fetch(
                    args.get("job_token", ""), page_no, *drain_args
                )
            self._send_sse(mcp_protocol.tool_call_response(req_id, result))
        elif name == "get_view":
            self._dispatch_call(req_id, ops_view.get_view, args)
        elif name == "get_section_view":
            self._dispatch_call(req_id, ops_view.get_section_view, args)
        elif name == "export_viewer_html":
            self._dispatch_call(req_id, ops_viewer_html.export_viewer_html, args)
        elif name == "set_display_state":
            self._dispatch_call(req_id, ops_view.set_display_state, args)
        elif name == "inspect_geometry":
            self._dispatch_call(req_id, ops_inspect.inspect_geometry, args)
        elif name == "analyze_stability":
            self._dispatch_call(req_id, ops_dfam.analyze_stability, args)
        elif name == "check_overhangs":
            self._dispatch_call(req_id, ops_dfam.check_overhangs, args)
        elif name == "inspect_fasteners":
            self._dispatch_call(req_id, ops_dfam.inspect_fasteners, args)
        elif name == "get_document_tree":
            self._dispatch_call(req_id, ops_inspect.get_document_tree, args)
        elif name == "diagnose_document":
            self._dispatch_call(req_id, ops_diagnostics.diagnose_document, args)
        elif name == "check_clearance":
            self._dispatch_call(req_id, ops_inspect.check_clearance, args)
        elif name == "insert_reference_dummy":
            self._dispatch_call(req_id, ops_dummies.insert_reference_dummy, args)
        elif name == "export_geometry":
            self._dispatch_call(req_id, ops_export.export_geometry, args)
        elif name == "manage_document":
            self._dispatch_call(req_id, ops_doc.manage_document, args)
        elif name == "undo_redo":
            self._dispatch_call(req_id, ops_doc.undo_redo, args)
        else:
            self._send_sse(
                mcp_protocol.error_response(
                    req_id, INVALID_PARAMS, f"Unknown tool: {name}"
                )
            )

    def _dispatch_call(self, req_id, fn, kwargs):
        try:
            res = self.server.executor.submit_call(fn, **kwargs)
            self._send_sse(mcp_protocol.tool_call_response(req_id, res))
        except Exception as exc:
            self._send_sse(
                mcp_protocol.tool_call_response(
                    req_id, {"error": str(exc), "status": "error"}
                )
            )

    def _run_code(self, req_id, code, drain_args, filepath=None, use_transaction=True):
        token, output_queue = paging.start_page()
        self.server.executor.submit(code, output_queue, filepath, use_transaction)
        result = paging.fetch(token, 0, *drain_args)
        self._send_sse(mcp_protocol.tool_call_response(req_id, result))

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b"event: message\ndata: " + body + b"\n\n")


def _as_page_no(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _parse_error():
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": PARSE_ERROR, "message": "Parse error"},
    }


class HttpServer:
    def __init__(self):
        self._httpd = None
        self._thread = None
        self._executor = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._executor = Executor()
        bind_port = config.port()
        try:
            self._httpd = ThreadingHTTPServer(
                ("127.0.0.1", bind_port), McpRequestHandler
            )
        except OSError as exc:
            self._httpd = None
            self._executor = None
            FreeCAD.Console.PrintError(
                f"{LOG_PREFIX} Could not bind 127.0.0.1:{bind_port} ({exc}).\n"
            )
            raise
        self._httpd.executor = self._executor
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="mcp-bridge-http",
            daemon=True,
        )
        self._thread.start()
        FreeCAD.Console.PrintMessage(
            f"{LOG_PREFIX} HTTP server listening on "
            f"127.0.0.1:{bind_port}{ENDPOINT_PATH}\n"
        )

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None
        self._executor = None
        paging.clear_all()
        FreeCAD.Console.PrintMessage(f"{LOG_PREFIX} HTTP server stopped\n")
