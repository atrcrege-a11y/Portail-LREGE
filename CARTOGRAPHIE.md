# CARTOGRAPHIE FONCTIONNELLE — LREGE v8.6

> Document de référence projet. À lire en début de session avant toute modification.
> Généré le 2026-05-26 par lecture exhaustive du code source.

---

## 1. PRÉSENTATION DU PROJET

Suite d'outils de gestion sportive Python pour le **Comité Régional d'Escrime Grand Est (CREGE Grand Est)**.
Distribuée sous forme d'un installeur Windows unique (`PortailLREGE.exe`), elle regroupe 7 applications autonomes orchestrées par un portail central.

**Dépôt GitHub :** `https://github.com/atrcrege-a11y/Portail-LREGE`

---

## 2. ARCHITECTURE GLOBALE

```
LREGE/
├── portail.py              # Hub Flask port 5000 — lancement outils + MAJ auto
├── lanceur.py              # Micro-lanceur PyInstaller → appelle LANCER_PORTAIL.bat
├── audit.py                # Tests de régression SelecGE (fixtures FFE 2025-26)
├── version.json            # Version courante + URL installeur pour MAJ auto
│
├── crege_app/              # Bibliothèque métier SelecGE (version développement)
├── routes/                 # Blueprints Flask SelecGE (version développement)
├── services/               # Services transversaux SelecGE (version développement)
├── templates/index.html    # Interface SelecGE
│
├── SelecGE/                # ← COPIE AUTONOME pour l'installeur (miroir + 2 fichiers en plus)
├── SYNESC/                 # Compétitions régionales (port 5002)
├── SelecMaster/            # Sélection Masters M11/M13 (port 5004)
├── SuiviGE/                # Suivi confirmations CDF (port 5006)
├── SuiviMaster/            # Suivi confirmations Masters + arbitres (port 5005)
├── CalendrierLREGE/        # Calendrier compétitions (port 5003)
└── EscriTools/             # App Tkinter desktop — conversions PDF
```

### Ports par outil

| Port | Outil | Description |
|------|-------|-------------|
| 5000 | Portail | Hub de lancement, MAJ auto, watchdog 60s |
| 5001 | SelecGE | Génération feuilles de sélection CDF armes olympiques |
| 5002 | SYNESC | Compétitions régionales Grand Est/Alsace/Lorraine (XML BellePoule) |
| 5003 | CalendrierLREGE | Calendrier CRUD + exports iCal/Excel/PDF |
| 5004 | SelecMaster | Sélection Masters M11/M13 |
| 5005 | SuiviMaster | Suivi confirmations Masters + arbitres |
| 5006 | SuiviGE | Suivi confirmations CDF individuel + équipes |
| —    | EscriTools | Tkinter desktop — pas de port Flask |

---

## 3. DUPLIFICATION CRITIQUE : crege_app/ racine vs SelecGE/crege_app/

La bibliothèque métier existe en **deux exemplaires** :

- `crege_app/` (racine) → version de **développement**
- `SelecGE/crege_app/` → version **autonome embarquée** dans l'installeur

**⚠️ Fichiers présents UNIQUEMENT dans `SelecGE/crege_app/` :**
- `generateur/equipes_veterans.py`
- `generateur/indiv_veterans.py`

Toute modification de la bibliothèque métier doit être propagée dans les deux répertoires.
Idem pour `routes/` et `services/`.

---

## 4. BIBLIOTHÈQUE MÉTIER : crege_app/

### 4.1 Structure

```
crege_app/
├── core/
│   ├── utils.py              # Colonnes FFE, est_grand_est(), filtrer_df()
│   ├── reglementation.py     # Matrice réglementaire (cat × arme × genre → règle)
│   ├── quotas_lrege.py       # Table des quotas GE 2025-2026
│   ├── calendrier_cdf.py     # Dates/lieux CDF individuel et équipes
│   ├── feuille.py            # Entête Excel, lignes info, lignes tireurs, arbitrage
│   ├── styles.py             # Couleurs, polices, bordures openpyxl + palettes par cat
│   ├── parser_pdf_equipes.py # Parseur PDF équipes BellePoule
│   └── parser_engarde_equipes.py # Parseur Engarde XML/FFF équipes
├── categories/
│   ├── base.py               # BaseCategorie (ABC) — interface construire() + generer()
│   ├── jeunes.py             # M13/M15/M17/M20 + 4 fonctions construire_*
│   ├── seniors.py            # Seniors, V1→V4 (_make_seniors_class factory)
│   ├── selection.py          # Moteur générique par étapes (ETAPES dict)
│   ├── equipes_m15.py        # Construction équipes M15
│   └── equipes_seniors.py    # Construction équipes Seniors/Vétérans
├── generateur/
│   ├── excel.py              # generer_multi_genres(), generer_equipes_m15()
│   ├── sections.py           # bloc_section() — rendu bloc tireurs dans feuille
│   ├── equipes.py            # remplir_feuille_equipes() M15
│   ├── equipes_seniors.py    # generer_equipes_seniors()
│   ├── equipes_veterans.py   # (SelecGE/ uniquement)
│   └── indiv_veterans.py     # (SelecGE/ uniquement)
└── sabre_laser/
    ├── config.py
    ├── generateur.py
    ├── parseurs.py
    └── selection.py
```

### 4.2 Colonnes FFE (core/utils.py)

| Constante | Valeur |
|-----------|--------|
| `COL_RANG` | `"Rang"` |
| `COL_NOM` | `"Nom"` |
| `COL_PRENOM` | `"Prenom"` |
| `COL_CLUB` | `"Nom club"` |
| `COL_REGION` | `"Region"` |
| `COL_NATION` | `"Nationalite"` |

**Détection Grand Est** (`est_grand_est`) : accepte `"alsace"`, `"lorraine"`, `"champagne-ardenne"`, `"champagne ardenne"`, `"grand est"`, `"grand-est"`, `"ges - grand est"`, `"ges"`, ou toute chaîne contenant `"grand est"` ou commençant par `"ges"`.

**Filtre nationalité** (`est_francais`) : accepte `FRA`, `FRANÇAISE`, `FRANCAIS`, `FR`, `FRANCE`, ou chaîne vide (pas de colonne = supposé français).

---

## 5. RÉGLEMENTATION (core/reglementation.py)

### 5.1 Les 7 modes de sélection

| Constante | Valeur string | Usage |
|-----------|---------------|-------|
| `N2_QUOTA_LREGE` | `"quota_lrege"` | Split 1/3 FFE + 2/3 régional — cas standard |
| `N2_FFE_N3_QUOTA` | `"ffe_n3_quota"` | N1+N2 PDF FFE, N3 quotas LREGE (FH M17/M20 Épée/Fleuret) |
| `N1_FFE_N2_QUOTA` | `"n1_ffe_n2_quota"` | N1 PDF FFE, N2 quotas LREGE (FD M17/M20 Épée/Fleuret) |
| `N2_OPEN_CIRCUIT` | `"open_circuit"` | Open sous condition circuit national (Sabre M17/M20/M23/Seniors, Vét. Épée D) |
| `N2_QUOTA_FFE` | `"quota_ffe"` | Quota FFE pur (cas unique : Fleuret Dame Seniors) |
| `N2_REG_ONLY` | `"reg_only"` | 100% classement régional, zéro FFE (M13 Épée/Fleuret) |
| `N2_OPEN` | `"open"` | Open sans quota (M13 Sabre, Vétérans Fleuret/Sabre, V4 Épée H) |

### 5.2 Matrice réglementaire par catégorie

| Catégorie | Arme | Hommes | Dames |
|-----------|------|--------|-------|
| M13 | Épée/Fleuret | `N2_REG_ONLY` | `N2_REG_ONLY` |
| M13 | Sabre | `N2_OPEN` | `N2_OPEN` |
| M17/M20 | Épée/Fleuret | `N2_FFE_N3_QUOTA` (N1+N2 PDF + N3 quota) | `N1_FFE_N2_QUOTA` (N1 PDF + N2 quota) |
| M17/M20 | Sabre | `N2_OPEN_CIRCUIT` (≥1 circuit national) | `N2_OPEN_CIRCUIT` |
| M23 | Épée/Fleuret | `N2_QUOTA_LREGE` (≥3 épreuves territoire) | `N2_QUOTA_LREGE` |
| M23 | Sabre | `N2_OPEN_CIRCUIT` | `N2_OPEN_CIRCUIT` |
| Seniors | Épée | `N2_QUOTA_LREGE` | `N2_QUOTA_LREGE` |
| Seniors | Fleuret H | `N2_QUOTA_LREGE` | — |
| Seniors | Fleuret D | — | `N2_QUOTA_FFE` (20 suivantes FFE) |
| Seniors | Sabre | `N2_OPEN_CIRCUIT` | `N2_OPEN_CIRCUIT` |
| V1/V2/V3 | Épée H | `N2_QUOTA_LREGE` | — |
| V4 | Épée H | `N2_OPEN` | — |
| V1/V2/V3/V4 | Épée D | `N2_OPEN_CIRCUIT` (≥2 circuits) | — |
| Tous Vétérans | Fleuret/Sabre | `N2_OPEN` (critérium) | `N2_OPEN` |

**Fallback `get_regle()`** : si combinaison non trouvée → `N2_QUOTA_LREGE` avec `n1_default=32`.

---

## 6. QUOTAS (core/quotas_lrege.py)

### 6.1 Quotas individuels 2025-2026

| Catégorie | Arme | Hommes | Dames |
|-----------|------|--------|-------|
| M13 | Épée | 10 | 10 |
| M13 | Fleuret | 11 | 10 |
| M17 | Épée | 5 (N3) | 4 (N2) |
| M17 | Fleuret | 5 (N3) | 3 (N2) |
| M20 | Épée | 5 (N3) | 5 (N2) |
| M20 | Fleuret | 4 (N3) | 2 (N2) |
| M23 | Épée | 4 | 4 |
| M23 | Fleuret | 4 | 3 |
| M23 | Sabre | 3 | 2 |
| Seniors | Épée | 6 (N3) | 6 (N3) |
| Seniors | Fleuret | 4 (N3) | 4 (N2) |
| V1/V2/V3 | Épée H | 4 | 1-2 (open circuit) |

### 6.2 ⚠️ Comportement V4

`get_quota_equipes()` pour `V4` substitue silencieusement `"V3"` comme clé (ligne 98-100). V4 Équipes hérite donc du quota V3. Ce comportement n'est pas documenté dans la table `QUOTAS_EQUIPES`.

---

## 7. CONSTRUCTION (services/construction.py)

### 7.1 TABLE_LREGE — Split 1/3 FFE + 2/3 régional

```python
TABLE_LREGE = {
    3: (1, 2),  4: (1, 3),  5: (2, 3),  6: (2, 4),
    7: (2, 5),  8: (3, 5),  9: (3, 6), 10: (3, 7), 11: (4, 7),
}
```

Pour quota > 11 : `ffe = round(quota/3)`, `reg = quota - ffe` (calcul dynamique).
Pour quota = 1 : `(0, 1)`. Pour quota = 2 : `(1, 1)`.

**⚠️ Point de fragilité** : `round(12/3) = 4` → `(4, 8)`. Si un quota de 12 est jamais introduit, vérifier que le résultat est conforme à la table officielle.

### 7.2 build_cfg()

Construit le dict de configuration complet à partir des `params` du formulaire + règle réglementaire.

Comportements à retenir :
- `nationalite_francaise` est forcé à `True` pour M17/M20/M23/Seniors/V1-V4 (pas modifiable)
- `quota_federal` et `quota_crege_nat` sont mis à 0 si mode `N2_REG_ONLY` (M13)
- `quota_crege_reg` vaut `quota_total` (pas de split) si mode `N2_REG_ONLY`
- `nb_wildcards` n'est actif que pour M17 et M20

### 7.3 Dispatch des fonctions construire_*

| Condition | Fonction appelée |
|-----------|-----------------|
| `n2_mode == N2_OPEN_CIRCUIT` | `construire_genre_open_circuit()` |
| `n2_mode == N2_FFE_N3_QUOTA` | `construire_genre_ffe_n1n2_n3quota()` |
| `n2_mode == N1_FFE_N2_QUOTA` | `construire_genre_n1_ffe_n2_quota()` |
| `format == 'seniors'` | `construire_genre_seniors()` |
| `format == 'jeunes'` (défaut) | `construire_genre_jeunes()` |

---

## 8. CATÉGORIES (categories/)

### 8.1 Moteur par étapes (selection.py)

Le fichier `selection.py` implémente un moteur générique avec 5 classes d'étapes :

| Classe | Rôle |
|--------|------|
| `EtapeFFE(niveau)` | GES du df_ffe pour un niveau donné (N1/N2/N3) |
| `EtapeQuotaLREGE()` | Split ⅓ nat + ⅔ rég depuis df_nat et df_reg |
| `EtapeRegOnly()` | 100% classement régional (M13) |
| `EtapeOpenCircuit()` | GES de df_ffe N1 uniquement (Sabre open circuit) |
| `EtapeRemplacants()` | Suivants du classement régional hors qualifiés |

La matrice `ETAPES` dans `selection.py` définit la séquence d'étapes par `(cat_id, arme_id, genre)`.

**⚠️ Attention** : `jeunes.py` contient également des fonctions `_construire_jeunes_*` indépendantes qui sont appelées directement depuis `services/construction.py`. Le moteur `selection.py` est une refactorisation plus récente mais les deux coexistent.

### 8.2 Logique _construire_jeunes() (jeunes.py)

Flux principal :
1. Filtrer nationalité si `filtre_fr=True`
2. **Section N1 (Quota Fédéral)** : GES dans top-`n1_seuil` du classement national
3. **Wild Cards DTN** : GES dans rangs `n1_seuil+1` à `n1_seuil+nb_wc` → note "Montée N1 possible"
4. **Section LREGE national** : places WC + compléments depuis rang `> seuil_nat`
5. **Section LREGE régional** : top `quota_cr` du classement régional hors déjà sélectionnés
6. **Remplaçants** : suivants du classement régional

Mécanisme anti-doublon : set `noms_sel` de tuples `(NOM_NORM, PRENOM_NORM)`, mise à jour à chaque ajout.

Normalisation nom : NFD → ASCII → majuscules → suppression non-alpha.

### 8.3 Logique _construire_seniors() (seniors.py)

Deux branches selon la présence de `df_ffe` :
- **Avec `df_ffe`** : parcourir les niveaux PDF (N1/N2/N3), filtrer les GES, afficher par niveau
- **Sans `df_ffe`** : utiliser `df_national` directement (Sabre, Vétérans)

Ensuite section LREGE quota (quota_n2_reg places du classement régional hors qualifiés FFE).

---

## 9. GÉNÉRATION EXCEL (generateur/ + core/feuille.py)

### 9.1 Flux de génération

```
generer_multi_genres(data_h, data_d)
  └─ generer_feuille_simple(ws, data)
       ├─ init_feuille(ws, meta)          ← entête, lignes info, arbitrage
       └─ bloc_section(ws, ligne, section) ← pour chaque section
            ├─ fusionner_style(titre)
            ├─ textes critères (▸ italique)
            ├─ sous-sections (si présentes)
            └─ entete_tireurs() + ligne_tireur() × n
```

### 9.2 Structure d'une feuille Excel

| Zone | Lignes (approx.) | Contenu |
|------|-----------------|---------|
| Titre compétition | 1 | Couleur catégorie, texte blanc, fusion A:F |
| Date · Lieu | 1 | Couleur entête catégorie |
| Discipline | 1 | Couleur catégorie |
| Séparateur | 1 | — |
| Phrase engagement | 1 | M13 : clubs, autres : LREGE |
| Date limite | 0-1 | Si renseignée |
| Mail retour | 1 | Toujours présent |
| Date extranet | 0-1 | Si renseignée |
| Arbitrage | 1 | Texte + lignes saisissables si source ≠ aucun |
| Sections | variable | N1, LREGE, Remplaçants |

### 9.3 Palettes de couleurs par catégorie

| Catégorie | Titre / N1 | N2 | N3 |
|-----------|-----------|----|----|
| M13 | `6A0DAD` (violet) | `9B4DD4` | `C090E8` |
| M15 | `1A5C2A` (vert) | `4AAF68` | `80CC96` |
| M17 | `8B0000` (rouge) | `D94040` | `E88080` |
| M20 | `7A6000` (doré) | `C4A010` | `DFC050` |
| Seniors | `1B3F7A` (bleu) | `2563A8` | `4A86C8` |
| V1/V2/V3/V4 | `3D1A5C` (violet foncé) | `7A4A9E` | `A07ABE` |

---

## 10. SERVICES

### 10.1 cache.py

Cache à deux niveaux :
- **Mémoire** (`_cache` dict) + **Disque** (pickle `selecge_cache.pkl` dans `tmp` Flask)
- Survit aux redémarrages tant que le dossier tmp existe
- **Cache Sabre Laser séparé** (`_sl_cache`) : mémoire uniquement, pas de persistance disque

Clés typiques dans le cache :
- `"upload_national_h"`, `"upload_regional_h"` → DataFrame classement
- `"pdf_ffe_h_N1"`, `"pdf_ffe_h_N2"` → DataFrame niveau PDF

### 10.2 validation.py

Valide avant traitement :
- Extension + taille (max 16 Mo)
- DataFrame classement : colonnes `Nom`, `Prenom` présentes, ≥ 2 lignes
- DataFrame PDF : au moins une section non vide
- DataFrame PDF FFE : colonne `Niveau` présente, ≥ 5 tireurs
- Équipes : liste non vide

`ValidationError` : exception personnalisée avec `message` (utilisateur) + `detail` (debug).

---

## 11. ROUTES

### 11.1 routes/classements.py — Imports

| Route | Méthode | Source → Cache |
|-------|---------|----------------|
| `/api/upload_classement` | POST | Excel FFE → DataFrame → `cache.set(cle)` |
| `/api/upload_pdf` | POST | PDF BellePoule → dict niveaux → `cache.set(cle_N1)`, etc. |
| `/api/upload_pdf_ffe` | POST | PDF FFE qualifiés → DataFrame avec col `Niveau` |
| `/api/upload_pdf_ffe_equipes` | POST | PDF équipes FFE → liste équipes |
| `/api/upload_pdf_engarde_eq` | POST | PDF/XML Engarde équipes |
| `/api/upload_pdf_equipes` | POST | Dispatch PDF équipes ou Engarde |

### 11.2 routes/generation.py — Génération

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/generer_multi` | POST | Génère classeur individuel H+D selon n2_mode |
| `/api/generer_equipes_m15` | POST | Génère classeur équipes M15 |
| `/api/generer_equipes_seniors` | POST | Génère classeur équipes Seniors/Vétérans |
| `/api/telecharger/<nom>` | GET | Sert le fichier Excel généré |
| `/api/quotas_defaut` | GET | Retourne quotas H+D + infos CDF pour une cat+arme |

**Dispatch dans `generer_multi`** (ordre de priorité) :
1. `n2_mode == open_circuit` → `construire_genre_open_circuit()`
2. `regle.n2_mode == N2_FFE_N3_QUOTA` → `construire_genre_ffe_n1n2_n3quota()`
3. `regle.n2_mode == N1_FFE_N2_QUOTA` → `construire_genre_n1_ffe_n2_quota()`
4. `format == seniors` → `construire_genre_seniors()` (avec df_ffe si col Niveau présente)
5. Sinon → `construire_genre_jeunes()`

---

## 12. TESTS DE RÉGRESSION (audit.py)

Fichier de référence à exécuter avant ET après toute modification de la logique métier.

**Fixtures utilisées** (dans `/mnt/user-data/uploads/`) :
- PDFs FFE : FH/FD M17, FH/FD M20, SH M20, FH/FD/SH/SD/ED Seniors
- Classements Excel nationaux : FH/FD M17, FH/FD M20, FH/FD/ED Seniors
- Classements régionaux GE : FH/FD M17, FH/FD M20, FH/FD/ED Seniors, EH/ED M13

**Cas testés** :
- M17 FH : N1(1) + N2(1) + N3 quota(nat+rég)
- M17 FD : N1(0) + N2 quota(nat+rég)
- M20 FH : N2(1) + N3 quota
- M20 FD : N1(0) + N2 quota
- M20 SH : open_circuit N1+N2
- M13 EH/ED : 100% régional, quota 10
- Seniors FH : N3 FFE(1) + quota N3
- Seniors FD : quota N2
- Seniors SH : liste FFE N1 (8 GES)
- Seniors SD : liste FFE N1 (5 GES)
- Seniors ED : N1(7) + N2(3) + quota N3

**Exécution** : `python audit.py` depuis la racine LREGE.
Résultat attendu : `✅ N OK   ❌ 0 ERREUR(S)`

---

## 13. POINTS DE FRAGILITÉ ET RISQUES

| Point | Description | Fichier |
|-------|-------------|---------|
| Duplification crege_app/ | Modifications à propager manuellement dans racine ET SelecGE/ | Tout le projet |
| V4 Équipes emprunt V3 | `get_quota_equipes("V4",...)` substitue `"V3"` silencieusement | `quotas_lrege.py` L98-100 |
| TABLE_LREGE incomplète | Quota > 11 → calcul dynamique `round(n/3)`, non testé | `construction.py` L83-94 |
| Deux moteurs parallèles | `selection.py` (ETAPES) et `jeunes.py` (_construire_*) coexistent | `categories/` |
| Cache disque pickle | Si format df change entre versions, `selecge_cache.pkl` peut être corrompu | `services/cache.py` |
| Date hardcodée | `"19-20 décembre 2026"` hardcodée dans plusieurs fonctions | `jeunes.py`, `seniors.py`, `selection.py` |
| M13 fallback df_nat | Si `df_national=None`, utilise `df_regional` à la place (classe M13) | `jeunes.py` L654 |

---

## 14. PIPELINE DE LIVRAISON

```
PUBLIER_MAJ.bat
  1. maj_versions.py      → incrémente VERSION_LOCALE dans portail.py + version.json
  2. generer_setup_iss.py → génère setup.iss depuis version.json
  3. pyinstaller PortailLREGE.spec → compile PortailLREGE.exe
  4. ISCC.exe setup.iss   → génère l'installeur Windows
```

Nom des fichiers Excel générés : `LREGE_GE_{cat}_{comp}_{arme}_{genre}_{YYYYMMDD}.xlsx`

---

## 15. STACK TECHNIQUE

| Technologie | Version | Usage |
|-------------|---------|-------|
| Python | 3.11 | Langage principal |
| Flask | — | Framework web (tous les outils) |
| openpyxl | — | Génération Excel |
| pandas | — | Manipulation DataFrames classements |
| pdfplumber | — | Lecture PDFs classements |
| reportlab | — | Génération PDF arbitres (SuiviMaster) |
| Tkinter | stdlib | Interface EscriTools |
| PyInstaller | — | Compilation .exe |
| Inno Setup | — | Installeur Windows |
| pickle | stdlib | Cache disque SelecGE |

---

*Fin de cartographie. Mettre à jour ce document lors de tout changement architectural.*

---

## 16. CORRECTIONS DU 2026-07-10 (lots A+B)

| Correction | État |
|------------|------|
| .gitignore complété + désindexation .venv/build/pickles (3782 fichiers) | ✅ effectif au prochain commit |
| V4→V3 équipes : règle « Grands Vétérans » documentée (2 copies) | ✅ |
| TABLE_LREGE >11 : extrapolation round(n/3) verrouillée par tests (12-15) | ✅ |
| Date CDF hardcodée : remplacée par cfg["date"] dynamique (racine alignée sur SelecGE) | ✅ |
| calendrier.json : écriture atomique (tmp + os.replace) | ✅ |
| Marqueur version Excel : SELECGE_XLSX_V1 / SELECMASTER_V1 (propriété keywords), contrôle tolérant à la lecture | ✅ |
| .arbitres_master.pkl versionné (ARB_VERSION 2 + migration) | ✅ |
| Année M11 SelecMaster dérivée de la saison (plus de MAJ annuelle) | ✅ |
| Tests CalendrierLREGE créés (23) + bug bloquant ParseError corrigé | ✅ |
| verifier_duplication.py : contrôle racine vs SelecGE/ | ✅ (16 fichiers divergents détectés — chantier C11) |

**⚠️ État de la duplication (§3)** : la copie racine est OBSOLÈTE (Seniors ED 6 vs 4,
M23 équipes, quotas vétérans D…). **SelecGE/ fait foi** (REGLES.md). `SelecGE/` est un
sous-module git séparé. Resynchronisation racine ← SelecGE = chantier dédié (lot C).
