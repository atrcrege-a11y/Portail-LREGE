# CARTOGRAPHIE — SuiviGE

> Suivi des confirmations CDF individuel + équipes — port **5006**
> Générée le 2026-07-10 par lecture exhaustive du code source.

---

## 1. Rôle

Application web locale (Flask) de suivi des confirmations de participation aux Championnats de France,
toutes catégories. **Autonome de SelecGE** : lit les fichiers Excel générés par SelecGE (individuel et équipes),
suit les réponses oui/non/attente, calcule les remplaçants à appeler, et peut se synchroniser depuis la
**plateforme de confirmation en ligne** (voir `CARTOGRAPHIE_PLATEFORME_CONFIRMATION.md` à la racine).

## 2. Stack

| Composant | Technologie |
|-----------|-------------|
| Serveur | Flask (port 5006), CORS ouvert |
| Lecture Excel | openpyxl (`load_workbook`) |
| Persistance | pickle `.suivi_ge.pkl` — **versionné** (`DB_VERSION = 2` + migration v1→v2) |
| Plateforme en ligne | urllib (stdlib), `GET {PLATEFORME_URL}/api/suivi/{PLATEFORME_TOKEN}` |
| Interface | `templates/index.html` (SPA) |
| Tests | `tests/test_suivige.py` (pytest, fixtures synthétiques) |

## 3. Arborescence

```
SuiviGE/
├── app.py                (194 l.) Routes HTTP uniquement — délègue tout à suivi.py
├── suivi.py              (745 l.) Logique métier + persistance + parseurs Excel + client plateforme
├── .suivi_ge.pkl         Base pickle (créée au 1er usage)
├── templates/index.html  Interface SPA
├── tests/                fixtures.py + test_suivige.py
├── LANCER_SUIVIGE.bat
└── requirements.txt
```

## 4. Modèle de données (_db, pickle)

```
_db = {
  "__version__": 2,
  "indiv|Épée|Seniors|H": {
      type, arme, categorie, genre, competition, date_lieu,
      tireurs: [{rang, nom, prenom, club, statut(qualifie|remplacant),
                 confirmation(oui|non|attente), confirmation_at, note}],
      arbitres: [...], audit: [{ts, action, detail}],
      created_at, updated_at,
  },
  "equipe|Fleuret|M15|D": {
      ..., equipes: [{rang, nom, club(s), confirmation, note, composition:[...]}],
  },
}
```

Clé : `type|arme|categorie|genre`. Genre `HD` réservé aux imports plateforme (H+D fusionnés).
Migration `_migrer()` : complète les champs manquants, ré-écrit le pickle si version < 2.

## 5. Routes

| Route | Méthode | Rôle |
|-------|---------|------|
| `/api/import/indiv` | POST | Excel SelecGE individuel → `initialiser_indiv()` |
| `/api/import/equipes` | POST | Excel SelecGE équipes → `initialiser_equipes()` |
| `/api/import/retour_indiv` `/retour_equipes` | POST | Ré-import d'un Excel annoté (colonne confirmation remplie) |
| `/api/import/plateforme` | POST | Sync depuis la plateforme en ligne (url+token, sinon env) |
| `/api/suivis` | GET | Liste de tous les suivis |
| `/api/suivi/<type>/<arme>/<cat>/<genre>/stats` | GET | Compteurs oui/non/attente qualifiés + remplaçants |
| `…/detail` | GET | Liste complète tireurs/équipes |
| `…/remplacants` | GET (indiv) | Remplaçants à appeler = refus + remplaçants-non − remplaçants-oui |
| `…/audit` | GET | Journal des actions |
| `…/confirmation` | POST | MAJ confirmation tireur (nom+prénom) ou équipe (rang) |
| `…/composition` | POST (équipe) | MAJ composition d'équipe |
| `…/supprimer` | POST | Supprime un suivi |

## 6. Contrat de lecture Excel SelecGE (⚠️ couplage critique)

Constantes en tête de `suivi.py` — doivent correspondre **exactement** aux labels
générés par `SelecGE/crege_app/generateur/` :

| Constante | Valeur | Usage |
|-----------|--------|-------|
| `EXCEL_PREFIX_INDIV` | regex `^CL\s+(NAT|GE)\s+\d+` | Détection ligne tireur |
| `EXCEL_PREFIX_EQUIPE` | regex `^N°\s*\d+` | Détection ligne équipe |
| `EXCEL_PREFIX_COMPO` | regex `^\d{1,2}$` | Détection ligne composition |
| `EXCEL_LABEL_QUALIFIE` / `REMPLAÇANT` / `QUALIFIÉE` | titres de sections | Statut tireur/équipe |
| `EXCEL_ARMES_MAP`, `EXCEL_CATS` | — | Extraction méta depuis lignes 1-3 |

`_extraire_meta_titre()` : compétition (ligne 1), date/lieu (ligne 2), arme+genre+catégorie (ligne 3).
**Tout changement de mise en forme dans SelecGE casse silencieusement ce parsing.**
Aucun marqueur de version n'existe côté Excel.

## 7. Logique remplaçants (get_remplacants_a_appeler)

`manque = refus_qualifiés + refus_remplaçants − remplaçants_oui` ;
retourne les `manque` premiers remplaçants en attente, dans l'ordre du classement.

## 8. Client plateforme en ligne (§ dédié racine)

- Config : `PLATEFORME_URL` / `PLATEFORME_TOKEN` (env) ou saisis dans l'interface
- `mapper_plateforme()` : fonction pure JSON → entries ; genre forcé `HD` ; **individuel uniquement** (équipes = TODO)
- Mapping confirmation : non saisi → `attente` ; saisi+présent → `oui` ; saisi+absent → `non`
- L'import écrase l'entrée `…|HD` existante mais conserve `created_at` et `audit`

## 9. Points de fragilité

| Point | Description |
|-------|-------------|
| Couplage format Excel | Voir §6 — pas de marqueur de version dans les fichiers |
| Équipes hors plateforme | Sync plateforme = individuel seul (TODO documenté dans le code) |
| Doublons Excel/plateforme | Un même CDF peut exister en `…|H` + `…|D` (Excel) ET `…|HD` (plateforme) sans réconciliation |
| Identification tireur | Par (nom, prénom) — risque homonymes |
| CORS `*` | Acceptable en local, à ne pas exposer en ligne |

---

*Mettre à jour ce document lors de tout changement architectural.*
