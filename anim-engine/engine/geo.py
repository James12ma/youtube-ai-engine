"""Primitives géométriques sans opérateurs (bmesh), utilisables en headless."""
import math
import bmesh
import bpy
from mathutils import Matrix, Vector


def material(name, rgb, rough=0.5, emission=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*rgb, 1.0)
    p.inputs["Roughness"].default_value = rough
    if emission:
        p.inputs["Emission Color"].default_value = (*rgb, 1.0)
        p.inputs["Emission Strength"].default_value = emission
    return m


def _obj_from_bm(name, bm, mat=None, smooth=True, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def box(name, size, loc, mat=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    ob = _obj_from_bm(name, bm, mat, smooth=False)
    ob.location = loc
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return ob


def sphere(name, radius, loc, mat=None, scale=(1, 1, 1), segs=32):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=radius)
    ob = _obj_from_bm(name, bm, mat)
    ob.location = loc
    ob.scale = scale
    return ob


def cylinder(name, radius, depth, loc, mat=None, segs=40, cap=True, radius2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs,
                          radius1=radius, radius2=radius if radius2 is None else radius2, depth=depth)
    ob = _obj_from_bm(name, bm, mat)
    ob.location = loc
    return ob


def torus(name, major, minor, loc, mat=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    seg_major, seg_minor = 32, 12
    verts = []
    for i in range(seg_major):
        a = 2 * math.pi * i / seg_major
        ring = []
        for j in range(seg_minor):
            b = 2 * math.pi * j / seg_minor
            r = major + minor * math.cos(b)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
        verts.append(ring)
    for i in range(seg_major):
        for j in range(seg_minor):
            bm.faces.new((verts[i][j], verts[(i + 1) % seg_major][j],
                          verts[(i + 1) % seg_major][(j + 1) % seg_minor], verts[i][(j + 1) % seg_minor]))
    ob = _obj_from_bm(name, bm, mat)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def plane(name, size, loc, mat=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    ob = _obj_from_bm(name, bm, mat, smooth=False)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def parent_keep(child, parent, bone=None):
    """Parente en conservant la transformation monde (y compris parentage à un os)."""
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    if bone:
        child.parent_type = "BONE"
        child.parent_bone = bone
    bpy.context.view_layer.update()
    child.matrix_world = mw
