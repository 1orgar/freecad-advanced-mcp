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

## 🛠️ The 25 CAD Tools

FreeCAD Advanced MCP equips AI assistants with 25 specialized engineering tools:

| Category | Tool | Description |
| :--- | :--- | :--- |
| **Vision & GUI** | [`get_view`](#1-get_view) | Capture precision screenshots (`Isometric`, `Front`, `Top`, etc.) with `Flat Lines` styling and optimal framing. |
| | [`get_multi_view`](#2-get_multi_view) | Capture 4 camera angles (`Isometric`, `Front`, `Top`, `Rear`) in a single atomic tool call. |
| | [`get_section_view`](#14-get_section_view) | Non-destructive Coin3D cross-section clipping plane view without altering geometry. |
| | [`export_viewer_html`](#15-export_viewer_html) | Zero-dependency interactive WebGL 3D CAD viewer for in-chat embeds (`<agent-embed>`) with per-part colors, interactive **Explode** slider, and **Section** cut plane. |
| | [`set_display_state`](#13-set_display_state) | Batch control object visibility, shading modes, Tip display, and ghosted transparency. |
| **Smart Features & Modeling** | [`apply_smart_feature`](#3-apply_smart_feature) | Apply 20 semantic engineering primitives (honeycomb, heat-set bosses, grills, keystones, C14 inlets, snap-fits, enclosure lips, dovetails, mounting ears, ribs). |
| | [`cut_component_cavity`](#4-cut_component_cavity) | Carve exact component mounting profiles and screw holes into solids with configurable 3D printing clearance. |
| **DfAM (3D Printing)** | [`audit_wall_thickness`](#5-audit_wall_thickness) | Scan planar and coaxial cylindrical walls for thin regions (< 1.2 mm) that cause slicing gaps or fragile prints. |
| | [`split_part_for_bed`](#6-split_part_for_bed) | Split oversized models on X/Y/Z to fit 3D printer build beds with interlocking alignment dowel sockets. |
| | [`analyze_stability`](#16-analyze_stability) | Calculate base contact polygon convex hull (including curved/cylindrical bases on XY/XZ/YZ), center of mass, and tipping angles. |
| | [`check_overhangs`](#17-check_overhangs) | 3D printability analysis: overhang percentage below critical angle, Z-bounds, and support needs. |
| **Inspection & Selection** | [`get_selection`](#7-get_selection) | Human-in-the-Loop selection inspector: reads clicked faces/edges with TNP-safe query criteria. |
| | [`inspect_geometry`](#10-inspect_geometry) | Deep analysis: BoundingBox, volume, estimated mass (PLA/ABS/Al), surface type breakdown, and manifold verification. |
| | [`inspect_fasteners`](#18-inspect_fasteners) | Detect cylindrical features, match ISO metric fasteners (M2-M8), and measure hole/boss depths. |
| | [`check_clearance`](#11-check_clearance) | Real-time interference detection and minimum 3D clearance distance calculation (`distToShape`). |
| | [`diagnose_document`](#19-diagnose_document) | Deep health audit: recompute errors, Sketcher DoF, broken body Tips, and BRep topology defects. |
| **Hardware & Assembly** | [`insert_reference_dummy`](#9-insert_reference_dummy) | Insert accurate reference models (Raspberry Pi 5, C14, Keystones, Fans, DIN rails, PSUs, screws). |
| | [`get_document_tree`](#20-get_document_tree) | Retrieve full hierarchical document scene graph, object types, labels, and visibility. |
| **2D Drawings & Export** | [`generate_drawing`](#8-generate_drawing) | Automated TechDraw engineering drawings: multi-view orthogonal + isometric projections to vector PDF/SVG. |
| | [`export_geometry`](#12-export_geometry) | Export solids to **STL** (with custom deflection), **STEP** (AP214 PartDesign fix), **3MF**, or **DXF**. |
| **Document Lifecycle** | [`manage_document`](#21-manage_document) | Document control: active doc query, list all, create new, open `.FCStd`, save, close, and recompute. |
| | [`undo_redo`](#22-undo_redo) | Step forward or backward through transaction history. |
| **Code Execution** | [`execute_python`](#23-execute_python--cad-helpers) | Execute Python in FreeCAD Qt main thread with auto-rollback transactions. |
| | [`execute_python_file`](#24-execute_python_file) | Execute local script files in FreeCAD. |
| | [`get_output_page`](#25-get_output_page) | Retrieve paged output streams for long console logs. |

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

### 2. `get_multi_view`
Captures multiple standard camera angles (`Isometric`, `Front`, `Top`, `Rear`) in a single round-trip:
- **Parameters:**
  - `views` *(array of strings, default: `["Isometric", "Front", "Top", "Rear"]`)*
  - `target_object` *(string, optional)*: Focus and frame on a specific object.
  - `display_mode` *(string)*: `Flat Lines`, `Shaded`, `Wireframe`.
  - `width` / `height` *(int)*: Output resolution (default: `1920x1080`).

### 3. `apply_smart_feature`
Semantic CAD primitive library for rapid engineering design without manual sketch constraints:
- **Supported Features (20 primitives):**
  - **Patterns:** `honeycomb` (hexagonal ventilation grid), `slotted_grill` (cooling louvers), `circular_perforation` (staggered hole mesh).
  - **Fasteners & Inserts:** `heatset_boss` (Ruthex/CNC Kitchen M2-M5 with anti-sink lead-in chamfer), `screw_hole` (DIN 912 counterbore & DIN 7991 countersink), `hex_nut_pocket` (captive hex nut trap).
  - **Cutouts & Ports:** `keystone_jack` (standard snap-in RJ45), `c14_inlet` (chassis IEC power socket with screw mounts), `usb_port` (USB-A & USB-C cutouts), `fan_mount` (40mm, 60mm, 80mm, 92mm, 120mm with fan grille & mounting holes), `rocker_switch` (snap-in AC power switch).
  - **Enclosure & Assembly Joints:** `snap_fit` (cantilever snap-fit hook), `enclosure_lip` (perimeter tongue & groove mating rim), `dovetail_joint` (sliding 45°/60° male/female dovetail), `mounting_ear` (flanged mounting ear with stadium slots).
  - **Cable Management:** `zip_tie_mount` (saddle & flush tie bridges), `velcro_slot` (cable cinch slots), `cable_pass_through` (beveled grommet passthrough).
  - **Structural Reinforcement:** `stiffening_ribs` (flanged strengthening ribs), `gusset` (corner reinforcement web).
- **Parameters:**
  - `feature_type` *(string, required)*
  - `target_object` *(string, optional)*: Part or Body to modify.
  - `operation` *(string, optional)*: `cut` (subtractive/pocket), `fuse` (additive/union), or `new_object` (standalone). Auto-inferred from feature type if omitted.
  - `parameters` *(object)*: Feature-specific dimensions (`bounds_w`, `cell_size`, `thread`, `boss_height`, etc.).
  - `placement` *(object)*: `{"position": [x,y,z], "rotation": [yaw,pitch,roll], "normal": [nx,ny,nz]}`.

### 4. `cut_component_cavity`
Carves an exact negative mounting pocket for a hardware dummy with configurable 3D printing clearance:
- **Parameters:**
  - `target_object` *(string, required)*: Solid to carve into.
  - `dummy_type` *(string, required)*: `c14_socket`, `keystone_rj45`, `raspberry_pi_5`, `fan_40mm`, `fan_80mm`, `mean_well_rs25`, `mean_well_lrs35`, `usb_c_plug`.
  - `clearance` *(float, default: `0.3`)*: Tolerance in mm added to all axes.
  - `placement` *(object)*: `{"position": [x,y,z], "rotation": [yaw,pitch,roll]}`.

### 5. `audit_wall_thickness`
DfAM (Design for Additive Manufacturing) thickness audit. Detects antiparallel surfaces separated by less than the minimum printable threshold:
- **Parameters:**
  - `object_name` *(string, required)*
  - `min_thickness` *(float, default: `1.2` mm for 3 standard perimeters)*
- **Returns:** Minimum wall thickness found, list of thin wall regions with coordinates, and printability recommendations.

### 6. `split_part_for_bed`
Splits oversized models along X, Y, or Z to fit 3D printer build beds (e.g. 256×256 mm) with interlocking alignment dowel pin sockets:
- **Parameters:**
  - `object_name` *(string, required)*
  - `max_bed_size` *(float, default: `256.0`)*
  - `split_axis` *(string)*: `X`, `Y`, or `Z` (default: `X`).
  - `joint_type` *(string)*: `dowel` (pin holes) or `flat`.
  - `clearance` *(float, default: `0.2` mm)*.

### 7. `get_selection`
Human-in-the-Loop selection inspector. Reads user-clicked faces, edges, or vertices directly from the active FreeCAD 3D view:
- **Returns:** Surface types, normal vectors, midpoint/tangent coordinates, area, and pre-computed `tnp_query` selectors for Topological Naming Problem protection.

### 8. `generate_drawing`
Automated TechDraw 2D vector engineering drawing generator:
- **Parameters:**
  - `object_name` *(string, required)*
  - `format` *(string)*: `pdf` (vector PDF) or `svg`.
  - `output_path` *(string, optional)*
  - `scale` *(float, optional)*: View scale factor (auto-computed to fit A4 page if omitted).
  - `views` *(array of strings, default: `["front", "top", "isometric"]`)*.

### 9. `insert_reference_dummy`
Inserts dimensionally accurate, semi-transparent reference models for packaging fit testing:
- **Components:** `raspberry_pi_5`, `fan_40mm`, `fan_80mm`, `c14_socket`, `keystone_rj45`, `din_rail_35mm`, `mean_well_rs25`, `mean_well_lrs35`, `iphone_15_pro`, `iphone_15_pro_max`, `generic_phone`, `usb_c_plug`, `mikrotik_crs305`, `screw_m3`, `screw_m6`.

### 10. `inspect_geometry`
Performs comprehensive topological and physical property checks on any CAD object: BoundingBox, volume, surface area, center of mass, and watertight/manifold verification.

### 11. `check_clearance`
Detects collisions and measures minimal clearance distance between two solids using OpenCASCADE extrema (`distToShape`).

### 12. `export_geometry`
Exports solids to production formats (**STL** with custom chordal/angular deflection, **STEP** AP214 with native PartDesign body support, **3MF**, or **DXF**).

### 13. `set_display_state`
Controls rendering styling across the scene: body visibility, Tip display, sketch hiding, and display modes (`Flat Lines`, `Shaded`, `Wireframe`).

### 14. `get_section_view`
Captures non-destructive cross-section cut views using native Coin3D clipping planes (`XY`, `XZ`, `YZ`, or custom normal vector).

### 15. `export_viewer_html`
Exports the 3D model into an interactive WebGL CAD viewer. Zero external 3D engine dependencies (completely immune to strict CSP restrictions).
- **Parameters:**
  - `object_name` *(string, optional)*: Solid body, `Part::Compound` assembly, or `"all"` to export all visible solids in the document.
  - `mode` *(string)*: `"chat"` (compact inline card `< 450px` for chat embeds via `<agent-embed>`, theme-adaptive) or `"standalone"` (full-window CAD viewer with HUD). Default: `"standalone"`.
  - `output_path` *(string, optional)*: Destination `.html` path.
  - `title` *(string, optional)*: Viewer header title.
  - `linear_deflection` / `angular_deflection` *(float)*: OCCT tessellation mesh resolution.
- **Features:** Per-part RGB color rendering (`aColor`), interactive **Explode** slider (`aExplode`) for multi-solid assemblies, live **Section** clipping plane with interior highlight, CAD wireframe edge rendering, and automatic dark/light theme switching.

### 16. `analyze_stability`
Calculates 2D base contact polygon convex hull (including discretized curved/cylindrical edges on `XY`, `XZ`, or `YZ`), combined center of mass (with optional device payload), and tipping angles in all 4 cardinal directions.

### 17. `check_overhangs`
3D printability analysis: computes downward-facing surface areas, overhang percentage below critical angle (e.g. 45°), Z-bounds, and support necessity.

### 18. `inspect_fasteners`
Detects cylindrical features, classifies internal holes vs external mounting bosses, matches diameters to standard ISO metric fasteners (M2-M8, clearance, tap, heat-set brass inserts), and reports depths.

### 19. `diagnose_document`
Performs deep health audit: identifies recompute errors, inspects Sketcher degrees of freedom (`DoF`), conflicting or redundant constraints, broken body Tips, and OpenCASCADE BRepCheck topology defects.

### 20. `get_document_tree`
Returns the active document structure with object hierarchy, labels, and visibility states.

### 21. `manage_document`
Lifecycle management: `list`, `new`, `open`, `save`, `close`, `recompute`.

### 22. `undo_redo`
Undo or redo operations in FreeCAD (all mutating MCP tool calls are automatically wrapped in FreeCAD transactions).

### 23. `execute_python` & `cad` Helpers
Runs Python scripts directly inside FreeCAD. Pre-binds `FreeCAD`, `App`, `FreeCADGui`, `Gui`, `Part`, `PartDesign`, `Sketcher`, `Mesh`, `MeshPart`, `math`, and TNP-safe `cad` utilities:
- **Topology & Sketch Helpers:** `find_face`, `find_edges`, `add_rigid_rect`, `add_slot`.
- **High-Speed Solid Modeling:** `rounded_box`, `safe_fillet`, `safe_chamfer`, `boolean_chain` (with `removeSplitter()` refinement), `linear_pattern`, `polar_pattern`, `shell_solid`, `align_to`.

### 24. `execute_python_file`
Executes local `.py` script files in FreeCAD.

### 25. `get_output_page`
Retrieves paged output streams for long console logs.

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
