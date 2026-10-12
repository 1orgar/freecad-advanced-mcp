"""Production export (STL, STEP, 3MF, DXF) for FreeCAD MCP."""

import os
import FreeCAD
import Part
import Mesh
import MeshPart


def export_geometry(
    object_name,
    format="stl",
    output_path=None,
    document_name=None,
    linear_deflection=0.05,
    angular_deflection=0.5,
):
    """Export 3D object to production formats (STL, STEP, 3MF, DXF) with precision control."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found in document '{doc.Name}'."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape to export."}

    fmt = (format or "stl").strip().lower()

    if not output_path:
        export_dir = os.path.join(FreeCAD.getUserAppDataDir(), "mcp_exports")
        os.makedirs(export_dir, exist_ok=True)
        ext = fmt if fmt in ("stl", "step", "stp", "3mf", "dxf") else "stl"
        output_path = os.path.join(export_dir, f"{doc.Name}_{obj.Name}.{ext}")
    else:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    try:
        if fmt in ("stl", "3mf"):
            # High-precision mesh generation tailored for slicers
            mesh = MeshPart.meshFromShape(
                Shape=shape,
                LinearDeflection=float(linear_deflection),
                AngularDeflection=float(angular_deflection),
                Relative=False,
            )
            mesh.write(output_path)
        elif fmt in ("step", "stp"):
            Part.export([shape], output_path)
        elif fmt == "dxf":
            try:
                import Import
                Import.export([obj], output_path)
            except Exception:
                Part.export([shape], output_path)
        else:
            return {"error": f"Unsupported export format '{format}'. Use stl, step, 3mf, or dxf."}

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            return {"error": f"Export failed: file '{output_path}' was not created."}

        return {
            "status": "ok",
            "document": doc.Name,
            "object": obj.Name,
            "format": fmt,
            "output_path": output_path,
            "file_size_bytes": os.path.getsize(output_path),
            "parameters": {
                "linear_deflection": float(linear_deflection),
                "angular_deflection": float(angular_deflection),
            } if fmt in ("stl", "3mf") else {},
        }
    except Exception as exc:
        return {"error": f"Export error: {exc}"}


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
