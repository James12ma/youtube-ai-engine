# Anim Engine V1 — moteur d'animation 3D headless

Pipeline reproductible : Python + Blender (module `bpy`, Cycles CPU) + FFmpeg + Git.
Aucun GPU, aucun service payant.

## Lancer

```bash
python3 -m venv bvenv && bvenv/bin/pip install bpy==5.2.3 pillow
bvenv/bin/python tests/smoke_blender.py                      # test de fumée
bvenv/bin/python -m engine.run jobs/poc-001.json             # build -> render -> encode -> qa
bvenv/bin/python -m engine.run jobs/poc-001.json --stage render --frames 1,60,120   # rendu partiel
```

## Structure

| Dossier | Rôle |
|---|---|
| `engine/config.py` | Paramètres par défaut, fusionnés avec la section `config` d'un job |
| `engine/jobs.py` | États persistants : queued → building → rendering → encoding → qa → done/failed |
| `engine/geo.py` | Primitives bmesh, matériaux, parentage à un os |
| `engine/characters.py` | Personnages temporaires riggés (armature, IK, sourcils, clés de forme bouche) |
| `engine/scene.py` | Cuisine procédurale, accessoires, caméra basse, animation, solveur de contact |
| `engine/run.py` | Orchestrateur avec reprise (les images déjà rendues ne sont pas refaites) |
| `tests/` | Test de fumée Blender + QA mesurable |
| `jobs/` | Fichiers de job (entrée + état) |
| `output/<job>/` | `scene.blend`, `state.json`, images PNG, MP4 |
| `qa/` | Rapports QA (JSON + Markdown) |

## Contact main/tasse

Le solveur (`scene.solve_mug_contact`) évalue la main à chaque image après l'IK et place la
tasse exactement contre la surface de la main (rayon main + rayon tasse). Résultat : aucune
interpénétration, tasse immobile hors contact, z constant sur le plan de travail.
