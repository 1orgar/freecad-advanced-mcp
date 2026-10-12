"""MCP protocol handling — maps parsed JSON-RPC requests to responses."""

import json

from freecad.mcp_bridge.constants import PROTOCOL_VERSION, SERVER_NAME
from freecad.mcp_bridge.resources import addon_version
from freecad.mcp_bridge.tools import TOOL_DEFINITIONS

METHOD_NOT_FOUND = -32601


def handle_request(request: dict):
    """Return a JSON-RPC response dict, or None for a notification."""
    method = request.get("method")
    is_notification = "id" not in request
    req_id = request.get("id")

    if method == "initialize":
        return _result(req_id, _initialize_result())
    if method == "tools/list":
        return _result(req_id, {"tools": TOOL_DEFINITIONS})
    if is_notification:
        return None
    return _error(req_id, METHOD_NOT_FOUND, f"Method not found: {method}")


def _initialize_result() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": addon_version()},
    }


def _result(req_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def tool_call_response(req_id, result) -> dict:
    """Wrap a tool result as a standard MCP tools/call result."""
    if isinstance(result, dict) and "content" in result and isinstance(result["content"], list):
        return _result(req_id, result)

    # Legacy paged output support (execute_python, get_output_page)
    if isinstance(result, dict) and "page" in result:
        payload = {
            "page": result.get("page", []),
            "has_more": result.get("has_more", False),
        }
        if result.get("page_no") is not None:
            payload["page_no"] = result["page_no"]
        if result.get("job_token"):
            payload["job_token"] = result["job_token"]
        if result.get("error"):
            payload["error"] = result["error"]
        resp_obj = {"content": [{"type": "text", "text": json.dumps(payload)}]}
        if result.get("error"):
            resp_obj["isError"] = True
        return _result(req_id, resp_obj)

    # General structured result
    content = []
    is_err = False

    if isinstance(result, dict):
        if result.get("error") or result.get("status") == "error":
            is_err = True

        # Check for image content
        if "image_base64" in result and result["image_base64"]:
            b64_data = result.get("image_base64")
            mime_type = result.get("image_mime", "image/png")
            content.append({
                "type": "image",
                "data": b64_data,
                "mimeType": mime_type,
            })
            # Remove from text payload to keep response compact
            res_copy = dict(result)
            res_copy.pop("image_base64", None)
            res_copy.pop("image_mime", None)
            content.append({
                "type": "text",
                "text": json.dumps(res_copy, indent=2, ensure_ascii=False),
            })
        else:
            content.append({
                "type": "text",
                "text": json.dumps(result, indent=2, ensure_ascii=False),
            })
    else:
        content.append({
            "type": "text",
            "text": str(result),
        })

    resp_obj = {"content": content}
    if is_err:
        resp_obj["isError"] = True

    return _result(req_id, resp_obj)


def error_response(req_id, code, message) -> dict:
    """Public JSON-RPC error envelope, for the transport layer."""
    return _error(req_id, code, message)
