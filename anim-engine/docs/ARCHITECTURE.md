# Architecture de production — Anim Engine

Principe : **tout est décrit dans un fichier de job JSON**, puis rendu de façon déterministe
(même job + même version du moteur = même vidéo). Aucun clic manuel dans Blender.

## 1. Maillages et rigging des personnages
- **V1 (actuel)** : personnages « cartoon » construits par primitives (bmesh), pièces
  parentées aux os d'une armature (rigide, sans déformation de peau). Robuste, rapide.
- **V2** : un fichier `assets/characters/<nom>.blend` par personnage (Léo, Jade), modélisé une
  seule fois, avec un **squelette standard** (mêmes noms d'os : `spine`, `neck`, `head`,
  `upper.in/out`, `fore.in/out`, `brow.L/R`…) et un skinning par poids. Le moteur les
  *ajoute* (`bpy.data.libraries.load`) au lieu de les construire → les scripts
  d'animation restent identiques.
- **Bloquant réel** : modéliser Léo et Jade fidèles à vos fiches demande un artiste 3D
  (ou un outil image→3D) ; ce n'est pas automatisable de façon fiable aujourd'hui.

## 2. Chronologie et images clés
- Section `timeline` du job : temps nommés (`contact`, `push_end`, `react_peak`…).
- Fonctions d'action réutilisables : `reach(target, start, end)`, `push(prop, distance)`,
  `look_at(character, point)`, `react(character, expression, frame)`.
- Interpolation Bézier par défaut ; paliers « hold » pour le timing comique.

## 3. Interaction main / objet
- **IK** (2 os) vers une cible animée + pôle mesuré (angle choisi par mesure numérique,
  pas à l'œil).
- **Solveur de contact cinématique** : l'objet est placé à chaque image contre la surface
  de la main → zéro interpénétration garantie, immobilité hors contact.
- **V2** : prise (attacher l'objet à l'os `hand` via contrainte *Child Of* activée/désactivée
  par images clés) pour saisir, soulever, verser.

## 4. Expressions faciales
- Clés de forme sur la bouche (`O`, `smirk`, à étendre : `smile`, `frown`, `grimace`).
- Os de sourcils (translation), rotation de tête (lacet/tangage) mesurée en degrés.
- **V2** : bibliothèque d'expressions nommées = combinaisons de clés de forme + os.

## 5. Liquides
| Méthode | Qualité | Coût CPU | Fiabilité |
|---|---|---|---|
| Mantaflow (simulation FLIP) | Réaliste | **Élevé** (minutes–heures par seconde) | Bonne, réglage long |
| Maillage animé « cartoon » (flaque qui grandit + jet en courbe + gouttes) | Stylisée | Très faible | Excellente, déterministe |
| Particules | Moyenne | Moyen | Moyenne |
→ Recommandé : **liquide cartoon procédural** (forme contrôlée exactement, comme dans les
animations de référence), Mantaflow réservé aux plans spéciaux.

## 6. Lumière et caméra
- Préréglages dans le job : `camera.preset = "counter_low"` (caméra au ras du plan, 15 mm),
  `lighting.preset = "warm_morning"`.
- Rendu Cycles CPU (seul moteur fiable sans GPU/OpenGL), débruitage OIDN.

## 7. Son et compositing final
- FFmpeg : assemblage des images, mise à l'échelle 1080×1920, ajout de pistes son
  (bruitages déclenchés aux images `contact`, `react_peak`), musique libre de droits.
- Les instants sonores viennent de la même `timeline` → synchronisation exacte.

## 8. Soumission à distance depuis le téléphone
- Le job JSON est **committé** dans le dépôt GitHub (depuis l'appli GitHub, le navigateur,
  ou par Claude) → **GitHub Actions** (gratuit pour un dépôt public, 4 vCPU) installe
  Blender (`pip install bpy`), rend, lance la QA, publie le MP4 + le rapport QA.
- États du job visibles dans `jobs/<id>.json` (queued → … → done/failed + cause).

## Besoins de calcul (mesurés sur cette machine : 2 vCPU, 7 Go RAM)
| Élément | Mesure |
|---|---|
| Construction de la scène + solveur de contact | ~0,5 s |
| Rendu Cycles 540×960, 10 échantillons + débruitage | **~12 s / image** |
| Vidéo 5 s (120 images) | **~24 min** sur 2 vCPU |
| GitHub Actions (mesuré, run 40990714425) | **12,0 s / image → 24 min / 5 s** (pas plus rapide qu'ici) |
| Vidéo 15 s, même réglage | ~72 min (extrapolé, linéaire) |
| Installation de Blender sur GitHub | 34 s (mesuré) |
| Mantaflow (liquide réaliste) | +30 min à plusieurs heures (non mesuré) |
Limite GitHub Actions : 6 h par job → suffisant pour des vidéos de 15–30 s à ce niveau de qualité.
