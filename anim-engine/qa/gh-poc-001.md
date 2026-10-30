# QA — gh-poc-001

**Résultat : PASS**

| Test | Résultat | Mesure | Critique |
|---|---|---|---|
| mp4 existe et non vide | ✅ | 451639 | oui |
| codec h264 | ✅ | h264 | oui |
| résolution 1080x1920 (9:16) | ✅ | 1080x1920 | oui |
| durée 5,0 s ±0,05 | ✅ | 5.0 | oui |
| 120 images | ✅ | 120 | oui |
| décodage complet sans erreur | ✅ | ok | oui |
| aucune interpénétration main/tasse (écart min ≥ -2 mm) | ✅ | -0.0 mm | oui |
| contact réel main/tasse (≥ 10 images) | ✅ | 28 images ([50]…[77]) | oui |
| tasse immobile avant le contact | ✅ | premier contact image 50 | oui |
| la tasse ne bouge que pendant un contact | ✅ | ok | oui |
| tasse déplacée ≥ 0,20 m | ✅ | 0.300 m | oui |
| tasse posée sur le plan (z constant) | ✅ | 0.9600–0.9600 | oui |
| tasse reste sur le plan de travail | ✅ | x final -0.150 | oui |
| tasse immobile après retrait de la main | ✅ | 0.000000 | oui |
| main de A jamais dans son propre torse | ✅ | 0 image | oui |
| cafetière statique | ✅ | 1 | oui |
| pas de collision tasse/cafetière | ✅ | 0.030 m | oui |
| main atteint sa cible IK pendant la poussée (≤ 3 cm) | ✅ | 0.0 cm | non |
| tête de B tourne ≥ 30° vers la tasse (+X) | ✅ | 0.0° → 35.0° | oui |
| bouche de B ouverte (O ≥ 0,95) au pic | ✅ | 1.0 | oui |
| sourcils de B levés au pic (≥ 2 cm) | ✅ | 0.02199999988079071 | oui |
| réaction de B après la poussée | ✅ | réaction 82 ≥ contact 50 | oui |
| images échantillons présentes | ✅ | [1, 50, 75, 92, 120] | oui |
| images ni noires ni vides (moyenne 20–235, écart-type > 15) | ✅ | {1: [191.9, 39.6], 50: [190.4, 42.3], 75: [188.4, 44.5], 92: [192.9, 39.0], 120: [192.6, 38.7]} | oui |
