"""Viewport, camera, and screenshot operations for FreeCAD MCP."""

import base64
import os
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
    output_path=None,
    return_base64=False,
):
    """Capture a screenshot from a standard camera angle with optimal framing.

    Parameters:
    - view: Camera angle name ("Isometric", "Front", "Top", "Rear", "Left", "Right", "Bottom", "Dimetric").
    - document_name: Optional name of document (defaults to ActiveDocument).
    - target_object: Optional object name to focus and frame on.
    - display_mode: "Flat Lines", "Shaded", "Wireframe", "Points".
    - width, height: Dimensions of output image.
    - background: "Current", "White", "Black", "Transparent".
    - output_path: Optional destination file path.
    - return_base64: If True, include base64-encoded PNG in result.
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

    # Set camera angle
    view_norm = (view or "Isometric").strip().lower()
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

    h = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
    h.SetBool("EnableAnimation", False)
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

    # Flush Qt event loop so camera and scene graph updates are rendered immediately
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

    # Determine output path
    if not output_path:
        tmp_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_screenshots")
        os.makedirs(tmp_dir, exist_ok=True)
        ts = int(time.time() * 1000)
        output_path = os.path.join(tmp_dir, f"{doc.Name}_{view_norm}_{ts}.png")
    else:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    # Save image
    active_view.saveImage(output_path, int(width), int(height), background or "Current")

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        return {"error": f"Failed to save image to '{output_path}'."}

    result = {
        "status": "ok",
        "document": doc.Name,
        "view": view,
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


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
