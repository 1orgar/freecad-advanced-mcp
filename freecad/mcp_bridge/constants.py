"""Shared identifiers and defaults for the FreeCAD Advanced MCP addon."""

DISPLAY_NAME = "FreeCAD Advanced MCP"
LOG_PREFIX = "[FreeCAD Advanced MCP]"
COMMAND_ID = "FreeCAD_Advanced_MCP_Toggle"
TOOLBAR_OBJECT_NAME = "FreeCAD_Advanced_MCP"

# MCP server identity (serverInfo.version is read live from package.xml)
SERVER_NAME = "freecad-advanced-mcp"
PROTOCOL_VERSION = "2025-03-26"

# HTTP endpoint path the MCP server answers on
ENDPOINT_PATH = "/mcp"

# Network / timing defaults — overridable via FreeCAD preferences (see config.py)
DEFAULT_PORT = 39280
DEFAULT_MAX_RESPONSE_TIMEOUT_S = 15
DEFAULT_MAX_PAGE_SIZE_KB = 64
DEFAULT_MAX_HISTORY_RETENTION_MIN = 5

# FreeCAD preference group backing config.py
PREF_GROUP = "User parameter:BaseApp/Preferences/Mod/freecad-advanced-mcp"
