"""
calendrier_cdf.py — Dates et lieux des Championnats de France 2025-2026.

Source : Calendrier FFE 2025-2026

Structure : CALENDRIER[(cat_id, arme_id, niveau)] = {date, lieu, competition}
  - niveau : 'N1'|'N2'|'N3'|'individuel'|'equipes'
  - Pour les équipes, date = date de la finale
"""

# ── Championnats de France individuels ───────────────────────────────
# Format : (cat_id, arme_id) → {date, lieu, competition}
# Quand H et D ont des dates différentes on précise par genre

CDF_INDIVIDUELS = {
    # M13 — Challenge de France (20-21 juin 2026)
    ("M13", "F"): {"date": "20/06/2026", "lieu": "ANGOULÊME",      "competition": "Challenge de France M13"},
    ("M13", "E"): {"date": "21/06/2026", "lieu": "ALBI",           "competition": "Challenge de France M13"},
    ("M13", "S"): {"date": "20/06/2026", "lieu": "JOUÉ-LÈS-TOURS", "competition": "Challenge de France M13"},

    # M15 — Fête des Jeunes (13-14 juin 2026, PARIS)
    ("M15", "F"): {"date": "13/06/2026", "lieu": "PARIS",         "competition": "Fête des Jeunes M15"},
    ("M15", "E"): {"date": "14/06/2026", "lieu": "PARIS",         "competition": "Fête des Jeunes M15"},
    ("M15", "S"): {"date": "13/06/2026", "lieu": "PARIS",         "competition": "Fête des Jeunes M15"},

    # M17 — CDF N1 individuel + équipes
    # Épée : CORBAS 09-10 mai + ANTONY 23-24 mai + BOURGES 30-31 mai
    ("M17", "E"): {"date": "09/05/2026", "lieu": "CORBAS",        "competition": "Championnat de France M17"},
    ("M17", "F"): {"date": "23/05/2026", "lieu": "ANTONY",        "competition": "Championnat de France M17"},
    ("M17", "S"): {"date": "30/05/2026", "lieu": "BOURGES",       "competition": "Championnat de France M17"},

    # M20
    ("M20", "E"): {"date": "30/05/2026", "lieu": "SAINT-PAUL-TROIS-CHÂTEAUX", "competition": "Championnat de France M20"},
    ("M20", "F"): {"date": "30/05/2026", "lieu": "MARSEILLE",                   "competition": "Championnat de France M20"},
    ("M20", "S"): {"date": "16/05/2026", "lieu": "FACHES-THUMESNIL",           "competition": "Championnat de France M20"},

    # Seniors
    ("Seniors", "E"): {"date": "06/06/2026", "lieu": "DIJON",     "competition": "Championnat de France Seniors"},
    ("Seniors", "F"): {"date": "06/06/2026", "lieu": "NANTES",    "competition": "Championnat de France Seniors"},
    ("Seniors", "S"): {"date": "06/06/2026", "lieu": "ORLÉANS",   "competition": "Championnat de France Seniors"},

    # Vétérans (27-28 juin 2026, MONTARGIS)
    ("V1", "E"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V1", "F"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V1", "S"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V2", "E"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V2", "F"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V2", "S"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V3", "E"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V3", "F"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V3", "S"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V4", "E"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V4", "F"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
    ("V4", "S"): {"date": "27/06/2026", "lieu": "MONTARGIS",      "competition": "Championnat de France Vétérans"},
}

# ── Championnats de France par équipes ────────────────────────────────
CDF_EQUIPES = {
    # M17 équipes (½ finales + finales)
    ("M17", "E"): {"date": "09/05/2026", "lieu": "CORBAS",        "competition": "Championnat de France M17 Équipes"},
    ("M17", "F"): {"date": "23/05/2026", "lieu": "ANTONY",        "competition": "Championnat de France M17 Équipes"},
    ("M17", "S"): {"date": "30/05/2026", "lieu": "BOURGES",       "competition": "Championnat de France M17 Équipes"},

    # M20 équipes
    ("M20", "E"): {"date": "30/05/2026", "lieu": "SAINT-PAUL-TROIS-CHÂTEAUX", "competition": "Championnat de France M20 Équipes"},
    ("M20", "F"): {"date": "30/05/2026", "lieu": "MARSEILLE",                   "competition": "Championnat de France M20 Équipes"},
    ("M20", "S"): {"date": "16/05/2026", "lieu": "FACHES-THUMESNIL",           "competition": "Championnat de France M20 Équipes"},

    # Seniors équipes
    ("Seniors", "E"): {"date": "06/06/2026", "lieu": "DIJON",     "competition": "Championnat de France Seniors Équipes"},
    ("Seniors", "F"): {"date": "06/06/2026", "lieu": "NANTES",    "competition": "Championnat de France Seniors Équipes"},
    ("Seniors", "S"): {"date": "06/06/2026", "lieu": "ORLÉANS",   "competition": "Championnat de France Seniors Équipes"},

    # Vétérans équipes
    ("V1", "E"):  {"date": "27/06/2026", "lieu": "MONTARGIS",     "competition": "Championnat de France Vétérans Équipes"},
    ("V2", "E"):  {"date": "27/06/2026", "lieu": "MONTARGIS",     "competition": "Championnat de France Vétérans Équipes"},
    ("V3", "E"):  {"date": "27/06/2026", "lieu": "MONTARGIS",     "competition": "Championnat de France Vétérans Équipes"},
    ("V4", "E"):  {"date": "27/06/2026", "lieu": "MONTARGIS",     "competition": "Championnat de France Vétérans Équipes"},
}

# ── ½ finales équipes ─────────────────────────────────────────────────
DEMI_FINALES_EQUIPES = {
    ("M17", "F"):     {"date": "28/03/2026", "lieu": "MURET"},
    ("M17", "S"):     {"date": "07/03/2026", "lieu": "TARBES"},
    ("M20", "E"):     {"date": "14/03/2026", "lieu": "AIX-EN-PROVENCE"},
    ("M20", "F"):     {"date": "21/03/2026", "lieu": "CHÂLONS-EN-CHAMPAGNE"},
    ("M20", "S"):     {"date": "21/03/2026", "lieu": "BREST"},
    ("Seniors", "E"): {"date": "25/04/2026", "lieu": "CHÂLONS-EN-CHAMPAGNE"},
    ("Seniors", "F"): {"date": "25/04/2026", "lieu": "CHÂLONS-EN-CHAMPAGNE"},
    ("Seniors", "S"): {"date": "25/04/2026", "lieu": "CHÂLONS-EN-CHAMPAGNE"},
}


def _j_plus_1(date_str: str) -> str:
    """Retourne la date + 1 jour. Format DD/MM/YYYY."""
    from datetime import datetime, timedelta
    try:
        d = datetime.strptime(date_str, "%d/%m/%Y")
        return (d + timedelta(days=1)).strftime("%d/%m/%Y")
    except Exception:
        return date_str


def get_cdf_individuel(cat_id: str, arme_id: str) -> dict:
    """Retourne date/lieu/compétition du CDF individuel.
    Pour Seniors : date = J+1 (compétition sur 2 jours samedi+dimanche).
    """
    data = dict(CDF_INDIVIDUELS.get((cat_id, arme_id), {}))
    if not data:
        return {}
    if cat_id == "Seniors" and data.get("date"):
        data["date"] = _j_plus_1(data["date"])
    return data


def get_cdf_equipes(cat_id: str, arme_id: str) -> dict:
    """Retourne date/lieu/compétition du CDF équipes.
    Pour M17, M20, Vétérans : date = J+1 du calendrier (compétition sur 2 jours).
    """
    data = dict(CDF_EQUIPES.get((cat_id, arme_id), {}))
    if not data:
        return {}
    # J+1 pour M17, M20 et Vétérans (épreuves sur 2 jours)
    # Seniors équipes : même date que le calendrier (06/06)
    if cat_id in ("M17", "M20", "V1", "V2", "V3", "V4") and data.get("date"):
        data["date"] = _j_plus_1(data["date"])
    return data


def get_demi_finale_equipes(cat_id: str, arme_id: str) -> dict:
    """Retourne date/lieu de la ½ finale équipes."""
    return DEMI_FINALES_EQUIPES.get((cat_id, arme_id), {})
