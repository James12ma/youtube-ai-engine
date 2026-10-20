"""Blender (bpy / Cycles CPU) 3D plate for the "Focus" premium motion prototype.

Editorial monochrome look: paper-white studio floor, glossy black ceramic hero
sphere, 24 satellite dots, a hairline floor grid and a polished orbit ring, lit
by one large soft key so every object casts a long, soft shadow.

All motion is computed in Python (explicit easing, one keyframe per frame) so
timing matches ../timeline.json exactly; Remotion overlays the typography/UI.

Usage (bpy wheel):
    python focus_scene.py --out /path/plates --start 0 --end 389 [--scale 100] [--samples 40]
    python focus_scene.py --save focus_scene.blend      # write editable .blend only
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy  # noqa: I001  (bpy must load before addon_utils)
import addon_utils
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE.parent / "timeline.json").read_text())
B = TL["beats"]
FPS, FRAMES = TL["fps"], TL["frames"]

HERO_R = 1.0
DOT_R = 0.17
N_DOTS = 24


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(f, a, b):
    return clamp((f - a) / float(b - a))


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_back(t, s=1.9):
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def ease_in_back(t, s=1.7):
    return (s + 1) * t ** 3 - s * t ** 2


def ease_out_expo(t):
    return 1 if t >= 1 else 1 - 2 ** (-10 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- scene setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("cycles", default_set=True)


def mat_principled(name, color, rough, metallic=0.0, coat=0.0, coat_rough=0.05, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = coat_rough
    p.inputs["Specular IOR Level"].default_value = spec
    return m


def fade_lines(mat, inner=2.2, outer=3.6):
    """Grid ink fades into the paper with distance from the centre (vignetted grid)."""
    nt = mat.node_tree
    p = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = inner
    rng.inputs["From Max"].default_value = outer
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.05, 0.05, 0.05, 1)
    mix.inputs["B"].default_value = (0.9, 0.9, 0.89, 1)
    nt.links.new(geo.outputs["Position"], length.inputs[0])
    nt.links.new(length.outputs["Value"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])


def add_obj(obj, mat):
    obj.data.materials.append(mat)
    return obj


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def build():
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.render.resolution_x, scn.render.resolution_y = TL["width"], TL["height"]
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 0, FRAMES - 1
    scn.cycles.use_denoising = True
    scn.cycles.denoiser = "OPENIMAGEDENOISE"
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.adaptive_threshold = 0.03
    scn.cycles.max_bounces = 6
    scn.cycles.diffuse_bounces = 3
    scn.cycles.glossy_bounces = 3
    scn.cycles.transmission_bounces = 2
    scn.cycles.caustics_reflective = False
    scn.cycles.caustics_refractive = False
    scn.cycles.blur_glossy = 1.0
    scn.render.use_persistent_data = True
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Base Contrast"
    scn.view_settings.exposure = 0.85
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.color_depth = "8"
    scn.render.film_transparent = False
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.5

    # World: soft neutral fill so shadows never go fully black.
    world = bpy.data.worlds.new("Studio")
    scn.world = world
    world.use_nodes = True
    # Diffuse/camera rays see a bright studio; glossy rays see a dark ceiling, so the
    # black ceramic stays deep black with crisp softbox highlights (classic product trick).
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.55
    dark = nt.nodes.new("ShaderNodeBackground")
    dark.inputs["Color"].default_value = (1, 1, 1, 1)
    dark.inputs["Strength"].default_value = 0.025
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Glossy Ray"], mix.inputs["Fac"])
    nt.links.new(bg.outputs["Background"], mix.inputs[1])
    nt.links.new(dark.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], nt.nodes["World Output"].inputs["Surface"])

    # Paper floor (huge so the frame edges never show a horizon).
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Floor"
    add_obj(floor, mat_principled("Paper", (0.9, 0.9, 0.89), 0.8, spec=0.2))

    # Key: one large soft box upper-left -> long soft shadow toward lower-right.
    bpy.ops.object.light_add(type="AREA", location=(-7.5, 8.0, 7.0))
    key = bpy.context.object
    key.name = "KeySoftbox"
    key.data.shape = "DISK"
    key.data.size = 5.5
    key.data.energy = 3400
    key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat("-Z", "Y").to_euler()

    # Rim strip for a crisp highlight edge on the glossy black objects.
    bpy.ops.object.light_add(type="AREA", location=(6.5, -2.0, 6.0))
    rim = bpy.context.object
    rim.name = "RimStrip"
    rim.data.shape = "RECTANGLE"
    rim.data.size, rim.data.size_y = 0.8, 7.0
    rim.data.energy = 900
    rim.rotation_euler = (Vector((0, 0, 1)) - rim.location).to_track_quat("-Z", "Y").to_euler()
    rim.visible_diffuse = False  # only shows up in reflections, keeps the paper clean

    ceramic = mat_principled("GlossBlackCeramic", (0.008, 0.008, 0.009), 0.45, coat=0.55, coat_rough=0.16, spec=0.06)
    dot_mat = mat_principled("SatinBlack", (0.01, 0.01, 0.011), 0.4, coat=0.8, coat_rough=0.06, spec=0.1)
    line_mat = mat_principled("Graphite", (0.05, 0.05, 0.05), 0.9, spec=0.1)
    fade_lines(line_mat)
    chrome = mat_principled("DarkChrome", (0.55, 0.55, 0.56), 0.12, metallic=1.0)

    # Hero sphere.
    bpy.ops.mesh.primitive_uv_sphere_add(radius=HERO_R, segments=96, ring_count=48, location=(0, 0, HERO_R))
    hero = bpy.context.object
    hero.name = "Hero"
    smooth(hero)
    add_obj(hero, ceramic)

    # Satellite dots: deterministic ring cluster around the hero.
    rnd = random.Random(7)
    dots = []
    tries = 0
    while len(dots) < N_DOTS and tries < 5000:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(1.55, 2.45)
        p = Vector((r * math.cos(a), r * math.sin(a), 0))
        if all((p - q["pos"]).length > 0.52 for q in dots):
            size = DOT_R * rnd.choice([0.55, 0.8, 1.0, 1.0, 1.0, 1.15])
            dots.append({"pos": p, "angle": a, "r": r, "size": size})
    for i, d in enumerate(dots):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=40, ring_count=20, location=d["pos"])
        o = bpy.context.object
        o.name = f"Dot{i:02d}"
        smooth(o)
        add_obj(o, dot_mat)
        d["obj"] = o
    # Pop in from the centre outwards; remove with a clockwise sweep.
    for k, d in enumerate(sorted(dots, key=lambda d: d["r"])):
        d["in_order"] = k
    for k, d in enumerate(sorted(dots, key=lambda d: (-(d["angle"] - math.pi / 2)) % (2 * math.pi))):
        d["out_order"] = k

    # Hairline grid with crosshair overshoot (lines extend past the cluster).
    lines = []
    step, n = 0.62, 4
    span = step * n + 0.55
    for axis in ("x", "y"):
        for k in range(-n, n + 1):
            off = k * step
            bpy.ops.mesh.primitive_cube_add(size=1)
            o = bpy.context.object
            o.name = f"Grid_{axis}{k:+d}"
            if axis == "x":
                o.location = (0, off, 0.004)
                o.scale = (2 * span, 0.008, 0.004)
            else:
                o.location = (off, 0, 0.004)
                o.scale = (0.008, 2 * span, 0.004)
            add_obj(o, line_mat)
            lines.append({"obj": o, "axis": axis, "k": k, "full": 2 * span})

    # Polished orbit ring (appears in act 3).
    bpy.ops.mesh.primitive_torus_add(major_radius=1.62, minor_radius=0.045, major_segments=160, minor_segments=24,
                                     location=(0, 0, HERO_R))
    ring = bpy.context.object
    ring.name = "OrbitRing"
    smooth(ring)
    add_obj(ring, chrome)

    # Camera + aim target.
    bpy.ops.object.empty_add(location=(0, 0, 0))
    target = bpy.context.object
    target.name = "CamTarget"
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "Camera"
    cam.data.lens = 50
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 36
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = hero
    cam.data.dof.aperture_fstop = 5.6
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    scn.camera = cam

    animate(hero, dots, lines, ring, cam, target)
    return scn


# ---------------------------------------------------------------- animation
def hero_z(f):
    a, b = B["hero_drop"]
    contact = a + (b - a) * 0.62
    if f <= contact:
        t = prog(f, a, contact)
        return HERO_R + 7.0 * (1 - t * t)  # gravity-like fall
    t = prog(f, contact, b)
    return HERO_R + 0.22 * math.sin(math.pi * t) * (1 - t)  # one small settle bounce


def hero_squash(f):
    a, b = B["hero_drop"]
    contact = a + (b - a) * 0.62
    t = clamp(1 - abs(f - contact) / 3.0)
    return 1 - 0.08 * t, 1 + 0.04 * t


def dot_scale(d, f):
    a0 = B["dots_in"][0] + d["in_order"] * 1.7
    s_in = ease_out_back(prog(f, a0, a0 + 13)) if f >= a0 else 0.0
    o0 = B["dots_out"][0] + d["out_order"] * 1.6
    s_out = 1 - ease_in_back(prog(f, o0, o0 + 11)) if f >= o0 else 1.0
    return max(0.0, s_in * s_out) * d["size"]


def restless(d, f):
    """Small, nervous drift: the 24 'distractions' never sit still (calms as they appear)."""
    k = d["in_order"]
    amp = 0.05 * ease_out_cubic(prog(f, B["dots_in"][0], B["dots_in"][1] + 20))
    return (amp * math.sin(f * (0.21 + 0.013 * k) + k * 1.7),
            amp * math.cos(f * (0.17 + 0.011 * k) + k * 2.3))


def grid_scale(line, f):
    start = 2 + abs(line["k"]) * 2.5 + (0 if line["axis"] == "x" else 4)
    return max(0.0005, ease_out_expo(prog(f, start, start + 30)))


def ring_state(f):
    a, b = B["ring_in"]
    t = ease_out_cubic(prog(f, a, b))
    scale = lerp(0.001, 1.0, ease_out_back(prog(f, a, b), 1.2)) if f >= a else 0.001
    tilt = lerp(math.radians(85), math.radians(24), t)
    spin = math.radians(lerp(-140, 0, t) + (f - a) * 0.35)
    lift = lerp(0.9, 0.05, t)
    return scale, tilt, spin, lift


def camera_state(f):
    """Continuous move: slow orbit + push-in, tilting to a 3/4 view for the ring act."""
    g = f / (FRAMES - 1)
    az = math.radians(lerp(-10, 12, ease_in_out_sine(g)))
    dist = lerp(15.5, 12.4, ease_in_out_cubic(prog(f, 0, 300)))
    dist = lerp(dist, 10.6, ease_in_out_cubic(prog(f, 290, FRAMES - 1)))
    tilt = math.radians(lerp(16, 34, ease_in_out_cubic(prog(f, 220, 320))))
    aim_off = lerp(1.25, 1.05, ease_in_out_cubic(prog(f, 220, 320)))  # keeps subject in lower 60 %
    fwd = Vector((math.sin(az), math.cos(az), 0))
    target = fwd * aim_off + Vector((0, 0, lerp(0, 0.5, ease_in_out_cubic(prog(f, 220, 320)))))
    pos = target - fwd * dist * math.sin(tilt) + Vector((0, 0, dist * math.cos(tilt)))
    return pos, target


def animate(hero, dots, lines, ring, cam, target):
    for f in range(FRAMES):
        sz, sxy = hero_squash(f)
        hero.location = (0, 0, hero_z(f) - (1 - sz) * HERO_R)
        hero.scale = (sxy, sxy, sz)
        hero.keyframe_insert("location", frame=f)
        hero.keyframe_insert("scale", frame=f)
        for d in dots:
            s = dot_scale(d, f)
            o = d["obj"]
            o.scale = (max(s, 1e-4),) * 3
            jx, jy = restless(d, f)
            o.location = (d["pos"].x + jx, d["pos"].y + jy, max(s, 1e-4))
            o.hide_render = s <= 1e-4
            o.keyframe_insert("scale", frame=f)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("hide_render", frame=f)
        for ln in lines:
            o, s = ln["obj"], grid_scale(ln, f)
            if ln["axis"] == "x":
                o.scale = (ln["full"] * s, 0.008, 0.004)
            else:
                o.scale = (0.008, ln["full"] * s, 0.004)
            o.keyframe_insert("scale", frame=f)
        sc, tilt, spin, lift = ring_state(f)
        ring.scale = (sc, sc, sc)
        ring.rotation_euler = (tilt, 0.25, spin)
        ring.location = (0, 0, HERO_R + lift)
        ring.hide_render = sc < 0.01
        ring.keyframe_insert("scale", frame=f)
        ring.keyframe_insert("rotation_euler", frame=f)
        ring.keyframe_insert("location", frame=f)
        ring.keyframe_insert("hide_render", frame=f)
        pos, tgt = camera_state(f)
        cam.location, target.location = pos, tgt
        cam.keyframe_insert("location", frame=f)
        target.keyframe_insert("location", frame=f)
    # Linear interpolation everywhere: easing already lives in the per-frame values.
    for obj in bpy.data.objects:
        ad = obj.animation_data
        if ad and ad.action:
            for layer in getattr(ad.action, "layers", []):
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for fc in bag.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "LINEAR"
            for fc in getattr(ad.action, "fcurves", []) or []:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


# ---------------------------------------------------------------- main
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=FRAMES - 1)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--frames", type=str, default="", help="comma list, overrides start/end")
    ap.add_argument("--scale", type=int, default=100, help="resolution percentage")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--save", type=Path)
    a = ap.parse_args(argv)

    reset()
    scn = build()
    scn.render.resolution_percentage = a.scale
    scn.cycles.samples = a.samples
    if a.threads:
        scn.render.threads_mode = "FIXED"
        scn.render.threads = a.threads
    if a.save:
        bpy.ops.wm.save_as_mainfile(filepath=str(a.save.resolve()))
        print("saved", a.save)
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        frames = [int(x) for x in a.frames.split(",") if x] or range(a.start, a.end + 1, a.step)
        for f in frames:
            path = a.out / f"plate_{f:04d}.png"
            if path.exists():
                continue
            scn.frame_set(f)
            scn.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            print(f"[plate] {path.name}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
