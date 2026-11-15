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


# ==============================================================================
# High-Speed Solid Modeling & TNP-Safe Dress-up Helpers
# ==============================================================================

def rounded_box(lx, ly, lz, r_xy=2.0, center_xy=True, center_z=False, radius=None, corner_radius=None):
    """Create a box with analytic rounded vertical corners (zero fillet failure risk).

    Parameters:
    - lx, ly, lz: Dimensions in mm along X, Y, Z.
    - r_xy (or radius / corner_radius): Corner radius on vertical Z edges.
    - center_xy: If True (default), centers X and Y at origin (0, 0).
    - center_z: If True, centers Z at 0 (-lz/2 to +lz/2); otherwise Z goes 0 to lz.
    """
    if radius is not None:
        r_xy = radius
    elif corner_radius is not None:
        r_xy = corner_radius
    w, h, d = float(lx), float(ly), float(lz)
    z0 = -d / 2.0 if center_z else 0.0
    x_off = 0.0 if center_xy else w / 2.0
    y_off = 0.0 if center_xy else h / 2.0

    r = min(float(r_xy), min(w, h) / 2.0 - 0.05)
    if r <= 0.05:
        return Part.makeBox(w, h, d, FreeCAD.Vector(x_off - w / 2.0, y_off - h / 2.0, z0))

    hw = (w - 2.0 * r) / 2.0
    hh = (h - 2.0 * r) / 2.0

    p1 = FreeCAD.Vector(x_off - hw, y_off - h / 2.0, z0)
    p2 = FreeCAD.Vector(x_off + hw, y_off - h / 2.0, z0)
    p3 = FreeCAD.Vector(x_off + w / 2.0, y_off - hh, z0)
    p4 = FreeCAD.Vector(x_off + w / 2.0, y_off + hh, z0)
    p5 = FreeCAD.Vector(x_off + hw, y_off + h / 2.0, z0)
    p6 = FreeCAD.Vector(x_off - hw, y_off + h / 2.0, z0)
    p7 = FreeCAD.Vector(x_off - w / 2.0, y_off + hh, z0)
    p8 = FreeCAD.Vector(x_off - w / 2.0, y_off - hh, z0)

    z_axis = FreeCAD.Vector(0, 0, 1)
    a1 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(x_off + hw, y_off - hh, z0), z_axis, r), -math.pi / 2, 0)
    a2 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(x_off + hw, y_off + hh, z0), z_axis, r), 0, math.pi / 2)
    a3 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(x_off - hw, y_off + hh, z0), z_axis, r), math.pi / 2, math.pi)
    a4 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(x_off - hw, y_off - hh, z0), z_axis, r), math.pi, 3 * math.pi / 2)

    wire = Part.Wire([
        Part.LineSegment(p1, p2).toShape(), a1.toShape(),
        Part.LineSegment(p3, p4).toShape(), a2.toShape(),
        Part.LineSegment(p5, p6).toShape(), a3.toShape(),
        Part.LineSegment(p7, p8).toShape(), a4.toShape(),
    ])
    return Part.Face(wire).extrude(FreeCAD.Vector(0, 0, d))


def safe_fillet(shape, radius=1.0, edges=None, direction=None, length_min=None, length_max=None, z_min=None, z_max=None, z_level=None):
    """Apply TNP-safe fillet with automatic fallback if OpenCASCADE kernel rejects radius.

    If target radius is too large for local geometry, automatically tries 75% and 50%
    radius or filters edges individually so script execution never crashes.
    """
    if z_level is not None:
        z_min = float(z_level) - 0.1
        z_max = float(z_level) + 0.1
    target_edges = edges if edges is not None else find_edges(
        shape, direction=direction, length_min=length_min, length_max=length_max, z_min=z_min, z_max=z_max
    )
    if not target_edges:
        return shape

    r = float(radius)
    for factor in (1.0, 0.75, 0.5):
        try:
            res = shape.makeFillet(r * factor, target_edges)
            if res and not res.isNull() and res.isValid():
                return res
        except Exception:
            pass
    return shape


def safe_chamfer(shape, size=0.5, edges=None, direction=None, length_min=None, length_max=None, z_min=None, z_max=None, z_level=None, distance=None):
    """Apply TNP-safe chamfer with automatic fallback if OpenCASCADE kernel rejects size."""
    if distance is not None:
        size = distance
    if z_level is not None:
        z_min = float(z_level) - 0.1
        z_max = float(z_level) + 0.1
    target_edges = edges if edges is not None else find_edges(
        shape, direction=direction, length_min=length_min, length_max=length_max, z_min=z_min, z_max=z_max
    )
    if not target_edges:
        return shape

    s = float(size)
    for factor in (1.0, 0.75, 0.5):
        try:
            res = shape.makeChamfer(s * factor, target_edges)
            if res and not res.isNull() and res.isValid():
                return res
        except Exception:
            pass
    return shape


def boolean_chain(base_shape, cuts=(), fuses=(), refine=True, add=(), cut=()):
    """Execute batch boolean fuses and cuts with optional splitter refinement.

    Removing coplanar splitter edges (refine=True) prevents subsequent fillets/chamfers
    from failing on residual seam lines.
    """
    res = base_shape
    all_fuses = list(fuses) + list(add)
    all_cuts = list(cuts) + list(cut)
    for f_shape in all_fuses:
        if f_shape is not None and not f_shape.isNull():
            res = res.fuse(f_shape)
    if all_cuts:
        valid_cuts = [c for c in all_cuts if c is not None and not c.isNull()]
        if len(valid_cuts) == 1:
            res = res.cut(valid_cuts[0])
        elif len(valid_cuts) > 1:
            res = res.cut(Part.Compound(valid_cuts))
    if refine and hasattr(res, "removeSplitter"):
        try:
            refined = res.removeSplitter()
            if refined and not refined.isNull() and refined.isValid():
                res = refined
        except Exception:
            pass
    return res


def linear_pattern(shape, step_vec=None, count=1, center=False, direction_x=None, count_x=1, direction_y=None, count_y=1):
    """Create a 1D or 2D linear pattern of shapes."""
    if direction_x is not None or direction_y is not None:
        nx = max(1, int(count_x))
        ny = max(1, int(count_y))
        dx = direction_x if direction_x is not None else (0, 0, 0)
        dy = direction_y if direction_y is not None else (0, 0, 0)
        sx1, sy1, sz1 = float(dx[0]), float(dx[1]), float(dx[2])
        sx2, sy2, sz2 = float(dy[0]), float(dy[1]), float(dy[2])
        ox = (-sx1 * (nx - 1) - sx2 * (ny - 1)) / 2.0 if center else 0.0
        oy = (-sy1 * (nx - 1) - sy2 * (ny - 1)) / 2.0 if center else 0.0
        oz = (-sz1 * (nx - 1) - sz2 * (ny - 1)) / 2.0 if center else 0.0
        items = []
        for ix in range(nx):
            for iy in range(ny):
                c = shape.copy()
                c.translate(FreeCAD.Vector(
                    ox + ix * sx1 + iy * sx2,
                    oy + ix * sy1 + iy * sy2,
                    oz + ix * sz1 + iy * sz2,
                ))
                items.append(c)
        return Part.Compound(items)

    n = int(count)
    if n <= 1 or step_vec is None:
        return shape.copy()
    sx, sy, sz = float(step_vec[0]), float(step_vec[1]), float(step_vec[2])
    start_x = -sx * (n - 1) / 2.0 if center else 0.0
    start_y = -sy * (n - 1) / 2.0 if center else 0.0
    start_z = -sz * (n - 1) / 2.0 if center else 0.0

    items = []
    for i in range(n):
        c = shape.copy()
        c.translate(FreeCAD.Vector(start_x + i * sx, start_y + i * sy, start_z + i * sz))
        items.append(c)
    return Part.Compound(items)


def polar_pattern(shape, count, angle_deg=360.0, center_pt=(0, 0, 0), axis=(0, 0, 1)):
    """Create a polar (circular) pattern of shapes around center_pt and axis."""
    n = int(count)
    if n <= 1:
        return shape.copy()
    tot_ang = float(angle_deg)
    step = tot_ang / n if abs(tot_ang - 360.0) < 1e-3 else tot_ang / (n - 1)
    c_vec = FreeCAD.Vector(*center_pt)
    a_vec = FreeCAD.Vector(*axis)

    items = []
    for i in range(n):
        c = shape.copy()
        if i > 0:
            c.rotate(c_vec, a_vec, i * step)
        items.append(c)
    return Part.Compound(items)


_FACE_DIR_MAP = {
    "+Z": (0, 0, 1), "-Z": (0, 0, -1),
    "+Y": (0, 1, 0), "-Y": (0, -1, 0),
    "+X": (1, 0, 0), "-X": (-1, 0, 0),
}


def shell_solid(shape, thickness=-2.0, open_face_normal=(0, 0, 1), open_faces=None, tol=1e-3):
    """Hollow out a solid into a thin-walled enclosure by removing open face(s).

    Negative thickness hollows inwards; positive thickness expands outwards.
    Accepts open_face_normal=(nx,ny,nz) or open_faces=["+Z", "-Z", ...].
    """
    faces_to_remove = []
    if open_faces:
        for spec in open_faces:
            norm = _FACE_DIR_MAP.get(str(spec).upper(), spec) if isinstance(spec, str) else spec
            f = find_face(shape, normal=norm, tol=tol)
            if f is not None:
                faces_to_remove.append(f)
    else:
        norm = _FACE_DIR_MAP.get(str(open_face_normal).upper(), open_face_normal) if isinstance(open_face_normal, str) else open_face_normal
        f = find_face(shape, normal=norm, tol=tol)
        if f is not None:
            faces_to_remove.append(f)

    if not faces_to_remove:
        return shape
    try:
        res = shape.makeThickness(faces_to_remove, float(thickness), 1e-3)
        if res and not res.isNull() and res.isValid():
            return res
    except Exception:
        pass
    return shape


def align_to(shape_to_move, target_shape, align_x="center", align_y="center", align_z="stack_top", offset=(0, 0, 0)):
    """Align shape_to_move relative to target_shape's BoundingBox.

    Modes for each axis:
    - "min": Aligns min bounds (flush left/front/bottom)
    - "center": Aligns centers
    - "max": Aligns max bounds (flush right/back/top)
    - "stack_max" / "stack_top": Places shape_to_move's min flush against target_shape's max
    - "stack_min" / "stack_bottom": Places shape_to_move's max flush against target_shape's min
    - None: Leaves axis untouched
    """
    moved = shape_to_move.copy()
    bb_src = moved.BoundBox
    bb_tgt = target_shape.BoundBox

    def _calc_delta(src_min, src_max, src_c, tgt_min, tgt_max, tgt_c, mode):
        if not mode:
            return 0.0
        m = str(mode).lower().strip()
        if m == "center":
            return tgt_c - src_c
        elif m == "min":
            return tgt_min - src_min
        elif m == "max":
            return tgt_max - src_max
        elif m in ("stack_max", "stack_top", "above"):
            return tgt_max - src_min
        elif m in ("stack_min", "stack_bottom", "below"):
            return tgt_min - src_max
        return 0.0

    dx = _calc_delta(bb_src.XMin, bb_src.XMax, bb_src.Center.x, bb_tgt.XMin, bb_tgt.XMax, bb_tgt.Center.x, align_x)
    dy = _calc_delta(bb_src.YMin, bb_src.YMax, bb_src.Center.y, bb_tgt.YMin, bb_tgt.YMax, bb_tgt.Center.y, align_y)
    dz = _calc_delta(bb_src.ZMin, bb_src.ZMax, bb_src.Center.z, bb_tgt.ZMin, bb_tgt.ZMax, bb_tgt.Center.z, align_z)

    ox, oy, oz = float(offset[0]), float(offset[1]), float(offset[2])
    moved.translate(FreeCAD.Vector(dx + ox, dy + oy, dz + oz))
    return moved
