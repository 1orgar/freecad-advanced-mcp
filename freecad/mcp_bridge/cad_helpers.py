"""TNP-safe geometric query and modeling helpers for FreeCAD MCP.

These utilities prevent Topological Naming Problems (TNP) by querying faces and
edges by geometric orientation and spatial bounds rather than unstable topological indexes.
Also provides fully constrained 2D sketch primitive builders.
"""

import math
import FreeCAD
import Part
import Sketcher


def find_face(shape, normal=None, z_min=None, z_max=None, x_min=None, x_max=None,
              y_min=None, y_max=None, area_min=None, area_max=None, tol=1e-3):
    """Find the best-matching face on a shape by geometric criteria.

    Parameters:
    - shape: Part.Shape to query.
    - normal: (nx, ny, nz) tuple. Compares face normal at parameter center.
    - z_min, z_max: Bounds for face center Z coordinate.
    - x_min, x_max: Bounds for face center X coordinate.
    - y_min, y_max: Bounds for face center Y coordinate.
    - area_min, area_max: Bounds for face area in mm2.
    - tol: Tolerance for vector and bounding checks.

    Returns the matching Part.Face or None.
    """
    candidates = []
    if normal is not None:
        n_len = math.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        target_n = (normal[0] / n_len, normal[1] / n_len, normal[2] / n_len)
    else:
        target_n = None

    for f in shape.Faces:
        # Check area
        if area_min is not None and f.Area < (area_min - tol):
            continue
        if area_max is not None and f.Area > (area_max + tol):
            continue

        # Check center of mass coordinates
        c = f.CenterOfMass
        if z_min is not None and c.z < (z_min - tol):
            continue
        if z_max is not None and c.z > (z_max + tol):
            continue
        if x_min is not None and c.x < (x_min - tol):
            continue
        if x_max is not None and c.x > (x_max + tol):
            continue
        if y_min is not None and c.y < (y_min - tol):
            continue
        if y_max is not None and c.y > (y_max + tol):
            continue

        # Check normal
        if target_n is not None:
            try:
                fn = f.normalAt(0, 0)
                dot = fn.x * target_n[0] + fn.y * target_n[1] + fn.z * target_n[2]
                if abs(dot - 1.0) > 0.05:  # within ~18 degrees
                    continue
            except Exception:
                continue

        candidates.append(f)

    if not candidates:
        return None
    # If multiple candidates, pick the largest by area
    candidates.sort(key=lambda item: item.Area, reverse=True)
    return candidates[0]


def find_edges(shape, direction=None, length_min=None, length_max=None,
               z_min=None, z_max=None, tol=1e-3):
    """Find edges matching geometric orientation and size criteria.

    Parameters:
    - shape: Part.Shape to query.
    - direction: "X", "Y", "Z", or (dx, dy, dz) vector.
    - length_min, length_max: Bounds for edge length in mm.
    - z_min, z_max: Bounds for edge midpoint Z coordinate.
    """
    matched = []
    dir_vec = None
    if isinstance(direction, str):
        d = direction.upper()
        if d == "X":
            dir_vec = (1.0, 0.0, 0.0)
        elif d == "Y":
            dir_vec = (0.0, 1.0, 0.0)
        elif d == "Z":
            dir_vec = (0.0, 0.0, 1.0)
    elif direction is not None:
        v_len = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
        if v_len > 1e-6:
            dir_vec = (direction[0] / v_len, direction[1] / v_len, direction[2] / v_len)

    for e in shape.Edges:
        l = e.Length
        if length_min is not None and l < (length_min - tol):
            continue
        if length_max is not None and l > (length_max + tol):
            continue

        mid = e.valueAt(0.5 * (e.FirstParameter + e.LastParameter))
        if z_min is not None and mid.z < (z_min - tol):
            continue
        if z_max is not None and mid.z > (z_max + tol):
            continue

        if dir_vec is not None and hasattr(e, "tangentAt"):
            try:
                t = e.tangentAt(0.5 * (e.FirstParameter + e.LastParameter))[0]
                dot = abs(t.x * dir_vec[0] + t.y * dir_vec[1] + t.z * dir_vec[2])
                if dot < 0.95:
                    continue
            except Exception:
                continue

        matched.append(e)

    return matched


def add_rigid_rect(sketch, cx, cy, w, h):
    """Add a fully constrained centered rectangle to a Sketcher sketch.

    Eliminates all unconstrained degrees of freedom (DoF = 0).
    """
    hw, hh = w / 2.0, h / 2.0
    p1 = FreeCAD.Vector(cx - hw, cy - hh, 0)
    p2 = FreeCAD.Vector(cx + hw, cy - hh, 0)
    p3 = FreeCAD.Vector(cx + hw, cy + hh, 0)
    p4 = FreeCAD.Vector(cx - hw, cy + hh, 0)

    start_idx = sketch.GeometryCount

    sketch.addGeometry(Part.LineSegment(p1, p2), False)
    sketch.addGeometry(Part.LineSegment(p2, p3), False)
    sketch.addGeometry(Part.LineSegment(p3, p4), False)
    sketch.addGeometry(Part.LineSegment(p4, p1), False)

    # 4 coincidences
    sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx, 2, start_idx + 1, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 1, 2, start_idx + 2, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 2, 2, start_idx + 3, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 3, 2, start_idx, 1))

    # Horizontal and vertical
    sketch.addConstraint(Sketcher.Constraint("Horizontal", start_idx))
    sketch.addConstraint(Sketcher.Constraint("Vertical", start_idx + 1))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", start_idx + 2))
    sketch.addConstraint(Sketcher.Constraint("Vertical", start_idx + 3))

    # Dimensions
    sketch.addConstraint(Sketcher.Constraint("DistanceX", start_idx, 1, start_idx, 2, float(w)))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", start_idx + 1, 1, start_idx + 1, 2, float(h)))

    # Centering positions relative to sketch origin
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, start_idx, 1, float(cx - hw)))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, start_idx, 1, float(cy - hh)))


def add_slot(sketch, cx, cy, length, width, vertical=False):
    """Add a fully constrained stadium slot (2 parallel lines, 2 semicircles)."""
    r = width / 2.0
    half_dist = (length - width) / 2.0
    start_idx = sketch.GeometryCount

    if not vertical:
        c_left = FreeCAD.Vector(cx - half_dist, cy, 0)
        c_right = FreeCAD.Vector(cx + half_dist, cy, 0)

        # Bottom line (left to right)
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(cx - half_dist, cy - r, 0),
                                            FreeCAD.Vector(cx + half_dist, cy - r, 0)), False)
        # Right arc
        sketch.addGeometry(Part.ArcOfCircle(Part.Circle(c_right, FreeCAD.Vector(0,0,1), r), -math.pi/2, math.pi/2), False)
        # Top line (right to left)
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(cx + half_dist, cy + r, 0),
                                            FreeCAD.Vector(cx - half_dist, cy + r, 0)), False)
        # Left arc
        sketch.addGeometry(Part.ArcOfCircle(Part.Circle(c_left, FreeCAD.Vector(0,0,1), r), math.pi/2, 3*math.pi/2), False)

        # Coincidences
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx, 2, start_idx + 1, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 1, 2, start_idx + 2, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 2, 2, start_idx + 3, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 3, 2, start_idx, 1))

        sketch.addConstraint(Sketcher.Constraint("Horizontal", start_idx))
        sketch.addConstraint(Sketcher.Constraint("Horizontal", start_idx + 2))
        sketch.addConstraint(Sketcher.Constraint("Radius", start_idx + 1, float(r)))
        sketch.addConstraint(Sketcher.Constraint("DistanceX", start_idx, 1, start_idx, 2, float(length - width)))
        sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, start_idx, 1, float(cx - half_dist)))
        sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, start_idx, 1, float(cy - r)))
    else:
        c_bottom = FreeCAD.Vector(cx, cy - half_dist, 0)
        c_top = FreeCAD.Vector(cx, cy + half_dist, 0)

        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(cx + r, cy - half_dist, 0),
                                            FreeCAD.Vector(cx + r, cy + half_dist, 0)), False)
        sketch.addGeometry(Part.ArcOfCircle(Part.Circle(c_top, FreeCAD.Vector(0,0,1), r), 0, math.pi), False)
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(cx - r, cy + half_dist, 0),
                                            FreeCAD.Vector(cx - r, cy - half_dist, 0)), False)
        sketch.addGeometry(Part.ArcOfCircle(Part.Circle(c_bottom, FreeCAD.Vector(0,0,1), r), math.pi, 2*math.pi), False)

        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx, 2, start_idx + 1, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 1, 2, start_idx + 2, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 2, 2, start_idx + 3, 1))
        sketch.addConstraint(Sketcher.Constraint("Coincident", start_idx + 3, 2, start_idx, 1))

        sketch.addConstraint(Sketcher.Constraint("Vertical", start_idx))
        sketch.addConstraint(Sketcher.Constraint("Vertical", start_idx + 2))
        sketch.addConstraint(Sketcher.Constraint("Radius", start_idx + 1, float(r)))
        sketch.addConstraint(Sketcher.Constraint("DistanceY", start_idx, 1, start_idx, 2, float(length - width)))
        sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, start_idx, 1, float(cx + r)))
        sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, start_idx, 1, float(cy - half_dist)))
