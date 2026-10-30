"""Construction procédurale de la scène + animation + solveur de contact main/tasse."""
import json
import math
import bpy
from mathutils import Vector

from . import characters, geo


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def kitchen(cfg):
    top = cfg["counter_top_z"]
    white = geo.material("cabinet_white", (0.85, 0.83, 0.78), 0.45)
    wood = geo.material("counter_wood", (0.55, 0.32, 0.15), 0.35)
    wall = geo.material("wall_cream", (0.92, 0.84, 0.70), 0.9)
    floor = geo.material("floor", (0.45, 0.32, 0.22), 0.6)
    green = geo.material("plant", (0.12, 0.38, 0.12), 0.7)
    pot_terra = geo.material("terracotta", (0.65, 0.33, 0.20), 0.7)
    window = geo.material("window", (1.0, 0.92, 0.75), 0.2, emission=1.5)

    geo.plane("floor", 10, (0, 0.5, 0), floor)
    geo.plane("back_wall", 10, (0, 1.5, 2.5), wall, rot=(math.radians(90), 0, 0))
    # Îlot central (premier plan) + plan de travail bois
    geo.box("island", (2.4, 0.6, top - 0.04), (0, 0.30, (top - 0.04) / 2), white, bevel=0.01)
    geo.box("island_top", (2.5, 0.66, 0.04), (0, 0.30, top - 0.02), wood, bevel=0.004)
    # Meubles du fond
    geo.box("back_cabinets", (3.6, 0.25, 0.9), (0, 1.36, 0.45), white, bevel=0.01)
    geo.box("back_top", (3.6, 0.28, 0.04), (0, 1.35, 0.92), wood)
    for i, x in enumerate((-1.3, -0.65, 0.65, 1.3)):
        geo.box(f"upper_cab{i}", (0.6, 0.3, 0.7), (x, 1.34, 1.95), white, bevel=0.01)
    geo.box("window", (0.7, 0.02, 0.6), (0.0, 1.49, 1.85), window)
    for i, x in enumerate((-1.0, 1.0)):
        geo.cylinder(f"plant_pot{i}", 0.07, 0.12, (x, 1.33, 1.0), pot_terra)
        geo.sphere(f"plant{i}", 0.13, (x, 1.33, 1.13), green, scale=(1, 1, 0.9))


def props(cfg):
    top, m = cfg["counter_top_z"], cfg["mug"]
    yellow = geo.material("mug_yellow", (0.95, 0.75, 0.15), 0.35)
    glass = geo.material("pot_glass", (0.25, 0.15, 0.08), 0.15)
    black = geo.material("plastic_black", (0.03, 0.03, 0.03), 0.4)
    mug = geo.cylinder("mug", m["radius"], m["height"], (m["x"], m["y"], top + m["height"] / 2), yellow)
    handle = geo.torus("mug_handle", 0.032, 0.009, (m["x"] - m["radius"] - 0.012, m["y"], top + m["height"] / 2),
                       yellow, rot=(math.radians(90), 0, 0))
    geo.parent_keep(handle, mug)  # anse à l'opposé de la main qui pousse
    p = cfg["pot"]
    pot = geo.cylinder("coffee_pot", 0.07, 0.16, (p["x"], p["y"], top + 0.08), glass, radius2=0.055)
    lid = geo.cylinder("pot_lid", 0.058, 0.03, (p["x"], p["y"], top + 0.175), black)
    phandle = geo.torus("pot_handle", 0.045, 0.012, (p["x"] - 0.08, p["y"], top + 0.09), black,
                        rot=(math.radians(90), 0, 0))
    for ob in (lid, phandle):
        geo.parent_keep(ob, pot)
    return mug, pot


def camera_and_lights(cfg):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 15
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0.0, -0.45, cfg["counter_top_z"] + 0.06)  # caméra basse, au ras du plan de travail
    direction = Vector((0.0, 0.85, 1.36)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam

    key = bpy.data.lights.new("key", "AREA")
    key.energy, key.size = 180, 1.6
    key_ob = bpy.data.objects.new("key", key)
    key_ob.location = (-1.2, -1.0, 2.6)
    key_ob.rotation_euler = (Vector((0, 0.6, 1.2)) - key_ob.location).to_track_quat("-Z", "Y").to_euler()
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy, sun.color = 2.5, (1.0, 0.85, 0.65)
    sun_ob = bpy.data.objects.new("sun", sun)
    sun_ob.rotation_euler = (math.radians(55), 0, math.radians(200))
    for ob in (key_ob, sun_ob):
        bpy.context.scene.collection.objects.link(ob)
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.8, 0.65, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    bpy.context.scene.world = world
    vs = bpy.context.scene.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            vs.look = look
            break
        except TypeError:
            pass
    return cam


def _key(obj, path, frame, value=None, index=-1):
    if value is not None:
        setattr(obj, path, value) if index == -1 else getattr(obj, path).__setitem__(index, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def animate(cfg, a, b):
    t, m = cfg["timeline"], cfg["mug"]
    top, rh = cfg["counter_top_z"], cfg["hand_radius"]
    zc = top + m["height"] / 2 + 0.005
    contact_x = m["x"] + m["radius"] + rh
    tgt = a["ik_target"]
    rest = a["rest_tip"]
    path = [
        (1, rest), (t["reach_start"], rest),
        (t["reach_start"] + 13, Vector((contact_x + 0.08, 0.50, top + 0.12))),  # approche par la droite, jamais au-dessus de la tasse
        (t["pre_contact"], Vector((contact_x + 0.015, m["y"], zc))),
        (t["contact"], Vector((contact_x, m["y"], zc))),
        (t["push_end"], Vector((contact_x - cfg["push_distance"], m["y"], zc))),
        (t["push_end"] + 13, Vector((contact_x - cfg["push_distance"] + 0.08, 0.50, top + 0.12))),
        (t["retract_end"], rest), (cfg["frames"], rest),
    ]
    for f, loc in path:
        _key(tgt, "location", f, loc.copy())

    rig_a, rig_b = a["rig"], b["rig"]
    spine, head_a = rig_a.pose.bones["spine"], rig_a.pose.bones["head"]
    for f, ang in ((t["reach_start"], 0), (t["pre_contact"], 12), (t["push_end"], 14), (t["retract_end"], 0)):
        _key(spine, "rotation_euler", f, math.radians(ang), index=0)
    for f, ang in ((t["reach_start"], 0), (t["pre_contact"], 14), (t["push_end"], 16), (t["retract_end"] + 5, 4)):
        _key(head_a, "rotation_euler", f, math.radians(ang), index=0)
    smirk = a["mouth"].data.shape_keys.key_blocks["smirk"]
    for f, v in ((t["pre_contact"], 0), (t["contact"] + 5, 1.0), (cfg["frames"], 1.0)):
        smirk.value = v
        smirk.keyframe_insert("value", frame=f)

    # Personnage B : petite respiration, tournée de tête vers la tasse, surprise
    head_b = rig_b.pose.bones["head"]
    for f, ang in ((1, 0), (t["head_turn_start"], 0), (t["head_turn_end"], cfg["head_turn_deg"]),
                   (cfg["frames"], cfg["head_turn_deg"])):
        _key(head_b, "rotation_euler", f, math.radians(ang), index=1)
    for f, ang in ((1, 0), (t["head_turn_start"], 0), (t["react_peak"], -6), (cfg["frames"], -6)):
        _key(head_b, "rotation_euler", f, math.radians(ang), index=0)  # léger recul de surprise
    for tag in ("L", "R"):
        brow = rig_b.pose.bones[f"brow.{tag}"]
        for f, y in ((1, 0), (t["react_start"], 0), (t["react_peak"], 0.022), (cfg["frames"], 0.022)):
            _key(brow, "location", f, y, index=1)
    o = b["mouth"].data.shape_keys.key_blocks["O"]
    for f, v in ((1, 0), (t["react_start"], 0), (t["react_peak"], 1.0), (cfg["frames"], 1.0)):
        o.value = v
        o.keyframe_insert("value", frame=f)


def world_pos(ob):
    """Position monde ÉVALUÉE (IK + parentage à l'os appliqués) — même valeur que le rendu."""
    dg = bpy.context.evaluated_depsgraph_get()
    return ob.evaluated_get(dg).matrix_world.translation.copy()


def solve_mug_contact(cfg, hand, mug):
    """Contact cinématique : la tasse est repoussée exactement par la surface de la main.
    Garantit l'absence d'interpénétration et l'immobilité hors contact. Cuit une clé par image."""
    m, rh = cfg["mug"], cfg["hand_radius"]
    top = cfg["counter_top_z"]
    scene = bpy.context.scene
    mug_x = m["x"]
    contact_frames = []
    for f in range(1, cfg["frames"] + 1):
        scene.frame_set(f)
        h = world_pos(hand)
        aligned = abs(h.y - m["y"]) < m["radius"] and top < h.z < top + m["height"] + rh
        if aligned:
            limit = h.x - (rh + m["radius"])
            if limit < mug_x:
                mug_x = limit
                contact_frames.append(f)
        mug.location = (mug_x, m["y"], top + m["height"] / 2)
        mug.keyframe_insert("location", frame=f)
    return contact_frames


def export_state(cfg, a, b, mug, pot, path):
    """Positions/rotations mesurées à chaque image (pour la QA sans Blender)."""
    scene = bpy.context.scene
    rig_b = b["rig"]
    rest_rot = (rig_b.matrix_world @ rig_b.data.bones["head"].matrix_local).to_3x3()
    frames = []
    for f in range(1, cfg["frames"] + 1):
        scene.frame_set(f)
        pose_rot = (rig_b.matrix_world @ rig_b.pose.bones["head"].matrix).to_3x3()
        face = (pose_rot @ rest_rot.inverted()) @ Vector((0, -1, 0))
        frames.append({
            "frame": f,
            "hand_a": list(world_pos(a["hand.in"])),
            "ik_target_a": list(world_pos(a["ik_target"])),
            "mug": list(world_pos(mug)),
            "hand_a_in_torso_local": list(a["torso"].evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.inverted() @ world_pos(a["hand.in"])),
            "pot": list(world_pos(pot)),
            "head_b_yaw_deg": math.degrees(math.atan2(face.x, -face.y)),
            "mouth_b_O": b["mouth"].data.shape_keys.key_blocks["O"].value,
            "mouth_a_smirk": a["mouth"].data.shape_keys.key_blocks["smirk"].value,
            "brow_b_raise": rig_b.pose.bones["brow.L"].location.y,
        })
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"config": cfg, "frames": frames}, fh, indent=1)


def build(cfg):
    reset()
    scene = bpy.context.scene
    cfg["frames"] = cfg["fps"] * cfg["seconds"]
    scene.render.fps = cfg["fps"]
    scene.frame_start, scene.frame_end = 1, cfg["frames"]
    kitchen(cfg)
    mug, pot = props(cfg)
    a = characters.build(dict(cfg["fig_a"]), side=+1)
    b = characters.build(dict(cfg["fig_b"], bun=True), side=-1)
    camera_and_lights(cfg)
    animate(cfg, a, b)
    contacts = solve_mug_contact(cfg, a["hand.in"], mug)
    return {"a": a, "b": b, "mug": mug, "pot": pot, "contact_frames": contacts}
