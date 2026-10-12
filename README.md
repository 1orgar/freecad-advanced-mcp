<div align="center">

<img src="Resources/Icons/icon.svg" alt="FreeCAD Advanced MCP Logo" width="96" height="96">

# FreeCAD Advanced MCP

**High-Performance, In-Process Model Context Protocol (MCP) Server for FreeCAD**

[![Release](https://img.shields.io/github/v/release/1orgar/freecad-advanced-mcp?style=flat-square&color=blue)](https://github.com/1orgar/freecad-advanced-mcp/releases)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-v1.1+-teal?style=flat-square&logo=freecad)](https://www.freecad.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP%20Protocol-2025--03--26-purple?style=flat-square)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

*Empower AI coding agents (Claude, Antigravity, Cursor, Windsurf) with native 3D CAD modeling, deep geometric topology inspection, real-time collision & clearance analysis, multi-angle Coin3D rendering, and multi-format CAD exports.*

---

</div>

## 🌟 Highlights

Unlike external CLI bridges or headless subprocesses, **FreeCAD Advanced MCP runs directly inside the live FreeCAD GUI application on the Qt main thread**. This provides:

- ⚡ **Zero-Latency OCCT Kernel Access**: Inspect B-Rep topologies, exact bounding boxes, volumes, and distances using OpenCASCADE without file serialization bottlenecks.
- 📸 **Active Coin3D Viewport Control**: Capture multi-angle screenshots (`Isometric`, `Front`, `Top`, etc.) with `Flat Lines` wireframe-on-shaded styling and instant camera framing.
- 💥 **Automated Clash & Clearance Analysis**: Detect geometric interferences and compute exact minimum gaps between solids before sending models to 3D printers or CNC mills.
- 🛡️ **Transaction-Safe Execution**: Macro errors automatically trigger an undo transaction rollback, preventing broken document states during iterative AI design.
- 🚀 **Zero-Click Auto-Start**: Automatically begins listening on `127.0.0.1:39280` when FreeCAD opens, complete with an interactive toolbar toggle and status-bar feedback.

---

## 🛠️ The 11 CAD Tools

FreeCAD Advanced MCP equips AI assistants with 11 specialized engineering tools:

| Category | Tool | Description |
| :--- | :--- | :--- |
| **Vision & GUI** | [`get_view`](#1-get_view) | Capture precision screenshots (`Isometric`, `Front`, `Top`, etc.) with `Flat Lines` styling and optimal framing. |
| | [`set_display_state`](#2-set_display_state) | Batch control object visibility, shading modes, and ghosted transparency. |
| **Geometry & Inspection** | [`inspect_geometry`](#3-inspect_geometry) | Deep analysis: BoundingBox, volume, surface area, center of mass, and watertight/manifold verification. |
| | [`check_clearance`](#4-check_clearance) | Real-time interference detection and minimum 3D clearance distance calculation (`distToShape`). |
| | [`get_document_tree`](#5-get_document_tree) | Retrieve full hierarchical document scene graph, object types, labels, and visibility. |
| **Manufacturing Export** | [`export_geometry`](#6-export_geometry) | Export solids to **STL** (with custom linear/angular mesh deflection), **STEP** (AP214), **3MF**, or **DXF**. |
| **Document Lifecycle** | [`manage_document`](#7-manage_document) | Document control: active doc query, list all, create new, open `.FCStd`, save, close, and recompute. |
| | [`undo_redo`](#8-undo_redo) | Step forward or backward through transaction history. |
| **Code Execution** | [`execute_python`](#9-execute_python) | Execute Python in FreeCAD Qt main thread with auto-rollback transactions. |
| | [`execute_python_file`](#10-execute_python_file) | Execute local script files in FreeCAD. |
| | [`get_output_page`](#11-get_output_page) | Retrieve paged output streams for long console logs. |

---

## 📦 Installation

### Method 1: Git Clone (Fastest & Recommended)

Clone this repository into your FreeCAD `Mod/` directory:

#### **macOS**
```bash
git clone https://github.com/1orgar/freecad-advanced-mcp.git ~/Library/Application\ Support/FreeCAD/v1-1/Mod/freecad-advanced-mcp
```

#### **Linux**
```bash
git clone https://github.com/1orgar/freecad-advanced-mcp.git ~/.local/share/FreeCAD/v1-1/Mod/freecad-advanced-mcp
```

#### **Windows (Command Prompt / PowerShell)**
```cmd
git clone https://github.com/1orgar/freecad-advanced-mcp.git "%APPDATA%\FreeCAD\v1-1\Mod\freecad-advanced-mcp"
```

Restart FreeCAD. The server will auto-start on port `39280`.

---

### Method 2: FreeCAD Addon Manager (Custom Repository)

1. Open FreeCAD.
2. Go to **Edit → Preferences → Addon Manager**.
3. Under **Custom repositories**, click **+** and enter:
   - **URL:** `https://github.com/1orgar/freecad-advanced-mcp`
   - **Branch:** `main`
4. Click **OK**, open **Tools → Addon Manager**, search for `FreeCAD Advanced MCP`, and click **Install**.
5. Restart FreeCAD.

---

## ⚙️ AI Client Configuration

### 1. Antigravity & Gemini Code Assist

In your `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "freecad": {
      "url": "http://127.0.0.1:39280/mcp"
    }
  }
}
```

### 2. Claude Code

In your project or global `.mcp.json`:

```json
{
  "mcpServers": {
    "freecad": {
      "type": "http",
      "url": "http://127.0.0.1:39280/mcp"
    }
  }
}
```

### 3. Claude Desktop

Claude Desktop communicates via `stdio`. Use the bundled zero-dependency Node.js shim inside `mcp-stdio-shim/`:

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "freecad": {
      "command": "node",
      "args": [
        "<PATH_TO_MOD>/freecad-advanced-mcp/mcp-stdio-shim/index.js"
      ],
      "env": {
        "FREECAD_MCP_PORT": "39280"
      }
    }
  }
}
```

*Or download the pre-packaged `.mcpb` bundle from [Releases](https://github.com/1orgar/freecad-advanced-mcp/releases) and drop it into Claude Desktop (Settings → Extensions).*

### 4. Cursor / Windsurf

In your cursor MCP configuration:

```json
{
  "mcpServers": {
    "freecad": {
      "url": "http://127.0.0.1:39280/mcp"
    }
  }
}
```

---

## 📖 Detailed Tool Documentation

### 1. `get_view`
Captures multi-angle camera views of the 3D scene.
- **Parameters:**
  - `view` *(string)*: `Isometric`, `Front`, `Top`, `Rear`, `Left`, `Right`, `Bottom`, `Dimetric`, `Axonometric`. Default: `Isometric`.
  - `display_mode` *(string)*: `Flat Lines` (recommended for CAD clarity), `Shaded`, `Wireframe`, `Points`.
  - `target_object` *(string, optional)*: Name of an object to zoom and center on.
  - `include_base64` *(boolean)*: If `true`, returns base64 image data directly in the MCP response for multimodal models.
  - `save_path` *(string, optional)*: Explicit PNG file path to save the screenshot.
  - `width` / `height` *(int)*: Viewport resolution (default: `1280x720`).

### 2. `inspect_geometry`
Performs comprehensive topological and physical property checks on any CAD object.
- **Parameters:**
  - `object_name` *(string, required)*: Label or internal name of the object.
- **Returns:**
  ```json
  {
    "status": "ok",
    "name": "Body",
    "type": "PartDesign::Body",
    "is_valid": true,
    "is_closed_manifold": true,
    "bounding_box": {
      "min": [-127.0, -22.0, -1.5],
      "max": [127.0, 22.0, 1.5],
      "dimensions": [254.0, 44.0, 3.0],
      "center": [0.0, 0.0, 0.0]
    },
    "volume_mm3": 33528.0,
    "surface_area_mm2": 23412.5,
    "center_of_mass": [0.0, 0.0, 0.0],
    "topology_counts": {
      "solids": 1,
      "faces": 28,
      "edges": 74,
      "vertices": 48
    }
  }
  ```

### 3. `check_clearance`
Detects collisions and measures minimal clearance distance between two solids using OpenCASCADE extrema.
- **Parameters:**
  - `object_a` *(string, required)*: First object.
  - `object_b` *(string, required)*: Second object.
- **Returns:**
  ```json
  {
    "status": "ok",
    "collision_detected": false,
    "clearance_mm": 2.45,
    "closest_points": {
      "point_on_a": [112.5, 10.0, 1.5],
      "point_on_b": [112.5, 12.45, 1.5]
    }
  }
  ```

### 4. `export_geometry`
Exports objects to production formats.
- **Parameters:**
  - `object_names` *(array of strings, optional)*: Objects to export (exports entire active document if omitted).
  - `filepath` *(string, required)*: Output path (`.stl`, `.step`, `.stp`, `.3mf`, `.dxf`).
  - `format` *(string)*: `STL`, `STEP`, `3MF`, `DXF` (auto-detected from filepath extension if omitted).
  - `stl_deflection` *(float)*: Linear surface deflection in mm (default `0.05` for fine 3D printing curves).
  - `stl_angular_deflection` *(float)*: Angular deflection in radians (default `0.5`).

### 5. `set_display_state`
Controls rendering styling across the scene: body visibility, Tip display, sketch hiding, and display modes (`Flat Lines`, `Shaded`, `Wireframe`).

### 6. `get_section_view`
Captures non-destructive cross-section cut views using native Coin3D clipping planes:
- **Parameters:**
  - `plane` *(string or [x,y,z])*: `XY`, `XZ`, `YZ`, or custom normal vector.
  - `offset` *(float)*: Distance along normal in mm.
  - `flip_direction` *(bool)*: Clip the opposite side.
  - `view`, `coordinate_system`, `direction`, `zoom_margin`, `display_mode`.

### 7. `export_viewer_html`
Exports the 3D model into a standalone, zero-dependency WebGL HTML viewer with Three.js OrbitControls, dimensions overlay, and HUD.

### 8. `analyze_stability`
Calculates 2D base contact polygon convex hull, combined center of mass (with optional smartphone/device payload), and tipping angles in all 4 cardinal directions.

### 9. `check_overhangs`
3D printability analysis: computes downward-facing surface areas, overhang percentage below critical angle (e.g. 45°), Z-bounds, and support necessity.

### 10. `inspect_fasteners`
Detects cylindrical features, classifies internal holes vs external mounting bosses, matches diameters to standard ISO metric fasteners (M2-M8, clearance, tap, heat-set brass inserts), and reports depths.

### 11. `diagnose_document`
Performs deep health audit: identifies recompute errors, inspects Sketcher degrees of freedom (`DoF`), conflicting or redundant constraints, broken body Tips, and OpenCASCADE BRepCheck topology defects.

### 12. `insert_reference_dummy`
Inserts dimensionally accurate, semi-transparent reference models (`iphone_15_pro`, `iphone_15_pro_max`, `generic_phone`, `usb_c_plug`, `mean_well_rs25`, `mikrotik_crs305`, `screw_m3`, `screw_m6`) for fit testing.

### 13. `get_document_tree`
Returns the active document structure with object hierarchy, labels, and visibility states.

### 14. `manage_document`
Lifecycle management: `list`, `new`, `open`, `save`, `close`, `recompute`.

### 15. `undo_redo`
Undo or redo operations in FreeCAD.

### 16. `execute_python` & `cad` Helpers
Runs Python scripts directly inside FreeCAD. Pre-binds `FreeCAD`, `App`, `FreeCADGui`, `Gui`, `Part`, `Sketcher`, and TNP-safe `cad` utilities (`find_face`, `find_edges`, `add_rigid_rect`, `add_slot`). Wrapped in automatic transactions.

---

## 💡 Practical AI Workflow Example

Here is how an AI agent uses FreeCAD Advanced MCP to create a parametric part, inspect it, verify clearances, and export it for manufacturing:

```python
# 1. AI creates a parametric bracket via execute_python
# 2. AI verifies watertightness and dimensions:
#    inspect_geometry(object_name="LBracket")
#    -> is_closed_manifold: true, dimensions: [40.0, 40.0, 20.0]

# 3. AI verifies clearance against neighboring assembly parts:
#    check_clearance(object_a="LBracket", object_b="Chassis")
#    -> clearance_mm: 1.5 mm (Safe)

# 4. AI captures isometric and front screenshots for visual verification:
#    get_view(view="Isometric", display_mode="Flat Lines", include_base64=true)

# 5. AI exports high-resolution STL ready for 3D printing:
#    export_geometry(filepath="/path/to/bracket.stl", stl_deflection=0.02)
```

---

## 🔒 Security & Privacy

FreeCAD Advanced MCP is built for **local, privacy-first** engineering workflows:
- **Loopback Only:** Binds strictly to `127.0.0.1`.
- **CORS Protection:** Rejects any HTTP request whose `Origin` header is not `localhost` or `127.0.0.1`.
- **Zero External Telemetry:** The server never sends data over the internet.
- **User in Control:** The server can be toggled on/off at any time using the FreeCAD toolbar button.

---

## 📄 License

Licensed under the [MIT License](LICENSE).
