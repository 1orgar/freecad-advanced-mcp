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


def audit_wall_thickness(
    object_name,
    min_thickness=1.2,
    document_name=None,
):
    """Audit solid for thin walls below printable FDM threshold (e.g. < 1.2 mm).

    Parameters:
    - object_name: Name of target object.
    - min_thickness: Minimum acceptable wall thickness in mm (default 1.2 for 3 perimeters).
    - document_name: Optional document name.
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

    min_t = float(min_thickness)
    thin_regions = []
    min_found = float("inf")

    # Inspect opposing planar faces
    faces = [f for f in shape.Faces if f.Surface.TypeId == "Part::GeomPlane"]
    for i, f1 in enumerate(faces):
        try:
            n1 = f1.normalAt(0, 0)
            c1 = f1.CenterOfMass
        except Exception:
            continue

        for f2 in faces[i + 1:]:
            try:
                n2 = f2.normalAt(0, 0)
                dot = n1.x * n2.x + n1.y * n2.y + n1.z * n2.z
                if dot < -0.98:  # antiparallel within ~11 degrees
                    diff = FreeCAD.Vector(f2.CenterOfMass.x - c1.x, f2.CenterOfMass.y - c1.y, f2.CenterOfMass.z - c1.z)
                    dist = abs(diff.x * n1.x + diff.y * n1.y + diff.z * n1.z)

                    if 0.05 < dist < min_t:
                        tangent_dist = math.sqrt(max(0.0, diff.Length**2 - dist**2))
                        max_diag = max(math.sqrt(f1.Area), math.sqrt(f2.Area))
                        if tangent_dist < max_diag * 1.5:
                            min_found = min(min_found, dist)
                            thin_regions.append({
                                "thickness_mm": round(dist, 3),
                                "location": [round(c1.x, 2), round(c1.y, 2), round(c1.z, 2)],
                                "normal": [round(n1.x, 3), round(n1.y, 3), round(n1.z, 3)],
                                "area_mm2": round(min(f1.Area, f2.Area), 2),
                            })
            except Exception:
                continue

    # Deduplicate overlapping regions
    unique_thin = []
    for r in thin_regions:
        if not any(math.dist(r["location"], u["location"]) < 5.0 for u in unique_thin):
            unique_thin.append(r)

    is_safe = len(unique_thin) == 0
    return {
        "status": "ok",
        "document": doc.Name,
        "object": obj.Name,
        "min_thickness_threshold_mm": min_t,
        "min_detected_thickness_mm": round(min_found, 3) if min_found < float("inf") else None,
        "safe_for_printing": is_safe,
        "thin_regions_count": len(unique_thin),
        "thin_regions": unique_thin[:10],
        "recommendation": "All walls meet minimum FDM threshold." if is_safe else f"Found {len(unique_thin)} thin wall regions < {min_t}mm that may cause slicing gaps or weak parts.",
    }


def split_part_for_bed(
    object_name,
    max_bed_size=256.0,
    split_axis="X",
    joint_type="dowel",
    clearance=0.2,
    document_name=None,
):
    """Split oversized part to fit 3D printer build bed with interlocking joints.

    Parameters:
    - object_name: Target solid name.
    - max_bed_size: Maximum printable bed dimension in mm (default 256.0 for Bambu Lab/Prusa).
    - split_axis: "X", "Y", or "Z" axis to split along (default "X").
    - joint_type: "dowel" (pin holes for alignment pins) or "flat".
    - clearance: Joint tolerance in mm (default 0.2).
    - document_name: Optional document name.
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
    axis = split_axis.upper()
    size_on_axis = bb.XLength if axis == "X" else (bb.YLength if axis == "Y" else bb.ZLength)

    if size_on_axis <= float(max_bed_size):
        return {
            "status": "ok",
            "message": f"Object size on {axis} ({size_on_axis:.1f} mm) already fits within {max_bed_size:.1f} mm bed.",
            "split_performed": False,
        }

    # Split coordinate at midpoint
    split_coord = (bb.XMin + bb.XMax) / 2.0 if axis == "X" else ((bb.YMin + bb.YMax) / 2.0 if axis == "Y" else (bb.ZMin + bb.ZMax) / 2.0)

    margin = 50.0
    big_box_w = bb.XLength + 2.0 * margin
    big_box_h = bb.YLength + 2.0 * margin
    big_box_d = bb.ZLength + 2.0 * margin

    if axis == "X":
        box_a = Part.makeBox(split_coord - (bb.XMin - margin), big_box_h, big_box_d,
                              FreeCAD.Vector(bb.XMin - margin, bb.YMin - margin, bb.ZMin - margin))
        box_b = Part.makeBox((bb.XMax + margin) - split_coord, big_box_h, big_box_d,
                              FreeCAD.Vector(split_coord, bb.YMin - margin, bb.ZMin - margin))
    elif axis == "Y":
        box_a = Part.makeBox(big_box_w, split_coord - (bb.YMin - margin), big_box_d,
                              FreeCAD.Vector(bb.XMin - margin, bb.YMin - margin, bb.ZMin - margin))
        box_b = Part.makeBox(big_box_w, (bb.YMax + margin) - split_coord, big_box_d,
                              FreeCAD.Vector(bb.XMin - margin, split_coord, bb.ZMin - margin))
    else:
        box_a = Part.makeBox(big_box_w, big_box_h, split_coord - (bb.ZMin - margin),
                              FreeCAD.Vector(bb.XMin - margin, bb.YMin - margin, bb.ZMin - margin))
        box_b = Part.makeBox(big_box_w, big_box_h, (bb.ZMax + margin) - split_coord,
                              FreeCAD.Vector(bb.XMin - margin, bb.YMin - margin, split_coord))

    part_a = shape.common(box_a)
    part_b = shape.common(box_b)

    if joint_type == "dowel":
        pin_r = 1.75  # 3.5 mm pin
        pin_depth = 12.0
        cy_mid = (bb.YMin + bb.YMax) / 2.0
        cz_mid = (bb.ZMin + bb.ZMax) / 2.0

        if axis == "X":
            pin1 = Part.makeCylinder(pin_r, pin_depth * 2, FreeCAD.Vector(split_coord - pin_depth, cy_mid - 15.0, cz_mid), FreeCAD.Vector(1, 0, 0))
            pin2 = Part.makeCylinder(pin_r, pin_depth * 2, FreeCAD.Vector(split_coord - pin_depth, cy_mid + 15.0, cz_mid), FreeCAD.Vector(1, 0, 0))
            part_a = part_a.cut(pin1).cut(pin2)
            part_b = part_b.cut(pin1).cut(pin2)

    obj_a = doc.addObject("Part::Feature", f"{obj.Label}_Part_A")
    obj_a.Shape = part_a
    obj_b = doc.addObject("Part::Feature", f"{obj.Label}_Part_B")
    obj_b.Shape = part_b

    doc.recompute()

    return {
        "status": "ok",
        "split_performed": True,
        "split_axis": axis,
        "split_coordinate": round(split_coord, 2),
        "joint_type": joint_type,
        "part_a": {
            "name": obj_a.Name,
            "bounding_box": [round(part_a.BoundBox.XLength, 1), round(part_a.BoundBox.YLength, 1), round(part_a.BoundBox.ZLength, 1)],
            "fits_bed": max(part_a.BoundBox.XLength, part_a.BoundBox.YLength) <= max_bed_size,
        },
        "part_b": {
            "name": obj_b.Name,
            "bounding_box": [round(part_b.BoundBox.XLength, 1), round(part_b.BoundBox.YLength, 1), round(part_b.BoundBox.ZLength, 1)],
            "fits_bed": max(part_b.BoundBox.XLength, part_b.BoundBox.YLength) <= max_bed_size,
        },
    }


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
