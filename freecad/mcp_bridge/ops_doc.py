"""Document lifecycle, transactions, recompute, and undo/redo operations for FreeCAD MCP."""

import FreeCAD
import FreeCADGui


def manage_document(action="list", document_name=None, file_path=None):
    """Manage FreeCAD documents: list, new, open, save, close, set_active, recompute."""
    act = (action or "list").strip().lower()

    if act == "list":
        docs = []
        for name, d in FreeCAD.listDocuments().items():
            docs.append({
                "name": name,
                "label": getattr(d, "Label", name),
                "file_path": d.FileName or None,
                "is_active": FreeCAD.ActiveDocument and (FreeCAD.ActiveDocument.Name == name),
                "objects_count": len(d.Objects),
            })
        return {
            "status": "ok",
            "active_document": FreeCAD.ActiveDocument.Name if FreeCAD.ActiveDocument else None,
            "documents": docs,
        }

    if act == "new":
        name = document_name or "Unnamed"
        doc = FreeCAD.newDocument(name)
        return {
            "status": "ok",
            "action": "new",
            "document": doc.Name,
        }

    if act == "open":
        if not file_path:
            return {"error": "Parameter 'file_path' is required for 'open' action."}
        doc = FreeCAD.openDocument(file_path)
        return {
            "status": "ok",
            "action": "open",
            "document": doc.Name,
            "file_path": file_path,
        }

    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": f"Document '{document_name or active}' not found."}

    if act == "save":
        if file_path:
            doc.saveCopy(file_path)
            saved_to = file_path
        else:
            doc.save()
            saved_to = doc.FileName
        return {
            "status": "ok",
            "action": "save",
            "document": doc.Name,
            "saved_to": saved_to,
        }

    if act == "close":
        doc_name = doc.Name
        FreeCAD.closeDocument(doc_name)
        return {
            "status": "ok",
            "action": "close",
            "document": doc_name,
        }

    if act == "set_active":
        FreeCAD.setActiveDocument(doc)
        if FreeCADGui.getDocument(doc.Name):
            FreeCADGui.setActiveDocument(doc)
        return {
            "status": "ok",
            "action": "set_active",
            "document": doc.Name,
        }

    if act == "recompute":
        count = doc.recompute()
        has_err = getattr(doc, "hasErrors", lambda: False)()
        return {
            "status": "ok",
            "action": "recompute",
            "document": doc.Name,
            "recomputed_features": count,
            "has_errors": has_err,
        }

    return {"error": f"Unknown document action '{action}'."}


def undo_redo(action="undo", document_name=None):
    """Perform undo or redo operation on document."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    act = (action or "undo").strip().lower()
    if act == "undo":
        doc.undo()
    elif act == "redo":
        doc.redo()
    else:
        return {"error": f"Unknown action '{action}'. Use 'undo' or 'redo'."}

    doc.recompute()
    return {
        "status": "ok",
        "action": act,
        "document": doc.Name,
        "objects_count": len(doc.Objects),
    }


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
