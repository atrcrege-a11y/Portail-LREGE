"""
quotas_lrege.py — Quotas LREGE Grand Est 2025-2026.

Source : Quotas_2025-2026_site.xlsx

Structure : QUOTAS[(cat_id, arme_id, genre, niveau)] = (quota_individuel, quota_equipes)
  - quota_individuel : total quota GE pour les sélections individuelles
  - quota_equipes    : quota GE pour les équipes N3
  - niveau : 'N1'|'N2'|'N3'|'V1'|'V2'|'V3'

Note : les quotas individuels sont les quotas TOTAUX Grand Est
       à répartir 1/3 FFE + 2/3 régional via TABLE_LREGE.
"""

# ── Quotas individuels Grand Est ──────────────────────────────────────
# (cat_id, arme_id, genre) → quota_total_ge
# Source : colonnes "Individuel" du fichier quotas
QUOTAS_INDIV = {
    # M13 — Challenge de France (100% classement régional, pas de split FFE)
    ("M13", "E", "D"): 10,
    ("M13", "E", "H"): 10,
    ("M13", "F", "D"): 10,
    ("M13", "F", "H"): 11,
    # Sabre M13 : open, pas de quota fixe
    # M17
    ("M17", "E", "D"): 4,   # Épée Dame N2
    ("M17", "E", "H"): 5,   # Épée Homme N3
    ("M17", "F", "D"): 3,   # Fleuret Dame N2
    ("M17", "F", "H"): 5,   # Fleuret Homme N3
    # M20
    ("M20", "E", "D"): 5,   # Épée Dame N2
    ("M20", "E", "H"): 5,   # Épée Homme N3
    ("M20", "F", "D"): 2,   # Fleuret Dame N2
    ("M20", "F", "H"): 4,   # Fleuret Homme N3
    # M23 (individuels uniquement)
    ("M23", "E", "D"): 4,
    ("M23", "E", "H"): 4,
    ("M23", "F", "D"): 3,
    ("M23", "F", "H"): 4,
    ("M23", "S", "H"): 3,
    ("M23", "S", "D"): 2,
    # Seniors
    ("Seniors", "E", "D"): 6,   # Épée Dame N3
    ("Seniors", "E", "H"): 6,   # Épée Homme N3
    ("Seniors", "F", "D"): 4,   # Fleuret Dame N2
    ("Seniors", "F", "H"): 4,   # Fleuret Homme N3
    # Vétérans épée hommes
    ("V1", "E", "H"): 4,
    ("V2", "E", "H"): 4,
    ("V3", "E", "H"): 4,
    # Vétérans épée dames
    ("V1", "E", "D"): 1,
    ("V2", "E", "D"): 2,
    ("V3", "E", "D"): 2,
}

# ── Quotas équipes Grand Est ──────────────────────────────────────────
# (cat_id, arme_id, genre) → quota_equipes_n3
# Source : colonnes "Par équipes" du fichier quotas
QUOTAS_EQUIPES = {
    # M17
    ("M17", "E", "D"): 2,
    ("M17", "E", "H"): 2,
    ("M17", "F", "H"): 2,
    # M20
    ("M20", "E", "D"): 2,
    ("M20", "E", "H"): 2,
    ("M20", "F", "H"): 2,
    # M23 (individuels uniquement)
    ("M23", "E", "D"): 4,
    ("M23", "E", "H"): 4,
    ("M23", "F", "D"): 3,
    ("M23", "F", "H"): 4,
    ("M23", "S", "H"): 3,
    ("M23", "S", "D"): 2,
    # Seniors
    ("Seniors", "E", "D"): 2,
    ("Seniors", "E", "H"): 2,
    ("Seniors", "F", "H"): 2,
    # Vétérans
    ("V1", "E", "D"): 1,
    ("V1", "E", "H"): 2,
    ("V2", "E", "D"): 2,   # inclus dans Grands Vétérans
    ("V2", "E", "H"): 2,
    ("V3", "E", "D"): 2,
    ("V3", "E", "H"): 2,
}


def get_quota_indiv(cat_id: str, arme_id: str, genre: str) -> int | None:
    """Quota individuel total Grand Est. None si non défini (open ou variable)."""
    return QUOTAS_INDIV.get((cat_id, arme_id, genre))


def get_quota_equipes(cat_id: str, arme_id: str, genre: str) -> int:
    """Quota équipes N3 Grand Est. 0 si open ou non défini."""
    # V4 : même quota que V3
    key = cat_id
    if cat_id == "V4":
        key = "V3"
    return QUOTAS_EQUIPES.get((key, arme_id, genre), 0)


def get_quotas_complets(cat_id: str, arme_id: str) -> dict:
    """Retourne tous les quotas pour une combinaison cat+arme (H et D)."""
    return {
        "indiv_h":  get_quota_indiv(cat_id, arme_id, "H"),
        "indiv_d":  get_quota_indiv(cat_id, arme_id, "D"),
        "equipes_h": get_quota_equipes(cat_id, arme_id, "H"),
        "equipes_d": get_quota_equipes(cat_id, arme_id, "D"),
    }
