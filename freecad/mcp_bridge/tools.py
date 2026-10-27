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
        "Export the 3D model to a self-contained, zero-dependency interactive WebGL HTML viewer optimized for "
        "inline chat rendering (<agent-embed>) or standalone browser viewing. Includes pure WebGL OrbitControls, "
        "CAD Flat Lines wireframe edge overlay, and theme integration."
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
            "mode": {
                "type": "string",
                "enum": ["chat", "standalone"],
                "default": "chat",
                "description": "Viewer mode: 'chat' (compact inline card < 450px with <agent-embed>) or 'standalone' (fullscreen).",
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

APPLY_SMART_FEATURE = {
    "name": "apply_smart_feature",
    "description": (
        "Apply a high-level parametric engineering Smart Feature to a 3D model or create a standalone feature: "
        "honeycomb, slotted_grill, circular_perforation, heatset_boss (M2-M5), screw_hole, hex_nut_pocket, "
        "keystone_jack, c14_inlet, usb_port, fan_mount, rocker_switch, zip_tie_mount, velcro_slot, "
        "cable_pass_through, stiffening_ribs, or gusset."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "feature_type": {
                "type": "string",
                "enum": [
                    "honeycomb",
                    "slotted_grill",
                    "circular_perforation",
                    "heatset_boss",
                    "screw_hole",
                    "hex_nut_pocket",
                    "keystone_jack",
                    "c14_inlet",
                    "usb_port",
                    "fan_mount",
                    "rocker_switch",
                    "zip_tie_mount",
                    "velcro_slot",
                    "cable_pass_through",
                    "stiffening_ribs",
                    "gusset",
                ],
                "description": "Smart feature type.",
            },
            "target_object": {
                "type": "string",
                "description": "Optional target object name (PartDesign::Body or Part) to modify.",
            },
            "parameters": {
                "type": "object",
                "description": "Feature-specific dimensions (bounds_w, bounds_h, cell_size, wall_thickness, depth, thread, etc.).",
            },
            "placement": {
                "type": "object",
                "properties": {
                    "position": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    "rotation": {"type": "array", "items": {"type": "number"}},
                },
                "description": "Spatial placement [position: [x,y,z], rotation: [yaw,pitch,roll]].",
            },
            "operation": {
                "type": "string",
                "enum": ["cut", "fuse", "new_object"],
                "default": "cut",
                "description": "Boolean operation: 'cut' (pocket), 'fuse' (add material), or 'new_object' (standalone solid).",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["feature_type"],
    },
}

AUDIT_WALL_THICKNESS = {
    "name": "audit_wall_thickness",
    "description": (
        "Audit 3D solid for thin walls below printable FDM threshold (e.g. < 1.2 mm for 3 perimeters). "
        "Identifies fragile regions that could cause slicing voids or structural failure."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of target object to inspect.",
            },
            "min_thickness": {
                "type": "number",
                "default": 1.2,
                "description": "Minimum acceptable wall thickness in mm (default 1.2).",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["object_name"],
    },
}

SPLIT_PART_FOR_BED = {
    "name": "split_part_for_bed",
    "description": (
        "Split oversized parts to fit 3D printer build bed with interlocking alignment dowel joints or puzzle seams."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of target object to split.",
            },
            "max_bed_size": {
                "type": "number",
                "default": 256.0,
                "description": "Maximum printable build volume size in mm (default 256.0).",
            },
            "split_axis": {
                "type": "string",
                "enum": ["X", "Y", "Z"],
                "default": "X",
                "description": "Axis along which to split.",
            },
            "joint_type": {
                "type": "string",
                "enum": ["dowel", "flat"],
                "default": "dowel",
                "description": "Joint type: 'dowel' (creates alignment pin holes) or 'flat'.",
            },
            "clearance": {
                "type": "number",
                "default": 0.2,
                "description": "Joint tolerance clearance in mm.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["object_name"],
    },
}

CUT_COMPONENT_CAVITY = {
    "name": "cut_component_cavity",
    "description": (
        "Subtract an accurate mounting cavity for a hardware component (c14_socket, keystone_rj45, "
        "raspberry_pi_5, fan_40mm, fan_80mm, mean_well_rs25, mean_well_lrs35) directly from target solid with clearance tolerance."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "target_object": {
                "type": "string",
                "description": "Name of target object to cut.",
            },
            "dummy_type": {
                "type": "string",
                "enum": [
                    "c14_socket",
                    "keystone_rj45",
                    "raspberry_pi_5",
                    "fan_40mm",
                    "fan_80mm",
                    "mean_well_rs25",
                    "mean_well_lrs35",
                    "usb_c_plug",
                ],
                "description": "Hardware component type.",
            },
            "placement": {
                "type": "object",
                "properties": {
                    "position": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    "rotation": {"type": "array", "items": {"type": "number"}},
                },
                "description": "Spatial placement [position: [x,y,z], rotation: [yaw,pitch,roll]].",
            },
            "clearance": {
                "type": "number",
                "default": 0.3,
                "description": "Fit clearance offset in mm (default 0.3).",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["target_object", "dummy_type"],
    },
}

GENERATE_DRAWING = {
    "name": "generate_drawing",
    "description": (
        "Generate automated multi-view 2D engineering drawing (Front, Top, Isometric views) "
        "and export to PDF or SVG vector formats using FreeCAD TechDraw."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "Name of object to draw.",
            },
            "format": {
                "type": "string",
                "enum": ["pdf", "svg"],
                "default": "pdf",
                "description": "Output drawing format.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional destination file path.",
            },
            "scale": {
                "type": "number",
                "description": "Optional drawing scale (default: auto-fit).",
            },
            "views": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["front", "top", "isometric"],
                "description": "Views to include in drawing.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
        },
        "required": ["object_name"],
    },
}

GET_SELECTION = {
    "name": "get_selection",
    "description": (
        "Inspect active user selection in FreeCAD GUI. Returns selected objects, faces, edges, "
        "and vertices with geometric normals, centers of mass, dimensions, and TNP-safe query filters."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
}

GET_MULTI_VIEW = {
    "name": "get_multi_view",
    "description": (
        "Capture 4 standard camera angles (Front, Rear, Top, Isometric) in a single tool call "
        "with clean shading and optimal framing."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "views": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["Isometric", "Front", "Top", "Rear"],
                "description": "List of view angles to capture.",
            },
            "document_name": {
                "type": "string",
                "description": "Optional document name.",
            },
            "target_object": {
                "type": "string",
                "description": "Optional target object to frame.",
            },
            "display_mode": {
                "type": "string",
                "enum": ["Flat Lines", "Shaded", "Wireframe"],
                "default": "Flat Lines",
                "description": "3D display mode.",
            },
            "width": {"type": "integer", "default": 1920},
            "height": {"type": "integer", "default": 1080},
            "background": {
                "type": "string",
                "enum": ["White", "Current", "Black", "Transparent"],
                "default": "White",
            },
            "coordinate_system": {
                "type": "string",
                "enum": ["standard", "rack", "printbed"],
                "default": "standard",
            },
            "zoom_margin": {"type": "number", "default": 1.1},
            "output_dir": {
                "type": "string",
                "description": "Optional destination directory.",
            },
        },
    },
}

TOOL_DEFINITIONS = [
    EXECUTE_PYTHON,
    EXECUTE_PYTHON_FILE,
    GET_OUTPUT_PAGE,
    GET_VIEW,
    GET_MULTI_VIEW,
    GET_SECTION_VIEW,
    EXPORT_VIEWER_HTML,
    SET_DISPLAY_STATE,
    INSPECT_GEOMETRY,
    ANALYZE_STABILITY,
    CHECK_OVERHANGS,
    AUDIT_WALL_THICKNESS,
    SPLIT_PART_FOR_BED,
    INSPECT_FASTENERS,
    GET_DOCUMENT_TREE,
    DIAGNOSE_DOCUMENT,
    CHECK_CLEARANCE,
    INSERT_REFERENCE_DUMMY,
    CUT_COMPONENT_CAVITY,
    APPLY_SMART_FEATURE,
    GENERATE_DRAWING,
    GET_SELECTION,
    EXPORT_GEOMETRY,
    MANAGE_DOCUMENT,
    UNDO_REDO,
]
