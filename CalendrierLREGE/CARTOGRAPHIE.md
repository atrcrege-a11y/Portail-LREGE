# CARTOGRAPHIE — CalendrierLREGE

> Calendrier des compétitions LREGE — port **5003**
> Générée le 2026-07-10 par lecture exhaustive du code source.

---

## 1. Rôle

Application web locale (Flask) de gestion du calendrier des compétitions et stages du Grand Est.
Import du calendrier FFE (.xlsx), ajout/édition manuelle d'événements, filtres, exports iCal / Excel / PDF.

## 2. Stack

| Composant | Technologie |
|-----------|-------------|
| Serveur | Flask (port 5003) |
| Import Excel FFE | pandas (`parse_xlsx`) |
| Import PDF FFE | pdfplumber (`parser_pdf.py`) — **⚠️ orphelin, non branché à une route** |
| Exports | iCal (manuel), Excel (openpyxl), PDF (reportlab) |
| Stockage | `data/calendrier.json` (JSON indenté UTF-8) |
| Interface | `templates/index.html` (SPA, 704 lignes) |

## 3. Arborescence

```
CalendrierLREGE/
├── app.py                  (187 l.) Routes Flask + load/save/filtres
├── parser_ffe.py           (114 l.) Excel FFE → événements JSON
├── parser_pdf.py           (238 l.) PDF FFE grille annuelle → événements (NON UTILISÉ)
├── exports.py              (236 l.) build_ical() / build_excel() / build_pdf()
├── data/calendrier.json    Base de données (source unique de vérité)
├── templates/index.html    Interface SPA
├── LANCER_CALENDRIER.bat / PREMIER_LANCEMENT.bat
└── requirements.txt
```

## 4. Routes

| Route | Méthode | Rôle |
|-------|---------|------|
| `/` | GET | Interface |
| `/api/events` | GET | Liste filtrée (niveau, arme, catégorie, type, grand_est, mois, search, date_from/to) |
| `/api/events` | POST | Ajout manuel (validation date_debut AAAA-MM-JJ + intitule obligatoires) |
| `/api/events/<id>` | PUT | Mise à jour (dict.update, pas de validation de schéma) |
| `/api/events/<id>` | DELETE | Suppression |
| `/api/stats` | GET | Compteurs par niveau/type/source |
| `/api/import` | POST | Import .xlsx FFE — **remplace tous les événements FFE, conserve les manuels** |
| `/api/export/ical` `/excel` `/pdf` | GET | Exports (mêmes filtres que /api/events) |

## 5. Modèle d'événement (JSON)

Champs : `id` (uuid4), `source` (`ffe`/`manuel`), `manuel` (bool), `type_evenement`
(`competition`/`stage`/`formation_arbitrage`/`formation_animateur`/`formation_cadre`),
`statut`, `date_debut`/`date_fin` (AAAA-MM-JJ), `niveau`, `niveau_raw`, `numero`,
`intitule`, `lieu`, `perimetre`, `arme`, `armes[]`, `sexe`, `categories[]`,
`type_epreuve`, `url`, `grand_est` (bool), `notes`, `__version__`.

**Migration ascendante** : `load_events()` complète les champs manquants (`setdefault`) à chaque lecture.
`JSON_VERSION = 1` dans `parser_ffe.py` — à incrémenter si le schéma change.

## 6. Parseur FFE (parser_ffe.py)

- Constantes colonnes FFE centralisées en tête de fichier (si la FFE renomme → un seul point de modif)
- Décodage arme/sexe : `EPEM/EPEF/…` → (arme, H/D/H+D), inclut sabre laser et artistique
- Détection Grand Est : périmètre ∈ {Régional, Interrégional…} OU intitulé contenant `grand est`/`lrege`/`crege`
- Détection type événement par mots-clés dans l'intitulé (`arbitr`, `stage`, `animateur`…)
- Déduplication par clé `(date_debut, intitule.lower(), lieu.lower())` — fusion des armes/catégories

## 7. Import : règle de fusion

`POST /api/import` : nouveaux événements FFE + événements `manuel=True` existants.
**Les événements FFE précédents sont écrasés** (pas de merge par id). Les éditions manuelles
d'événements FFE (PUT) sont donc **perdues au ré-import** sauf si `manuel` a été mis à True.

## 8. Points de fragilité

| Point | Description |
|-------|-------------|
| Aucun test | Seul outil du portail sans dossier `tests/` |
| Écriture non atomique | `save_events()` écrit directement `calendrier.json` — corruption possible si crash en cours d'écriture |
| PUT sans validation | `update_event` applique `dict.update(data)` sans vérifier le schéma ni les dates |
| parser_pdf.py orphelin | Code complet mais non branché à une route ni importé |
| Ré-import destructif | Éditions d'événements FFE perdues au ré-import (voir §7) |
| Concurrence | Pas de verrou — deux requêtes simultanées peuvent se marcher dessus (usage mono-utilisateur local : risque faible) |

---

*Mettre à jour ce document lors de tout changement architectural.*
