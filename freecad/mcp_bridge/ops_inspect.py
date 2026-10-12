"""Geometry inspection, document tree, clearance, and 3D print audit for FreeCAD MCP."""

import FreeCAD
import FreeCADGui


def get_document_tree(document_name=None):
    """Return hierarchical tree of document objects, types, errors, and visibility."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    gui_doc = FreeCADGui.getDocument(doc.Name)

    doc_info = {
        "name": doc.Name,
        "label": getattr(doc, "Label", doc.Name),
        "file_path": doc.FileName or None,
        "is_active": FreeCAD.ActiveDocument and (FreeCAD.ActiveDocument.Name == doc.Name),
        "has_errors": getattr(doc, "hasErrors", lambda: False)(),
        "objects_count": len(doc.Objects),
        "bodies": [],
        "other_objects": [],
    }

    body_sub_names = set()
    for obj in doc.Objects:
        if obj.isDerivedFrom("PartDesign::Body"):
            features = []
            tip_name = obj.Tip.Name if hasattr(obj, "Tip") and obj.Tip else None
            for feat in getattr(obj, "Group", []):
                body_sub_names.add(feat.Name)
                f_vo = gui_doc.getObject(feat.Name) if gui_doc else None
                features.append({
                    "name": feat.Name,
                    "label": feat.Label,
                    "type": feat.TypeId,
                    "is_tip": (feat.Name == tip_name),
                    "visible": f_vo.Visibility if f_vo else None,
                    "has_errors": getattr(feat, "hasErrors", lambda: False)(),
                })
            b_vo = gui_doc.getObject(obj.Name) if gui_doc else None
            doc_info["bodies"].append({
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "tip": tip_name,
                "visible": b_vo.Visibility if b_vo else None,
                "features_count": len(features),
                "features": features,
            })

    for obj in doc.Objects:
        if not obj.isDerivedFrom("PartDesign::Body") and obj.Name not in body_sub_names:
            vo = gui_doc.getObject(obj.Name) if gui_doc else None
            doc_info["other_objects"].append({
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "visible": vo.Visibility if vo else None,
                "has_errors": getattr(obj, "hasErrors", lambda: False)(),
            })

    return doc_info


def inspect_geometry(object_name, document_name=None):
    """Compute precision geometry metrics, topology validity, and 3D printing audit."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found in document '{doc.Name}'."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape."}

    bb = shape.BoundBox
    com = _get_robust_com(shape)

    # 3D Print and Topology audit
    is_valid = shape.isValid()
    is_closed = shape.isClosed()
    solids_cnt = len(shape.Solids)
    faces_cnt = len(shape.Faces)
    edges_cnt = len(shape.Edges)
    verts_cnt = len(shape.Vertexes)

    # Edge analysis
    min_edge_len = None
    if edges_cnt > 0:
        edge_lens = [e.Length for e in shape.Edges if e.Length > 1e-6]
        if edge_lens:
            min_edge_len = round(min(edge_lens), 4)

    audit = {
        "manifold_watertight": bool(is_closed and is_valid and solids_cnt > 0),
        "is_valid_opencascade": bool(is_valid),
        "solids_count": solids_cnt,
        "single_solid": (solids_cnt == 1),
        "min_edge_length_mm": min_edge_len,
        "print_volume_fits_256mm_cube": bool(bb.XLength <= 256.0 and bb.YLength <= 256.0 and bb.ZLength <= 256.0),
    }

    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
        "bounding_box": {
            "min": [round(bb.XMin, 4), round(bb.YMin, 4), round(bb.ZMin, 4)],
            "max": [round(bb.XMax, 4), round(bb.YMax, 4), round(bb.ZMax, 4)],
            "size": [round(bb.XLength, 4), round(bb.YLength, 4), round(bb.ZLength, 4)],
            "center": [round(bb.Center.x, 4), round(bb.Center.y, 4), round(bb.Center.z, 4)],
        },
        "volume_mm3": round(shape.Volume, 4),
        "area_mm2": round(shape.Area, 4),
        "center_of_mass": [round(com.x, 4), round(com.y, 4), round(com.z, 4)],
        "topology": {
            "solids": solids_cnt,
            "faces": faces_cnt,
            "edges": edges_cnt,
            "vertices": verts_cnt,
        },
        "manufacturing_audit": audit,
    }


def check_clearance(object1, object2="all", document_name=None, tolerance=0.1):
    """Check spatial interference (collision volume) and clearance distance.

    If object2 is "all" or None, checks object1 against all other solid objects in the document.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    o1 = doc.getObject(object1)
    if not o1:
        return {"error": f"Object 1 '{object1}' not found."}

    s1 = getattr(o1, "Shape", None)
    if s1 is None or s1.isNull():
        return {"error": f"Object 1 '{object1}' has no valid Shape."}

    # If checking against all other objects
    if not object2 or str(object2).strip().lower() == "all":
        # Collect internal sub-feature names from all bodies so we only check top-level solids
        sub_feature_names = set()
        for b in doc.Objects:
            if b.isDerivedFrom("PartDesign::Body"):
                for feat in getattr(b, "Group", []):
                    sub_feature_names.add(feat.Name)

        results = []
        total_clash_vol = 0.0
        min_overall_dist = float("inf")
        has_any_clash = False

        ignored_types = {"App::Line", "App::Plane", "PartDesign::CoordinateSystem", "PartDesign::Plane", "PartDesign::Line"}
        ignored_names = {"X_Axis", "Y_Axis", "Z_Axis", "XY_Plane", "XZ_Plane", "YZ_Plane", "Origin"}

        for candidate in doc.Objects:
            if candidate.Name == o1.Name or candidate.Name in sub_feature_names or candidate.Name in ignored_names:
                continue
            if candidate.TypeId in ignored_types or candidate.isDerivedFrom("Sketcher::SketchObject"):
                continue

            c_shape = getattr(candidate, "Shape", None)
            if c_shape is None or c_shape.isNull() or len(c_shape.Solids) == 0:
                continue

            pair_res = _check_pair(s1, c_shape, float(tolerance))
            if pair_res["has_clash"]:
                has_any_clash = True
                total_clash_vol += pair_res["clash_volume_mm3"]
            if pair_res["clearance_distance_mm"] < min_overall_dist:
                min_overall_dist = pair_res["clearance_distance_mm"]

            results.append({
                "other_object": candidate.Name,
                "other_label": candidate.Label,
                "has_clash": pair_res["has_clash"],
                "clash_volume_mm3": pair_res["clash_volume_mm3"],
                "clearance_distance_mm": pair_res["clearance_distance_mm"],
                "is_touching": pair_res["is_touching"],
            })

        return {
            "status": "ok",
            "target_object": o1.Name,
            "checked_against_count": len(results),
            "has_clash": has_any_clash,
            "total_clash_volume_mm3": round(total_clash_vol, 4),
            "min_clearance_distance_mm": round(min_overall_dist, 4) if min_overall_dist != float("inf") else None,
            "pairs": results,
        }

    # Otherwise check specific pair
    o2 = doc.getObject(object2)
    if not o2:
        return {"error": f"Object 2 '{object2}' not found."}

    s2 = getattr(o2, "Shape", None)
    if s2 is None or s2.isNull():
        return {"error": f"Object 2 '{object2}' has no valid Shape."}

    pair_res = _check_pair(s1, s2, float(tolerance))
    pair_res["status"] = "ok"
    pair_res["object1"] = o1.Name
    pair_res["object2"] = o2.Name
    return pair_res


def _check_pair(s1, s2, tolerance=0.1):
    bb1 = s1.BoundBox
    bb2 = s2.BoundBox
    bb_overlap = not (
        bb1.XMax < bb2.XMin or bb1.XMin > bb2.XMax or
        bb1.YMax < bb2.YMin or bb1.YMin > bb2.YMax or
        bb1.ZMax < bb2.ZMin or bb1.ZMin > bb2.ZMax
    )

    clash_volume = 0.0
    has_clash = False
    if bb_overlap:
        try:
            common = s1.common(s2)
            if not common.isNull():
                clash_volume = common.Volume
                has_clash = (clash_volume > 1e-4)
        except Exception:
            pass

    dist_info = s1.distToShape(s2)
    min_dist = dist_info[0]
    closest_pts = {}
    if len(dist_info) > 1 and dist_info[1] and len(dist_info[1]) > 0:
        first_pair = dist_info[1][0]
        if isinstance(first_pair, (tuple, list)) and len(first_pair) >= 2:
            p1, p2 = first_pair[0], first_pair[1]
            closest_pts = {
                "point_on_object1": [round(p1.x, 4), round(p1.y, 4), round(p1.z, 4)],
                "point_on_object2": [round(p2.x, 4), round(p2.y, 4), round(p2.z, 4)],
            }

    return {
        "has_clash": bool(has_clash),
        "clash_volume_mm3": round(clash_volume, 4),
        "clearance_distance_mm": round(min_dist, 4),
        "is_touching": bool(min_dist <= tolerance),
        "closest_points": closest_pts,
    }


def _get_robust_com(shape):
    if hasattr(shape, "Solids") and len(shape.Solids) > 0:
        tot_v = sum(s.Volume for s in shape.Solids)
        if tot_v > 1e-6:
            return FreeCAD.Vector(
                sum(s.CenterOfMass.x * s.Volume for s in shape.Solids) / tot_v,
                sum(s.CenterOfMass.y * s.Volume for s in shape.Solids) / tot_v,
                sum(s.CenterOfMass.z * s.Volume for s in shape.Solids) / tot_v,
            )
    try:
        return shape.CenterOfMass
    except Exception:
        return shape.BoundBox.Center


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
