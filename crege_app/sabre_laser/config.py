"""
sabre_laser/config.py — Paramètres Sabre Laser 2025-2026.
"""

# ── Palettes couleurs par discipline ─────────────────────────────────
PALETTES = {
    "combat_sportif_senior": {
        "nom":        "Rouge Bordeaux",
        "titre":      "7B1A1A",
        "section1":   "C0392B",
        "section2":   "E74C3C",
        "section3":   "F1948A",
        "alerte":     "FDEDEC",
        "entete_col": "FADBD8",
        "fond_ligne": "FEF9F9",
        "bord":       "F1948A",
    },
    "combat_sportif_m17": {
        "nom":        "Orange Ambre",
        "titre":      "7D4300",
        "section1":   "E67E22",
        "section2":   "F39C12",
        "section3":   "FAD7A0",
        "alerte":     "FEF9E7",
        "entete_col": "FDEBD0",
        "fond_ligne": "FEFDF8",
        "bord":       "FAD7A0",
    },
    "epreuve_technique": {
        "nom":        "Vert Jade",
        "titre":      "1A5C2A",
        "section1":   "27AE60",
        "section2":   "2ECC71",
        "section3":   "A9DFBF",
        "alerte":     "EAFAF1",
        "entete_col": "D5F5E3",
        "fond_ligne": "F9FEFC",
        "bord":       "A9DFBF",
    },
    "combat_choregraphie": {
        "nom":        "Violet Indigo",
        "titre":      "4B0082",
        "section1":   "6A0DAD",
        "section2":   "8B5CF6",
        "section3":   "C4B5FD",
        "alerte":     "F3E8FF",
        "entete_col": "EDE9FE",
        "fond_ligne": "F9F5FF",
        "bord":       "C4B5FD",
    },
}

def get_palette(disc_id: str) -> dict:
    return PALETTES.get(disc_id, PALETTES["combat_choregraphie"])

# ── Disciplines ───────────────────────────────────────────────────────
DISCIPLINES = [
    {
        "id":          "combat_sportif_senior",
        "label":       "Combat Sportif Seniors",
        "label_court": "CS Seniors",
        "categorie":   "Seniors",
        "mixte":       True,
        "niveaux": [
            {
                "id":           "epreuve_nationale",
                "label":        "Épreuve Nationale",
                "quota_ge":     11,
                # Épreuve Nationale : classement régional uniquement (pas de liste FFE)
                "national_only": False,
                "regional_only": True,
            },
            {
                "id":           "cdf",
                "label":        "Championnat de France",
                "quota_ge":     3,
                "national_only": False,
                "regional_only": False,
            },
        ],
    },
    {
        "id":          "combat_sportif_m17",
        "label":       "Combat Sportif M17",
        "label_court": "CS M17",
        "categorie":   "M17",
        "mixte":       True,
        "niveaux": [
            {
                "id":           "cdf",
                "label":        "Championnat de France",
                "quota_ge":     6,
                "national_only": False,
                "regional_only": False,
            },
        ],
    },
    {
        "id":          "epreuve_technique",
        "label":       "Épreuve Technique Seniors",
        "label_court": "ET Seniors",
        "categorie":   "Seniors",
        "mixte":       True,
        # Parseur spécial : format "Nème: NOM Prénom - score"
        # Pas de filtre GE (classement déjà régional GE)
        "parseur":     "et",
        "niveaux": [
            {
                "id":           "cdf",
                "label":        "Championnat de France",
                "quota_ge":     7,
                "national_only": False,
                "regional_only": False,
            },
        ],
    },
    {
        "id":          "combat_choregraphie",
        "label":       "Combat Chorégraphie Seniors",
        "label_court": "Chorégraphie",
        "categorie":   "Seniors",
        "mixte":       True,
        # Parseur spécial : groupes séparés par "/", 3 sous-catégories
        "parseur":     "chore",
        "sous_categories": ["Duel", "Bataille", "Ensemble"],
        "niveaux": [
            {
                "id":           "cdf",
                "label":        "Championnat de France",
                # quota_ge = total toutes sous-catégories confondues
                "quota_ge":     5,
                "national_only": False,
                "regional_only": False,
            },
        ],
    },
]

# Index par id
DISC_MAP = {d["id"]: d for d in DISCIPLINES}

def get_discipline(disc_id: str) -> dict:
    return DISC_MAP.get(disc_id, {})

def get_quota_ge(disc_id: str, niveau_id: str) -> int:
    disc = DISC_MAP.get(disc_id, {})
    for n in disc.get("niveaux", []):
        if n["id"] == niveau_id:
            return n["quota_ge"]
    return 0

def get_niveau(disc_id: str, niveau_id: str) -> dict:
    disc = DISC_MAP.get(disc_id, {})
    for n in disc.get("niveaux", []):
        if n["id"] == niveau_id:
            return n
    return {}

# ── Calendrier ────────────────────────────────────────────────────────
CALENDRIER_SL = {
    "combat_sportif_senior": {
        "epreuve_nationale": {"date": "15/02/2026", "lieu": "CANNES"},
        "epreuve_internationale": {"date": "07/03/2026", "lieu": "COLMAR"},
        "cdf": {"date": "", "lieu": ""},
    },
    "combat_sportif_m17": {"cdf": {"date": "", "lieu": ""}},
    "epreuve_technique":  {"cdf": {"date": "", "lieu": ""}},
    "combat_choregraphie":{"cdf": {"date": "", "lieu": ""}},
}

def get_calendrier(disc_id: str, niveau_id: str) -> dict:
    return CALENDRIER_SL.get(disc_id, {}).get(niveau_id, {})

# ── Formats d'import ──────────────────────────────────────────────────
FORMATS_IMPORT = ["pdf", "xlsx", "xls", "html", "htm", "fff"]

def detecter_format(nom_fichier: str) -> str:
    ext = nom_fichier.lower().rsplit(".", 1)[-1] if "." in nom_fichier else ""
    if ext == "pdf":              return "pdf"
    if ext in ("xlsx", "xls"):   return "xlsx"
    if ext in ("html", "htm"):   return "html"
    if ext == "fff":              return "fff"
    if ext == "md":               return "md"
    return "inconnu"

# ── Colonnes DataFrame unifié ─────────────────────────────────────────
COL_RANG       = "Rang"
COL_NOM        = "Nom"
COL_PRENOM     = "Prenom"
COL_ADHERENT   = "Adherent"
COL_REGION     = "Region"
COL_CLUB       = "Club"
COL_GRAND_EST  = "Grand_Est"
COL_NOTE       = "Note"          # score ET
COL_PARTICIPANTS = "Participants" # groupe Chorégraphie (NOM1 / NOM2)
COL_SOUS_CAT   = "Sous_categorie" # Duel / Bataille / Ensemble
