# CARTOGRAPHIE — SYNESC v2.4.4

**SYNESC** (Synthèse Compétitions Escrime) est une application web locale (Flask/Python) destinée à la Ligue Régionale d'Escrime Grand Est (LREGE). Elle transforme des fichiers XML exportés par Engarde en fichiers Excel standardisés (format EGESC), génère des mails de synthèse pour les DTs, et produit des PDF arbitres.

---

## 1. Stack technique

| Composant | Technologie |
|-----------|-------------|
| Serveur web | Flask 3.x (Python 3.9+) |
| Génération Excel | openpyxl 3.1+ |
| Extraction PDF horaires | pdfplumber 0.10+ |
| Génération PDF arbitres | reportlab 4.0+ |
| Lecture XML Engarde | xml.etree.ElementTree (stdlib) |
| Lanceur Windows | Batch + venv auto-créé |
| Interface utilisateur | Template Jinja2 (templates/index.html) + JS inline |
| Stockage session | Dict Python en mémoire (`_store`) + session Flask (cookie) |

---

## 2. Arborescence commentée

```
SYNESC/
│
├── app.py                    Point d'entrée Flask : routes HTTP uniquement, _store en mémoire
├── requirements.txt          Dépendances : flask, openpyxl, pdfplumber, requests, reportlab
├── Lancer_SYNESC.bat         Lanceur Windows : détecte Python, crée le venv, installe les deps, ouvre le navigateur sur port 5000
│
├── core/                     Couche métier partagée — indépendante du type de compétition
│   ├── __init__.py           (vide)
│   ├── config.py             Constantes globales : version, changelog, barèmes arbitres, couleurs Excel, listes CRA/superviseurs (TODO : à remplir)
│   ├── parser.py             Parsing XML Engarde → (meta, tireurs, arbitres) + agrégation multi-fichiers
│   ├── excel_base.py         Helpers de style openpyxl : border_all, mk_font, mk_fill, mk_align, sc(), gcl()
│   ├── excel_commun.py       Feuilles Excel communes : feuille_extranet(), feuille_arbitres(), feuille_recap_arbitres()
│   └── pdf_arbitres.py       Génération PDF liste arbitres (retenus/libérés) depuis un Excel SYNESC déjà généré
│
├── competitions/             Couche compétition — pattern Strategy
│   ├── __init__.py           Registre COMPETITIONS + COMPETITIONS_META, fonction get_competition()
│   ├── base.py               Classe abstraite CompetitionBase : pipeline generer_excel(), méthodes abstraites
│   ├── grand_est.py          Championnat Régional Grand Est : catégories M13→V4, tarifs, bilan financier
│   ├── alsace.py             Championnat d'Alsace : hérite GrandEst, ajoute M9/M11, feuilles par arme, bilan financier par arme
│   └── lorraine.py           Coupe de Lorraine : individuel uniquement, M9→M15, 3 armes séparées, bilan par arme
│
├── templates/
│   └── index.html            Interface SPA : sidebar upload + dropzone PDF, panneau principal onglets (Aperçu / Changelog / À propos)
│
└── static/
    ├── logo_lrege.png        Logo pour l'interface web
    └── logo_lrege_excel.png  Logo (conservé, non utilisé dans les Excel depuis v2.4.0)
```

---

## 3. Architecture — flux de données

```
Utilisateur (navigateur)
        │  glisser-déposer XML / ZIP
        ▼
  POST /api/upload
        │  parse_xml() [core/parser.py]
        │  → (meta, tireurs, arbitres) ajouté à _store[sid]
        ▼
  GET  /api/preview         ← aperçu tableau clubs × catégories
  POST /api/upload_programme ← extraction horaires depuis PDF programme (pdfplumber)
        │
        ▼
  POST /api/generate
        │  get_competition(comp_type)   [competitions/__init__.py]
        │  → GrandEst | Alsace | Lorraine
        │
        │  comp.generer_excel(fichiers_list)
        │       └── construire_donnees()  [core/parser.py]
        │               → groupes_indiv, groupes_equipe, arbitres_all, …
        │
        │  ┌── feuille_arbitres()        [core/excel_commun.py]
        │  ├── feuille_recap_arbitres()  [core/excel_commun.py]
        │  ├── feuille_financiere()      [competition spécifique]
        │  ├── feuille_indiv()           [competition spécifique]
        │  ├── feuille_equipe()          [competition spécifique]
        │  └── feuille_extranet()        [core/excel_commun.py]
        │
        ▼
  send_file() → .xlsx téléchargé
        │
        ▼
  POST /api/charger_excel_arbitres  ← rechargement de l'Excel modifié (statuts Retenu/Libéré)
  POST /api/mail_body               ← corps du mail (JSON, pour Gmail)
  POST /api/generate_mail           ← .eml avec Excel en PJ (pour Outlook)
  POST /api/pdf_arbitres            ← PDF arbitres depuis l'Excel SYNESC
```

---

## 4. Points d'entrée HTTP

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/` | Interface web principale |
| GET | `/api/version` | Infos version + changelog (JSON) |
| POST | `/api/upload` | Upload XML / ZIP → parse + stocke dans `_store` |
| GET | `/api/files` | Liste des fichiers chargés dans la session |
| POST | `/api/remove` | Supprime un fichier par son `uid` |
| POST | `/api/clear` | Vide le store de la session |
| GET | `/api/preview` | Aperçu tableau clubs × catégories (tous fichiers chargés) |
| POST | `/api/generate` | Génère et retourne le fichier Excel EGESC |
| POST | `/api/upload_programme` | Extrait les horaires d'un PDF programme (4 formats) |
| POST | `/api/clear_programme` | Supprime les horaires PDF de la session |
| POST | `/api/mail_body` | Génère sujet + corps mail en JSON |
| POST | `/api/generate_mail` | Génère un .eml avec l'Excel en PJ |
| POST | `/api/pdf_arbitres` | Génère un PDF liste arbitres depuis un Excel SYNESC |
| POST | `/api/charger_excel_arbitres` | Lit les statuts Retenu/Libéré d'un Excel SYNESC modifié |
| POST | `/api/clear_excel_arbitres` | Supprime les statuts arbitres de la session |

---

## 5. Structures de données circulantes

### Dans `_store[sid]` (mémoire serveur)
Liste de tuples `(meta, tireurs, arbitres)` par session utilisateur.

**meta** — dict issu du parsing XML :
```python
{
  "uid": str,          # UUID généré à l'upload (dédoublonnage)
  "arme": "F"|"E"|"S",
  "arme_label": str,   # "Fleuret" | "Épée" | "Sabre"
  "categorie": str,    # uppercase, ex: "M13", "SENIORS"
  "sexe": "M"|"F"|"MF",
  "type": "I"|"E",     # Individuel | Équipe
  "titre": str,        # TitreLong Engarde
  "date": str,         # JJ.MM.AAAA
  "date_debut": str,
  "date_fin": str,
  "id": str,           # ID Engarde
  "filename": str,
}
```

**tireur** — dict :
```python
{"nom", "prenom", "licence", "club", "equipe", "region", "ligue", "dept", "sexe", "naissance"}
```

**arbitre** — dict :
```python
{"nom", "prenom", "licence", "club", "region", "ligue", "dept",
 "categorie",    # niveau : FT/FD/T/D/FR/R/FN/N/I
 "arme", "arme_label", "cat_comp", "type_comp", "date_source"}
```

### Données agrégées (produites par `construire_donnees()`)

```
groupes_indiv  : {date_str → {cat_key → {club → {"H": int, "D": int}}}}
groupes_equipe : {date_str → {cat_key → {club → {"equipes": set, "tireurs_H": int, "tireurs_D": int, ["mixte": bool, "tireurs_MX": int]}}}}
arbitres_all   : [arbitre enrichi, ...]
ligue_info     : {club → {region, ligue, dept}}
```

Quand `par_arme=True` (Alsace, Lorraine) : `cat_key` devient `"CAT|ARME"` (ex: `"M9|F"`).

### Dans la session Flask (cookie)
| Clé | Contenu |
|-----|---------|
| `sid` | UUID identifiant le bucket dans `_store` |
| `programme` | `{"lieu": str, "categories": [{cat, date, appel, scratch, debut, …}]}` issu du PDF |
| `arbitres_statuts` | `{date_label → {retenu: int, libere: int, cout_retenu: float}}` issu du rechargement Excel |

---

## 6. Dépendances externes

| Bibliothèque | Usage |
|---|---|
| `flask` | Serveur web, sessions, routing |
| `openpyxl` | Création et mise en forme des fichiers Excel .xlsx |
| `pdfplumber` | Extraction de texte et tableaux depuis les PDFs programme |
| `reportlab` | Génération PDF liste arbitres |
| `requests` | Présente dans requirements.txt (non utilisée dans le code actuel — vestige d'une version précédente avec API Claude) |
| `xml.etree.ElementTree` | Parsing XML Engarde (stdlib, pas de dépendance externe) |

---

## 7. Configuration — variables clés (`core/config.py`)

| Variable | Valeur actuelle | Rôle |
|----------|----------------|------|
| `APP_VERSION` | `"2.4.4"` | Version affichée dans l'interface |
| `APP_RELEASE_DATE` | `"2026-05-12"` | Date de release |
| `BAREME_ARBITRES` | liste de tuples `(code, tarif €)` | Barème indemnités arbitres FFE 2024–2025 |
| `COLORS` | dict hex | Palette couleurs Excel partagée |
| `JOURS_SEMAINE` | liste | Noms jours (lundi=0) pour formatage dates |
| `NOMS_CRA` | `[]` (vide) | **À compléter** — responsable CRA pour Grand Est et Alsace |
| `NOMS_SUPERVISEURS_GRAND_EST` | `[]` (vide) | **À compléter** — superviseur Grand Est |
| `NOMS_SUPERVISEURS_LORRAINE` | `[]` (vide) | **À compléter** — superviseurs Lorraine par arme |
| `app.secret_key` (app.py) | `"lrege-synesc-secret-2025"` | Clé de signature des sessions Flask (hardcodée) |
| `MAX_CONTENT_LENGTH` | 32 Mo | Taille max des fichiers uploadés |

