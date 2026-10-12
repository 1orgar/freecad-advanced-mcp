"""MCP tool definitions exposed by the FreeCAD bridge.

Schemas only. tools/list returns these; the HTTP layer dispatches
tools/call by name.
"""

EXECUTE_PYTHON = {
    "name": "execute_python",
    "description": (
        "Execute Python code inside the running FreeCAD GUI process. "
        "App/FreeCAD and Gui/FreeCADGui are pre-bound. Output is returned. "
        "Transactions auto-rollback on error when use_transaction=True."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source code to execute in FreeCAD.",
            },
            "use_transaction": {
                "type": "boolean",
                "description": "If True (default), wraps execution in openTransaction and aborts on error.",
                "default": True,
            },
        },
        "required": ["code"],
    },
}

EXECUTE_PYTHON_FILE = {
    "name": "execute_python_file",
    "description": (
        "Read a local Python file and execute it inside the running FreeCAD "
        "GUI process. Same execution context as execute_python."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Absolute path to a .py file.",
            },
            "use_transaction": {
                "type": "boolean",
                "description": "If True (default), wraps execution in openTransaction and aborts on error.",
                "default": True,
            },
        },
        "required": ["filepath"],
    },
}

GET_OUTPUT_PAGE = {
    "name": "get_output_page",
    "description": (
        "Retrieve a page of output for a prior execute call that returned has_more=true."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_token": {
                "type": "string",
                "description": "Token from a previous execute response.",
            },
            "page_no": {
                "type": "integer",
                "minimum": 0,
                "description": "0-based index of the page to retrieve.",
            },
        },
        "required": ["job_token", "page_no"],
    },
}

GET_VIEW = {
    "name": "get_view",
    "description": (
        "Capture a precision screenshot of the 3D model from standard camera angles "
        "(Isometric, Front, Top, Rear, Left, Right, Bottom) with optimal framing and display styling."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "view": {
                "type": "string",
                "enum": ["Isometric", "Front", "Top", "Rear", "Left", "Right", "Bottom", "Dimetric", "Axonometric"],
                "default": "Isometric",
                "description": "Camera perspective preset.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional name of document (defaults to active document).",
            },
            "target_object": {
                "type": "string",
                "description": "Optional object name to focus and frame on.",
            },
            "display_mode": {
                "type": "string",
                "enum": ["Flat Lines", "Shaded", "Wireframe", "Points"],
                "default": "Flat Lines",
                "description": "3D shading and edge style.",
            },
            "width": {
                "type": "integer",
                "default": 1920,
                "description": "Image width in pixels.",
            },
            "height": {
                "type": "integer",
                "default": 1080,
                "description": "Image height in pixels.",
            },
            "background": {
                "type": "string",
                "enum": ["Current", "White", "Black", "Transparent"],
                "default": "Current",
                "description": "Background color style.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional destination file path for PNG image.",
            },
            "return_base64": {
                "type": "boolean",
                "default": False,
                "description": "If True, include base64-encoded image data in the response.",
            },
        },
    },
}

SET_DISPLAY_STATE = {
    "name": "set_display_state",
    "description": (
        "Normalize the 3D GUI viewport: ensure PartDesign Body visibility, show only Tip feature, "
        "hide auxiliary sketches, and set display mode."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "body_name": {
                "type": "string",
                "description": "Optional target PartDesign::Body name.",
            },
            "show_only_tip": {
                "type": "boolean",
                "default": True,
                "description": "If True, hides intermediate features and shows only the final Tip.",
            },
            "hide_sketches": {
                "type": "boolean",
                "default": True,
                "description": "If True, hides all 2D sketches.",
            },
            "display_mode": {
                "type": "string",
                "default": "Flat Lines",
                "description": "Display mode (Flat Lines, Shaded, Wireframe).",
            },
            "shape_color": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "RGB color tuple with values from 0.0 to 1.0, e.g. [0.8, 0.8, 0.9].",
            },
        },
    },
}

INSPECT_GEOMETRY = {
    "name": "inspect_geometry",
    "description": (
        "Compute exact geometry metrics (BoundingBox min/max/size/center, volume, surface area, center of mass, "
        "face/edge counts) and perform 3D-printing topology audit (watertight/manifold, validity, min edge length)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of the object to inspect.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["object_name"],
    },
}

GET_DOCUMENT_TREE = {
    "name": "get_document_tree",
    "description": (
        "Get the complete hierarchical object tree of the FreeCAD document, including PartDesign bodies, "
        "features, tip status, visibility, and recomputation error flags."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "document_name": {
                "type": "string",
                "description": "Optional document name (defaults to active document).",
            },
        },
    },
}

CHECK_CLEARANCE = {
    "name": "check_clearance",
    "description": (
        "Check spatial interference (collision volume) and exact clearance distance (gap) between "
        "two 3D objects with closest contact point coordinates."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object1": {
                "type": "string",
                "description": "Name of the first object.",
            },
            "object2": {
                "type": "string",
                "description": "Name of the second object.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "tolerance": {
                "type": "number",
                "default": 0.1,
                "description": "Touch tolerance in mm (default 0.1).",
            },
        },
        "required": ["object1", "object2"],
    },
}

EXPORT_GEOMETRY = {
    "name": "export_geometry",
    "description": (
        "Export a 3D object to manufacturing formats: STL (with configurable mesh deflection for slicers), "
        "STEP (AP214 solid CAD), 3MF, or DXF."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of the object to export.",
            },
            "format": {
                "type": "string",
                "enum": ["stl", "step", "3mf", "dxf"],
                "default": "stl",
                "description": "Export format.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional destination file path.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "linear_deflection": {
                "type": "number",
                "default": 0.05,
                "description": "Maximum chordal distance for STL mesh approximation in mm.",
            },
            "angular_deflection": {
                "type": "number",
                "default": 0.5,
                "description": "Maximum angular deflection in radians for STL mesh generation.",
            },
        },
        "required": ["object_name"],
    },
}

MANAGE_DOCUMENT = {
    "name": "manage_document",
    "description": (
        "Manage FreeCAD documents: list open documents, create new document, open existing file, "
        "save, close, set active document, or force recompute."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "new", "open", "save", "close", "set_active", "recompute"],
                "default": "list",
                "description": "Document action to perform.",
            },
            "document_name": {
                "type": "string",
                "description": "Document name (required for save/close/set_active/recompute).",
            },
            "file_path": {
                "type": "string",
                "description": "File path (required for open and save as copy).",
            },
        },
    },
}

UNDO_REDO = {
    "name": "undo_redo",
    "description": "Undo or redo the last operation in the FreeCAD document.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["undo", "redo"],
                "default": "undo",
                "description": "Action: undo or redo.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
    },
}

TOOL_DEFINITIONS = [
    EXECUTE_PYTHON,
    EXECUTE_PYTHON_FILE,
    GET_OUTPUT_PAGE,
    GET_VIEW,
    SET_DISPLAY_STATE,
    INSPECT_GEOMETRY,
    GET_DOCUMENT_TREE,
    CHECK_CLEARANCE,
    EXPORT_GEOMETRY,
    MANAGE_DOCUMENT,
    UNDO_REDO,
]
