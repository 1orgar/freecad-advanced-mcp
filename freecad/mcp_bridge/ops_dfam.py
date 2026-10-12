"""DfAM (Design for Additive Manufacturing) engineering analysis for FreeCAD MCP.

Provides stability and tipping angle analysis, 3D printing overhang detection,
and automated fastener/hole inspection.
"""

import math
import collections
import FreeCAD
import Part


def analyze_stability(
    object_name,
    document_name=None,
    base_plane="XY",
    z_tolerance=0.5,
    density_g_cm3=1.25,
    payload_mass_kg=0.0,
    payload_center_of_mass=None,
):
    """Compute physical stability, base support polygon, and tipping angles.

    Parameters:
    - object_name: Target solid or compound object name.
    - document_name: Optional FreeCAD document name.
    - base_plane: Support plane ("XY", "XZ", "YZ"). Default "XY" (Z is vertical).
    - z_tolerance: Tolerance in mm from minimum plane level to consider contact points.
    - density_g_cm3: Material density for mass calculation (default 1.25 for PETG/PLA).
    - payload_mass_kg: Optional weight of placed item (e.g. smartphone 0.205 kg).
    - payload_center_of_mass: [x, y, z] coordinates of payload center of mass in mm.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape."}

    bb = shape.BoundBox
    z_base = bb.ZMin

    # Extract contact points near the base
    contact_pts = []
    for v in shape.Vertexes:
        if abs(v.Z - z_base) <= float(z_tolerance):
            contact_pts.append((round(v.X, 3), round(v.Y, 3)))

    if not contact_pts:
        return {"error": "No base contact points found within tolerance."}

    # Compute 2D Convex Hull of base contact points
    hull = _convex_hull(contact_pts)
    if len(hull) < 3:
        return {
            "status": "unstable",
            "is_stable": False,
            "error": "Insufficient contact points to form a stable 2D base polygon.",
            "contact_points_count": len(contact_pts),
        }

    hull_area = _polygon_area(hull)

    # Object center of mass and mass
    obj_com = _get_shape_com(shape)
    volume_mm3 = shape.Volume
    obj_mass_kg = (volume_mm3 * float(density_g_cm3)) / 1e6

    # Calculate combined center of mass if payload is specified
    payload_m = float(payload_mass_kg or 0.0)
    if payload_m > 0 and payload_center_of_mass and len(payload_center_of_mass) == 3:
        p_com = FreeCAD.Vector(*payload_center_of_mass)
        total_mass = obj_mass_kg + payload_m
        eff_com = FreeCAD.Vector(
            (obj_com.x * obj_mass_kg + p_com.x * payload_m) / total_mass,
            (obj_com.y * obj_mass_kg + p_com.y * payload_m) / total_mass,
            (obj_com.z * obj_mass_kg + p_com.z * payload_m) / total_mass,
        )
    else:
        total_mass = obj_mass_kg
        eff_com = obj_com

    # Height above base
    h = eff_com.z - z_base
    if h <= 0.01:
        h = 0.01

    # Check stability and calculate tipping angles over each edge of the convex hull
    is_stable = True
    tipping_angles = []
    edges_count = len(hull)

    for i in range(edges_count):
        p1 = hull[i]
        p2 = hull[(i + 1) % edges_count]
        # Edge vector
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        edge_len = math.hypot(dx, dy)
        if edge_len < 1e-6:
            continue

        # Outward unit normal for CCW polygon: (dy, -dx) / len
        nx = dy / edge_len
        ny = -dx / edge_len

        # Vector from p1 to CoM
        vx = eff_com.x - p1[0]
        vy = eff_com.y - p1[1]

        # Outward projection: positive means CoM is outside the hull
        proj_out = vx * nx + vy * ny
        dist_to_edge = -proj_out  # positive when inside

        if dist_to_edge < 0:
            is_stable = False
            angle_deg = 0.0
        else:
            angle_deg = math.degrees(math.atan(dist_to_edge / h))

        tipping_angles.append({
            "edge": [list(p1), list(p2)],
            "normal": [round(nx, 3), round(ny, 3)],
            "dist_to_edge_mm": round(dist_to_edge, 2),
            "tipping_angle_deg": round(angle_deg, 2),
        })

    # Find minimum and directional tipping angles
    min_tip = min((e["tipping_angle_deg"] for e in tipping_angles), default=0.0)

    # Classify directional tipping:
    # Forward: normal closest to +Y (ny > 0.5)
    # Backward: normal closest to -Y (ny < -0.5)
    # Left: normal closest to -X (nx < -0.5)
    # Right: normal closest to +X (nx > 0.5)
    def _find_dir_tip(filter_fn):
        filtered = [e["tipping_angle_deg"] for e in tipping_angles if filter_fn(e["normal"])]
        return min(filtered) if filtered else None

    forward_tip = _find_dir_tip(lambda n: n[1] > 0.4)
    backward_tip = _find_dir_tip(lambda n: n[1] < -0.4)
    left_tip = _find_dir_tip(lambda n: n[0] < -0.4)
    right_tip = _find_dir_tip(lambda n: n[0] > 0.4)

    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "is_stable": is_stable,
        "base_support": {
            "z_level_mm": round(z_base, 2),
            "contact_points_count": len(contact_pts),
            "hull_vertices_count": len(hull),
            "support_area_mm2": round(hull_area, 2),
            "hull_polygon": hull,
        },
        "mass_and_center": {
            "object_mass_g": round(obj_mass_kg * 1000.0, 1),
            "payload_mass_g": round(payload_m * 1000.0, 1),
            "total_mass_g": round(total_mass * 1000.0, 1),
            "effective_center_of_mass": [round(eff_com.x, 2), round(eff_com.y, 2), round(eff_com.z, 2)],
            "height_above_base_mm": round(h, 2),
        },
        "tipping_analysis": {
            "min_tipping_angle_deg": round(min_tip, 2),
            "backward_tipping_angle_deg": backward_tip,
            "forward_tipping_angle_deg": forward_tip,
            "left_tipping_angle_deg": left_tip,
            "right_tipping_angle_deg": right_tip,
            "safety_rating": "EXCELLENT" if min_tip > 25 else ("GOOD" if min_tip > 15 else ("MARGINAL" if min_tip > 5 else "UNSTABLE")),
        },
    }


def check_overhangs(
    object_name,
    document_name=None,
    max_overhang_angle=45.0,
    print_direction=(0, 0, 1),
    linear_deflection=0.5,
):
    """Analyze downward-facing surfaces to detect 3D print overhangs needing support.

    Parameters:
    - object_name: Target solid name.
    - document_name: Optional FreeCAD document name.
    - max_overhang_angle: Threshold angle to horizontal in degrees (default 45.0).
    - print_direction: Print build direction vector (default [0, 0, 1] / +Z).
    - linear_deflection: Mesh tessellation accuracy in mm (default 0.5).
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape."}

    pts, tris = shape.tessellate(float(linear_deflection))
    bb = shape.BoundBox
    z_min = bb.ZMin

    tot_area = 0.0
    downward_area = 0.0
    overhang_area = 0.0
    overhang_z_min = float("inf")
    overhang_z_max = float("-inf")
    critical_triangles = 0

    p_dir_len = math.hypot(print_direction[0], print_direction[1], print_direction[2])
    pd = (print_direction[0] / p_dir_len, print_direction[1] / p_dir_len, print_direction[2] / p_dir_len)

    for t in tris:
        p0, p1, p2 = pts[t[0]], pts[t[1]], pts[t[2]]
        e1 = p1 - p0
        e2 = p2 - p0
        cp = e1.cross(e2)
        area = 0.5 * cp.Length
        tot_area += area

        if cp.Length < 1e-6:
            continue

        nx = cp.x / cp.Length
        ny = cp.y / cp.Length
        nz = cp.z / cp.Length

        # Dot product with print direction
        dot_pd = nx * pd[0] + ny * pd[1] + nz * pd[2]
        z_avg = (p0.z + p1.z + p2.z) / 3.0

        # Downward facing if normal points opposite to build direction
        if dot_pd < -0.01:
            downward_area += area
            # Ignore triangles sitting directly on the build plate (Z within 0.3mm of z_min)
            if (z_avg - z_min) > 0.3:
                # Angle to horizontal build plane
                slope_angle = math.degrees(math.asin(min(1.0, abs(dot_pd))))
                if slope_angle < float(max_overhang_angle):
                    overhang_area += area
                    critical_triangles += 1
                    if z_avg < overhang_z_min:
                        overhang_z_min = z_avg
                    if z_avg > overhang_z_max:
                        overhang_z_max = z_avg

    overhang_pct = (overhang_area / tot_area * 100.0) if tot_area > 0 else 0.0
    needs_support = overhang_area > 5.0  # more than nominal noise

    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "max_overhang_threshold_deg": float(max_overhang_angle),
        "total_surface_area_mm2": round(tot_area, 2),
        "downward_area_mm2": round(downward_area, 2),
        "overhang_area_mm2": round(overhang_area, 2),
        "overhang_ratio_percent": round(overhang_pct, 2),
        "needs_supports": bool(needs_support),
        "overhang_z_range": [round(overhang_z_min, 2), round(overhang_z_max, 2)] if needs_support else None,
        "printable_without_support": not needs_support,
        "recommendation": (
            "Printable cleanly without supports!"
            if not needs_support else
            f"Requires supports or 45-degree chamfers on {round(overhang_area, 1)} mm2 of overhangs between Z={round(overhang_z_min,1)} and {round(overhang_z_max,1)} mm."
        ),
    }


def inspect_fasteners(object_name, document_name=None):
    """Detect and classify cylindrical holes, mounting bosses, and fastener sizes (M2 to M8)."""
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    obj = doc.getObject(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found."}

    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return {"error": f"Object '{object_name}' has no valid Shape."}

    holes = []
    bosses = []

    for idx, f in enumerate(shape.Faces):
        surf = f.Surface
        if hasattr(surf, "Radius"):
            r = surf.Radius
            d = round(r * 2.0, 2)
            axis = surf.Axis
            c = f.CenterOfMass

            # Determine whether hole (normal points inwards) or boss (normal points outwards)
            is_hole = True
            try:
                fn = f.normalAt(0, 0)
                # Vector from axis center to face center
                rad_vec = FreeCAD.Vector(c.x - surf.Center.x, c.y - surf.Center.y, c.z - surf.Center.z)
                dot = fn.x * rad_vec.x + fn.y * rad_vec.y + fn.z * rad_vec.z
                if dot > 0:
                    is_hole = False
            except Exception:
                pass

            # Classify ISO fastener match
            iso_match = _classify_fastener(d)

            entry = {
                "face_index": idx,
                "diameter_mm": d,
                "depth_mm": round(f.Area / (math.pi * d), 2) if d > 0 else 0.0,
                "axis": [round(axis.x, 2), round(axis.y, 2), round(axis.z, 2)],
                "center": [round(c.x, 2), round(c.y, 2), round(c.z, 2)],
                "iso_match": iso_match,
            }

            if is_hole:
                holes.append(entry)
            else:
                bosses.append(entry)

    # Group holes by diameter
    grouped_holes = collections.defaultdict(list)
    for h in holes:
        grouped_holes[h["diameter_mm"]].append(h)

    summary_holes = []
    for d, items in sorted(grouped_holes.items()):
        summary_holes.append({
            "diameter_mm": d,
            "count": len(items),
            "iso_fastener": items[0]["iso_match"],
            "avg_depth_mm": round(sum(it["depth_mm"] for it in items) / len(items), 2),
        })

    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "total_cylindrical_features": len(holes) + len(bosses),
        "holes_count": len(holes),
        "bosses_count": len(bosses),
        "hole_groups": summary_holes,
        "mounting_bosses": [
            {"diameter_mm": b["diameter_mm"], "center": b["center"], "height_mm": b["depth_mm"]}
            for b in bosses[:10]
        ],
    }


def _classify_fastener(diameter):
    """Match hole diameter in mm to ISO metric standard fastener conventions."""
    d = float(diameter)
    if 1.9 <= d <= 2.5:
        return "M2 (Clearance/Tap)"
    elif 2.6 <= d <= 2.9:
        return "M2.5 (Clearance)"
    elif 3.0 <= d <= 3.6:
        return "M3 (Clearance hole, normal fit 3.2-3.4mm)"
    elif 3.9 <= d <= 4.8:
        return "M3 Heat-Set Insert (Ruthex standard 4.0-4.6mm) or M4 Tap"
    elif 4.9 <= d <= 5.8:
        return "M5 Clearance or M4 Heat-Set Insert"
    elif 5.9 <= d <= 6.8:
        return "M6 Clearance (standard rack EIA-310 6.0-6.5mm)"
    elif 7.8 <= d <= 8.8:
        return "M8 Clearance"
    return "Custom"


def _get_shape_com(shape):
    """Compute Center of Mass robustly across Solids and Compounds."""
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


def _convex_hull(points):
    """Andrew's monotone chain 2D convex hull algorithm."""
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _polygon_area(poly):
    """Compute 2D polygon area using surveyor's formula."""
    n = len(poly)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
    return abs(area) / 2.0


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument
