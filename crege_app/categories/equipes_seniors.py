"""
categories/equipes_seniors.py — Équipes M17/M20/Seniors/Vétérans.

Règles LREGE Grand Est 2025-2026 :
  N1/N2 : 8 premières équipes de la ½ finale nationale (FFE direct)
  N3     : quotas LREGE (classement championnat régional GE) OU open selon arme/genre

Modes N3 par catégorie+arme+genre :
  M17/M20  ÉH/ÉD/FH : quota LREGE
  M17/M20  FD/SH/SD  : open
  Seniors  ÉH/ÉD/FH  : quota LREGE
  Seniors  FD/SH/SD   : open
  Vétérans ÉH/ÉD      : quota LREGE (Vétérans) / open (Grands Vétérans ÉD)
  Vétérans F/S        : open (critérium)
"""

# ── Matrice N3 mode par (cat_id, arme_id, genre) ────────────────────
EQ_N3_QUOTA  = "quota"   # classement régional GE dans la limite du quota
EQ_N3_OPEN   = "open"    # open sans quota

MATRICE_EQUIPES_N3 = {}
for _cat in ["M17", "M20"]:
    MATRICE_EQUIPES_N3[(_cat, "E", "H")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "E", "D")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "F", "H")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "F", "D")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "H")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "D")] = EQ_N3_OPEN

for _cat in ["Seniors"]:
    MATRICE_EQUIPES_N3[(_cat, "E", "H")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "E", "D")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "F", "H")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "F", "D")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "H")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "D")] = EQ_N3_OPEN

# Vétérans V1/V2 : épée H/D quota, F/S open
for _cat in ["V1", "V2"]:
    MATRICE_EQUIPES_N3[(_cat, "E", "H")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "E", "D")] = EQ_N3_QUOTA
    MATRICE_EQUIPES_N3[(_cat, "F", "H")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "F", "D")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "H")] = EQ_N3_OPEN
    MATRICE_EQUIPES_N3[(_cat, "S", "D")] = EQ_N3_OPEN

# Grands Vétérans V3/V4 : tout open
for _cat in ["V3", "V4"]:
    for _a in ["E", "F", "S"]:
        for _g in ["H", "D"]:
            MATRICE_EQUIPES_N3[(_cat, _a, _g)] = EQ_N3_OPEN


def get_n3_mode(cat_id, arme_id, genre):
    return MATRICE_EQUIPES_N3.get((cat_id, arme_id, genre), EQ_N3_QUOTA)


def construire_equipes_seniors(equipes_n1n2_h, equipes_n1n2_d,
                                equipes_n3_ffe_h, equipes_n3_ffe_d,
                                equipes_n3_h, equipes_n3_d,
                                config: dict,
                                remplacants_h=None, remplacants_d=None) -> dict:
    """
    Construit la structure de données équipes pour M17→Vétérans.

    equipes_n1n2_H/D : liste de dicts {rang, nom_equipe, club}
                       (8 premières équipes de la ½ finale FFE)
    equipes_n3_H/D   : liste de dicts {rang, nom_equipe, club}
                       (classement championnat régional GE)
    config           : dict de configuration (cat_id, arme_id, competition, ...)
    """
    cat_id  = config.get("cat_id", "Seniors")
    arme_id = config.get("arme_id", "E")

    quota_n3_h = int(config.get("quota_n3_eq_h", 0))
    quota_n3_d = int(config.get("quota_n3_eq_d", 0))

    mode_n3_h = get_n3_mode(cat_id, arme_id, "H")
    mode_n3_d = get_n3_mode(cat_id, arme_id, "D")

    # Limiter les N3 au quota
    eq_n3_h_sel = equipes_n3_h[:quota_n3_h] if quota_n3_h > 0 else []
    eq_n3_d_sel = equipes_n3_d[:quota_n3_d] if quota_n3_d > 0 else []

    remplacants_h     = remplacants_h or []
    remplacants_d     = remplacants_d or []
    equipes_n3_ffe_h  = equipes_n3_ffe_h or []
    equipes_n3_ffe_d  = equipes_n3_ffe_d or []

    return {
        "format": "equipes_seniors",
        "meta": {
            "region":                   "Grand Est",
            "cat_id":                   cat_id,
            "arme_id":                  arme_id,
            "competition":              config.get("competition", ""),
            "cat_label":                config.get("cat_label", cat_id),
            "date":                     config.get("date", ""),
            "lieu":                     config.get("lieu", ""),
            "discipline":               config.get("discipline", ""),
            "mail_retour":              config.get("mail_retour", ""),
            "date_limite_retour":       config.get("date_limite_retour", ""),
            "date_engagement_extranet": config.get("date_engagement_extranet", ""),
            "arbitrage_config":         config.get("arbitrage_config", {}),
        },
        "equipes_n1n2_h":    equipes_n1n2_h,
        "equipes_n1n2_d":    equipes_n1n2_d,
        "equipes_n3_ffe_h":  equipes_n3_ffe_h,
        "equipes_n3_ffe_d":  equipes_n3_ffe_d,
        "equipes_n3_h":      eq_n3_h_sel,
        "equipes_n3_d":      eq_n3_d_sel,
        "quota_n3_h":     quota_n3_h,
        "quota_n3_d":     quota_n3_d,
        "mode_n3_h":      mode_n3_h,
        "mode_n3_d":      mode_n3_d,
        "remplacants_h":  remplacants_h,
        "remplacants_d":  remplacants_d,
    }
