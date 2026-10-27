"""Selection inspector and Human-in-the-Loop bridge for FreeCAD MCP."""

import math
import FreeCAD
import FreeCADGui


def _safe_shape_com(shape):
    try:
        c = shape.CenterOfMass
        return [round(c.x, 2), round(c.y, 2), round(c.z, 2)]
    except Exception:
        try:
            bb = shape.BoundBox
            return [round(bb.Center.x, 2), round(bb.Center.y, 2), round(bb.Center.z, 2)]
        except Exception:
            return None


def _safe_shape_volume(shape):
    try:
        return round(shape.Volume, 2)
    except Exception:
        return 0.0


def get_selection():
    """Inspect active user selection in FreeCAD GUI (objects, faces, edges, vertices).

    Returns detailed geometric properties (normals, centers of mass, lengths, areas)
    and TNP-safe query criteria for subsequent modeling operations.
    """
    sel_ex = FreeCADGui.Selection.getSelectionEx()
    if not sel_ex:
        return {
            "status": "ok",
            "has_selection": False,
            "selected_count": 0,
            "message": "No objects or sub-elements currently selected in FreeCAD 3D view.",
        }

    results = []
    for s in sel_ex:
        obj = s.Object
        sub_names = s.SubElementNames
        sub_objs = s.SubObjects

        obj_data = {
            "object_name": obj.Name,
            "object_label": obj.Label,
            "type": obj.TypeId,
            "sub_elements": [],
        }

        if not sub_names:
            # Whole object selected
            shape = getattr(obj, "Shape", None)
            if shape and not shape.isNull():
                bb = shape.BoundBox
                obj_data["bounding_box"] = [
                    round(bb.XLength, 2),
                    round(bb.YLength, 2),
                    round(bb.ZLength, 2),
                ]
                obj_data["center_of_mass"] = _safe_shape_com(shape)
                obj_data["volume_mm3"] = _safe_shape_volume(shape)
            results.append(obj_data)
            continue

        for name, sub in zip(sub_names, sub_objs):
            elem_info = {"name": name, "type": type(sub).__name__}

            if hasattr(sub, "Area"):  # Face
                c = sub.CenterOfMass
                elem_info["area_mm2"] = round(sub.Area, 2)
                elem_info["center_of_mass"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]
                try:
                    norm = sub.normalAt(0, 0)
                    elem_info["normal"] = [round(norm.x, 3), round(norm.y, 3), round(norm.z, 3)]
                    elem_info["surface_type"] = sub.Surface.TypeId
                except Exception:
                    elem_info["normal"] = None

                # Ready-to-use TNP query snippet
                elem_info["tnp_query"] = {
                    "normal": elem_info["normal"],
                    "z_min": round(c.z - 0.5, 2),
                    "z_max": round(c.z + 0.5, 2),
                    "area_min": round(sub.Area * 0.95, 1),
                    "area_max": round(sub.Area * 1.05, 1),
                }

            elif hasattr(sub, "Length"):  # Edge
                mid = sub.valueAt(0.5 * (sub.FirstParameter + sub.LastParameter))
                elem_info["length_mm"] = round(sub.Length, 3)
                elem_info["midpoint"] = [round(mid.x, 3), round(mid.y, 3), round(mid.z, 3)]
                try:
                    t = sub.tangentAt(0.5 * (sub.FirstParameter + sub.LastParameter))[0]
                    elem_info["tangent"] = [round(t.x, 3), round(t.y, 3), round(t.z, 3)]
                    elem_info["curve_type"] = sub.Curve.TypeId
                except Exception:
                    elem_info["tangent"] = None

                # Radius if circular
                if hasattr(sub.Curve, "Radius"):
                    elem_info["radius_mm"] = round(sub.Curve.Radius, 3)

            elif hasattr(sub, "Point"):  # Vertex
                p = sub.Point
                elem_info["point"] = [round(p.x, 3), round(p.y, 3), round(p.z, 3)]

            obj_data["sub_elements"].append(elem_info)

        results.append(obj_data)

    return {
        "status": "ok",
        "has_selection": True,
        "selected_count": len(results),
        "selected_objects": results,
    }
