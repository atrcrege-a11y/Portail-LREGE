# RÈGLES MÉTIER — SYNESC v2.4.4

Ce document décrit les règles métier extraites du code source. Il complète la cartographie technique.

---

## 1. Types de compétitions supportées

| Clé | Classe | Spécificités |
|-----|--------|-------------|
| `grand_est` | `GrandEst` | Championnat Régional Grand Est — référence de base |
| `alsace` | `Alsace` (hérite de GrandEst) | Ajoute M9/M11 indiv + M9/M11/M13 équipe — feuilles séparées par arme |
| `lorraine` | `Lorraine` | Individuel uniquement — M9→M15 — 3 armes — feuilles séparées par arme |

---

## 2. Catégories par compétition

### Grand Est — Individuel
`M13 · M15 · M17 · M20 · SENIORS · V1 · V2 · V3 · V4`

### Grand Est — Équipe
`M15 · M17 · M20 · SENIORS · VET (V1+V2) · GVET (V3+V4)`

### Alsace — Individuel
`M9 · M11 · M13 · M15 · M17 · M20 · SENIORS · V1 · V2 · V3 · V4`

### Alsace — Équipe
`M9 · M11 · M13 · M15 · M17 · M20 · SENIORS · VET · GVET`

### Lorraine — Individuel uniquement
`M9 · M11 · M13 · M15`

---

## 3. Correspondances catégories XML Engarde → clés internes

### Grand Est indiv
| XML Engarde | Clé interne |
|-------------|-------------|
| M13 | M13 |
| M15 | M15 |
| M17 | M17 |
| M20 | M20 |
| SENIORS, SENIOR | SENIORS |
| V1 | V1 |
| V2 | V2 |
| V3 | V3 |
| V4 | V4 |
| V1, V2 | V1 |
| V3, V4 | V3 |
| V1, V2, V3, V4 | V1 |

### Grand Est équipe (fusion Vétérans)
| XML Engarde | Clé interne |
|-------------|-------------|
| M15 | M15 |
| M17 | M17 |
| M20 | M20 |
| SENIORS, SENIOR | SENIORS |
| V1, V2, V1+V2 | VET (Vétérans) |
| V3, V4, V3+V4 | GVET (Gds Vétérans) |

**Règle** : En équipe, V1 et V2 fusionnent en "Vétérans" ; V3 et V4 fusionnent en "Gds Vétérans".

### Alsace — additions par rapport à Grand Est
- Indiv : M9, M11 ajoutés en tête
- Équipe : M9, M11, M13 ajoutés en tête (M13 équipe inexistant en Grand Est)

### Mode par arme (Alsace + Lorraine)
Quand `par_arme=True`, la clé devient `"CAT|ARME"` (ex: `"M9|F"`, `"M13|E"`).
Les armes sont : `F` = Fleuret, `E` = Épée, `S` = Sabre.

---

## 4. Tarifs d'inscription (droits d'engagement)

### Grand Est & Alsace — Individuel
| Catégorie | Tarif |
|-----------|-------|
| M9, M11, M13, M15 | 10 € |
| M17, M20, SENIORS, V1, V2, V3, V4 | 15 € |

### Grand Est — Équipe
| Catégorie | Tarif |
|-----------|-------|
| M15 | 30 € |
| M17, M20, SENIORS, VET, GVET | 40 € |

### Alsace — Équipe (ajouts vs Grand Est)
| Catégorie | Tarif |
|-----------|-------|
| M9, M11, M13 | 30 € |
| M15, M17, M20, SENIORS, VET, GVET | idem Grand Est |

### Lorraine — Individuel
| Catégorie | Tarif |
|-----------|-------|
| M9, M11, M13, M15 | 10 € |

---

## 5. Règles d'arbitrage — quotas par club

### Individuel
| Nb tireurs du club ce jour | Besoin arbitres |
|---------------------------|-----------------|
| < 4 | 0 |
| 4 à 8 | 1 |
| > 8 | 2 |

Formule Excel générée : `=IF(T<4,0,IF(T<=8,1,2))`

### Équipe
| Nb équipes du club ce jour | Besoin arbitres |
|---------------------------|-----------------|
| 0 | 0 |
| 1 à 2 | 1 |
| 3 à 4 | 2 |
| 5 et + | 3 |

Formule Excel générée : `=IF(T=0,0,IF(T<=2,1,IF(T<=4,2,3)))`

**Note** : Le quota est commun H+D (indiv) ou total équipes (équipe). Il n'y a pas de quota séparé par sexe.

### Périmètre du décompte — par arme et par journée

Le barème s'applique **par arme et par journée**, puis les besoins de chaque arme sont sommés. Cumuler toutes les armes d'une journée donne un résultat faux :

| Cas (même club, même jour) | Par arme | Cumul (faux) |
|---|---|---|
| 3 épée + 3 fleuret | 0 + 0 = 0 | 6 → 1 |
| 9 épée + 9 fleuret | 2 + 2 = 4 | 18 → 2 |

- Grand Est : compétition mono-arme, le cumul journée était déjà équivalent.
- Alsace / Lorraine : `construire_donnees(par_arme=True)` produit des clés `"CAT|ARME"` ; l'arme se lit dans la clé. Les feuilles Excel « Indiv <arme> » sont déjà construites arme par arme, leurs formules Besoin sont donc correctes sans modification.

**Côté « fournis »** : total des arbitres distincts du club ce jour, **sans ventilation par arme**. Le dédoublonnage se fait par licence et par jour (§9) et un arbitre issu d'un `EngardeArbitres.txt` est rattaché à toutes les épreuves du ZIP — son arme n'est pas une donnée exploitable.

### Vétérans — pas de seuil particulier

Le barème LREGE est unique : **1 arbitre dès 4 tireurs, 2 dès 9**, toutes armes et toutes catégories, **vétérans inclus**. Il n'y a pas de seuil d'entrée à 3 tireurs en région.

Le règlement FFE de l'arbitrage 2026-2027 (MAJ 17/08/2026) prévoit bien des seuils différenciés, mais **pour les épreuves nationales uniquement** : §7.4 épée vétérans 1 dès 4 ; §7.5 et §7.6 fleuret et sabre vétérans 1 dès 3, 2 dès 9. Ne pas transposer ces valeurs aux épreuves régionales.

---

## 6. Barème des indemnités arbitres (source : FFE 2024–2025)

| Code Engarde | Libellé | Indemnité |
|--------------|---------|-----------|
| FT | Formation Territoriale | 25 € |
| FD | Formation Territoriale (alias Engarde) | 25 € |
| T | Territorial | 30 € |
| D | Territorial (alias Engarde) | 30 € |
| FR | Formation Régionale | 35 € |
| R | Régional | 45 € |
| FN | Formation Nationale | 50 € |
| N | National | 70 € |
| I | International | 100 € |

**Commentaire dans le code** : "Source : règlement FFE 2024–2025 (en attente des informations 2025–2026)". Le barème doit être mis à jour dans `core/config.py` dès réception des données officielles 2025–2026.

Le tarif est écrit directement dans la cellule Excel (valeur numérique, pas de VLOOKUP) afin que les formules COUNTIF/SUMIFS du bilan fonctionnent sans dépendance croisée.

---

## 7. Format et contraintes du XML Engarde

- Encodage : ISO-8859-1 déclaré dans le XML (`ET.fromstring()` gère l'encodage, retourne des `str` Python unicode).
- Élément racine : attributs `Arme`, `Categorie`, `Sexe`, `Type`, `TitreLong`, `Date`, `DateDebut`, `DateFin`, `ID`.
- `Sexe` de l'épreuve : `M` = Hommes, `F` = Dames, `MF` = Mixte (équipes mixtes type M9 Alsace).
- `Type` de l'épreuve : `I` = Individuel, `E` = Équipe.
- Éléments `<Tireur>` : attributs `Nom, Prenom, Licence, Club, Equipe, Region, Ligue, Departement, Sexe, DateNaissance`.
- Éléments `<Arbitre>` : attributs `Nom, Prenom, Licence, Club, Region, Ligue, Departement, Categorie` (niveau).
- Formats de date acceptés : `JJ.MM.AAAA` (Engarde standard) et `AAAA-MM-JJ` (ISO, géré en fallback dans `date_avec_jour()`).
- Fichiers ZIP acceptés : l'app extrait tous les XML présents, en ignorant `__MACOSX/`.
- Balise racine acceptée : `CompetitionIndividuelle`, `CompetitionEquipe`, `CompetitionSynchrone`, `Competition`, `Epreuve`, et leurs variantes préfixées `Base` (`BaseCompetitionIndividuelle`… = export de la base d'engagés Engarde, même structure).
- Arbitres exportés à part : si le ZIP contient un `.txt` dont le nom contient « arbitre » (`EngardeArbitres.txt`), il est lu en CSV `;` **par nom d'en-tête** (jamais par position) et rattaché à **toutes** les épreuves du ZIP. Le XML fait foi : un arbitre du TXT n'est ajouté que si sa licence (à défaut nom+prénom) n'est pas déjà dans le XML.
- Niveau d'arbitrage du TXT (colonne `categorie`) : code du barème accepté tel quel (FT, FD, T, D, FR, R, FN, N, I) ; libellé long normalisé (« Régional » → `R`) ; valeur non reconnue conservée telle quelle **et signalée** dans les erreurs d'import — jamais ramenée silencieusement à 0 €.
- Le TXT ne porte ni `region` ni `departement` : `region` reprend la valeur de `ligue`, `dept` reste vide.
- Import du PDF programme (horaires) : les horaires extraits sont injectés dans le mail pour **tous** les types de compétition (Grand Est, Alsace, Coupe de Lorraine), sous la forme `⏰ Appel … — Scratch … — Début …` sous chaque catégorie. Sans PDF importé, le mail est inchangé.
- Besoin estimé en arbitres, par journée de compétition :
  - **Coupe de Lorraine avec PDF programme importé** : nombre de poules du créneau d'appel le plus tôt, par arme (inchangé).
  - **Grand Est, Alsace, et Lorraine sans PDF** : somme des poules de **toutes** les épreuves individuelles de la journée. Le comptage se fait fichier par fichier (une épreuve = une catégorie + une arme + un sexe). Les catégories hors périmètre du type de compétition ne sont pas comptées.
  - **Une compétition Grand Est est mono-arme** (règle confirmée). Le comptage par fichier reste néanmoins exact pour l'Alsace et la Lorraine, qui peuvent mélanger les armes, et ne dépend pas du regroupement `par_arme`.
  - Nombre de poules : `n < 2 → 0` ; `n ≤ 9 → 1` ; sinon `ceil(n / 7)`.
  - Le terme épreuves par équipes (1-2 → 1, 3-4 → 2, 5-6 → 3) est conservé tel quel et s'ajoute au total.

### Génération Excel — conteneurs XML vides

Un élément openpyxl écrit vide (`<dataValidations count="0"/>`) est **invalide au schéma OOXML** : Excel affiche « Excel a pu ouvrir le fichier en supprimant ou en réparant le contenu illisible » et répare la feuille. Cas rencontré : la validation « Retenu / Libéré » de la feuille Arbitres était attachée à la feuille avant de savoir si une cellule la référencerait ; sans aucun arbitre chargé, elle ne couvrait rien. **Règle : n'attacher une validation (ou tout conteneur de ce type) qu'une fois qu'elle couvre au moins une cellule.**
- Extraction FORMAT 4 : la ligne peut porter des colonnes après les 3 horaires (ex. `Tarif`), à condition qu'elles ne contiennent pas d'horaire — sinon la lecture Appel/Scratch/Assaut serait décalée.

---

## 8. Dédoublonnage des fichiers XML

Un fichier est considéré comme "déjà chargé" si un fichier avec le même `ID`, la même `categorie` et le même `type` est déjà dans le store. Un UUID est attribué à chaque fichier chargé (`meta["uid"]`) pour permettre la suppression individuelle depuis l'interface.

---

## 9. Dédoublonnage des arbitres

Dans la feuille Arbitres et dans toute les agrégations : un arbitre ne compte qu'**une fois par jour** (dédoublonnage par numéro de licence). Si un arbitre arbitre plusieurs catégories le même jour, il n'apparaît qu'une seule fois.

---

## 10. Détection des arbitres-tireurs

Croisement des numéros de licence entre la liste des tireurs et la liste des arbitres. Les doublons sont signalés dans la feuille Arbitres (section "Arbitres-Tireurs") et dans le corps du mail généré.

---

## 11. Statut des arbitres (Retenu / Libéré)

- Valeur par défaut à la génération : **"Retenu"** (colonne G de la feuille Arbitres).
- L'utilisateur peut modifier manuellement dans Excel via une liste déroulante (`DataValidation` : "Retenu,Libéré").
- Mise en forme conditionnelle : vert = Retenu, rouge = Libéré.
- Pour que le mail et le bilan financier utilisent les vrais statuts, l'utilisateur doit recharger son Excel modifié via `POST /api/charger_excel_arbitres`. Sinon, tous les arbitres sont comptés comme retenus.

---

## 12. Rôles — CRA, superviseur

| Rôle | Compétition | Config |
|------|-------------|--------|
| Responsable CRA | Grand Est, Alsace | `NOMS_CRA` dans `core/config.py` — **liste vide à compléter** |
| Superviseur | Grand Est | `NOMS_SUPERVISEURS_GRAND_EST` dans `core/config.py` — **liste vide à compléter** |
| Superviseurs | Lorraine (1 par arme) | `NOMS_SUPERVISEURS_LORRAINE` dans `core/config.py` — **liste vide à compléter** |

Ces listes alimentent les listes déroulantes dans la feuille "Récap Arbitres" de l'Excel et dans le PDF arbitres. Tant qu'elles sont vides, les cellules correspondantes sont éditables librement.

---

## 13. Comportement du `_store` (session en mémoire)

```python
_store = {}   # Dictionnaire global Python — survit aussi longtemps que le processus Flask

def get_store():
    sid = session.get("sid")   # Cookie Flask
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return _store.setdefault(sid, [])
```

- **Structure** : `_store[sid]` = liste de tuples `(meta, tireurs, arbitres)`.
- **Durée de vie** : jusqu'à l'arrêt du processus Flask (pas de persistance disque). Si le serveur redémarre, le store est vide même si le cookie client est encore valide.
- **Isolation** : chaque session navigateur a son propre bucket (par UUID dans le cookie).
- **Pas de nettoyage automatique** : les buckets abandonnés (fermeture de navigateur sans `clear`) restent en mémoire jusqu'au redémarrage du serveur. Pas de TTL, pas de garbage collection.
- **Taille maximale** fichier : 32 Mo (`MAX_CONTENT_LENGTH`).

---

## 14. Structure du fichier Excel généré

### Feuilles communes (toutes compétitions)
1. **Bilan Financier** — recettes par jour (indiv + équipes) + dépenses arbitres + solde coloré
2. **Épreuve Individuelle** — tableau clubs × catégories (H/D) + totaux + besoin arbitrage
3. **Épreuve Équipe** — tableau clubs × catégories (Eq.H/Tir.H/Eq.D/Tir.D) + totaux — absent si aucune équipe
4. **Indiv Extranet** — liste individuelle des tireurs par catégorie (format FFE Extranet)
5. **Equipe Extranet** — liste individuelle des tireurs par équipe — absent si aucune équipe
6. **Arbitres** — liste des arbitres par jour, dédoublonnés, avec statut Retenu/Libéré
7. **Récap Arbitres** — formules liées à la colonne Statut — cellules CRA/superviseur sélectionnables

### Spécificités Alsace
- Feuilles **Indiv Fleuret / Indiv Épée / Indiv Sabre** à la place d'une feuille indiv unique
- Feuilles **Équipe Fleuret / Équipe Épée / Équipe Sabre** par arme
- Seules les armes présentes dans les fichiers chargés génèrent une feuille
- Bilan Financier : équipes regroupées par arme, colonne Eq.MX pour les équipes mixtes (M9)

### Spécificités Lorraine
- Feuilles **Indiv Fleuret / Indiv Épée / Indiv Sabre** uniquement (pas d'équipe)
- Feuilles **Extranet Fleuret / Extranet Épée / Extranet Sabre** séparées
- Bilan Financier par arme puis par catégorie

### Ordre des feuilles
`Bilan Financier → feuilles indiv/équipe/extranet → Arbitres → Récap Arbitres` (Arbitres et Récap déplacés en fin par `move_sheet`).

### Calcul Excel
- `calcMode = 'auto'`, `fullCalcOnLoad = True`, `iterate = False` pour forcer le recalcul à l'ouverture et éviter les faux positifs de référence circulaire.
- Les colonnes Besoin Arbitres / Statut utilisent des **formules Excel** (pas des valeurs) pour rester dynamiques si l'utilisateur modifie les chiffres.
- La colonne Tarif arbitres est une **valeur numérique** (pas VLOOKUP) pour que `SUMIFS` fonctionne sans dépendance croisée entre feuilles.

---

## 15. Formule de composition des poules

Règle FFE — calculée par `_formule_poules(n)` dans `app.py` :

| Effectif | Résultat |
|----------|---------|
| < 2 | — (pas de formule) |
| 2 à 9 | 1 poule de N → Tableau T(2^x ≥ N) |
| ≥ 10 | ceil(N/7) poules → préférence poules de 7, puis de 6 pour compléter → Tableau T(2^x ≥ N) |

La taille du tableau direct (T8, T16, T32…) est toujours la puissance de 2 supérieure ou égale à l'effectif.

**Comportement confirmé** : toutes les catégories (y compris M9 et M11) ont un tour de poules — c'est le comportement réglementaire attendu. `_CATS_TABLEAU_DIRECT` reste vide intentionnellement.

---

## 16. Génération du corps de mail

Le mail est généré par `_generer_corps_mail()`, partagé entre `mail_body` (JSON pour Gmail) et `generate_mail` (fichier .eml pour Outlook).

Contenu du mail :
- Introduction standard
- Par jour : épreuves individuelles (avec formule poules) + épreuves équipe + arbitres inscrits + besoin estimé + clubs en déficit d'arbitrage
- Pour Lorraine : horaires extraits du PDF si disponibles (Appel · Scratch · Début par arme et catégorie)
- Arbitres également inscrits comme tireurs (détection par croisement licences)
- Bilan financier prévisionnel (recettes estimées − dépenses arbitres)
- Rappels fixes : absents restent dus, hors-délai majorés, contact CRA (Auxane Cholley, email hardcodé), envoi fichiers résultats à atrcrege@gmail.com

### Calcul du besoin arbitres dans le mail
- Grand Est / Alsace : somme besoin indiv + besoin équipe selon les règles des quotas (§5).
- Lorraine avec PDF horaires chargé : calcul par arme — on identifie le créneau d'appel le plus tôt par arme, on somme le nombre de poules des catégories de ce créneau. C'est une estimation du besoin en simultané (piste, pas total journée).

---

## 17. Extraction des horaires PDF (4 formats reconnus)

| Format | Description |
|--------|-------------|
| Format 0 | Tableau colonnes : une colonne par catégorie, lignes Appel/Scratch/Début |
| Format 1 | Tableau structuré pdfplumber : colonne Catégorie + colonnes horaires avec en-tête reconnu |
| Format 2 | Texte ligne par ligne : "M13 ... Appel : 9h00 Scratch : 9h15 Début : 9h30" |
| Format 3 | Texte condensé : "M13 – Inscriptions : 8h30 – Scratch : 8h45 – Début : 9h00" |
| Format 4 | Tableau texte avec jours en en-tête et 3 colonnes horaires alignées |

Le format 4 est préféré s'il donne plus de résultats que les formats précédents.

Normalisation des catégories dans les PDF :
- Regex avec gestion des accents pour Épée/Epée
- Exclusion des épreuves loisir, handi, inauguration, convivial, consolante
- V1/V2/V3/V4/Hommes/Dames → "Vétérans"
- Senior → "Seniors"

---

## 18. TODOs et comportements incomplets identifiés dans le code

| Fichier | Ligne / Section | Description |
|---------|----------------|-------------|
| `core/config.py` | `NOMS_CRA = []` | Liste vide — à remplir avec les noms officiels |
| `core/config.py` | `NOMS_SUPERVISEURS_GRAND_EST = []` | Liste vide — à remplir |
| `core/config.py` | `NOMS_SUPERVISEURS_LORRAINE = []` | Liste vide — à remplir |
| `core/config.py` | Commentaire `BAREME_ARBITRES` | "en attente des informations 2025–2026" — barème FFE 2024–2025 utilisé |
| `app.py` | `_CATS_TABLEAU_DIRECT = set()` | Intentionnellement vide — toutes les catégories (M9, M11 inclus) ont un tour de poules, comportement réglementaire confirmé |
| `app.py` | Après `@app.route("/api/generate")` | Bloc commenté vide "Génération mail .eml" — route suivante opérationnelle, commentaire résiduel |
| `app.py` | `secret_key = "lrege-synesc-secret-2025"` | Clé de session hardcodée — acceptable pour usage local mais à externaliser si déploiement multi-utilisateurs |
| `requirements.txt` | `requests>=2.31` | Dépendance présente mais non utilisée dans le code actuel (vestige de la version avec API Claude supprimée en v2.4.0) |
| `competitions/lorraine.py` | `feuille_indiv()` / `feuille_equipe()` | Méthodes abstraites implémentées avec `pass` — remplacées par `_feuille_indiv_arme()` et le pipeline surchargé `generer_excel()` |
| `static/logo_lrege_excel.png` | — | Fichier conservé mais non utilisé dans les Excel depuis v2.4.0 |
| `_store` global | — | Aucun nettoyage des sessions expirées — fuite mémoire potentielle sur usage prolongé |

