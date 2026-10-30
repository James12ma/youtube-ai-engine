"""Personnages cartoon temporaires, riggés (armature + parentage aux os + IK + clés de forme)."""
import math
import bpy
from mathutils import Matrix, Vector

from . import geo

ARM_LEN = 0.44  # segment de bras (m) — proportions fixes, pas de bras élastiques


def _bone(eb, name, head, tail, parent=None):
    b = eb.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.roll = 0.0
    if parent:
        b.parent = eb[parent]
        b.use_connect = (Vector(head) - eb[parent].tail).length < 1e-6
    return b


def _limb_mesh(name, rig, bone_name, radius, mat):
    """Cylindre aligné sur l'os (Y de l'os -> Z du cylindre), parenté à l'os."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone_name]
    length = pb.length
    ob = geo.cylinder(name, radius, length, (0, 0, 0), mat, segs=20)
    bone_world = rig.matrix_world @ pb.matrix
    ob.matrix_world = bone_world @ Matrix.Translation((0, length / 2, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    geo.parent_keep(ob, rig, bone_name)
    return ob


def build(cfg, side):
    """side = +1 : le bras de poussée est du côté -X (vers le centre). Retourne un dict d'objets."""
    name, x0, y0 = cfg["name"], cfg["x"], cfg["y"]
    skin = geo.material(f"{name}_skin", cfg["skin"], 0.55)
    shirt = geo.material(f"{name}_shirt", cfg["shirt"], 0.8)
    dark = geo.material("eye_dark", (0.02, 0.02, 0.02), 0.2)
    white = geo.material("eye_white", (0.95, 0.95, 0.95), 0.3)
    hair = geo.material(f"{name}_hair", (0.03, 0.02, 0.02), 0.6)
    lip = geo.material(f"{name}_mouth", (0.25, 0.06, 0.07), 0.5)

    arm_data = bpy.data.armatures.new(f"{name}_rig")
    rig = bpy.data.objects.new(f"{name}_rig", arm_data)
    bpy.context.scene.collection.objects.link(rig)
    rig.location = (x0, y0, 0)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    _bone(eb, "root", (0, 0, 0), (0, 0, 0.85))
    _bone(eb, "spine", (0, 0, 0.85), (0, 0, 1.42), "root")
    _bone(eb, "neck", (0, 0, 1.42), (0, 0, 1.52), "spine")
    _bone(eb, "head", (0, 0, 1.52), (0, 0, 1.85), "neck")
    for tag, s in (("in", -side), ("out", side)):  # "in" = bras côté centre de la scène
        _bone(eb, f"upper.{tag}", (s * 0.20, 0, 1.40), (s * 0.22, 0.06, 1.40 - 0.4349), "spine")
        up = eb[f"upper.{tag}"].tail.copy()
        _bone(eb, f"fore.{tag}", up, (s * 0.23, 0.0, up.z - 0.4349), f"upper.{tag}")
    for tag, s in (("L", -1), ("R", 1)):
        _bone(eb, f"brow.{tag}", (s * 0.065, -0.172, 1.752), (s * 0.065, -0.172, 1.782), "head")
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"

    parts = {}
    # Torse, cou, tête
    torso = geo.cylinder(f"{name}_torso", 0.17, 0.60, (x0, y0, 1.13), shirt, radius2=0.15)
    torso.scale = (1.0, 0.75, 1.0)
    geo.parent_keep(torso, rig, "spine")
    parts["torso"] = torso
    neck = geo.cylinder(f"{name}_neck", 0.05, 0.12, (x0, y0, 1.47), skin)
    geo.parent_keep(neck, rig, "neck")
    head = geo.sphere(f"{name}_head", 0.17, (x0, y0, 1.68), skin)
    head.scale = (0.95, 0.92, 1.05)
    parts["head"] = head
    face = [head]
    face.append(geo.sphere(f"{name}_nose", 0.034, (x0, y0 - 0.175, 1.655), skin))
    for s in (-1, 1):
        face.append(geo.sphere(f"{name}_eye{s}", 0.042, (x0 + s * 0.062, y0 - 0.135, 1.71), white))
        face.append(geo.sphere(f"{name}_pupil{s}", 0.021, (x0 + s * 0.062, y0 - 0.172, 1.71), dark))
        face.append(geo.sphere(f"{name}_ear{s}", 0.035, (x0 + s * 0.165, y0, 1.68), skin, scale=(0.5, 1, 1.2)))
    if cfg.get("bun"):
        face.append(geo.sphere(f"{name}_hair", 0.172, (x0, y0 + 0.01, 1.71), hair, scale=(1.0, 0.95, 0.85)))
        face.append(geo.sphere(f"{name}_bun", 0.07, (x0, y0 + 0.13, 1.66), hair))
    else:
        face.append(geo.sphere(f"{name}_hair", 0.168, (x0, y0 + 0.015, 1.74), hair, scale=(1.0, 0.98, 0.7)))
        face.append(geo.sphere(f"{name}_beard", 0.12, (x0, y0 - 0.07, 1.585), hair, scale=(1.05, 0.9, 0.55)))
    for ob in face:
        geo.parent_keep(ob, rig, "head")

    # Bouche avec clés de forme (expressions faciales)
    mouth = geo.sphere(f"{name}_mouth", 1.0, (x0, y0 - 0.163, 1.605), lip, segs=24)
    mouth.scale = (0.055, 0.015, 0.016)
    mouth.shape_key_add(name="Basis")
    k_o = mouth.shape_key_add(name="O", from_mix=False)
    k_smirk = mouth.shape_key_add(name="smirk", from_mix=False)
    for i, v in enumerate(mouth.data.vertices):
        co = v.co
        k_o.data[i].co = Vector((co.x * 0.6, co.y, co.z * 3.2))
        k_smirk.data[i].co = Vector((co.x, co.y, co.z + co.x * 0.9 * side))
    geo.parent_keep(mouth, rig, "head")
    parts["mouth"] = mouth

    # Sourcils (os dédiés -> animables en translation)
    for tag in ("L", "R"):
        s = -1 if tag == "L" else 1
        brow = geo.box(f"{name}_brow{tag}", (0.07, 0.02, 0.016), (x0 + s * 0.065, y0 - 0.172, 1.762), hair)
        geo.parent_keep(brow, rig, f"brow.{tag}")

    # Bras + mains
    for tag in ("in", "out"):
        _limb_mesh(f"{name}_upper.{tag}", rig, f"upper.{tag}", 0.055, shirt)
        _limb_mesh(f"{name}_fore.{tag}", rig, f"fore.{tag}", 0.045, shirt)
        bpy.context.view_layer.update()
        tip = rig.matrix_world @ rig.pose.bones[f"fore.{tag}"].tail
        hand = geo.sphere(f"{name}_hand.{tag}", 0.045, tip, skin)
        geo.parent_keep(hand, rig, f"fore.{tag}")
        parts[f"hand.{tag}"] = hand

    # IK sur le bras intérieur : cible + pôle (empties animables)
    tip = rig.matrix_world @ rig.pose.bones["fore.in"].tail
    target = bpy.data.objects.new(f"{name}_ik_target", None)
    target.location = tip
    pole = bpy.data.objects.new(f"{name}_ik_pole", None)
    pole.location = (x0 - side * 0.25, y0 + 0.8, 0.9)  # coude vers l'arrière et le bas
    for e in (target, pole):
        e.empty_display_size = 0.05
        bpy.context.scene.collection.objects.link(e)
    ik = rig.pose.bones["fore.in"].constraints.new("IK")
    ik.target, ik.pole_target, ik.chain_count = target, pole, 2
    ik.pole_angle = math.radians(135 if side > 0 else 45)  # mesuré : coude vers le bas/extérieur

    parts.update(rig=rig, ik_target=target, ik_pole=pole, rest_tip=tip.copy())
    return parts
