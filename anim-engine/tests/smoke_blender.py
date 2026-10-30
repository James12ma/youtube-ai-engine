"""Test de fumée : Blender headless importable, Cycles CPU rend une image réelle non vide."""
import sys
import tempfile
from pathlib import Path

import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.mesh.primitive_cube_add()
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
cam.location, cam.rotation_euler = (4, -4, 3), (1.1, 0, 0.785)
sc.camera = cam
light = bpy.data.objects.new("l", bpy.data.lights.new("l", "SUN"))
sc.collection.objects.link(light)
sc.render.engine = "CYCLES"
sc.cycles.device, sc.cycles.samples = "CPU", 4
sc.render.resolution_x = sc.render.resolution_y = 64
out = Path(tempfile.mkdtemp()) / "smoke.png"
sc.render.filepath = str(out)
bpy.ops.render.render(write_still=True)

from PIL import Image, ImageStat  # noqa: E402
ok = out.exists() and ImageStat.Stat(Image.open(out).convert("L")).stddev[0] > 1
print(f"Blender {bpy.app.version_string} | Cycles CPU | image {out} | {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
