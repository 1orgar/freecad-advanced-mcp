"""Automated TechDraw engineering drawing generation for FreeCAD MCP."""

import os
import FreeCAD
import TechDraw
try:
    import TechDrawGui
except ImportError:
    TechDrawGui = None


def generate_drawing(
    object_name,
    format="pdf",
    output_path=None,
    scale=None,
    views=None,
    document_name=None,
):
    """Generate professional engineering 2D drawings with multi-view projection.

    Parameters:
    - object_name: Name of target Part or Body to draw.
    - format: "pdf" or "svg" (default "pdf").
    - output_path: Destination file path.
    - scale: Optional view scale factor (default: auto-computed to fit A4 page).
    - views: List of views to include (default: ["front", "top", "isometric"]).
    - document_name: Optional document name.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found."}

    shape = getattr(obj, "Shape", None)
    if not shape or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape to draw."}

    fmt = (format or "pdf").lower().strip()
    bb = shape.BoundBox

    # Find TechDraw template
    templates_dir = os.path.join(FreeCAD.getResourceDir(), "Mod/TechDraw/Templates")
    template_file = os.path.join(templates_dir, "Default_Template_A4_Landscape.svg")
    if not os.path.isfile(template_file):
        # Fallback check
        alt_template = os.path.join(templates_dir, "A4_Landscape_blank.svg")
        template_file = alt_template if os.path.isfile(alt_template) else template_file

    # Create TechDraw Page and Template
    page_name = f"Drawing_{obj.Name}"
    page = doc.addObject("TechDraw::DrawPage", page_name)
    template = doc.addObject("TechDraw::DrawSVGTemplate", f"Template_{obj.Name}")
    if os.path.isfile(template_file):
        template.Template = template_file
    page.Template = template

    # Compute optimal scale to fit A4 sheet (297 x 210 mm)
    # Available drawing area roughly 250 x 170 mm
    max_part_dim = max(bb.XLength, bb.YLength, bb.ZLength, 1.0)
    if scale:
        computed_scale = float(scale)
    else:
        # Auto-scale
        if max_part_dim > 200:
            computed_scale = 0.5 if max_part_dim <= 400 else 0.25
        elif max_part_dim < 30:
            computed_scale = 2.0
        else:
            computed_scale = 1.0

    # Auto-populate SVG template title block editable texts if available
    try:
        import datetime
        et = dict(getattr(template, "EditableTexts", {}) or {})
        if et:
            dims_str = f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm"
            vol_cm3 = shape.Volume / 1000.0
            scale_str = f"{computed_scale:g}:1" if computed_scale >= 1.0 else f"1:{int(round(1.0 / computed_scale))}"
            today_str = datetime.date.today().isoformat()
            for k in list(et.keys()):
                kl = k.lower()
                if "title" in kl or "name" in kl or "description" in kl:
                    et[k] = f"{obj.Label} ({dims_str})"
                elif "scale" in kl:
                    et[k] = scale_str
                elif "date" in kl:
                    et[k] = today_str
                elif "weight" in kl or "mass" in kl:
                    et[k] = f"{vol_cm3 * 1.25:.1f} g (PETG)"
                elif "author" in kl or "drawn" in kl:
                    et[k] = "FreeCAD Advanced MCP"
            template.EditableTexts = et
    except Exception:
        pass

    view_list = [v.lower().strip() for v in (views or ["front", "top", "isometric"])]
    created_views = []

    # Front View (Elevation)
    if "front" in view_list:
        vf = doc.addObject("TechDraw::DrawViewPart", f"View_Front_{obj.Name}")
        vf.Source = [obj]
        vf.Direction = FreeCAD.Vector(0, -1, 0)
        vf.X = 85.0
        vf.Y = 140.0
        vf.Scale = computed_scale
        page.addView(vf)
        created_views.append("front")

    # Top View (Plan)
    if "top" in view_list:
        vt = doc.addObject("TechDraw::DrawViewPart", f"View_Top_{obj.Name}")
        vt.Source = [obj]
        vt.Direction = FreeCAD.Vector(0, 0, 1)
        vt.X = 85.0
        vt.Y = 65.0
        vt.Scale = computed_scale
        page.addView(vt)
        created_views.append("top")

    # Right Side View
    if "right" in view_list or "side" in view_list:
        vr = doc.addObject("TechDraw::DrawViewPart", f"View_Right_{obj.Name}")
        vr.Source = [obj]
        vr.Direction = FreeCAD.Vector(1, 0, 0)
        vr.X = 165.0
        vr.Y = 140.0
        vr.Scale = computed_scale
        page.addView(vr)
        created_views.append("right")

    # Isometric View
    if "isometric" in view_list or "iso" in view_list:
        vi = doc.addObject("TechDraw::DrawViewPart", f"View_Iso_{obj.Name}")
        vi.Source = [obj]
        vi.Direction = FreeCAD.Vector(1, -1, 1)
        vi.X = 220.0
        vi.Y = 135.0
        vi.Scale = computed_scale * 0.85
        page.addView(vi)
        created_views.append("isometric")

    doc.recompute()

    # Destination output path
    if not output_path:
        out_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_drawings")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{doc.Name}_{obj.Name}_Drawing.{fmt}")
    else:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    try:
        if fmt == "pdf":
            if TechDrawGui and hasattr(TechDrawGui, "exportPageAsPdf"):
                TechDrawGui.exportPageAsPdf(page, output_path)
            else:
                return {"error": "TechDrawGui not available for PDF export in current FreeCAD environment."}
        elif fmt == "svg":
            if TechDrawGui and hasattr(TechDrawGui, "exportPageAsSvg"):
                TechDrawGui.exportPageAsSvg(page, output_path)
            else:
                return {"error": "TechDrawGui not available for SVG export."}
        else:
            return {"error": f"Unsupported drawing format '{format}'. Use 'pdf' or 'svg'."}

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            return {"error": f"Failed to export drawing to '{output_path}'."}

        return {
            "status": "ok",
            "document": doc.Name,
            "object": obj.Name,
            "page_name": page.Name,
            "format": fmt,
            "output_path": output_path,
            "file_size_bytes": os.path.getsize(output_path),
            "scale": computed_scale,
            "views": created_views,
            "bounding_box_mm": [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
        }
    except Exception as exc:
        return {"error": f"TechDraw export error: {exc}"}


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
