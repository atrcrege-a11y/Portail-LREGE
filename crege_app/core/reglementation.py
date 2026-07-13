"""
Matrice réglementaire LREGE Grand Est 2025-2026
Source : RS FFE (Fleuret/Épée/Sabre) + Règlement LREGE Grand Est

Structure par (cat_id, arme_id, genre) :
  n1_default  : quota N1 FFE direct (0 = pas de N1 direct)
  n1_open     : True si N1 entièrement open
  n2_mode     : 'quota_lrege' | 'open' | 'open_circuit' | 'quota_ffe'
  n2_texte    : texte explicatif pour le document
  condition   : condition préalable (affichée dans le doc)
"""

# ── Constantes modes N2 ───────────────────────────────────────────────
N2_QUOTA_LREGE  = "quota_lrege"   # répartition 1/3 FFE + 2/3 régional
N2_OPEN         = "open"          # open sans condition
N2_OPEN_CIRCUIT = "open_circuit"  # open avec condition circuit national
N2_QUOTA_FFE    = "quota_ffe"     # quota FFE pur (ex : FD Seniors N2 = 20 suivantes)
N2_FFE_N3_QUOTA = "ffe_n3_quota"  # N1+N2 sur liste PDF FFE, N3 quotas LREGE (FH M17/M20 Fleuret/Épée)
N1_FFE_N2_QUOTA = "n1_ffe_n2_quota"  # N1 sur liste PDF FFE, N2 quotas LREGE (FD M17/M20 Fleuret/Épée)
N2_REG_ONLY     = "reg_only"          # 100% classement régional, pas de split FFE (M13 Épée/Fleuret)

# ── Matrice (cat_id, arme_id, genre) ─────────────────────────────────
# arme_id : 'E'=Épée, 'F'=Fleuret, 'S'=Sabre
MATRICE_REGLEMENTAIRE = {

    # ─── M17 ───────────────────────────────────────────────────────────
    ("M17", "E", "H"): dict(n1_default=32, n2_mode=N2_FFE_N3_QUOTA,
        n2_texte="Les 32 premiers du classement FFE non qualifiés en N1 + jusqu'à 4 Wild Cards",
        n3_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M17", "E", "D"): dict(n1_default=32, n2_mode=N1_FFE_N2_QUOTA,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M17", "F", "H"): dict(n1_default=32, n2_mode=N2_FFE_N3_QUOTA,
        n2_texte="Les 32 premiers du classement FFE non qualifiés en N1 + jusqu'à 4 Wild Cards",
        n3_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M17", "F", "D"): dict(n1_default=32, n2_mode=N1_FFE_N2_QUOTA,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M17", "S", "H"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),
    ("M17", "S", "D"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),

    # ─── M20 ───────────────────────────────────────────────────────────
    ("M20", "E", "H"): dict(n1_default=32, n2_mode=N2_FFE_N3_QUOTA,
        n2_texte="Les 32 premiers du classement FFE non qualifiés en N1 + jusqu'à 4 Wild Cards",
        n3_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M20", "E", "D"): dict(n1_default=32, n2_mode=N1_FFE_N2_QUOTA,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M20", "F", "H"): dict(n1_default=32, n2_mode=N2_FFE_N3_QUOTA,
        n2_texte="Les 32 premiers du classement FFE non qualifiés en N1 + jusqu'à 4 Wild Cards",
        n3_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M20", "F", "D"): dict(n1_default=32, n2_mode=N1_FFE_N2_QUOTA,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M20", "S", "H"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),
    ("M20", "S", "D"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),

    # ─── M23 ───────────────────────────────────────────────────────────
    ("M23", "E", "H"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition="Participation à au moins 3 épreuves de territoire"),
    ("M23", "E", "D"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition="Participation à au moins 3 épreuves de territoire"),
    ("M23", "F", "H"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition="Participation à au moins 3 épreuves de territoire"),
    ("M23", "F", "D"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition="Participation à au moins 3 épreuves de territoire"),
    ("M23", "S", "H"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),
    ("M23", "S", "D"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),

    # ─── Seniors ───────────────────────────────────────────────────────
    ("Seniors", "E", "H"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("Seniors", "E", "D"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("Seniors", "F", "H"): dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("Seniors", "F", "D"): dict(n1_default=32, n2_mode=N2_QUOTA_FFE,
        n2_texte="20 suivantes du classement FFE + quota LREGE Grand Est",
        condition=""),
    ("Seniors", "S", "H"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),
    ("Seniors", "S", "D"): dict(n1_default=32, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 1 circuit national requise",
        condition="Participation à au moins 1 circuit national"),

    # ─── Vétérans V1/V2/V3 (traités identiquement) ────────────────────
    # Épée Hommes : quota N1 FFE + quota LREGE 1/3-2/3
    # Épée Dames  : open avec condition 2 circuits nationaux
    # Fleuret & Sabre : open (critérium)

    # ─── M15 — Fête des Jeunes ────────────────────────────────────────
    # Toutes armes : quota fédéral = 40 premiers classement national
    # Quota LREGE : variable (calculé depuis les 8es de finale), saisi dans l'UI
    # Pas de filtre nationalité
    ("M15", "E", "H"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M15", "E", "D"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M15", "F", "H"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M15", "F", "D"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M15", "S", "H"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),
    ("M15", "S", "D"): dict(n1_default=40, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition=""),

    # ─── M13 — Challenge de France ────────────────────────────────────
    # Épée et Fleuret : quotas régionaux, 100% classement régional (pas de split FFE)
    # Sabre : open
    ("M13", "E", "H"): dict(n1_default=0, n2_mode=N2_REG_ONLY,
        n2_texte="Quota LREGE Grand Est — classement régional uniquement",
        condition=""),
    ("M13", "E", "D"): dict(n1_default=0, n2_mode=N2_REG_ONLY,
        n2_texte="Quota LREGE Grand Est — classement régional uniquement",
        condition=""),
    ("M13", "F", "H"): dict(n1_default=0, n2_mode=N2_REG_ONLY,
        n2_texte="Quota LREGE Grand Est — classement régional uniquement",
        condition=""),
    ("M13", "F", "D"): dict(n1_default=0, n2_mode=N2_REG_ONLY,
        n2_texte="Quota LREGE Grand Est — classement régional uniquement",
        condition=""),
    ("M13", "S", "H"): dict(n1_default=0, n2_mode=N2_OPEN,
        n2_texte="Épreuve open — pas de quota", condition=""),
    ("M13", "S", "D"): dict(n1_default=0, n2_mode=N2_OPEN,
        n2_texte="Épreuve open — pas de quota", condition=""),
}

# Ajouter les vétérans V1/V2/V3/V4 programmatiquement
for _v in ["V1", "V2", "V3", "V4"]:
    MATRICE_REGLEMENTAIRE[(_v, "E", "H")] = dict(
        n1_default=32, n2_mode=N2_QUOTA_LREGE,
        n2_texte="Quota LREGE Grand Est (1/3 FFE + 2/3 classement régional GE)",
        condition="") if _v != "V4" else dict(
        n1_default=0, n2_mode=N2_OPEN,
        n2_texte="Épreuve open", condition="")
    MATRICE_REGLEMENTAIRE[(_v, "E", "D")] = dict(
        n1_default=0, n2_mode=N2_OPEN_CIRCUIT,
        n2_texte="Épreuve open — participation à au moins 2 circuits nationaux requise",
        condition="Participation à au moins 2 circuits nationaux")
    for _a in ["F", "S"]:
        MATRICE_REGLEMENTAIRE[(_v, _a, "H")] = dict(
            n1_default=0, n2_mode=N2_OPEN,
            n2_texte="Épreuve open (critérium national)", condition="")
        MATRICE_REGLEMENTAIRE[(_v, _a, "D")] = dict(
            n1_default=0, n2_mode=N2_OPEN,
            n2_texte="Épreuve open (critérium national)", condition="")


def get_regle(cat_id: str, arme_id: str, genre: str) -> dict:
    """Retourne la règle pour une combinaison cat/arme/genre."""
    return MATRICE_REGLEMENTAIRE.get(
        (cat_id, arme_id, genre),
        dict(n1_default=32, n2_mode=N2_QUOTA_LREGE,
             n2_texte="Quota LREGE Grand Est", condition="")
    )
