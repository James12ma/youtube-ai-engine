# Project Brain — Mission TikTok France (90 jours)

Mémoire permanente du projet. Chaque session programmée lit ce fichier en premier et y ajoute ses décisions.

## Identité (décidée le 2026-10-29)
- Compte : @maxielpretty1 (à renommer par le propriétaire)
- Nom proposé : **Histoires Vraies Oubliées**
- Bio proposée : `Chaque jour, une histoire vraie qu'on ne t'a jamais racontée 📜 | Voix et visuels assistés par IA`
- Format : sans visage, narration FR, photos d'archives libres (Wikimedia Commons), 65–120 s
- Série signature : « L'histoire que l'école ne t'a pas racontée »
- Fin de vidéo fixe : appel à s'abonner, sans manipulation

## Règles non négociables
- Aucun achat de vues/abonnés, aucune manipulation d'engagement
- Images : uniquement licences libres (domaine public, CC0, CC BY, CC BY-SA), crédits conservés dans `output/*.credits.txt`
- Pas de musique sous licence inconnue
- Étiquette « contenu IA » (isAigc) activée sur chaque publication
- Chaque fait vérifié avec au moins 2 sources listées dans le JSON ; les faits douteux sont présentés comme légendes
- Aucun résultat inventé : les chiffres viennent uniquement de Metricool/TikTok Studio
- Creator Rewards France : le propriétaire réside en République dominicaine → non éligible tant qu'aucune solution conforme n'est trouvée (décision de monétisation en attente)

## Chaîne de production
1. Claude (tâche programmée quotidienne) écrit l'épisode `episodes/NNN-*.json` (status `ready`) et le pousse.
2. GitHub Actions (`.github/workflows/render.yml`) rend le MP4 : edge-tts (voix fr-FR-HenriNeural) + Wikimedia Commons + Pillow + ffmpeg → `output/NNN-*.mp4`.
3. Claude programme la publication via Metricool (autoPublish, isAigc=true) avec l'URL brute GitHub du MP4.
4. Claude lit les statistiques Metricool et met à jour le tableau de bord.

## Hypothèses à tester (registre)
| # | Hypothèse | Statut |
|---|---|---|
| H1 | Les histoires militaires/catastrophes retiennent mieux que les curiosités culturelles | DONNÉES INSUFFISANTES |
| H2 | Un hook « chiffre/date + paradoxe » dans les 3 premières secondes améliore le taux de complétion | DONNÉES INSUFFISANTES |
| H3 | 85–95 s est la durée optimale | DONNÉES INSUFFISANTES |
| H4 | Publication 12h–13h ou 19h–21h heure de Paris performe mieux | DONNÉES INSUFFISANTES |

## Journal des décisions
- 2026-10-29 : niche choisie = histoires vraies méconnues (sans visage). Persona « virtual girl » abandonné à la demande du propriétaire.
- 2026-10-29 : moteur de rendu testé hors-ligne (90,4 s, 1080x1920). Épisodes 001–003 écrits.
- 2026-10-29 : bloquants : (1) dépôt GitHub public à créer, (2) Metricool encore relié à @digitalprompt8, (3) voie de monétisation à choisir.
