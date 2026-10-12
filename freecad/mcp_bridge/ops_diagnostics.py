"""Comprehensive tree diagnostics, constraint audit, and health scoring for FreeCAD MCP."""

import FreeCAD


def diagnose_document(document_name=None):
    """Perform a deep health and geometric integrity audit on a FreeCAD document."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    issues = []
    sketches_audit = []
    bodies_audit = []
    shapes_audit = []

    for obj in doc.Objects:
        # Check object recompute state
        state = getattr(obj, "State", [])
        state_list = [str(s) for s in state] if isinstance(state, (list, tuple)) else [str(state)]
        has_error = any("error" in s.lower() or "recomputefailed" in s.lower() for s in state_list)
        if has_error:
            issues.append({
                "severity": "ERROR",
                "object": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "message": f"Object failed recomputation or is in error state: {state_list}",
            })

        # Deep audit for Sketcher sketches
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            dof = getattr(obj, "DoF", 0)
            conflicts = list(getattr(obj, "ConflictingConstraints", []))
            redundant = list(getattr(obj, "RedundantConstraints", []))
            malformed = list(getattr(obj, "MalformedConstraints", []))
            cnt_c = getattr(obj, "ConstraintCount", 0)
            cnt_g = getattr(obj, "GeometryCount", 0)

            sk_status = "FULLY_CONSTRAINED"
            if conflicts or malformed:
                sk_status = "CONFLICT"
                issues.append({
                    "severity": "ERROR",
                    "object": obj.Name,
                    "label": obj.Label,
                    "type": "Sketch",
                    "message": f"Sketch has {len(conflicts)} conflicting and {len(malformed)} malformed constraints.",
                })
            elif dof > 0:
                sk_status = "UNDERCONSTRAINED"
                issues.append({
                    "severity": "WARNING",
                    "object": obj.Name,
                    "label": obj.Label,
                    "type": "Sketch",
                    "message": f"Sketch is underconstrained ({dof} degrees of freedom missing).",
                })
            elif redundant:
                sk_status = "REDUNDANT"
                issues.append({
                    "severity": "INFO",
                    "object": obj.Name,
                    "label": obj.Label,
                    "type": "Sketch",
                    "message": f"Sketch has {len(redundant)} redundant constraints.",
                })

            sketches_audit.append({
                "name": obj.Name,
                "label": obj.Label,
                "status": sk_status,
                "degrees_of_freedom": dof,
                "constraints_count": cnt_c,
                "geometries_count": cnt_g,
                "conflicts": conflicts,
                "redundant": redundant,
            })

        # PartDesign Body audit
        if obj.isDerivedFrom("PartDesign::Body"):
            tip = getattr(obj, "Tip", None)
            tip_name = tip.Name if tip else None
            tip_err = getattr(tip, "hasErrors", lambda: False)() if tip else False
            features = getattr(obj, "Group", [])

            if not tip:
                issues.append({
                    "severity": "WARNING",
                    "object": obj.Name,
                    "label": obj.Label,
                    "type": "Body",
                    "message": "Body has no active Tip assigned.",
                })

            bodies_audit.append({
                "name": obj.Name,
                "label": obj.Label,
                "tip": tip_name,
                "tip_has_errors": bool(tip_err),
                "features_count": len(features),
            })

        # Shape integrity audit
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            is_valid = shape.isValid()
            if not is_valid:
                issues.append({
                    "severity": "ERROR",
                    "object": obj.Name,
                    "label": obj.Label,
                    "type": "Shape",
                    "message": "OpenCASCADE BRepCheck report: Shape has geometric defects or invalid topology.",
                })

    # Overall document rating
    errors_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warnings_count = sum(1 for i in issues if i["severity"] == "WARNING")

    if errors_count > 0:
        overall_health = "ERROR"
    elif warnings_count > 0:
        overall_health = "WARNING"
    else:
        overall_health = "CLEAN"

    return {
        "status": "ok",
        "document": doc.Name,
        "overall_health": overall_health,
        "summary": {
            "total_objects": len(doc.Objects),
            "errors_count": errors_count,
            "warnings_count": warnings_count,
            "issues_count": len(issues),
            "sketches_count": len(sketches_audit),
            "bodies_count": len(bodies_audit),
        },
        "issues": issues,
        "sketches": sketches_audit,
        "bodies": bodies_audit,
    }


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
