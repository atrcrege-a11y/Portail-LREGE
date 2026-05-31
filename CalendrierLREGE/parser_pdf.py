"""
parser_pdf.py — Extraction du calendrier FFE depuis un PDF (format grille mensuelle).

Format attendu : PDF FFE calendrier annuel avec grilles arme/genre par mois.
Structure par tableau :
  - Ligne 0  : "Mois1 AAAA Mois2 AAAA ..."
  - Ligne 2  : plages de dates ("5-6", "12-13", "26-27", ...)
  - Ligne N  : [arme+genre inversé | catégorie | événements par colonne-date]

Colonne 0 : texte inversé ("semad teruelF" → "Fleuret Dames")
Catégories extraites : Seniors, M20, M17, M13/M15, M13, M15, Vétérans
"""
import re
import uuid
from datetime import date

try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

# ── Constantes ────────────────────────────────────────────────────────────────

MOIS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

# Catégories françaises nationales à conserver
CATS_FRANCE = {
    "seniors": "Seniors",
    "m20": "M20", "m17": "M17", "m15": "M15", "m13": "M13",
    "m13/m15": "M13/M15",
    "vétérans": "Vétérans", "veterans": "Vétérans",
}

# Décodage arme+genre depuis texte inversé (col 0)
# La colonne 0 est écrite en texte miroir par le logiciel de mise en page
ARME_DECODE = {
    # Fleuret
    "fleuret dames":  ("fleuret", "D"),
    "fleuret hommes": ("fleuret", "H"),
    "fleuret":        ("fleuret", ""),
    # Épée — avec et sans accent (le texte inversé peut perdre l'accent)
    "épée dames":     ("épée", "D"),
    "épée hommes":    ("épée", "H"),
    "epée dames":     ("épée", "D"),
    "epée hommes":    ("épée", "H"),
    "epee dames":     ("épée", "D"),
    "epee hommes":    ("épée", "H"),
    "épée":           ("épée", ""),
    "epee":           ("épée", ""),
    "epée":           ("épée", ""),
    # Sabre
    "sabre dames":    ("sabre", "D"),
    "sabre hommes":   ("sabre", "H"),
    "sabre":          ("sabre", ""),
}


def _inverser(texte: str) -> str:
    """Inverse un texte miroir et normalise les espaces."""
    if not texte:
        return ""
    return " ".join(texte.strip()[::-1].split()).lower()


def _decoder_arme(col0: str) -> tuple[str, str]:
    """Retourne (arme, genre) depuis la colonne 0 inversée."""
    inv = _inverser(col0)
    for pattern, val in ARME_DECODE.items():
        if pattern in inv:
            return val
    return ("", "")


def _parser_mois_annee(header: str) -> list[tuple[int, int]]:
    """
    Extrait les paires (mois, année) depuis l'en-tête de tableau.
    Ex: "Septembre 2026 Octobre 2026" → [(9,2026),(10,2026)]
    """
    header = (header or "").lower()
    tokens = header.replace("(", " ").replace(")", " ").replace("+", " ").split()
    resultats = []
    for i, tok in enumerate(tokens):
        if tok in MOIS_FR and i + 1 < len(tokens):
            try:
                annee = int(tokens[i + 1])
                if 2020 <= annee <= 2035:
                    resultats.append((MOIS_FR[tok], annee))
            except ValueError:
                pass
    return resultats


def _associer_date(plage: str, mois_annees: list) -> list[date]:
    """
    Retourne la ou les dates de début depuis une plage comme "5-6", "17-18-19", "31-1".
    Prend le premier jour de la plage.
    mois_annees = [(mois1, annee1), (mois2, annee2)] dans l'ordre du tableau.
    """
    if not plage or not mois_annees:
        return []
    nums = re.findall(r'\d+', plage)
    if not nums:
        return []
    jour = int(nums[0])
    # Trouver le bon mois : si jour > 20 et 2+ mois → premier mois ; si jour < 10 → dernier mois
    if len(mois_annees) >= 2 and jour < 10:
        mois, annee = mois_annees[-1]
    else:
        mois, annee = mois_annees[0]
    try:
        return [date(annee, mois, jour)]
    except ValueError:
        return []


def _parser_tableau(table: list, mois_annees: list) -> list[dict]:
    """
    Parse un tableau extrait par pdfplumber.
    Retourne une liste d'événements.
    """
    if not table or len(table) < 3:
        return []

    # Ligne des dates (toujours ligne index 2)
    date_row = table[2]
    plages_dates = [str(c).strip() if c else "" for c in date_row[2:]]

    # Arme depuis col 0 (toutes les lignes de données ont la même arme dans le bloc)
    arme, sexe = "", ""
    for row in table[3:]:
        if row and row[0]:
            arme, sexe = _decoder_arme(str(row[0]))
            if arme:
                break

    if not arme:
        return []

    evenements = []

    for row in table[3:]:
        if not row or not row[1]:
            continue
        cat_raw = str(row[1]).strip().lower()
        cat = None
        for pattern, label in CATS_FRANCE.items():
            if pattern in cat_raw:
                cat = label
                break
        if not cat:
            continue

        # Parcourir les colonnes dates
        for col_idx, plage in enumerate(plages_dates):
            if col_idx + 2 >= len(row):
                break
            val = str(row[col_idx + 2]).strip() if row[col_idx + 2] else ""
            # Filtrer : ignorer vide, chiffres isolés, lettres isolées (<3 chars)
            if not val or len(val) < 2:
                continue
            if re.match(r'^[\d\s/\-?]+$', val):
                continue

            dates = _associer_date(plage, mois_annees)
            if not dates:
                continue

            d = dates[0]
            evenements.append({
                "id":              str(uuid.uuid4()),
                "source":          "pdf_ffe",
                "manuel":          False,
                "type_evenement":  "competition",
                "statut":          "À venir",
                "date_debut":      d.strftime("%Y-%m-%d"),
                "date_fin":        None,
                "type_competition": "",
                "niveau":          "national",
                "niveau_raw":      "National(e)",
                "numero":          "",
                "intitule":        val,
                "lieu":            val,
                "perimetre":       "National(e)",
                "armes":           [arme],
                "arme":            arme,
                "sexe":            sexe,
                "categories":      [cat],
                "type_epreuve":    "",
                "url":             "",
                "grand_est":       False,
                "notes":           "",
                "__version__":     1,
            })

    return evenements


def parse_pdf_calendrier(filepath: str) -> list[dict]:
    """
    Parse un PDF calendrier FFE (format grille mensuelle).
    Retourne une liste d'événements dédupliqués triés par date.
    """
    tous = []

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 3:
                    continue
                # Ligne 0 = en-tête avec mois
                header = " ".join(str(c) for c in table[0] if c).strip()
                mois_annees = _parser_mois_annee(header)
                if not mois_annees:
                    continue
                evs = _parser_tableau(table, mois_annees)
                tous.extend(evs)

    # Déduplications : même date + intitulé + catégorie
    dedup = {}
    for e in tous:
        key = (e["date_debut"], e["intitule"].lower(), e["arme"], tuple(e["categories"]))
        if key not in dedup:
            dedup[key] = e
        else:
            # Fusionner armes/catégories si doublon
            existing = dedup[key]
            for cat in e["categories"]:
                if cat not in existing["categories"]:
                    existing["categories"].append(cat)

    return sorted(dedup.values(), key=lambda e: e["date_debut"])
