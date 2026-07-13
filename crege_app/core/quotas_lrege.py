"""
quotas_lrege.py — Quotas LREGE Grand Est 2025-2026.

Source : Quotas_2025-2026_site.xlsx

Structure : QUOTAS[(cat_id, arme_id, genre)] = quota_total_ge
  - quota_individuel : total quota GE pour les sélections individuelles
                       réparti 1/3 FFE + 2/3 régional via TABLE_LREGE
  - quota_equipes    : quota GE pour les équipes N3

Règle : si une combinaison est absente → pas de quota fixe (open ou variable)
  - M13 Sabre       : open
  - M17/M20/M23/Seniors Sabre : open circuit (liste FFE PDF, pas de quota)
  - M23 par équipes : AUCUNE épreuve par équipes au CDF
  - Vétérans Épée Dames (V1/V2/V3) : OPEN (participation libre)
  - Vétérans Épée Hommes V4 : open
  - M15 : quotas variables (saisis dans l'UI, calculés depuis les 8es de finale)
"""

# ── Quotas individuels Grand Est ──────────────────────────────────────
# (cat_id, arme_id, genre) → quota_total_ge
# Source : colonnes "Individuel" du fichier quotas
QUOTAS_INDIV = {
    # ── M13 — Challenge de France ─────────────────────────────────────
    # 100% classement régional (N2_REG_ONLY), pas de split FFE
    # Sabre M13 : open → absent de ce dict
    ("M13", "E", "D"): 10,
    ("M13", "E", "H"): 10,
    ("M13", "F", "D"): 10,
    ("M13", "F", "H"): 11,

    # ── M17 ───────────────────────────────────────────────────────────
    # Épée/Fleuret H : N1+N2 liste FFE + N3 quota (N2_FFE_N3_QUOTA)
    # Épée/Fleuret D : N1 liste FFE + N2 quota (N1_FFE_N2_QUOTA)
    # Sabre H/D : open circuit (liste FFE PDF) → absent de ce dict
    ("M17", "E", "D"): 4,   # N2 : 1 FFE + 3 rég
    ("M17", "E", "H"): 5,   # N3 : 2 FFE + 3 rég
    ("M17", "F", "D"): 3,   # N2 : 1 FFE + 2 rég
    ("M17", "F", "H"): 5,   # N3 : 2 FFE + 3 rég

    # ── M20 ───────────────────────────────────────────────────────────
    # Même logique que M17
    # Sabre H/D : open circuit → absent de ce dict
    ("M20", "E", "D"): 5,   # N2 : 2 FFE + 3 rég
    ("M20", "E", "H"): 5,   # N3 : 2 FFE + 3 rég
    ("M20", "F", "D"): 2,   # N2 : 1 FFE + 1 rég
    ("M20", "F", "H"): 4,   # N3 : 1 FFE + 3 rég

    # ── M23 ───────────────────────────────────────────────────────────
    # Épée/Fleuret H/D : quota LREGE (N2_QUOTA_LREGE)
    # Sabre H/D : open circuit (liste FFE PDF) → absent de ce dict
    ("M23", "E", "D"): 4,   # N2 : 1 FFE + 3 rég
    ("M23", "E", "H"): 4,   # N2 : 1 FFE + 3 rég
    ("M23", "F", "D"): 3,   # N2 : 1 FFE + 2 rég
    ("M23", "F", "H"): 4,   # N2 : 1 FFE + 3 rég

    # ── Seniors ───────────────────────────────────────────────────────
    # Sabre H/D : open circuit (liste FFE PDF) → absent de ce dict
    ("Seniors", "E", "D"): 4,   # N3 : 1 FFE + 3 rég
    ("Seniors", "E", "H"): 6,   # N3 : 2 FFE + 4 rég
    ("Seniors", "F", "D"): 4,   # N2 FFE (quota_ffe) : 1 FFE + 3 rég
    ("Seniors", "F", "H"): 4,   # N3 : 1 FFE + 3 rég

    # ── Vétérans Épée Hommes ──────────────────────────────────────────
    # V1/V2/V3 : quota LREGE (1/3 FFE + 2/3 rég)
    # V4H : open → absent de ce dict
    # V1/V2/V3/V4 Dames : OPEN (participation libre) → absent de ce dict
    ("V1", "E", "H"): 4,   # 1 FFE + 3 rég
    ("V2", "E", "H"): 4,   # 1 FFE + 3 rég
    ("V3", "E", "H"): 4,   # 1 FFE + 3 rég
}

# ── Quotas équipes Grand Est ──────────────────────────────────────────
# (cat_id, arme_id, genre) → quota_equipes_n3
# Source : colonnes "Par équipes" du fichier quotas
# Règle : M23 n'a PAS d'épreuves par équipes au CDF → absent de ce dict
QUOTAS_EQUIPES = {
    # ── M17 ───────────────────────────────────────────────────────────
    ("M17", "E", "D"): 2,
    ("M17", "E", "H"): 2,
    ("M17", "F", "H"): 2,

    # ── M20 ───────────────────────────────────────────────────────────
    ("M20", "E", "D"): 2,
    ("M20", "E", "H"): 2,
    ("M20", "F", "H"): 2,

    # ── Seniors ───────────────────────────────────────────────────────
    ("Seniors", "E", "D"): 2,
    ("Seniors", "E", "H"): 2,
    ("Seniors", "F", "H"): 2,

    # ── Vétérans Épée (via routes dédiées, quotas saisis dans l'UI) ───
    # Ces valeurs sont les défauts — l'UI permet de les modifier
    ("V1", "E", "H"): 2,
    ("V2", "E", "H"): 2,
    ("V3", "E", "H"): 2,
    # Dames vétérans équipes : V1-V2 = 1 quota, V3-V4 = open
    ("V1", "E", "D"): 1,
    ("V2", "E", "D"): 1,
}


def get_quota_indiv(cat_id: str, arme_id: str, genre: str) -> int | None:
    """Quota individuel total Grand Est. None si non défini (open ou variable)."""
    return QUOTAS_INDIV.get((cat_id, arme_id, genre))


def get_quota_equipes(cat_id: str, arme_id: str, genre: str) -> int:
    """Quota équipes N3 Grand Est. 0 si open ou non défini.

    ⚠️ Règle métier : V3 et V4 forment la catégorie unique « Grands Vétérans »
    (cf. generateur/equipes_veterans.py, feuilles EHGV/EDGV V3-V4).
    V4 est donc volontairement mappé sur la clé V3 de QUOTAS_EQUIPES.
    """
    key = "V3" if cat_id == "V4" else cat_id
    return QUOTAS_EQUIPES.get((key, arme_id, genre), 0)


def get_quotas_complets(cat_id: str, arme_id: str) -> dict:
    """Retourne tous les quotas pour une combinaison cat+arme (H et D)."""
    return {
        "indiv_h":   get_quota_indiv(cat_id, arme_id, "H"),
        "indiv_d":   get_quota_indiv(cat_id, arme_id, "D"),
        "equipes_h": get_quota_equipes(cat_id, arme_id, "H"),
        "equipes_d": get_quota_equipes(cat_id, arme_id, "D"),
    }
