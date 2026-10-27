"""Smart Features (Semantic CAD) engineering primitives for FreeCAD MCP.

Provides high-level parametric features for common engineering and 3D-printing cases:
1. Patterns: honeycomb, slotted grill, circular perforations.
2. Structural: stiffening ribs, support gussets.
3. Fasteners: heat-set insert bosses (Ruthex/CNC Kitchen M2-M5), counterbores, captive hex nut pockets.
4. Cutouts: Keystone RJ45, C14 AC inlet, USB-A/C, PC fan mounts (40-120mm), rocker switches.
5. Cable management: zip-tie saddles/slots, velcro strap slots, anti-chafing grommet pass-throughs.
6. Enclosure joints: lip-and-groove mating rims, cantilever snap-fits.
"""

import math
import FreeCAD
import Part
import Sketcher
from freecad.mcp_bridge import cad_helpers


# ==============================================================================
# 1. Patterns & Perforations
# ==============================================================================

def make_honeycomb_shape(bounds_w, bounds_h, cell_size=10.0, wall_thickness=2.2, depth=10.0):
    """Generate a solid compound of hexagonal prisms for cutting a honeycomb grid."""
    r_in = float(cell_size) / 2.0
    r_circ = r_in / math.cos(math.radians(30))
    step_x = 2.0 * r_in + float(wall_thickness)
    step_y = step_x * math.sqrt(3) / 2.0

    n_cols = int(bounds_w / step_x) + 2
    n_rows = int(bounds_h / step_y) + 2

    hex_solids = []
    half_w = bounds_w / 2.0
    half_h = bounds_h / 2.0

    for row in range(-n_rows, n_rows + 1):
        cy = row * step_y
        offset_x = (step_x / 2.0) if (row % 2 != 0) else 0.0
        for col in range(-n_cols, n_cols + 1):
            cx = col * step_x + offset_x

            # Check if cell is within bounds with half-cell margin
            if abs(cx) + r_circ > half_w or abs(cy) + r_circ > half_h:
                continue

            # Create 2D hexagon polygon
            pts = []
            for a_deg in (30, 90, 150, 210, 270, 330):
                rad = math.radians(a_deg)
                pts.append(FreeCAD.Vector(cx + r_circ * math.cos(rad), cy + r_circ * math.sin(rad), -depth / 2.0))
            pts.append(pts[0])

            poly = Part.makePolygon(pts)
            face = Part.Face(poly)
            prism = face.extrude(FreeCAD.Vector(0, 0, depth))
            hex_solids.append(prism)

    if not hex_solids:
        return Part.Shape()
    return Part.Compound(hex_solids)


def make_slotted_grill_shape(bounds_w, bounds_h, slot_width=3.5, slot_pitch=7.0, depth=10.0, angle_deg=0.0):
    """Generate an array of parallel stadium slots for ventilation grills."""
    half_w = bounds_w / 2.0
    half_h = bounds_h / 2.0
    n_slots = int(bounds_w / slot_pitch) + 1

    slot_solids = []
    slot_len = bounds_h - 2.0 * slot_width
    r = slot_width / 2.0
    half_l = (slot_len - slot_width) / 2.0

    for i in range(-n_slots, n_slots + 1):
        cx = i * slot_pitch
        if abs(cx) + r > half_w:
            continue

        p1 = FreeCAD.Vector(cx - r, -half_l, -depth / 2.0)
        p2 = FreeCAD.Vector(cx + r, -half_l, -depth / 2.0)
        p3 = FreeCAD.Vector(cx + r, half_l, -depth / 2.0)
        p4 = FreeCAD.Vector(cx - r, half_l, -depth / 2.0)

        arc_top = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(cx, half_l, -depth / 2.0), FreeCAD.Vector(0, 0, 1), r), 0, math.pi)
        arc_bot = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(cx, -half_l, -depth / 2.0), FreeCAD.Vector(0, 0, 1), r), math.pi, 2 * math.pi)

        wire = Part.Wire([
            Part.LineSegment(p1, p4).toShape(),
            arc_top.toShape(),
            Part.LineSegment(p3, p2).toShape(),
            arc_bot.toShape(),
        ])
        face = Part.Face(wire)
        prism = face.extrude(FreeCAD.Vector(0, 0, depth))

        if abs(angle_deg) > 0.01:
            prism.rotate(FreeCAD.Vector(cx, 0, 0), FreeCAD.Vector(0, 0, 1), angle_deg)
        slot_solids.append(prism)

    if not slot_solids:
        return Part.Shape()
    return Part.Compound(slot_solids)


def make_circular_perforation_shape(bounds_w, bounds_h, hole_dia=4.0, pitch=7.0, pattern="staggered", depth=10.0):
    """Generate an array of circular holes (staggered 60 deg or orthogonal grid)."""
    r = float(hole_dia) / 2.0
    half_w = bounds_w / 2.0
    half_h = bounds_h / 2.0

    step_x = float(pitch)
    step_y = pitch * math.sqrt(3) / 2.0 if pattern == "staggered" else float(pitch)

    n_cols = int(bounds_w / step_x) + 2
    n_rows = int(bounds_h / step_y) + 2

    holes = []
    for row in range(-n_rows, n_rows + 1):
        cy = row * step_y
        offset_x = (step_x / 2.0) if (pattern == "staggered" and row % 2 != 0) else 0.0
        for col in range(-n_cols, n_cols + 1):
            cx = col * step_x + offset_x
            if abs(cx) + r > half_w or abs(cy) + r > half_h:
                continue

            cyl = Part.makeCylinder(r, depth, FreeCAD.Vector(cx, cy, -depth / 2.0), FreeCAD.Vector(0, 0, 1))
            holes.append(cyl)

    if not holes:
        return Part.Shape()
    return Part.Compound(holes)


# ==============================================================================
# 2. Fasteners & Inserts
# ==============================================================================

HEATSET_SPECS = {
    "M2": {"hole_top": 3.2, "hole_bot": 3.0, "hole_depth": 4.0, "boss_dia": 6.0, "min_wall": 1.4},
    "M2.5": {"hole_top": 3.8, "hole_bot": 3.6, "hole_depth": 5.5, "boss_dia": 7.0, "min_wall": 1.6},
    "M3": {"hole_top": 4.2, "hole_bot": 4.0, "hole_depth": 5.7, "boss_dia": 8.0, "min_wall": 1.8},
    "M4": {"hole_top": 5.8, "hole_bot": 5.5, "hole_depth": 7.5, "boss_dia": 10.0, "min_wall": 2.0},
    "M5": {"hole_top": 7.0, "hole_bot": 6.6, "hole_depth": 9.5, "boss_dia": 12.0, "min_wall": 2.2},
}

def make_heatset_boss_shape(thread="M3", boss_height=8.0, boss_dia=None, with_gussets=True):
    """Generate a heat-set insert mounting boss with tapered insert cavity and 4 base gussets."""
    spec = HEATSET_SPECS.get(thread.upper(), HEATSET_SPECS["M3"])
    b_dia = float(boss_dia) if boss_dia else spec["boss_dia"]
    b_rad = b_dia / 2.0
    h_top_r = spec["hole_top"] / 2.0
    h_bot_r = spec["hole_bot"] / 2.0
    h_depth = spec["hole_depth"]

    # Outer cylindrical boss
    outer = Part.makeCylinder(b_rad, boss_height, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))

    # Tapered internal cavity with entrance chamfer
    # Cone from top of boss pointing downwards
    cavity_z = max(0.0, boss_height - h_depth)
    cone = Part.makeCone(h_bot_r, h_top_r, h_depth, FreeCAD.Vector(0, 0, cavity_z), FreeCAD.Vector(0, 0, 1))

    # Small top chamfer for soldering iron centering
    chamfer_cone = Part.makeCone(h_top_r, h_top_r + 0.6, 0.6, FreeCAD.Vector(0, 0, boss_height - 0.6), FreeCAD.Vector(0, 0, 1))
    cavity = cone.fuse(chamfer_cone)

    boss = outer.cut(cavity)

    # 4 triangular base gussets for torsional strength
    if with_gussets:
        g_w = 1.8  # gusset thickness
        g_len = b_rad + 3.0
        g_h = min(boss_height * 0.75, 6.0)

        gussets = []
        for angle in (0, 90, 180, 270):
            p1 = FreeCAD.Vector(b_rad - 0.5, -g_w / 2.0, 0)
            p2 = FreeCAD.Vector(g_len, -g_w / 2.0, 0)
            p3 = FreeCAD.Vector(b_rad - 0.5, -g_w / 2.0, g_h)
            w = Part.makePolygon([p1, p2, p3, p1])
            f = Part.Face(w)
            g_prism = f.extrude(FreeCAD.Vector(0, g_w, 0))
            g_prism.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), angle)
            boss = boss.fuse(g_prism)

    return boss


def make_screw_hole_shape(screw_size="M3", head_type="counterbore", plate_thickness=5.0):
    """Generate a cutter for DIN 912 (counterbore), DIN 7991 (countersunk), or clearance hole."""
    s = screw_size.upper()
    specs = {
        "M2": {"body_r": 1.2, "head_r": 2.2, "head_h": 2.0},
        "M2.5": {"body_r": 1.45, "head_r": 2.6, "head_h": 2.5},
        "M3": {"body_r": 1.7, "head_r": 3.0, "head_h": 3.2},
        "M4": {"body_r": 2.25, "head_r": 3.8, "head_h": 4.2},
        "M5": {"body_r": 2.75, "head_r": 4.6, "head_h": 5.2},
        "M6": {"body_r": 3.3, "head_r": 5.5, "head_h": 6.2},
    }
    spec = specs.get(s, specs["M3"])
    overshoot = 2.0
    tot_h = plate_thickness + 2.0 * overshoot

    # Shaft cylinder
    shaft = Part.makeCylinder(spec["body_r"], tot_h, FreeCAD.Vector(0, 0, -overshoot), FreeCAD.Vector(0, 0, 1))

    if head_type == "counterbore":
        cb = Part.makeCylinder(spec["head_r"], spec["head_h"] + overshoot, FreeCAD.Vector(0, 0, plate_thickness - spec["head_h"]), FreeCAD.Vector(0, 0, 1))
        return shaft.fuse(cb)
    elif head_type == "countersunk":
        cone = Part.makeCone(spec["body_r"], spec["head_r"], spec["head_r"] - spec["body_r"], FreeCAD.Vector(0, 0, plate_thickness - (spec["head_r"] - spec["body_r"])), FreeCAD.Vector(0, 0, 1))
        return shaft.fuse(cone)
    return shaft


def make_hex_nut_pocket_shape(nut_size="M3", depth=3.0, through_hole=True):
    """Generate a captive hex nut pocket for DIN 934 nuts."""
    s_map = {
        "M2": {"s": 4.0, "m": 1.6, "bolt_r": 1.15},
        "M2.5": {"s": 5.0, "m": 2.0, "bolt_r": 1.45},
        "M3": {"s": 5.5, "m": 2.4, "bolt_r": 1.7},
        "M4": {"s": 7.0, "m": 3.2, "bolt_r": 2.25},
        "M5": {"s": 8.0, "m": 4.0, "bolt_r": 2.75},
        "M6": {"s": 10.0, "m": 5.0, "bolt_r": 3.3},
    }
    spec = s_map.get(nut_size.upper(), s_map["M3"])
    r_in = (spec["s"] + 0.3) / 2.0  # +0.3 mm clearance
    r_circ = r_in / math.cos(math.radians(30))
    p_depth = max(float(depth), spec["m"] + 0.4)

    pts = []
    for a in (0, 60, 120, 180, 240, 300):
        rad = math.radians(a)
        pts.append(FreeCAD.Vector(r_circ * math.cos(rad), r_circ * math.sin(rad), 0))
    pts.append(pts[0])

    poly = Part.makePolygon(pts)
    face = Part.Face(poly)
    nut_prism = face.extrude(FreeCAD.Vector(0, 0, p_depth))

    if through_hole:
        bolt = Part.makeCylinder(spec["bolt_r"], p_depth + 20.0, FreeCAD.Vector(0, 0, -10.0), FreeCAD.Vector(0, 0, 1))
        return nut_prism.fuse(bolt)
    return nut_prism


# ==============================================================================
# 3. Standard Cutouts & Ports
# ==============================================================================

def make_keystone_cutout_shape(depth=15.0):
    """Generate standard snap-in Keystone modular jack cutout (14.8 x 19.4 mm)."""
    kw = 14.8
    kh = 19.4
    box = Part.makeBox(kw, kh, depth, FreeCAD.Vector(-kw / 2.0, -kh / 2.0, -depth / 2.0))

    # Retention catch notches (top latch clearance)
    notch_w = 16.5
    notch_h = 2.0
    notch_d = depth
    notch = Part.makeBox(notch_w, notch_h, notch_d, FreeCAD.Vector(-notch_w / 2.0, kh / 2.0 - notch_h, -depth / 2.0))
    return box.fuse(notch)


def make_c14_inlet_cutout_shape(depth=15.0):
    """Generate IEC C14 power inlet socket cutout (27.5 x 19.8 mm + 2x M3 holes at 40mm pitch)."""
    w = 27.5
    h = 19.8
    r_corner = 2.0
    half_w = (w - 2.0 * r_corner) / 2.0
    half_h = (h - 2.0 * r_corner) / 2.0

    # Rounded rectangle body
    p1 = FreeCAD.Vector(-half_w, -h / 2.0, -depth / 2.0)
    p2 = FreeCAD.Vector(half_w, -h / 2.0, -depth / 2.0)
    p3 = FreeCAD.Vector(w / 2.0, -half_h, -depth / 2.0)
    p4 = FreeCAD.Vector(w / 2.0, half_h, -depth / 2.0)
    p5 = FreeCAD.Vector(half_w, h / 2.0, -depth / 2.0)
    p6 = FreeCAD.Vector(-half_w, h / 2.0, -depth / 2.0)
    p7 = FreeCAD.Vector(-w / 2.0, half_h, -depth / 2.0)
    p8 = FreeCAD.Vector(-w / 2.0, -half_h, -depth / 2.0)

    a1 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(half_w, -half_h, -depth / 2.0), FreeCAD.Vector(0,0,1), r_corner), -math.pi/2, 0)
    a2 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(half_w, half_h, -depth / 2.0), FreeCAD.Vector(0,0,1), r_corner), 0, math.pi/2)
    a3 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(-half_w, half_h, -depth / 2.0), FreeCAD.Vector(0,0,1), r_corner), math.pi/2, math.pi)
    a4 = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(-half_w, -half_h, -depth / 2.0), FreeCAD.Vector(0,0,1), r_corner), math.pi, 3*math.pi/2)

    wire = Part.Wire([
        Part.LineSegment(p1, p2).toShape(), a1.toShape(),
        Part.LineSegment(p3, p4).toShape(), a2.toShape(),
        Part.LineSegment(p5, p6).toShape(), a3.toShape(),
        Part.LineSegment(p7, p8).toShape(), a4.toShape(),
    ])
    body = Part.Face(wire).extrude(FreeCAD.Vector(0, 0, depth))

    # 2x M3 mounting screw holes at X = +-20.0 mm
    hole_l = Part.makeCylinder(1.7, depth, FreeCAD.Vector(-20.0, 0, -depth / 2.0), FreeCAD.Vector(0, 0, 1))
    hole_r = Part.makeCylinder(1.7, depth, FreeCAD.Vector(20.0, 0, -depth / 2.0), FreeCAD.Vector(0, 0, 1))

    return body.fuse(hole_l).fuse(hole_r)


def make_usb_cutout_shape(usb_type="usb_c", depth=15.0):
    """Generate USB-A (14.2 x 7.2 mm) or USB-C (9.2 x 3.5 mm oval) cutout."""
    ut = usb_type.lower()
    if "c" in ut:
        w = 9.2
        h = 3.5
        r = h / 2.0
        dx = (w - h) / 2.0
        p1 = FreeCAD.Vector(-dx, -r, -depth / 2.0)
        p2 = FreeCAD.Vector(dx, -r, -depth / 2.0)
        p3 = FreeCAD.Vector(dx, r, -depth / 2.0)
        p4 = FreeCAD.Vector(-dx, r, -depth / 2.0)

        a_r = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(dx, 0, -depth / 2.0), FreeCAD.Vector(0,0,1), r), -math.pi/2, math.pi/2)
        a_l = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(-dx, 0, -depth / 2.0), FreeCAD.Vector(0,0,1), r), math.pi/2, 3*math.pi/2)
        wire = Part.Wire([
            Part.LineSegment(p1, p2).toShape(), a_r.toShape(),
            Part.LineSegment(p3, p4).toShape(), a_l.toShape(),
        ])
        return Part.Face(wire).extrude(FreeCAD.Vector(0, 0, depth))
    else:
        # USB-A
        w, h = 14.2, 7.2
        return Part.makeBox(w, h, depth, FreeCAD.Vector(-w / 2.0, -h / 2.0, -depth / 2.0))


def make_fan_mount_cutout_shape(fan_size=40, depth=15.0):
    """Generate PC fan ventilation port (central duct + 4 corner screw holes)."""
    specs = {
        40: {"duct_r": 19.0, "hole_pitch": 32.0, "hole_r": 1.7},
        60: {"duct_r": 29.0, "hole_pitch": 50.0, "hole_r": 2.2},
        80: {"duct_r": 38.5, "hole_pitch": 71.5, "hole_r": 2.2},
        92: {"duct_r": 44.5, "hole_pitch": 82.5, "hole_r": 2.2},
        120: {"duct_r": 58.5, "hole_pitch": 105.0, "hole_r": 2.2},
    }
    spec = specs.get(int(fan_size), specs[40])
    duct = Part.makeCylinder(spec["duct_r"], depth, FreeCAD.Vector(0, 0, -depth / 2.0), FreeCAD.Vector(0, 0, 1))

    hp = spec["hole_pitch"] / 2.0
    hr = spec["hole_r"]
    corner_holes = []
    for dx in (-hp, hp):
        for dy in (-hp, hp):
            h = Part.makeCylinder(hr, depth, FreeCAD.Vector(dx, dy, -depth / 2.0), FreeCAD.Vector(0, 0, 1))
            corner_holes.append(h)

    res = duct
    for h in corner_holes:
        res = res.fuse(h)
    return res


def make_rocker_switch_cutout_shape(switch_type="kcd1", depth=15.0):
    """Generate rocker switch cutout (KCD1: 19.2 x 13.0 mm)."""
    w, h = 19.2, 13.0
    return Part.makeBox(w, h, depth, FreeCAD.Vector(-w / 2.0, -h / 2.0, -depth / 2.0))


# ==============================================================================
# 4. Cable Management
# ==============================================================================

def make_zip_tie_mount_shape(mount_type="saddle", tie_width=3.6, height=5.0):
    """Generate a zip-tie surface saddle bridge or through-slots."""
    if mount_type == "saddle":
        # Solid arched bridge on surface
        base_w = 12.0
        base_l = 10.0
        bridge_h = max(float(height), 4.5)
        outer = Part.makeBox(base_l, base_w, bridge_h, FreeCAD.Vector(-base_l / 2.0, -base_w / 2.0, 0))

        # Tunnel for zip-tie
        tunnel_w = float(tie_width) + 1.2
        tunnel_h = 2.0
        tunnel = Part.makeBox(base_l + 2.0, tunnel_w, tunnel_h, FreeCAD.Vector(-base_l / 2.0 - 1.0, -tunnel_w / 2.0, 1.2))
        return outer.cut(tunnel)
    else:
        # Through-slots in a plate
        w = float(tie_width) + 1.0
        t = 2.2
        spacing = 5.0
        depth = 15.0
        s1 = Part.makeBox(t, w, depth, FreeCAD.Vector(-spacing / 2.0 - t, -w / 2.0, -depth / 2.0))
        s2 = Part.makeBox(t, w, depth, FreeCAD.Vector(spacing / 2.0, -w / 2.0, -depth / 2.0))
        return s1.fuse(s2)


def make_velcro_slot_shape(strap_width=20.0, depth=15.0):
    """Generate dual slots for 20mm reusable Velcro straps."""
    w = float(strap_width) + 2.0
    t = 3.0
    spacing = 14.0
    r = t / 2.0
    dx = (w - t) / 2.0

    slots = []
    for offset_x in (-spacing / 2.0 - t / 2.0, spacing / 2.0 + t / 2.0):
        p1 = FreeCAD.Vector(offset_x - r, -dx, -depth / 2.0)
        p2 = FreeCAD.Vector(offset_x + r, -dx, -depth / 2.0)
        p3 = FreeCAD.Vector(offset_x + r, dx, -depth / 2.0)
        p4 = FreeCAD.Vector(offset_x - r, dx, -depth / 2.0)

        a_top = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(offset_x, dx, -depth / 2.0), FreeCAD.Vector(0,0,1), r), 0, math.pi)
        a_bot = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(offset_x, -dx, -depth / 2.0), FreeCAD.Vector(0,0,1), r), math.pi, 2*math.pi)

        wire = Part.Wire([
            Part.LineSegment(p1, p4).toShape(), a_top.toShape(),
            Part.LineSegment(p3, p2).toShape(), a_bot.toShape(),
        ])
        s = Part.Face(wire).extrude(FreeCAD.Vector(0, 0, depth))
        slots.append(s)

    return slots[0].fuse(slots[1])


def make_cable_pass_through_shape(width=30.0, height=16.0, depth=15.0):
    """Generate a rounded stadium pass-through port with smooth edges."""
    r = height / 2.0
    dx = (width - height) / 2.0
    p1 = FreeCAD.Vector(-dx, -r, -depth / 2.0)
    p2 = FreeCAD.Vector(dx, -r, -depth / 2.0)
    p3 = FreeCAD.Vector(dx, r, -depth / 2.0)
    p4 = FreeCAD.Vector(-dx, r, -depth / 2.0)

    a_r = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(dx, 0, -depth / 2.0), FreeCAD.Vector(0,0,1), r), -math.pi/2, math.pi/2)
    a_l = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(-dx, 0, -depth / 2.0), FreeCAD.Vector(0,0,1), r), math.pi/2, 3*math.pi/2)

    wire = Part.Wire([
        Part.LineSegment(p1, p2).toShape(), a_r.toShape(),
        Part.LineSegment(p3, p4).toShape(), a_l.toShape(),
    ])
    return Part.Face(wire).extrude(FreeCAD.Vector(0, 0, depth))


# ==============================================================================
# 5. Structural Reinforcement (Ribs & Gussets)
# ==============================================================================

def make_stiffening_ribs_shape(length=100.0, depth=5.0, thickness=3.0, count=2, spacing=20.0, direction="X"):
    """Generate parallel stiffening ribs."""
    ribs = []
    half_t = thickness / 2.0
    offsets = [-(count - 1) * spacing / 2.0 + i * spacing for i in range(count)]

    for off in offsets:
        if direction.upper() == "X":
            # Length along X, spaced along Y
            box = Part.makeBox(length, thickness, depth, FreeCAD.Vector(-length / 2.0, off - half_t, 0))
        else:
            # Length along Y, spaced along X
            box = Part.makeBox(thickness, length, depth, FreeCAD.Vector(off - half_t, -length / 2.0, 0))
        ribs.append(box)

    if not ribs:
        return Part.Shape()
    res = ribs[0]
    for r in ribs[1:]:
        res = res.fuse(r)
    return res


def make_gusset_shape(width=15.0, height=15.0, thickness=3.0, chamfer_corner=True):
    """Generate a triangular 45 deg support gusset with optional cable/wire notch."""
    pts = [
        FreeCAD.Vector(0, 0, 0),
        FreeCAD.Vector(width, 0, 0),
        FreeCAD.Vector(0, height, 0),
        FreeCAD.Vector(0, 0, 0),
    ]
    poly = Part.makePolygon(pts)
    face = Part.Face(poly)
    gusset = face.extrude(FreeCAD.Vector(0, 0, thickness))

    if chamfer_corner:
        # Small 2x2 mm corner relief for welds / filament beads
        relief = Part.makeBox(2.5, 2.5, thickness + 2.0, FreeCAD.Vector(-0.5, -0.5, -1.0))
        gusset = gusset.cut(relief)

    return gusset


# ==============================================================================
# Unified Smart Feature Applicator
# ==============================================================================

def apply_smart_feature(
    feature_type,
    target_object=None,
    parameters=None,
    placement=None,
    operation="cut",
    document_name=None,
):
    """Apply a semantic smart feature to a target object or create a standalone solid.

    Parameters:
    - feature_type: One of:
        - "honeycomb", "slotted_grill", "circular_perforation"
        - "heatset_boss", "screw_hole", "hex_nut_pocket"
        - "keystone_jack", "c14_inlet", "usb_port", "fan_mount", "rocker_switch"
        - "zip_tie_mount", "velcro_slot", "cable_pass_through"
        - "stiffening_ribs", "gusset"
    - target_object: Optional target FreeCAD object (Body or Feature) to modify.
    - parameters: Dict of feature-specific dimensions.
    - placement: Optional dict with "position": [x,y,z] and "rotation": [yaw,pitch,roll].
    - operation: "cut" (subtract), "fuse" (union), or "new_object" (standalone Part).
    - document_name: Optional document name.
    """
    params = parameters or {}
    ft = feature_type.lower().strip()
    feat_shape = None

    # Dispatch to feature generator
    if ft == "honeycomb":
        feat_shape = make_honeycomb_shape(
            bounds_w=params.get("bounds_w", 100.0),
            bounds_h=params.get("bounds_h", 40.0),
            cell_size=params.get("cell_size", 10.0),
            wall_thickness=params.get("wall_thickness", 2.2),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("slotted_grill", "grill", "slots"):
        feat_shape = make_slotted_grill_shape(
            bounds_w=params.get("bounds_w", 100.0),
            bounds_h=params.get("bounds_h", 40.0),
            slot_width=params.get("slot_width", 3.5),
            slot_pitch=params.get("slot_pitch", 7.0),
            depth=params.get("depth", 15.0),
            angle_deg=params.get("angle_deg", 0.0),
        )
    elif ft in ("circular_perforation", "holes_grid"):
        feat_shape = make_circular_perforation_shape(
            bounds_w=params.get("bounds_w", 80.0),
            bounds_h=params.get("bounds_h", 40.0),
            hole_dia=params.get("hole_dia", 4.0),
            pitch=params.get("pitch", 7.0),
            pattern=params.get("pattern", "staggered"),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("heatset_boss", "boss"):
        feat_shape = make_heatset_boss_shape(
            thread=params.get("thread", "M3"),
            boss_height=params.get("boss_height", 8.0),
            boss_dia=params.get("boss_dia"),
            with_gussets=params.get("with_gussets", True),
        )
    elif ft in ("screw_hole", "hole"):
        feat_shape = make_screw_hole_shape(
            screw_size=params.get("screw_size", "M3"),
            head_type=params.get("head_type", "counterbore"),
            plate_thickness=params.get("plate_thickness", 5.0),
        )
    elif ft in ("hex_nut_pocket", "nut_pocket"):
        feat_shape = make_hex_nut_pocket_shape(
            nut_size=params.get("nut_size", "M3"),
            depth=params.get("depth", 3.0),
            through_hole=params.get("through_hole", True),
        )
    elif ft in ("keystone_jack", "keystone"):
        feat_shape = make_keystone_cutout_shape(depth=params.get("depth", 15.0))
    elif ft in ("c14_inlet", "c14"):
        feat_shape = make_c14_inlet_cutout_shape(depth=params.get("depth", 15.0))
    elif ft in ("usb_port", "usb"):
        feat_shape = make_usb_cutout_shape(
            usb_type=params.get("usb_type", "usb_c"),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("fan_mount", "fan"):
        feat_shape = make_fan_mount_cutout_shape(
            fan_size=params.get("fan_size", 40),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("rocker_switch", "switch"):
        feat_shape = make_rocker_switch_cutout_shape(depth=params.get("depth", 15.0))
    elif ft in ("zip_tie_mount", "zip_tie"):
        feat_shape = make_zip_tie_mount_shape(
            mount_type=params.get("mount_type", "saddle"),
            tie_width=params.get("tie_width", 3.6),
            height=params.get("height", 5.0),
        )
    elif ft in ("velcro_slot", "velcro"):
        feat_shape = make_velcro_slot_shape(
            strap_width=params.get("strap_width", 20.0),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("cable_pass_through", "grommet"):
        feat_shape = make_cable_pass_through_shape(
            width=params.get("width", 30.0),
            height=params.get("height", 16.0),
            depth=params.get("depth", 15.0),
        )
    elif ft in ("stiffening_ribs", "ribs"):
        feat_shape = make_stiffening_ribs_shape(
            length=params.get("length", 100.0),
            depth=params.get("depth", 5.0),
            thickness=params.get("thickness", 3.0),
            count=params.get("count", 2),
            spacing=params.get("spacing", 20.0),
            direction=params.get("direction", "X"),
        )
    elif ft == "gusset":
        feat_shape = make_gusset_shape(
            width=params.get("width", 15.0),
            height=params.get("height", 15.0),
            thickness=params.get("thickness", 3.0),
            chamfer_corner=params.get("chamfer_corner", True),
        )
    else:
        return {"error": f"Unknown smart feature type '{feature_type}'."}

    if feat_shape is None or feat_shape.isNull():
        return {"error": f"Failed to generate shape for feature '{feature_type}'."}

    # Apply placement transform
    if placement:
        pos = placement.get("position", [0, 0, 0])
        rot = placement.get("rotation", [0, 0, 0])
        pos_v = FreeCAD.Vector(*pos)
        if len(rot) == 3:
            rot_q = FreeCAD.Rotation(rot[0], rot[1], rot[2])
        elif len(rot) == 4:
            rot_q = FreeCAD.Rotation(FreeCAD.Vector(rot[0], rot[1], rot[2]), rot[3])
        else:
            rot_q = FreeCAD.Rotation()
        feat_shape.Placement = FreeCAD.Placement(pos_v, rot_q)

    # Document handling
    doc = FreeCAD.getDocument(document_name) if document_name else FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument("SmartFeatureDoc")

    op = operation.lower().strip()

    if target_object:
        target = doc.getObject(target_object)
        if not target:
            return {"error": f"Target object '{target_object}' not found."}

        target_shape = getattr(target, "Shape", None)
        if not target_shape or target_shape.isNull():
            return {"error": f"Target object '{target_object}' has no valid Shape."}

        if op in ("cut", "subtract", "pocket"):
            new_shape = target_shape.cut(feat_shape)
        elif op in ("fuse", "union", "pad", "add"):
            new_shape = target_shape.fuse(feat_shape)
        else:
            new_shape = feat_shape

        # If target is PartDesign::Body, add feature or update tip
        if target.isDerivedFrom("PartDesign::Body"):
            feat = doc.addObject("Part::Feature", f"{target.Label}_{ft}")
            feat.Shape = new_shape
            doc.recompute()
            return {
                "status": "ok",
                "feature": ft,
                "operation": op,
                "result_object": feat.Name,
                "is_closed": new_shape.isClosed(),
                "is_valid": new_shape.isValid(),
                "volume_mm3": round(new_shape.Volume, 2),
            }
        else:
            target.Shape = new_shape
            doc.recompute()
            return {
                "status": "ok",
                "feature": ft,
                "operation": op,
                "result_object": target.Name,
                "is_closed": new_shape.isClosed(),
                "is_valid": new_shape.isValid(),
                "volume_mm3": round(new_shape.Volume, 2),
            }

    # Standalone new object
    obj = doc.addObject("Part::Feature", f"SmartFeature_{ft}")
    obj.Shape = feat_shape
    doc.recompute()

    return {
        "status": "ok",
        "feature": ft,
        "operation": "new_object",
        "result_object": obj.Name,
        "is_closed": feat_shape.isClosed(),
        "is_valid": feat_shape.isValid(),
        "volume_mm3": round(feat_shape.Volume, 2),
    }
