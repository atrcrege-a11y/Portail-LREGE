# SelecMaster v1.8 — Cartographie technique

> LREGE Grand Est — Sélection Master M11 / M13
> Version : **v1.8** | Port : **5004** | Saison : automatique (bascule 1er septembre)
> Dernière mise à jour : mai 2026

---

## 1. Architecture générale

```
SelecMaster/
├── app.py                  ← Point d'entrée Flask (219 lignes)
│                              Routes API, cache pickle, CORS
├── parser.py               ← Parseur HTML BellePoule (172 lignes)
├── selection.py            ← Logique sélection M11/M13 (57 lignes)
├── generateur.py           ← Génération Excel (356 lignes)
├── LANCER_SELECMASTER.bat  ← Démarrage Windows
├── requirements.txt        ← flask, openpyxl, beautifulsoup4
├── sorties/                ← Fichiers Excel générés
└── templates/
    └── index.html          ← Interface SPA HTML/CSS/JS (490 lignes)
```

---

## 2. Routes API (app.py)

| Route | Méthode | Description |
|-------|---------|-------------|
| `GET /` | GET | Interface principale |
| `POST /api/upload` | POST | Import fichier HTML BellePoule |
| `POST /api/recalculer` | POST | Recalcule sélections après changement bonus organisateur |
| `POST /api/generer` | POST | Génère Excel → sauvegarde disque → retourne nom fichier |
| `GET /api/telecharger/<nom>` | GET | Téléchargement fichier Excel depuis sorties/ |
| `POST /api/reset` | POST | Vide le cache mémoire + disque |
| `OPTIONS /api/<path>` | OPTIONS | CORS preflight |

---

## 3. Cache (app.py)

- **En mémoire** : `_cache` dict, clés `"H_M11"`, `"H_M13"`, `"D_M11"`, `"D_M13"`
- **Persistance disque** : `.cache_selecmaster.pkl` (pickle) dans le dossier SelecMaster/
- Survit aux redémarrages Flask
- Supprimé au reset

---

## 4. Parseur HTML (parser.py)

### Entrée
Fichier HTML BellePoule classement territorial (encoding latin-1)

### Détection automatique depuis le titre HTML
- **Arme** : `E` → Épée, `F` → Fleuret, `S` → Sabre
- **Genre** : `H` → Hommes, `D` → Dames
- **Catégorie** : `M11` ou `M13`
- **Territoire** : Alsace, Lorraine, Champagne-Ardenne (détection par mots-clés)

### Structure tableau BellePoule
```
Row dates   : Date | date1 | date2 | ...
Row en-tête : Place | Nom | Prénom | Club | Année Nais. | Points | Rang | Pts | ...
Row tireur  : 1 | NOM | Prénom | Club | 2015 | 30000 | 1 | 10000 | ...
```

### Données tireur extraites
```python
{
    "place": int,
    "nom": str,
    "prenom": str,
    "club": str,
    "annee_naissance": str,
    "points_total": float,
    "participations": int,        # nb compétitions avec score non nul
    "resultats": [...],           # détail par compétition
    "est_m11_dans_m13": bool,     # True si né >= 2015 dans fichier M13
}
```

---

## 5. Logique de sélection (selection.py)

### Règles
| Arme | Condition sélectionnabilité |
|------|-----------------------------|
| Épée, Fleuret | ≥ 3 épreuves du territoire |
| Sabre | Aucune (open) |

### Quota
- **Standard** : 5 tireurs
- **Avec bonus organisateur** : 6 tireurs (toggle manuel dans l'interface)

### Ordre de traitement
1. Séparer sélectionnables / non-sélectionnables (dans l'ordre du classement)
2. Top N sélectionnables → **Sélectionnés**
3. Sélectionnables restants → **Remplaçants**
4. Non-sélectionnables → section à part (épée/fleuret uniquement)

### Croisement M11/M13 (`enrichir_alertes_m11`)
Déclenché automatiquement dès que M11 + M13 du même genre sont importés.

| `alerte_m11` | Signification |
|-------------|---------------|
| `"double"` | Tireur présent dans liste M11 ET M13 — choix obligatoire |
| `"m13only"` | Tireur M11 qualifié M13 uniquement — autorisé à participer |
| `None` | Pas de cas M11 |

---

## 6. Génération Excel (generateur.py)

### Structure du fichier généré
- **1 feuille Hommes** + **1 feuille Dames**
- Nom fichier : `Selection_Master_{arme}_{categorie}_{territoire}.xlsx`
- Sauvegardé dans `sorties/` avant téléchargement

### Palette couleurs par arme (R1-R4)
| Arme | Titre (foncé) | Clair |
|------|--------------|-------|
| Épée | `1E6B3A` vert | `D5EFDF` |
| Fleuret | `1B3F7A` bleu roi | `D6E8F7` |
| Sabre | `7B0C0C` rouge | `FADBD8` |

### Couleurs statut tireurs
| Statut | Couleur |
|--------|---------|
| Sélectionné | `E2EFDA` vert |
| Remplaçant | `FCE4D6` orange |
| Non sélectionnable | `FFCCCC` rouge |
| Double qualification M11+M13 | `FFF2CC` jaune |
| M11 autorisé M13 uniquement | `EBF3FF` bleu clair |

### Structure feuille (calquée sur SelecGE)
```
R1  : LREGE Grand Est — Sélection régionale       [couleur arme, blanc]
R2  : MASTER GRAND EST                             [couleur arme, blanc]
R3  : Territoire · Saison                          [clair arme, foncé]
R4  : {ARME} H/D {CAT} {GENRE}                    [couleur arme, blanc]
R5  : Note générale (italic)
R6  : 📧 Confirmations avant le : {date longue}
R7  : ↳ administration@crege.fr, copie atrcrege@gmail.com (italic bleu)
R8  : 🖥 Clôture extranet : {date longue}           [fond lilas EBF2FA]
R9  : ⚖️ Arbitrage : règle                          [fond lilas EBF2FA]
R10 : 👤 Arbitre 1 | Nom Prénom | | Club | liste ▼  [1 seule ligne]
R11 : (vide)
R12+: Section SÉLECTIONNÉS (titre bleu)
      Note quota
      En-têtes colonnes : Rang | Nom | Prénom | Club | Participation Oui/Non ▼ | Remarque
      Lignes tireurs (couleur statut)
      Section REMPLAÇANTS (titre gris foncé)
      ...
      Section NON SÉLECTIONNABLES (titre gris, si épée/fleuret)
```

### Liste déroulante arbitre
```
Formation Régionale | Régionale | Formation Nationale | National | International
```

### Colonnes Excel (6 colonnes, largeurs SelecGE)
| Col | Contenu | Largeur |
|-----|---------|---------|
| A | Rang / statut | 16 |
| B | Nom | 24 |
| C | Prénom | 18 |
| D | Club | 36 |
| E | Participation Oui/Non | 20 |
| F | Remarque | 28 |

---

## 7. Interface (templates/index.html)

### Paramètres (section ⚙)
- Arme (Épée / Fleuret / Sabre)
- Territoire importé (informatif — le parseur prime)
- Territoire organisateur
- Toggle bonus organisateur → quota 5 ↔ 6

### Import (4 zones)
Grille 2×2 : Hommes M11 | Dames M11 / Hommes M13 | Dames M13

Comportements :
- Territoire détecté automatiquement depuis le fichier HTML
- Alerte jaune si territoire saisi ≠ territoire détecté
- Croisement M11/M13 déclenché automatiquement
- Recalcul instantané si toggle bonus change après import

### Dates
- 📧 Confirmations avant le (date picker → format JJ/MM/AAAA)
- 🖥 Clôture extranet (date picker → format JJ/MM/AAAA)
- Converties en "Lundi JJ Mois AAAA" dans l'Excel

### Aperçu
- Onglets M11 / M13
- Badges : territoire, quota, nb sélectionnés, remplaçants, alertes M11
- Tableau par genre avec couleurs statut

### Génération
- Bouton "⬇ Générer M11" / "⬇ Générer M13"
- Actif dès qu'au moins un genre de la catégorie est importé
- Téléchargement via `/api/telecharger/<nom>` (lien direct, pas blob)

### Variables JS clés
```javascript
const API = window.location.port === "5004" ? "" : "http://localhost:5004";
// Permet le fonctionnement en direct ET depuis l'iframe du portail
const cache = {};  // clés : "H_M11", "H_M13", "D_M11", "D_M13"
```

---

## 8. Intégration Portail LREGE

| Paramètre | Valeur |
|-----------|--------|
| Port | 5004 |
| Script | `SelecMaster/app.py` |
| Venv | Python système (aucun venv dédié) |
| Clé OUTILS | `selecmaster` |
| Icône | 🥇 |
| Couleur portail | `#1F6B38` (vert) |
| CORS autorisé | `http://localhost:5000` |

---

## 9. Points d'attention

**Casse IDs boutons** : IDs en minuscules (`btn-gen-m11`), `generer()` reçoit `'m11'` et fait `.toUpperCase()` pour l'API.

**Cache pickle** : `.cache_selecmaster.pkl` dans le dossier SelecMaster/. Ignoré par git (ajouter à `.gitignore`).

**Téléchargement** : passe par `/api/telecharger/<nom>` (fichier sur disque) — pas de blob fetch. Nécessaire pour compatibilité Chrome/extensions.

**Détection M11** : basée sur l'année de naissance ≥ 2015 (saison 2025-2026). À mettre à jour chaque saison.

**Sabre** : pas de condition de participations — `condition_participations = False`.

**Territoire** : le parseur prime sur le select de l'interface. Alerte affichée si incohérence, mais le territoire du fichier est utilisé.

---

## 10. Dépendances

| Paquet | Usage |
|--------|-------|
| `flask` | Serveur web local |
| `openpyxl` | Génération Excel (styles, validation, fusion cellules) |
| `beautifulsoup4` | Parsing HTML BellePoule |
| `pickle` | Persistance cache (stdlib) |
