"""MCP tool definitions exposed by the FreeCAD bridge.

Schemas only. tools/list returns these; the HTTP layer dispatches
tools/call by name.
"""

EXECUTE_PYTHON = {
    "name": "execute_python",
    "description": (
        "Execute Python code inside the running FreeCAD GUI process. "
        "App/FreeCAD, Gui/FreeCADGui, and TNP-safe cad helpers (cad) are pre-bound. Output is returned. "
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
        "(Isometric, Front, Top, Rear, Left, Right, Bottom) with optimal framing, "
        "coordinate systems (standard, rack, printbed), and zoom margins."
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
            "coordinate_system": {
                "type": "string",
                "enum": ["standard", "rack", "printbed"],
                "default": "standard",
                "description": "Coordinate system orientation preset.",
            },
            "direction": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Optional [dx, dy, dz] custom camera view direction vector.",
            },
            "zoom_margin": {
                "type": "number",
                "default": 1.1,
                "description": "Framing zoom margin multiplier (e.g. 1.15 to leave breathing room).",
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

GET_SECTION_VIEW = {
    "name": "get_section_view",
    "description": (
        "Capture a cross-section cut view using Coin3D clipping plane without modifying the CAD model. "
        "Reveals internal geometry, cable channels, and hollow pockets."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "plane": {
                "description": "Section plane: 'XY', 'XZ', 'YZ', or custom normal vector [nx, ny, nz].",
                "default": "XY",
            },
            "offset": {
                "type": "number",
                "default": 0.0,
                "description": "Cut plane offset distance along normal in mm.",
            },
            "flip_direction": {
                "type": "boolean",
                "default": False,
                "description": "If True, clips the opposite side of the plane.",
            },
            "view": {
                "type": "string",
                "default": "Isometric",
                "description": "Camera perspective preset.",
            },
            "coordinate_system": {
                "type": "string",
                "enum": ["standard", "rack", "printbed"],
                "default": "standard",
                "description": "Coordinate system orientation preset.",
            },
            "direction": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Optional [dx, dy, dz] custom camera direction.",
            },
            "target_object": {
                "type": "string",
                "description": "Optional object name to focus on.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "display_mode": {
                "type": "string",
                "default": "Flat Lines",
                "description": "Display mode (Flat Lines, Shaded, Wireframe).",
            },
            "zoom_margin": {
                "type": "number",
                "default": 1.1,
                "description": "Framing margin multiplier.",
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
                "default": "Current",
                "description": "Background style.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional output PNG file path.",
            },
            "return_base64": {
                "type": "boolean",
                "default": False,
                "description": "If True, include base64-encoded image data.",
            },
        },
    },
}

EXPORT_VIEWER_HTML = {
    "name": "export_viewer_html",
    "description": (
        "Export the 3D model to a standalone, zero-dependency interactive WebGL HTML viewer with Three.js OrbitControls, "
        "bounding dimensions, and glassmorphism HUD for instant browser viewing."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Optional target object name (defaults to active object or first Body).",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional destination .html file path.",
            },
            "linear_deflection": {
                "type": "number",
                "default": 0.3,
                "description": "Mesh tessellation chordal deflection in mm (lower is smoother, default 0.3).",
            },
            "title": {
                "type": "string",
                "description": "Optional title for viewer HUD.",
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
                "array": "array",
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

ANALYZE_STABILITY = {
    "name": "analyze_stability",
    "description": (
        "Compute physical stability, 2D base contact polygon convex hull, combined center of mass "
        "(with optional payload), and tipping angles in all cardinal directions (forward, backward, left, right)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of target solid/body object.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "base_plane": {
                "type": "string",
                "enum": ["XY", "XZ", "YZ"],
                "default": "XY",
                "description": "Base contact support plane.",
            },
            "z_tolerance": {
                "type": "number",
                "default": 0.5,
                "description": "Tolerance in mm above base level to detect contact points.",
            },
            "density_g_cm3": {
                "type": "number",
                "default": 1.25,
                "description": "Material density in g/cm3 (default 1.25 for PETG/PLA).",
            },
            "payload_mass_kg": {
                "type": "number",
                "default": 0.0,
                "description": "Optional payload mass in kg (e.g. 0.205 for smartphone).",
            },
            "payload_center_of_mass": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Optional [x, y, z] coordinates of payload center of mass in mm.",
            },
        },
        "required": ["object_name"],
    },
}

CHECK_OVERHANGS = {
    "name": "check_overhangs",
    "description": (
        "Analyze 3D printability and overhangs: calculate downward-facing surface areas, "
        "overhang percentage below critical threshold, Z-range of overhangs, and support requirements."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of target object to analyze.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "max_overhang_angle": {
                "type": "number",
                "default": 45.0,
                "description": "Maximum printable slope angle to horizontal build plane in degrees (default 45.0).",
            },
            "print_direction": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
                "default": [0, 0, 1],
                "description": "Build direction vector (default [0,0,1] / +Z).",
            },
            "linear_deflection": {
                "type": "number",
                "default": 0.5,
                "description": "Tessellation accuracy in mm.",
            },
        },
        "required": ["object_name"],
    },
}

INSPECT_FASTENERS = {
    "name": "inspect_fasteners",
    "description": (
        "Detect and classify cylindrical features: distinguish internal holes vs external mounting bosses, "
        "match diameters to standard ISO metric fasteners (M2-M8, clearance, tap, heat-set brass inserts), and measure depths."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of target object to inspect.",
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

DIAGNOSE_DOCUMENT = {
    "name": "diagnose_document",
    "description": (
        "Perform deep diagnostic audit on document: identify recompute errors, check Sketcher degrees of freedom (DoF), "
        "conflicting or redundant constraints, broken body Tips, and OpenCASCADE BRepCheck topology errors."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
    },
}

CHECK_CLEARANCE = {
    "name": "check_clearance",
    "description": (
        "Check spatial interference (collision volume) and clearance distance. "
        "Can check between two specific objects, or set object2='all' to check against all other solids in the document."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object1": {
                "type": "string",
                "description": "Name of the primary object.",
            },
            "object2": {
                "type": "string",
                "default": "all",
                "description": "Name of the second object, or 'all' to check against all other solids.",
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
        "required": ["object1"],
    },
}

INSERT_REFERENCE_DUMMY = {
    "name": "insert_reference_dummy",
    "description": (
        "Insert a dimensionally accurate, semi-transparent reference dummy component "
        "(iphone_15_pro, iphone_15_pro_max, generic_phone, usb_c_plug, mean_well_rs25, mikrotik_crs305, screw_m3, screw_m6) "
        "into the document for fit testing and clash detection."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "dummy_type": {
                "type": "string",
                "enum": [
                    "iphone_15_pro",
                    "iphone_15_pro_max",
                    "generic_phone",
                    "usb_c_plug",
                    "mean_well_rs25",
                    "mikrotik_crs305",
                    "screw_m3",
                    "screw_m6",
                ],
                "default": "iphone_15_pro",
                "description": "Reference component type.",
            },
            "placement": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "[x, y, z] position in mm.",
                    },
                    "rotation": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "[yaw, pitch, roll] in degrees or [ax, ay, az, angle_deg].",
                    },
                },
                "description": "Spatial placement.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "label": {
                "type": "string",
                "description": "Optional custom object label.",
            },
            "transparency": {
                "type": "integer",
                "default": 50,
                "minimum": 0,
                "maximum": 100,
                "description": "Visual transparency percent (default 50).",
            },
        },
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
    GET_SECTION_VIEW,
    EXPORT_VIEWER_HTML,
    SET_DISPLAY_STATE,
    INSPECT_GEOMETRY,
    ANALYZE_STABILITY,
    CHECK_OVERHANGS,
    INSPECT_FASTENERS,
    GET_DOCUMENT_TREE,
    DIAGNOSE_DOCUMENT,
    CHECK_CLEARANCE,
    INSERT_REFERENCE_DUMMY,
    EXPORT_GEOMETRY,
    MANAGE_DOCUMENT,
    UNDO_REDO,
]
