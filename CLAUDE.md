# Projet : Station de scan MTG (projet Maker)

## Contexte
Projet Maker : transformer un scanner de cartes Magic existant en station de numérisation et d'inventaire (mécanique, électronique, impression 3D, logiciel).
Base logicielle : fork de `McDandle/local-mtg-scanner` (Local TCG Scanner).
Choisi pour son interface web (inventaire, tri par collection/édition, images) et parce qu'il tourne sous Windows **et** Linux (cible future : Raspberry Pi).
**On réutilise l'existant** : on n'améliore le logiciel que lorsque le matériel ou un besoin réel le justifie.

## Contraintes non négociables
- **100 % local et autonome** : aucun service payant, aucune IA cloud. Internet seulement pour mettre à jour les données/prix Scryfall (Wi-Fi acceptable).
- **Embarquable** : tout doit pouvoir tourner à terme sur une machine autonome (Raspberry Pi 5 visé comme cerveau, ESP32 pour moteurs/capteurs/LED/e-paper).
- **Multiplateforme** : ne pas introduire de dépendances Linux-only (ex. `fcntl`) ni Windows-only.

## Priorités
1. Le côté Maker (conception, électronique, impression 3D) passe avant le logiciel.
2. Avancer par petites itérations : un système fonctionnel d'abord, puis on perfectionne.
3. Rester évolutif : ne pas tout construire dès la V1.

## Environnement actuel
- PC Windows (serveur / logiciel) + iPhone (caméra) : le lien fonctionne.
- Python 3.15 installé sur le PC (lanceur `py`).
- Reconnaissance actuelle : OCR Tesseract sous Windows/Linux (Apple Vision sur macOS, nettement meilleur) ; données et prix via Scryfall, base hors-ligne (~60 Mo) recommandée pour rester 100 % local.
- Matériel prévu : Raspberry Pi 5, ESP32, LED, écran e-paper, pièces imprimées 3D (imprimante accessible via un ami).

## État actuel
- Le scan iPhone → PC fonctionne, reconnaissance partielle.
- Point faible principal : la reconnaissance. La double vérification set + numéro + nom **existe déjà** dans le code ; elle échoue parce que Tesseract lit mal la photo brute (voir `docs/IDEES.md`, section OCR).
- L'auteur propose un support de scan imprimable en 3D : https://makerworld.com/en/models/1152661 (point de départ possible pour l'étape 1).

## Carte du code (reconnaissance) — `server.py`, section « scanning » (~l. 1480-1730)
- `detect_ocr_backend()` : Apple Vision (macOS) sinon Tesseract.
- `_ocr_tesseract()` : Tesseract `--psm 3` sur **la photo entière**, sans recadrage ni prétraitement → lignes normalisées (origine en bas à gauche).
- `candidate_names()` : prend les lignes « surtout des lettres » les plus hautes de l'image comme titre probable.
- `parse_print_info()` : cherche numéro de collectionneur (`NUM_RE`, ex. `M 0026`) et code d'édition (`SET_RE`, ex. `TLE • EN`) dans les 8 lignes les plus basses.
- `identify_card()` : 1) set + numéro → impression exacte, validée par le nom (`names_agree`) ; 2) numéro + nom ; 3) repli sur nom approximatif (pas d'impression exacte).
- Autres fichiers : `static/` (interface web), `deckbuilder.py`, `assistant.py` (optionnel), `test_games.py` (tests de parsing).
- Licence : MIT (McDandle).

## Projets de référence (sources d'idées, pas des bases)
Avant de copier du code : **vérifier la licence**. Sans fichier LICENSE, on s'inspire de l'idée, on ne copie pas.
- `filipesibinel/scanner` (MIT) : double vérification set + numéro de collectionneur + nom, file « à vérifier », foil via marqueur ★/•, mode « zone fixe ». Linux uniquement et IA cloud → écarté comme base.
- `jlelectroterra1-jpg/card-scanner` : 100 % local, RapidOCR, reconnaissance par image (MobileNetV2) quand le nom est illisible, version web iPhone.
- `wmjg-alt/mtg_scanner` : prétraitement OCR (CLAHE + agrandissement ×2).
- `MeIsGaggy/MTG-Card-Scanner-Sorter` : RapidOCR + repli Tesseract, pensé pour Raspberry Pi.

## Où sont les idées ?
- Backlog détaillé : `docs/IDEES.md`

## Conventions de travail avec Claude Code
- Avant de modifier le code : lire le README du dépôt et expliquer le plan en quelques lignes.
- Un changement = une branche ou un commit clair.
- **Commits en anglais, au format [Conventional Commits](https://www.conventionalcommits.org/fr/v1.0.0-beta.3/)** :
  ```
  <type>[optional scope]: <description>

  [optional body]

  [optional footer]
  ```
  - Types : `feat` (nouvelle fonctionnalité), `fix` (correction de bug), `docs`, `style` (formatage, sans effet sur le code), `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
  - Scopes conseillés : `ocr`, `scan`, `ui`, `db`, `inventory`, `hardware`, `docs`.
  - Description à l'impératif, en minuscules, sans point final, ~70 caractères max (ex. `feat(ocr): crop title bar before running tesseract`).
  - Changement cassant : `!` après le type/scope (`feat(db)!: ...`) et/ou pied de page `BREAKING CHANGE: ...`.
  - Un commit = une seule intention ; si un commit mélange deux types, le découper.
- Ne pas refactorer le projet d'origine sans raison liée à un besoin listé dans `docs/IDEES.md`.
- Toute amélioration de reconnaissance se mesure sur le jeu de cartes de test (taux avant/après).
- Après chaque session : ajouter une ligne au journal ci-dessous.

## Journal des décisions
- 2026-10-11 : cadrage du projet dans un Project Claude ; création de `CLAUDE.md` + `docs/IDEES.md` pour la continuité vers Claude Code.
- 2026-10-12 : contrainte 100 % locale / embarquable actée (pas d'IA cloud payante).
- 2026-10-12 : test de `filipesibinel/scanner` → ne démarre pas sous Windows (`import fcntl`, module Unix) et aucune capture d'interface. Écarté comme base.
- 2026-10-12 : **décision : base = McDandle/local-mtg-scanner** (interface vue et appréciée, features complètes, Windows + Linux). Les autres projets servent de réservoir d'idées pour fiabiliser la reconnaissance.
- 2026-10-12 : fork `DonKadaj/local-mtg-scanner` cloné dans `D:\Projets\11 - MTG Scanner\local-mtg-scanner` (remote `upstream` = McDandle). Lecture du code de scan : la double vérification existe, le problème vient de l'OCR sur image entière non prétraitée.
- 2026-10-12 : convention de commits adoptée : Conventional Commits, en anglais.
