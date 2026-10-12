"""Viewport, camera, screenshot, and section view operations for FreeCAD MCP."""

import base64
import math
import os
import re
import time
import FreeCAD
import FreeCADGui


def get_view(
    view="Isometric",
    document_name=None,
    target_object=None,
    display_mode="Flat Lines",
    width=1920,
    height=1080,
    background="Current",
    coordinate_system="standard",
    direction=None,
    zoom_margin=1.1,
    output_path=None,
    return_base64=False,
):
    """Capture a screenshot with optimal framing, coordinate systems, and custom angles.

    Parameters:
    - view: Preset ("Isometric", "Front", "Top", "Rear", "Left", "Right", "Bottom", "Dimetric").
    - document_name: Optional document name.
    - target_object: Optional object name to focus on.
    - display_mode: "Flat Lines", "Shaded", "Wireframe", "Points".
    - coordinate_system: "standard" (Z up), "rack" (Y up, -Z depth, X width), "printbed".
    - direction: Optional [dx, dy, dz] custom camera vector.
    - zoom_margin: Margin factor (> 1 zooms out, e.g. 1.15 to leave breathing room).
    - width, height: Output image size in pixels.
    - background: "Current", "White", "Black", "Transparent".
    - output_path: Destination PNG file path.
    - return_base64: If True, include base64-encoded image string.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    gui_doc = FreeCADGui.getDocument(doc.Name)
    if not gui_doc or not hasattr(gui_doc, "ActiveView") or not gui_doc.ActiveView:
        return {"error": f"Document '{doc.Name}' has no active 3D view."}

    active_view = gui_doc.ActiveView

    # Target framing and visibility
    target_vo = None
    if target_object:
        obj = doc.getObject(target_object)
        if obj:
            target_vo = gui_doc.getObject(obj.Name)
            if target_vo:
                target_vo.Visibility = True
                if display_mode:
                    try:
                        target_vo.DisplayMode = display_mode
                    except Exception:
                        pass
        else:
            return {"error": f"Target object '{target_object}' not found in document '{doc.Name}'."}

    # Ensure PartDesign bodies are visible
    for obj in doc.Objects:
        if obj.isDerivedFrom("PartDesign::Body"):
            body_vo = gui_doc.getObject(obj.Name)
            if body_vo:
                body_vo.Visibility = True
                if display_mode and not target_object:
                    try:
                        body_vo.DisplayMode = display_mode
                    except Exception:
                        pass
                if hasattr(obj, "Tip") and obj.Tip:
                    tip_vo = gui_doc.getObject(obj.Tip.Name)
                    if tip_vo:
                        tip_vo.Visibility = True

    # Disable camera transition lag
    h = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
    h.SetBool("EnableAnimation", False)

    # Set camera direction / orientation
    view_norm = (view or "Isometric").strip().lower()
    cs_norm = (coordinate_system or "standard").strip().lower()

    if direction and len(direction) == 3:
        # Custom camera view vector
        d_vec = FreeCAD.Vector(*direction)
        active_view.setViewDirection(d_vec)
    elif cs_norm == "rack":
        # 10" Rack coordinates: X width, Y height, -Z depth into rack
        rack_views = {
            "front": "ViewTop",       # Front face at Z=+1.5 looking down -Z
            "rear": "ViewBottom",     # Rear looking +Z
            "top": "ViewFront",       # Looking down -Y
            "bottom": "ViewRear",     # Looking up +Y
            "left": "ViewLeft",
            "right": "ViewRight",
            "isometric": "ViewIsometric",
        }
        msg = rack_views.get(view_norm, "ViewTop")
        FreeCADGui.SendMsgToActiveView(msg)
    else:
        # Standard FreeCAD camera views
        view_msg_map = {
            "isometric": "ViewIsometric",
            "iso": "ViewIsometric",
            "front": "ViewFront",
            "top": "ViewTop",
            "rear": "ViewRear",
            "back": "ViewRear",
            "left": "ViewLeft",
            "right": "ViewRight",
            "bottom": "ViewBottom",
            "dimetric": "ViewDimetric",
            "axonometric": "ViewAxonometric",
        }
        msg = view_msg_map.get(view_norm, "ViewIsometric")
        FreeCADGui.SendMsgToActiveView(msg)

    # Fit framing
    if target_vo:
        try:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(doc.Name, target_object)
            active_view.fitSelection()
        except Exception:
            active_view.fitAll()
    else:
        active_view.fitAll()

    # Apply zoom margin if needed
    margin = float(zoom_margin or 1.0)
    if abs(margin - 1.0) > 0.01:
        try:
            cam_str = active_view.getCamera()
            def repl(m):
                return f"height {float(m.group(1)) * margin:.4f}"
            new_cam = re.sub(r'height\s+([0-9.]+)', repl, cam_str)
            active_view.setCamera(new_cam)
        except Exception:
            pass

    # Flush Qt event loop
    _flush_gui()

    # Save screenshot
    if not output_path:
        tmp_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_screenshots")
        os.makedirs(tmp_dir, exist_ok=True)
        ts = int(time.time() * 1000)
        output_path = os.path.join(tmp_dir, f"{doc.Name}_{view_norm}_{ts}.png")
    else:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    active_view.saveImage(output_path, int(width), int(height), background or "Current")

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        return {"error": f"Failed to save image to '{output_path}'."}

    result = {
        "status": "ok",
        "document": doc.Name,
        "view": view,
        "coordinate_system": coordinate_system,
        "width": width,
        "height": height,
        "image_path": output_path,
        "file_size_bytes": os.path.getsize(output_path),
    }

    if return_base64:
        with open(output_path, "rb") as f:
            result["image_base64"] = base64.b64encode(f.read()).decode("utf-8")
            result["image_mime"] = "image/png"

    return result


def get_section_view(
    plane="XY",
    offset=0.0,
    flip_direction=False,
    view="Isometric",
    coordinate_system="standard",
    direction=None,
    target_object=None,
    document_name=None,
    display_mode="Flat Lines",
    zoom_margin=1.1,
    width=1920,
    height=1080,
    background="Current",
    output_path=None,
    return_base64=False,
):
    """Capture a cross-section cut view using Coin3D clipping plane without modifying the model.

    Parameters:
    - plane: "XY", "XZ", "YZ", or custom normal vector [nx, ny, nz].
    - offset: Cut plane offset distance in mm.
    - flip_direction: Invert the clipped side.
    - view, coordinate_system, direction: Camera orientation settings.
    - target_object: Target object to focus on.
    - display_mode, width, height, background, output_path, return_base64: Standard rendering settings.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    gui_doc = FreeCADGui.getDocument(doc.Name)
    if not gui_doc or not hasattr(gui_doc, "ActiveView") or not gui_doc.ActiveView:
        return {"error": f"Document '{doc.Name}' has no active 3D view."}

    active_view = gui_doc.ActiveView

    # Compute normal vector for clipping plane
    if isinstance(plane, str):
        p_upper = plane.upper().strip()
        if p_upper == "XY":
            normal = (0.0, 0.0, 1.0)
        elif p_upper == "XZ":
            normal = (0.0, 1.0, 0.0)
        elif p_upper == "YZ":
            normal = (1.0, 0.0, 0.0)
        else:
            normal = (0.0, 0.0, 1.0)
    elif isinstance(plane, (list, tuple)) and len(plane) == 3:
        n_len = math.hypot(plane[0], plane[1], plane[2])
        normal = (plane[0] / n_len, plane[1] / n_len, plane[2] / n_len) if n_len > 1e-6 else (0.0, 0.0, 1.0)
    else:
        normal = (0.0, 0.0, 1.0)

    if flip_direction:
        normal = (-normal[0], -normal[1], -normal[2])

    # Rotation from +Z (Coin3D default clipping plane normal) to target normal
    z_axis = FreeCAD.Vector(0, 0, 1)
    norm_vec = FreeCAD.Vector(*normal)
    rot = FreeCAD.Rotation(z_axis, norm_vec)
    pos = norm_vec * float(offset)
    placement = FreeCAD.Placement(pos, rot)

    try:
        # Enable clipping plane
        active_view.toggleClippingPlane(1, False, True, placement)

        # Snap using get_view logic
        result = get_view(
            view=view,
            document_name=doc.Name,
            target_object=target_object,
            display_mode=display_mode,
            width=width,
            height=height,
            background=background,
            coordinate_system=coordinate_system,
            direction=direction,
            zoom_margin=zoom_margin,
            output_path=output_path,
            return_base64=return_base64,
        )
        if "status" in result and result["status"] == "ok":
            result["section_plane"] = {
                "plane": plane,
                "normal": list(normal),
                "offset_mm": float(offset),
                "flipped": bool(flip_direction),
            }
        return result
    finally:
        # Guarantee removal of clipping plane
        try:
            active_view.toggleClippingPlane(0)
            _flush_gui()
        except Exception:
            pass


def set_display_state(
    document_name=None,
    body_name=None,
    show_only_tip=True,
    hide_sketches=True,
    display_mode="Flat Lines",
    shape_color=None,
):
    """Normalize GUI display: ensure body visibility, hide clutter, set style."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    gui_doc = FreeCADGui.getDocument(doc.Name)
    if not gui_doc:
        return {"error": f"Document '{doc.Name}' has no GUI representation."}

    bodies = []
    if body_name:
        b = doc.getObject(body_name)
        if b and b.isDerivedFrom("PartDesign::Body"):
            bodies.append(b)
        else:
            return {"error": f"PartDesign::Body '{body_name}' not found."}
    else:
        bodies = [o for o in doc.Objects if o.isDerivedFrom("PartDesign::Body")]

    updated_bodies = []
    for body in bodies:
        body_vo = gui_doc.getObject(body.Name)
        if body_vo:
            body_vo.Visibility = True
            if display_mode:
                try:
                    body_vo.DisplayMode = display_mode
                except Exception:
                    pass
            if shape_color and len(shape_color) >= 3:
                try:
                    body_vo.ShapeColor = (float(shape_color[0]), float(shape_color[1]), float(shape_color[2]))
                except Exception:
                    pass

        tip = getattr(body, "Tip", None)
        tip_name = tip.Name if tip else None

        if show_only_tip and tip:
            tip_vo = gui_doc.getObject(tip.Name)
            if tip_vo:
                tip_vo.Visibility = True

            for feat in getattr(body, "Group", []):
                if feat.Name != tip_name:
                    f_vo = gui_doc.getObject(feat.Name)
                    if f_vo:
                        f_vo.Visibility = False

        updated_bodies.append({"name": body.Name, "tip": tip_name})

    if hide_sketches:
        for obj in doc.Objects:
            if obj.isDerivedFrom("Sketcher::SketchObject"):
                s_vo = gui_doc.getObject(obj.Name)
                if s_vo:
                    s_vo.Visibility = False

    if hasattr(gui_doc, "ActiveView") and gui_doc.ActiveView:
        gui_doc.ActiveView.fitAll()

    return {
        "status": "ok",
        "document": doc.Name,
        "updated_bodies": updated_bodies,
        "display_mode": display_mode,
    }


def _flush_gui():
    try:
        FreeCADGui.updateGui()
        try:
            from PySide import QtWidgets
            QtWidgets.QApplication.processEvents()
        except ImportError:
            from PySide2 import QtWidgets
            QtWidgets.QApplication.processEvents()
    except Exception:
        pass


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
