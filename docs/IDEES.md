# Idées & backlog — Station de scan MTG

> Fichier vivant : on y note les idées au fil de l'eau. Chaque idée a un statut :
> `💡 idée` · `🔍 à étudier` · `🔨 en cours` · `✅ fait` · `❌ abandonné`
>
> Rappel : tout doit rester **100 % local** (pas d'IA cloud) et **multiplateforme** (Windows + Linux/Raspberry Pi).

## 🧪 Avant toute amélioration
- 🔍 **Jeu de cartes de test** : 15 à 20 cartes, dont celles qui échouent aujourd'hui (texte blanc sur fond sombre, cartes anciennes, foil, borderless…). Noter le taux de reconnaissance de référence, puis le mesurer après chaque modification.

## 🧠 Logiciel (à faire dans Claude Code)

### Reconnaissance OCR
> **Diagnostic (lecture de `server.py`)** : la logique titre + numéro + édition existe déjà (`identify_card`). Mais Tesseract est lancé en `--psm 3` sur **la photo entière**, sans recadrage ni prétraitement. Conséquences :
> - le titre est deviné comme « la ligne de lettres la plus haute de l'image » → si le titre est mal lu (police stylisée, fond coloré) ou si du décor dépasse au-dessus de la carte, c'est la ligne de type ou la description qui est prise ;
> - la ligne du bas (`M 0026`, `TLE • EN`) est petite → souvent mal lue → on retombe sur la recherche par nom seul, sans impression exacte.

- 🔍 **Étape 1 — Redresser et recadrer** : détecter le contour de la carte (OpenCV, plus grand quadrilatère aux proportions 63×88 mm), la redresser, puis découper deux zones fixes : bandeau du titre et coin bas gauche.
- 🔍 **Étape 2 — OCR par zone** : Tesseract en `--psm 7` (une seule ligne) sur chaque zone, avec prétraitement (niveaux de gris, CLAHE, agrandissement ×2, seuillage) — idée de `wmjg-alt/mtg_scanner`. Garder le pipeline actuel en repli si la détection de contour échoue.
- 🔍 **Étape 3 — Moteur OCR** : comparer Tesseract et RapidOCR (local, ONNX) sur le jeu de test — idée de `MeIsGaggy` / `card-scanner`.
- 💡 Cartes anciennes (avant ~2015) sans ligne `set • langue` en bas : seul le titre + éventuellement le symbole d'extension permettent de trouver l'impression.
- 💡 Correspondance de nom plus tolérante aux erreurs d'OCR (accents, noms raccourcis).
- 💡 **File « à vérifier »** : les cartes incertaines ne bloquent pas le scan, elles vont dans une file à valider ensuite (capture + suggestion + recherche manuelle).
- 💡 **Reconnaissance par l'image** en dernier recours (nom illisible) : empreinte d'image comparée aux images Scryfall — idée de `card-scanner` (MobileNetV2). À évaluer sur Raspberry Pi.
- 💡 Cas ambigus : grille des impressions possibles pour choisir la bonne, plutôt qu'un échec sec.

### Interface
- 💡 Les 2-3 petites améliorations repérées sur l'interface actuelle (à lister ici).

## 🔧 Matériel / Maker

### Détection foil / non-foil
- 🔍 **Logiciel d'abord** : sur les cartes récentes (≈ 2020+), le foil est marqué par une **★** à la place du **•** à côté du code d'édition → lecture de ce coin par traitement d'image, sans IA. Croiser avec Scryfall (impressions qui n'existent qu'en foil ou qu'en non-foil).
- 🔍 **Éclairage** pour les cartes sans marqueur : deux prises de vue avec éclairage différent (angle ou LED allumées/éteintes) et comparaison des reflets.
- 🔍 Distinguer **foil classique** et **surge foil** (motifs de reflet différents). Faisabilité incertaine → à tester expérimentalement.

### Plateforme embarquée
- 💡 Cerveau : **Raspberry Pi 5** (OCR + reconnaissance + interface web). L'ESP32 ne suffit pas pour la vision.
- 💡 ESP32 en périphérique : moteur d'alimentation, capteurs, LED de statut, e-paper ; piloté par le Pi (USB série ou Wi-Fi).
- 💡 Mode « zone fixe » : la caméra est fixe, la carte toujours au même endroit → recadrage fiable sans détection de contour.

## 📌 Étapes du projet (rappel)
1. Station de scan fixe : support caméra imprimé 3D, emplacement de carte, LED homogènes sans reflets.
2. Automatiser le passage des cartes : bac, mécanisme carte par carte, capteurs, moteur, ESP32.
3. LED de statut, écran e-paper, commandes physiques.

## 🗒️ Vrac
- (idées en vrac ici)
