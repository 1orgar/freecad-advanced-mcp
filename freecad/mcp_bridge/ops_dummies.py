"""Parametric reference dummy generator for FreeCAD MCP.

Inserts translucent dimensionally accurate models of phones, plugs, power supplies,
and fasteners into the active document for visual fit, clearance checking, and clash detection.
"""

import math
import FreeCAD
import FreeCADGui
import Part


def insert_reference_dummy(
    dummy_type="iphone_15_pro",
    placement=None,
    document_name=None,
    label=None,
    transparency=50,
):
    """Insert a reference dummy component into the FreeCAD document.

    Parameters:
    - dummy_type: Component type:
        - "iphone_15_pro" (146.6 x 70.6 x 8.25 mm)
        - "iphone_15_pro_max" (159.9 x 76.7 x 8.25 mm)
        - "generic_phone" (150.0 x 75.0 x 9.0 mm)
        - "usb_c_plug" (standard USB Type-C plug with boot and cable)
        - "mean_well_rs25" (Mean Well RS-25-xx enclosed power supply)
        - "mikrotik_crs305" (MikroTik CRS305-1G-4S+IN switch)
        - "screw_m3" (ISO M3 socket head / pan head screw)
        - "screw_m6" (Rack mount M6 truss screw)
    - placement: Optional dict with "position": [x, y, z] and "rotation": [yaw, pitch, roll] or [axis_x, axis_y, axis_z, angle_deg].
    - document_name: Optional document name.
    - label: Custom label.
    - transparency: 0 to 100 visual transparency percent (default 50).
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    dtype = (dummy_type or "iphone_15_pro").lower().strip()
    shape = None
    color = (0.2, 0.65, 0.95)  # Default translucent cyber cyan

    if dtype in ("iphone_15_pro", "iphone15pro", "phone_pro"):
        shape = _make_phone(146.6, 70.6, 8.25, corner_r=10.0, cam_bump=True)
    elif dtype in ("iphone_15_pro_max", "iphone15promax", "phone_pro_max"):
        shape = _make_phone(159.9, 76.7, 8.25, corner_r=10.5, cam_bump=True)
    elif dtype in ("generic_phone", "phone"):
        shape = _make_phone(150.0, 75.0, 9.0, corner_r=8.0, cam_bump=False)
    elif dtype in ("usb_c_plug", "usb_c", "usbc"):
        shape = _make_usbc_plug()
        color = (0.3, 0.8, 0.4)
    elif dtype in ("mean_well_rs25", "rs25", "rs-25"):
        shape = _make_mean_well_rs25()
        color = (0.95, 0.6, 0.15)
    elif dtype in ("mikrotik_crs305", "crs305"):
        shape = _make_crs305()
        color = (0.2, 0.8, 0.8)
    elif dtype in ("screw_m3", "m3"):
        shape = _make_screw(3.0, 5.5, 12.0)
        color = (0.8, 0.8, 0.85)
    elif dtype in ("screw_m6", "m6"):
        shape = _make_screw(6.0, 11.5, 16.0)
        color = (0.8, 0.8, 0.85)
    elif dtype in ("raspberry_pi_5", "rpi5", "pi5"):
        shape = _make_raspberry_pi_5()
        color = (0.1, 0.65, 0.2)
    elif dtype in ("fan_40mm", "fan40"):
        shape = _make_fan(40.0, 10.0)
        color = (0.15, 0.15, 0.2)
    elif dtype in ("fan_80mm", "fan80"):
        shape = _make_fan(80.0, 25.0)
        color = (0.15, 0.15, 0.2)
    elif dtype in ("c14_socket", "c14"):
        shape = _make_c14_socket()
        color = (0.2, 0.2, 0.25)
    elif dtype in ("keystone_rj45", "keystone"):
        shape = _make_keystone_rj45()
        color = (0.85, 0.85, 0.9)
    elif dtype in ("din_rail_35mm", "din_rail", "din35"):
        shape = _make_din_rail_35mm(100.0)
        color = (0.75, 0.75, 0.8)
    elif dtype in ("mean_well_lrs35", "lrs35", "lrs-35"):
        shape = _make_mean_well_lrs35()
        color = (0.9, 0.7, 0.2)
    else:
        return {
            "error": f"Unknown dummy_type '{dummy_type}'. Supported: iphone_15_pro, iphone_15_pro_max, generic_phone, usb_c_plug, mean_well_rs25, mean_well_lrs35, mikrotik_crs305, raspberry_pi_5, fan_40mm, fan_80mm, c14_socket, keystone_rj45, din_rail_35mm, screw_m3, screw_m6."
        }

    # Create FreeCAD document object
    obj_name = f"Dummy_{dtype.replace('-', '_')}"
    feat = doc.addObject("Part::Feature", obj_name)
    feat.Label = label or f"[DUMMY] {dtype}"
    feat.Shape = shape

    # Apply placement if provided
    if placement and isinstance(placement, dict):
        pos = placement.get("position", [0, 0, 0])
        rot = placement.get("rotation", [0, 0, 0])
        p_vec = FreeCAD.Vector(*pos)
        if len(rot) == 3:
            # Yaw, pitch, roll
            r_rot = FreeCAD.Rotation(rot[0], rot[1], rot[2])
        elif len(rot) == 4:
            # Axis-angle [ax, ay, az, angle_deg]
            r_rot = FreeCAD.Rotation(FreeCAD.Vector(rot[0], rot[1], rot[2]), rot[3])
        else:
            r_rot = FreeCAD.Rotation()
        feat.Placement = FreeCAD.Placement(p_vec, r_rot)

    doc.recompute()

    # Apply visual styles in FreeCAD GUI
    gui_doc = FreeCADGui.getDocument(doc.Name)
    if gui_doc:
        vo = gui_doc.getObject(feat.Name)
        if vo:
            try:
                vo.ShapeColor = color
                vo.Transparency = int(transparency)
                vo.DisplayMode = "Flat Lines"
            except Exception:
                pass

    bb = feat.Shape.BoundBox
    return {
        "status": "ok",
        "document": doc.Name,
        "object_name": feat.Name,
        "label": feat.Label,
        "dummy_type": dtype,
        "dimensions_mm": [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
        "bounding_box": {
            "min": [round(bb.XMin, 2), round(bb.YMin, 2), round(bb.ZMin, 2)],
            "max": [round(bb.XMax, 2), round(bb.YMax, 2), round(bb.ZMax, 2)],
        },
    }


def _make_phone(length, width, thickness, corner_r=10.0, cam_bump=True):
    """Create rounded phone body with optional camera bump."""
    # Centered at (0, 0, 0)
    box = Part.makeBox(width, length, thickness, FreeCAD.Vector(-width/2, -length/2, 0))
    # Fillet vertical edges
    vert_edges = [e for e in box.Edges if abs(e.Length - thickness) < 1e-3 and abs(e.BoundBox.ZLength - thickness) < 1e-3]
    body = box.makeFillet(corner_r, vert_edges) if vert_edges else box

    if cam_bump:
        bump_w, bump_l, bump_h = 38.0, 38.0, 4.3
        bump_x = -width/2 + 2.0
        bump_y = length/2 - bump_l - 2.0
        bump = Part.makeBox(bump_w, bump_l, bump_h, FreeCAD.Vector(bump_x, bump_y, thickness))
        # Fillet bump corners
        bump_edges = [e for e in bump.Edges if abs(e.Length - bump_h) < 1e-3]
        if bump_edges:
            bump = bump.makeFillet(4.0, bump_edges)
        body = body.fuse(bump)

    return body


def _make_usbc_plug():
    """Create standard USB Type-C plug with metallic tip, plastic boot, and cable."""
    # Metallic tip: 8.3 x 2.6 x 6.6 mm
    tip_box = Part.makeBox(8.3, 2.6, 6.6, FreeCAD.Vector(-4.15, -1.3, 0))
    tip_edges = [e for e in tip_box.Edges if abs(e.Length - 6.6) < 1e-3]
    tip = tip_box.makeFillet(1.1, tip_edges) if tip_edges else tip_box

    # Overmold housing: 12.5 x 6.5 x 26.0 mm starting at Z = 6.6
    boot_box = Part.makeBox(12.5, 6.5, 26.0, FreeCAD.Vector(-6.25, -3.25, 6.6))
    boot_edges = [e for e in boot_box.Edges if abs(e.Length - 26.0) < 1e-3]
    boot = boot_box.makeFillet(1.5, boot_edges) if boot_edges else boot_box

    # Cable strain relief: D=4.2 cylinder, length 30mm starting at Z = 32.6
    cable = Part.makeCylinder(2.1, 30.0, FreeCAD.Vector(0, 0, 32.6), FreeCAD.Vector(0, 0, 1))

    return tip.fuse(boot).fuse(cable)


def _make_mean_well_rs25():
    """Create Mean Well RS-25 enclosed power supply: 78 x 51 x 28 mm."""
    # Main metal case
    case = Part.makeBox(51.0, 78.0, 28.0, FreeCAD.Vector(-25.5, -39.0, 0))
    # Front terminal barrier cutout: 42 x 15 x 12 mm
    tb_cut = Part.makeBox(42.0, 15.0, 14.0, FreeCAD.Vector(-21.0, -39.0, 14.0))
    body = case.cut(tb_cut)
    return body


def _make_crs305():
    """Create MikroTik CRS305-1G-4S+IN switch body: 115 x 141 x 28 mm."""
    # Width 115, Depth 141, Height 28
    body = Part.makeBox(115.0, 141.0, 28.0, FreeCAD.Vector(-57.5, -70.5, 0))
    return body


def _make_screw(d, head_d, length):
    """Create standard socket/pan head screw."""
    head_h = d * 0.7
    shaft = Part.makeCylinder(d / 2.0, length, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, -1))
    head = Part.makeCylinder(head_d / 2.0, head_h, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
    return shaft.fuse(head)


def _make_raspberry_pi_5():
    """Create Raspberry Pi 5 board: 85.0 x 56.0 x 17.0 mm with ports and M2.5 holes."""
    # Main PCB: 85 x 56 x 1.6 mm, corner radius 3.0 mm
    pcb = Part.makeBox(85.0, 56.0, 1.6, FreeCAD.Vector(-42.5, -28.0, 0))
    # 4x M2.5 mounting holes: 58.0 x 49.0 mm pitch (dx=29.0, dy=24.5 from center)
    for dx in (-29.0, 29.0):
        for dy in (-24.5, 24.5):
            h = Part.makeCylinder(1.35, 10.0, FreeCAD.Vector(dx, dy, -5.0), FreeCAD.Vector(0, 0, 1))
            pcb = pcb.cut(h)

    # Ethernet + Dual USB 3.0 + Dual USB 2.0 blocks
    eth_usb = Part.makeBox(22.0, 52.0, 15.0, FreeCAD.Vector(42.5 - 22.0, -26.0, 1.6))
    # Dual micro-HDMI + USB-C power
    hdmi = Part.makeBox(35.0, 10.0, 6.0, FreeCAD.Vector(-25.0, -28.0, 1.6))
    return pcb.fuse(eth_usb).fuse(hdmi)


def _make_fan(size=40.0, thickness=10.0):
    """Create standard PC cooling fan dummy: housing, rotor hub, 4 corner holes."""
    s = float(size)
    t = float(thickness)
    housing = Part.makeBox(s, s, t, FreeCAD.Vector(-s / 2.0, -s / 2.0, 0))
    # Central duct hole
    duct_r = (s / 2.0) - 2.0
    duct = Part.makeCylinder(duct_r, t + 2.0, FreeCAD.Vector(0, 0, -1.0), FreeCAD.Vector(0, 0, 1))
    frame = housing.cut(duct)

    # Rotor center hub
    hub = Part.makeCylinder(duct_r * 0.45, t, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))

    # Corner screw holes
    pitch = 32.0 if s <= 50.0 else (50.0 if s <= 70.0 else 71.5)
    hp = pitch / 2.0
    res = frame.fuse(hub)
    for dx in (-hp, hp):
        for dy in (-hp, hp):
            ch = Part.makeCylinder(1.7, t + 2.0, FreeCAD.Vector(dx, dy, -1.0), FreeCAD.Vector(0, 0, 1))
            res = res.cut(ch)
    return res


def _make_c14_socket():
    """Create standard C14 AC socket: 31 x 24 x 26 mm with mounting flange."""
    body = Part.makeBox(27.0, 19.5, 26.0, FreeCAD.Vector(-13.5, -9.75, -26.0))
    flange = Part.makeBox(48.0, 26.0, 3.0, FreeCAD.Vector(-24.0, -13.0, 0))
    # Mounting holes at +-20 mm
    h1 = Part.makeCylinder(1.7, 10.0, FreeCAD.Vector(-20.0, 0, -5.0), FreeCAD.Vector(0, 0, 1))
    h2 = Part.makeCylinder(1.7, 10.0, FreeCAD.Vector(20.0, 0, -5.0), FreeCAD.Vector(0, 0, 1))
    return body.fuse(flange).cut(h1).cut(h2)


def _make_keystone_rj45():
    """Create standard Keystone RJ45 jack dummy: 16.5 x 22.0 x 30.0 mm."""
    return Part.makeBox(16.5, 22.0, 30.0, FreeCAD.Vector(-8.25, -11.0, -15.0))


def _make_din_rail_35mm(length=100.0):
    """Create standard EN 50022 top-hat DIN rail 35 x 7.5 mm."""
    l = float(length)
    # Extrude cross-section
    pts = [
        FreeCAD.Vector(-17.5, 0, 0), FreeCAD.Vector(-17.5, 1.0, 0),
        FreeCAD.Vector(-12.5, 1.0, 0), FreeCAD.Vector(-12.5, 7.5, 0),
        FreeCAD.Vector(12.5, 7.5, 0), FreeCAD.Vector(12.5, 1.0, 0),
        FreeCAD.Vector(17.5, 1.0, 0), FreeCAD.Vector(17.5, 0, 0),
        FreeCAD.Vector(13.5, 0, 0), FreeCAD.Vector(13.5, 6.5, 0),
        FreeCAD.Vector(-13.5, 6.5, 0), FreeCAD.Vector(-13.5, 0, 0),
        FreeCAD.Vector(-17.5, 0, 0),
    ]
    poly = Part.makePolygon(pts)
    face = Part.Face(poly)
    return face.extrude(FreeCAD.Vector(0, 0, l))


def _make_mean_well_lrs35():
    """Create Mean Well LRS-35 enclosed power supply: 99 x 82 x 30 mm."""
    case = Part.makeBox(82.0, 99.0, 30.0, FreeCAD.Vector(-41.0, -49.5, 0))
    tb_cut = Part.makeBox(68.0, 18.0, 16.0, FreeCAD.Vector(-34.0, -49.5, 14.0))
    return case.cut(tb_cut)


def cut_component_cavity(
    target_object,
    dummy_type,
    placement=None,
    clearance=0.3,
    document_name=None,
):
    """Cut an accurate mounting cavity for a hardware component directly from target object.

    Parameters:
    - target_object: Target object name (PartDesign::Body or Part::Feature).
    - dummy_type: Component type (e.g. 'c14_socket', 'keystone_rj45', 'raspberry_pi_5', 'fan_40mm', 'mean_well_rs25').
    - placement: Optional dict with 'position': [x,y,z] and 'rotation': [yaw,pitch,roll].
    - clearance: Fit tolerance in mm (default 0.3 mm for 3D printing).
    - document_name: Optional document name.
    """
    doc = _resolve_doc(document_name)
    if not doc:
        return {"error": "No open FreeCAD document available."}

    target = doc.getObject(target_object)
    if not target:
        return {"error": f"Target object '{target_object}' not found."}

    target_shape = getattr(target, "Shape", None)
    if not target_shape or target_shape.isNull():
        return {"error": f"Target object '{target_object}' has no valid Shape."}

    dtype = dummy_type.lower().strip()
    if dtype in ("raspberry_pi_5", "rpi5"):
        dummy = _make_raspberry_pi_5()
    elif dtype in ("fan_40mm", "fan40"):
        dummy = _make_fan(40.0, 10.0)
    elif dtype in ("fan_80mm", "fan80"):
        dummy = _make_fan(80.0, 25.0)
    elif dtype in ("c14_socket", "c14"):
        dummy = _make_c14_socket()
    elif dtype in ("keystone_rj45", "keystone"):
        dummy = _make_keystone_rj45()
    elif dtype in ("mean_well_rs25", "rs25"):
        dummy = _make_mean_well_rs25()
    elif dtype in ("mean_well_lrs35", "lrs35"):
        dummy = _make_mean_well_lrs35()
    elif dtype in ("usb_c_plug", "usbc"):
        dummy = _make_usbc_plug()
    else:
        return {"error": f"Unsupported dummy_type '{dummy_type}' for cavity cut."}

    # Expand dummy by clearance using BoundBox expansion
    cl = float(clearance)
    bb = dummy.BoundBox
    cutter = Part.makeBox(
        bb.XLength + 2.0 * cl,
        bb.YLength + 2.0 * cl,
        bb.ZLength + 2.0 * cl,
        FreeCAD.Vector(bb.XMin - cl, bb.YMin - cl, bb.ZMin - cl),
    )

    # Apply spatial placement
    if placement and isinstance(placement, dict):
        pos = placement.get("position", [0, 0, 0])
        rot = placement.get("rotation", [0, 0, 0])
        p_vec = FreeCAD.Vector(*pos)
        if len(rot) == 3:
            r_rot = FreeCAD.Rotation(rot[0], rot[1], rot[2])
        elif len(rot) == 4:
            r_rot = FreeCAD.Rotation(FreeCAD.Vector(rot[0], rot[1], rot[2]), rot[3])
        else:
            r_rot = FreeCAD.Rotation()
        cutter.Placement = FreeCAD.Placement(p_vec, r_rot)

    new_shape = target_shape.cut(cutter)
    if target.isDerivedFrom("PartDesign::Body"):
        feat = doc.addObject("Part::Feature", f"{target.Label}_Cavity_{dtype}")
        feat.Shape = new_shape
        doc.recompute()
        res_name = feat.Name
    else:
        target.Shape = new_shape
        doc.recompute()
        res_name = target.Name

    return {
        "status": "ok",
        "target_object": target.Name,
        "dummy_type": dtype,
        "clearance_mm": cl,
        "result_object": res_name,
        "is_valid": new_shape.isValid(),
        "is_closed": new_shape.isClosed(),
        "volume_mm3": round(new_shape.Volume, 2),
    }


def _resolve_doc(doc_name=None):
    if doc_name:
        return FreeCAD.getDocument(doc_name)
    return FreeCAD.ActiveDocument

