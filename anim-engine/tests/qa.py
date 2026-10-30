"""QA mesurable : intégrité du fichier, durée, positions aux images clés, contact, réactions, images."""
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOL = 0.002  # 2 mm


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_name,width,height,nb_frames,avg_frame_rate",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def frame_stats(png):
    from PIL import Image, ImageStat
    im = Image.open(png).convert("L")
    st = ImageStat.Stat(im)
    return st.mean[0], st.stddev[0]


def run(job_id):
    d = ROOT / "output" / job_id
    results = []

    def check(name, ok, value, critical=True):
        results.append({"test": name, "pass": bool(ok), "value": value, "critical": critical})

    # 1. Fichier vidéo
    mp4 = d / f"{job_id}.mp4"
    check("mp4 existe et non vide", mp4.exists() and mp4.stat().st_size > 50_000,
          mp4.stat().st_size if mp4.exists() else 0)
    state = json.loads((d / "state.json").read_text())
    cfg, frames = state["config"], state["frames"]
    n = cfg["fps"] * cfg["seconds"]
    if mp4.exists():
        info = ffprobe(mp4)
        v = info["streams"][0]
        dur = float(info["format"]["duration"])
        check("codec h264", v["codec_name"] == "h264", v["codec_name"])
        check("résolution 1080x1920 (9:16)", (v["width"], v["height"]) == (1080, 1920), f'{v["width"]}x{v["height"]}')
        check("durée 5,0 s ±0,05", abs(dur - cfg["seconds"]) <= 0.05, round(dur, 3))
        check(f"{n} images", int(v.get("nb_frames", 0)) == n, v.get("nb_frames"))
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "null", "-"], capture_output=True, text=True)
        check("décodage complet sans erreur", dec.returncode == 0 and not dec.stderr.strip(), dec.stderr.strip()[:200] or "ok")

    # 2. Physique des accessoires
    m, rh, top = cfg["mug"], cfg["hand_radius"], cfg["counter_top_z"]
    min_gap = min(math.hypot(f["hand_a"][0] - f["mug"][0], f["hand_a"][1] - f["mug"][1]) - (m["radius"] + rh)
                  for f in frames if top < f["hand_a"][2] < top + m["height"] + rh)
    check("aucune interpénétration main/tasse (écart min ≥ -2 mm)", min_gap >= -TOL, f"{min_gap*1000:.1f} mm")
    contact = [f["frame"] for f in frames
               if abs(math.hypot(f["hand_a"][0] - f["mug"][0], f["hand_a"][1] - f["mug"][1]) - (m["radius"] + rh)) <= 0.003]
    check("contact réel main/tasse (≥ 10 images)", len(contact) >= 10, f"{len(contact)} images ({contact[:1]}…{contact[-1:]})")
    first = contact[0] if contact else n
    still = all(abs(f["mug"][0] - m["x"]) < 1e-6 for f in frames if f["frame"] < first)
    check("tasse immobile avant le contact", still, f"premier contact image {first}")
    moving = [f["frame"] for prev, f in zip(frames, frames[1:]) if abs(f["mug"][0] - prev["mug"][0]) > 1e-6]
    check("la tasse ne bouge que pendant un contact", set(moving) <= set(contact), sorted(set(moving) - set(contact))[:10] or "ok")
    moved = m["x"] - frames[-1]["mug"][0]
    check("tasse déplacée ≥ 0,20 m", moved >= 0.20, f"{moved:.3f} m")
    zs = [f["mug"][2] for f in frames]
    check("tasse posée sur le plan (z constant)", max(zs) - min(zs) < 1e-6 and abs(zs[0] - (top + m["height"] / 2)) < 1e-6,
          f"{min(zs):.4f}–{max(zs):.4f}")
    check("tasse reste sur le plan de travail", all(-1.2 + m["radius"] < f["mug"][0] < 1.2 - m["radius"] for f in frames),
          f"x final {frames[-1]['mug'][0]:.3f}")
    after = [f["mug"][0] for f in frames if f["frame"] > cfg["timeline"]["push_end"] + 2]
    check("tasse immobile après retrait de la main", max(after) - min(after) < 1e-6, f"{max(after)-min(after):.6f}")
    def inside_torso(p):  # coordonnées locales du maillage du torse (rayon 0,17, hauteur ±0,30)
        return abs(p[2]) < 0.30 and math.hypot(p[0], p[1]) < 0.17 + 0.02
    bad = [f["frame"] for f in frames if inside_torso(f["hand_a_in_torso_local"])]
    check("main de A jamais dans son propre torse", not bad, bad[:10] or "0 image")
    pots = {tuple(round(c, 6) for c in f["pot"]) for f in frames}
    check("cafetière statique", len(pots) == 1, len(pots))
    pot_gap = min(math.hypot(f["mug"][0] - f["pot"][0], f["mug"][1] - f["pot"][1]) for f in frames) - (m["radius"] + 0.07)
    check("pas de collision tasse/cafetière", pot_gap > 0, f"{pot_gap:.3f} m")
    ik_err = max(math.dist(f["hand_a"], f["ik_target_a"]) for f in frames
                 if cfg["timeline"]["pre_contact"] <= f["frame"] <= cfg["timeline"]["push_end"])
    check("main atteint sa cible IK pendant la poussée (≤ 3 cm)", ik_err <= 0.03, f"{ik_err*100:.1f} cm", critical=False)

    # 3. Réactions du personnage B
    t = cfg["timeline"]
    yaw0 = frames[t["head_turn_start"] - 1]["head_b_yaw_deg"]
    yaw1 = frames[t["head_turn_end"] - 1]["head_b_yaw_deg"]
    check("tête de B tourne ≥ 30° vers la tasse (+X)", yaw1 - yaw0 >= 30, f"{yaw0:.1f}° → {yaw1:.1f}°")
    check("bouche de B ouverte (O ≥ 0,95) au pic", frames[t["react_peak"] - 1]["mouth_b_O"] >= 0.95,
          frames[t["react_peak"] - 1]["mouth_b_O"])
    check("sourcils de B levés au pic (≥ 2 cm)", frames[t["react_peak"] - 1]["brow_b_raise"] >= 0.02,
          frames[t["react_peak"] - 1]["brow_b_raise"])
    check("réaction de B après la poussée", t["react_start"] >= first, f"réaction {t['react_start']} ≥ contact {first}")

    # 4. Images représentatives
    sample = [1, first, t["push_end"], t["react_peak"], n]
    stats = {}
    for f in sample:
        p = d / "frames" / f"frame_{f:04d}.png"
        if p.exists():
            stats[f] = frame_stats(p)
    check("images échantillons présentes", len(stats) == len(sample), sorted(stats))
    check("images ni noires ni vides (moyenne 20–235, écart-type > 15)",
          all(20 < mu < 235 and sd > 15 for mu, sd in stats.values()),
          {k: [round(x, 1) for x in v] for k, v in stats.items()})

    crit_fail = [r for r in results if r["critical"] and not r["pass"]]
    report = {"job": job_id, "pass": not crit_fail, "results": results}
    (ROOT / "qa").mkdir(exist_ok=True)
    (ROOT / "qa" / f"{job_id}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    lines = [f"# QA — {job_id}", "", f"**Résultat : {'PASS' if report['pass'] else 'FAIL'}**", "",
             "| Test | Résultat | Mesure | Critique |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['test']} | {'✅' if r['pass'] else '❌'} | {r['value']} | {'oui' if r['critical'] else 'non'} |")
    (ROOT / "qa" / f"{job_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for r in results:
        print(("PASS " if r["pass"] else "FAIL ") + r["test"] + f"  [{r['value']}]")
    return report["pass"]


if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[1]) else 1)
