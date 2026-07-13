# CARTOGRAPHIE — SuiviMaster

> Suivi des confirmations Master GE M11/M13 + gestion arbitres — port **5005**
> Générée le 2026-07-10 par lecture exhaustive du code source.

---

## 1. Rôle

Application web locale (Flask) de suivi des confirmations de participation au Master Grand Est M11/M13,
par territoire (Alsace / Lorraine / Champagne-Ardenne), avec logique de pioche inter-territoires,
plafond d'effectif (16), gestion des arbitres (proposés/retenus/libérés) et exports PDF.
**Autonome de SelecMaster** : lit les Excel générés par SelecMaster.

## 2. Stack

| Composant | Technologie |
|-----------|-------------|
| Serveur | Flask (port 5005), CORS ouvert |
| Lecture Excel | openpyxl |
| PDF | reportlab (`generer_pdf_suivi`, `generer_pdf_arbitres` dans app.py) |
| Persistance | 2 pickles : `.suivi_master.pkl` (**versionné** `DB_VERSION = 2` + migration) et `.arbitres_master.pkl` (**non versionné**) |
| Interface | `templates/index.html` (SPA) |
| Tests | `tests/test_suivimaster.py` (pytest) |

## 3. Arborescence

```
SuiviMaster/
├── app.py                 (585 l.) Routes HTTP + génération PDF reportlab
├── suivi.py               (783 l.) Métier : suivis (l.1-548) + arbitres (l.556-783)
├── .suivi_master.pkl      Base suivis (clé "arme|categorie")
├── .arbitres_master.pkl   Base arbitres (clé arme → liste)
├── templates/index.html   Interface SPA
├── tests/                 fixtures.py + test_suivimaster.py
├── LANCER_SUIVIMASTER.bat
└── requirements.txt
```

## 4. Modèle de données

### Suivis (`_db`, clé `arme|categorie`)
```
{
  territoires: {"Alsace": [tireur...], "Lorraine": [...], "Champagne-Ardenne": [...]},
  territoire_organisateur: str,
  audit: [{ts, action, detail}], created_at, updated_at,
}
tireur = {rang, nom, prenom, club, genre(H|D),
          statut(selectionne|remplacant|non_selectionnable),
          confirmation(oui|non|attente), appele(bool), note}
```
Identité tireur : `(NOM, PRENOM, genre)` majuscules (`_cle_tireur`).

### Arbitres (`_arbitres`, clé arme)
`{id, nom, prenom, niveau, club, territoire, statut(propose|retenu|libere), note}`
Contraintes : `MAX_RETENUS = 8` par arme, niveaux valides dans `NIVEAUX_ARB_OK`.

## 5. Routes

| Route | Méthode | Rôle |
|-------|---------|------|
| `/api/import_selection` | POST | Excel SelecMaster + territoire + territoire organisateur |
| `/api/import_retour` | POST | Ré-import Excel annoté (confirmations) |
| `/api/suivis` | GET | Liste des suivis |
| `/api/suivi/<arme>/<cat>/stats` `/detail` `/audit` | GET | Consultation |
| `/api/suivi/<arme>/<cat>/remplacants` | GET | Pioche : remplaçants à appeler par territoire |
| `/api/suivi/<arme>/<cat>/confirmation` | POST | MAJ confirmation (nom, prénom, genre, territoire) |
| `/api/suivi/<arme>/<cat>/appel` | POST | Marque un remplaçant comme appelé |
| `/api/suivi/<arme>/<cat>/supprimer` | POST | Suppression |
| `/api/suivi/<arme>/<cat>/export_pdf` | GET | PDF du suivi |
| `/api/arbitres[…]` | GET/POST | CRUD arbitres + import Excel + export PDF + stats |
| `/api/recap` | GET | Récapitulatif global |

## 6. Contrat de lecture Excel SelecMaster (⚠️ couplage critique)

Constantes en tête de `suivi.py` — doivent correspondre exactement à `SelecMaster/generateur.py` :

| Constante | Valeur |
|-----------|--------|
| `EXCEL_PREFIX_RANG` | `"M "` (lignes tireurs : "M 1", "M 2") |
| `EXCEL_LABEL_SELECTIONNES` | `"SÉLECTIONNÉS"` |
| `EXCEL_LABEL_REMPLACANTS` | `"REMPLAÇANTS"` |
| `EXCEL_LABEL_NON_SELECTIONNABLE` | `"NON SÉLECTIONNABLE"` |
| `EXCEL_FORMAT_VERSION` | `"SELECMASTER_V1"` — **déclaré mais non écrit/vérifié (« à venir »)** |

1 feuille = 1 genre (Hommes/Dames). Territoire fourni par l'utilisateur à l'import.

## 7. Logique de pioche (get_remplacants_a_appeler)

1. Ordre de pioche selon le territoire organisateur (`ORDRE_PIOCHE`) : l'organisateur d'abord, puis les 2 autres
2. Par territoire et par genre : `manquants = refus_sélectionnés + appelés_non − appelés_ok`
3. Pioche d'abord les remplaçants propres du territoire, dans l'ordre du classement
4. Plafond global `EFFECTIF_MAX = 16` (sélectionnés confirmés + remplaçants appelés non refusés), vérifié à chaque ajout

## 8. Points de fragilité

| Point | Description |
|-------|-------------|
| Couplage format Excel | §6 — marqueur `SELECMASTER_V1` prévu mais jamais écrit ni contrôlé |
| `.arbitres_master.pkl` non versionné | Contrairement au pickle suivis (DB_VERSION 2), pas de migration |
| PDF dans app.py | ~270 lignes de reportlab dans la couche routes (`generer_pdf_suivi`, `generer_pdf_arbitres`) — à extraire si évolution |
| Identité tireur | (nom, prénom, genre) — risque homonymes |
| Territoire déclaratif | Le territoire est saisi par l'utilisateur à l'import, non déduit du fichier |
| CORS `*` | Acceptable en local uniquement |

---

*Mettre à jour ce document lors de tout changement architectural.*
