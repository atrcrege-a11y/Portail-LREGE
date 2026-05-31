# CARTOGRAPHIE — EscriTools v2.0

**EscriTools** est une application web locale (Flask/Python) qui regroupe 5 outils
de conversion et traitement de fichiers liés à l'escrime (BellePoule, FFE WIN, PDF, Markdown).

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Serveur web | Flask 3.x |
| Extraction PDF | pdfplumber |
| Génération PDF | reportlab |
| Interface | HTML/JS vanilla (single page, 5 onglets) |
| Lanceur Windows | LANCER.bat + venv auto |

---

## Arborescence

```
EscriTools/
├── app.py                      Point d'entrée Flask (routes uniquement)
├── requirements.txt            Dépendances Python
├── LANCER.bat                  Lanceur Windows
├── CARTOGRAPHIE.md             Ce fichier
├── sorties/                    Fichiers générés (auto-créé)
│
├── core/                       Logique métier — indépendante de l'UI
│   ├── bellepoule_fff.py       BellePoule PDF individuel → .fff WIN/FFE
│   ├── pdf_markdown.py         PDF → Markdown structuré
│   ├── markdown_pdf.py         Markdown → PDF (reportlab)
│   ├── equipe_individuel.py    BellePoule équipes → classement individuel .fff
│   └── renommage.py            XML ↔ .cotcot (masquage FFE WIN)
│
├── templates/
│   └── index.html              Interface SPA 5 onglets
│
└── tests/
    └── test_escritools.py      Tests unitaires (pytest, fixtures synthétiques)
```

---

## Modules core

### `core/bellepoule_fff.py`
Conversion PDF BellePoule (épreuve individuelle) → fichier .fff WIN/FFE.
- `extraire_pages(pdf_path)` → liste de textes de pages
- `trouver_entete(pages)` → dict {arme, sexe, categorie, date, nom}
- `extraire_liste_appel(pages)` → {licence: {nom, prenom, club}}
- `extraire_classement(pages)` → [{place, nom, prenom, club}]
- `trouver_licence(nom, prenom, licences_map)` → str
- `charger_dates(csv_path)` → {licence: ddn}
- `ecrire_fff(classement, info, licences_map, dates, output_path)` → None
- `convertir(pdf_path, output_path, log, csv_path)` → (bool, str)

### `core/pdf_markdown.py`
Extraction PDF → Markdown structuré. Détecte titres (taille/graisse), listes,
tableaux, mise en page 2 colonnes.
- `extraire_blocs(page)` → list[dict] (text, size, bold, col, has_cols)
- `calculer_seuils(tous_blocs)` → {h1, h2, h3, body}
- `detecter_repetitifs(tous_blocs, nb_pages, seuil)` → set[str]
- `page_en_md(page, seuils, repetitifs)` → str Markdown
- `convertir(pdf_path, log)` → str Markdown

### `core/markdown_pdf.py`
Rendu Markdown → PDF soigné via reportlab.
- `echapper(txt)` → str (HTML + gras/italique inline)
- `convertir(md_path, output_path, log)` → (bool, str)
- `convertir_lot(md_paths, output_dir, fusion, log)` → (succes, erreurs)

### `core/equipe_individuel.py`
Conversion résultats BellePoule équipes → classement individuel .fff.
Supporte PDF et Markdown en entrée.
- `extraire_inscrits_md(texte)` / `extraire_inscrits_pdf(pages)`
- `extraire_classement_general_md(texte)` / `_pdf(pages)`
- `extraire_classement_poules_md(texte)` / `_pdf(pages, noms_eq)`
- `construire_classement_individuel(inscrits, cg, cp)` → list
- `generer_fff(tireurs, ...)` → None
- `traiter_fichier(chemin, ..., log)` → (bool, str)

### `core/renommage.py`
Renommage fichiers XML ↔ .cotcot.
- `xml_vers_cotcot(chemins)` → (nouveaux_chemins, erreurs)
- `cotcot_vers_xml(chemins)` → (nouveaux_chemins, erreurs)

---

## Routes Flask (`app.py`)

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Interface web |
| `/api/bellepoule/convertir` | POST | PDF → .fff |
| `/api/bellepoule/telecharger/<f>` | GET | Téléchargement |
| `/api/pdf2md/convertir` | POST | PDF(s) → Markdown |
| `/api/pdf2md/telecharger/<f>` | GET | Téléchargement |
| `/api/md2pdf/convertir` | POST | Markdown(s) → PDF |
| `/api/md2pdf/telecharger/<f>` | GET | Téléchargement |
| `/api/renommage/renommer` | POST | XML ↔ .cotcot |
| `/api/renommage/telecharger/<f>` | GET | Téléchargement |
| `/api/equipe_indiv/convertir` | POST | BellePoule équipes → .fff |
| `/api/equipe_indiv/telecharger/<f>` | GET | Téléchargement |

---

## Format .fff (WIN/FFE)

```
FFF;WIN;competition; ;individuel
DATE;ARME;SEXE;CATEGORIE;NOM_COMP;NOM_COMP
NOM,PRENOM,DDN,SEXE,FRA,;,,;LICENCE,,CLUB,PLACE,,;PLACE,t
...
```
Encodage : latin-1. Fin de ligne : CRLF.
