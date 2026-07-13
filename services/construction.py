"""
services/construction.py — Logique de construction des sélections.

Point d'entrée unique : construire_selection() depuis crege_app.categories.selection.
Ce module fournit build_cfg(), repartition_lrege() et les helpers de nommage.
"""
import datetime
import unicodedata
import re as _re

from crege_app.core.reglementation import get_regle, N2_QUOTA_LREGE, N2_FFE_N3_QUOTA, N1_FFE_N2_QUOTA, N2_REG_ONLY
from crege_app.core.quotas_lrege   import get_quota_indiv
from crege_app.categories.selection import construire_selection  # moteur unifie

# ── Table LREGE 1/3 FFE + 2/3 régional ──────────────────────────────
TABLE_LREGE = {
    3: (1, 2),  4: (1, 3),  5: (2, 3),  6: (2, 4),
    7: (2, 5),  8: (3, 5),  9: (3, 6), 10: (3, 7), 11: (4, 7),
}

ARME_CODES = {"S": "Sabre", "F": "Fleuret", "E": "Epee"}
CAT_CODES  = {
    "M13": "M13", "M15": "M15", "M17": "M17", "M20": "M20", "M23": "M23",
    "Seniors": "Seniors", "Veterants": "Vet",
    "V1": "Vet-V1", "V2": "Vet-V2", "V3": "GrdVet-V3", "V4": "GrdVet-V4",
}
COMP_CODES = {
    "Championnat de France": "CDF",
    "Championnat de France Veterans": "CDF-Vet",
    "Fete des Jeunes": "FDJ",
    "Epreuve de zone": "EprZone",
    "1/2 Finale": "DemiFinale",
    "Challenge de France": "ChallengeFrance",
}

CATEGORIES = [
    {"id": "M13",      "label": "M13",     "competition": "Challenge de France",             "format": "jeunes",  "nationalite_fr": False},
    {"id": "M15",      "label": "M15",     "competition": "Fete des Jeunes",                 "format": "jeunes",  "nationalite_fr": False,
     "competitions": ["Fete des Jeunes", "Epreuve de zone", "1/2 Finale"], "equipes": True},
    {"id": "M17",      "label": "M17",     "competition": "Championnat de France",           "format": "jeunes",  "nationalite_fr": True,  "equipes": True},
    {"id": "M20",      "label": "M20",     "competition": "Championnat de France",           "format": "jeunes",  "nationalite_fr": True,  "equipes": True},
    {"id": "M23",      "label": "M23",     "competition": "Championnat de France",           "format": "jeunes",  "nationalite_fr": True,  "equipes": False},
    {"id": "Seniors",  "label": "Seniors", "competition": "Championnat de France",           "format": "seniors", "nationalite_fr": True,  "equipes": True},
    {"id": "Veterans", "label": "Veterans","competition": "Championnat de France Veterans",  "format": "seniors", "nationalite_fr": True,  "equipes": True},
]
ARMES  = [{"id": "S", "label": "Sabre"}, {"id": "F", "label": "Fleuret"}, {"id": "E", "label": "Epee"}]
GENRES = [{"id": "H", "label": "Hommes"}, {"id": "D", "label": "Dames"}]


def get_saison() -> str:
    today = datetime.date.today()
    annee = today.year if today.month >= 9 else today.year - 1
    return f"{annee}-{annee + 1}"


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return _re.sub(r"[^a-zA-Z0-9_-]", "", s.replace(" ", "-").replace("/", "-")).strip("-")


def nom_fichier_selection(params: dict, mode: str = "individuel", categorie: str = None) -> str:
    today = datetime.date.today().strftime("%Y%m%d")
    cat   = CAT_CODES.get(categorie or params.get("cat", ""), slug(categorie or params.get("cat", "")))
    comp  = COMP_CODES.get(params.get("competition", ""), slug(params.get("competition", ""))) or "Selection"
    arme  = ARME_CODES.get(params.get("arme", ""), slug(params.get("arme", "")))
    genre = params.get("genre", "HD")
    parts = ["LREGE_GE", cat]
    if comp and comp != cat:
        parts.append(comp)
    if arme:
        parts.append(arme)
    parts.append(genre)
    if mode == "equipes":
        parts.append("Equipes")
    parts.append(today)
    return "_".join(p for p in parts if p) + ".xlsx"


def repartition_lrege(quota_total: int) -> tuple:
    if quota_total in TABLE_LREGE:
        return TABLE_LREGE[quota_total]
    if quota_total <= 0:
        return (0, 0)
    if quota_total == 1:
        return (0, 1)
    if quota_total == 2:
        return (1, 1)
    ffe = round(quota_total / 3)
    reg = quota_total - ffe
    return (ffe, reg)


def _niveau_lrege(cat_id: str, arme_id: str, genre: str = "") -> str:
    from crege_app.core.reglementation import get_regle, N2_FFE_N3_QUOTA
    regle = get_regle(cat_id, arme_id, genre) if genre else {}
    if regle.get("n2_mode") == N2_FFE_N3_QUOTA:
        return "N3"
    niveaux = {
        ("M17", "E"): "N2", ("M17", "F"): "N2", ("M17", "S"): "N3",
        ("M20", "E"): "N2", ("M20", "F"): "N2", ("M20", "S"): "N3",
        ("M23", "E"): "N2", ("M23", "F"): "N2", ("M23", "S"): "N3",
        # Seniors : Epee H/D -> N3, Fleuret H -> N3 (N1+N2+N3 FFE), Fleuret D -> N2
        ("Seniors", "E"): "N3", ("Seniors", "F", "H"): "N3", ("Seniors", "F", "D"): "N2", ("Seniors", "S"): "N3",
    }
    return niveaux.get((cat_id, arme_id, genre), niveaux.get((cat_id, arme_id), ""))


def build_cfg(params: dict, genre: str) -> tuple:
    """Construit le dict config passe aux fonctions construire_*. Retourne (cfg, suffix_genre)."""
    s       = genre.lower()
    cat_id  = params.get("cat_id", "Seniors")
    arme_id = params.get("arme_id", "E")
    regle   = get_regle(cat_id, arme_id, genre)
    quota_total = get_quota_indiv(cat_id, arme_id, genre) or 0
    ffe, reg    = repartition_lrege(quota_total)
    arme_label  = {"S": "Sabre", "F": "Fleuret", "E": "Epee"}.get(arme_id, arme_id)
    genre_label = "Hommes" if genre == "H" else "Dames"
    cfg = {
        "cat_id":                   cat_id,
        "arme_id":                  arme_id,
        "competition":              params.get("competition", "Championnat de France"),
        "cat_label":                next((c["label"] for c in CATEGORIES if c["id"] == cat_id), cat_id),
        "date":                     params.get("date", ""),
        "lieu":                     params.get("lieu", ""),
        "discipline":               f"{arme_label} {genre_label}",
        "mail_retour":              params.get("mail_retour", "administration@crege.fr"),
        "date_limite_retour":       params.get("date_limite_retour", ""),
        "date_engagement_extranet": params.get("date_engagement_extranet", ""),
        "arbitrage_config":         params.get("arbitrage_config", {}),
        "nationalite_francaise":    True if cat_id in ("M17", "M20", "M23", "Seniors", "V1", "V2", "V3", "V4", "Veterans") else params.get("nationalite_fr", False),
        "quota_n1":                 regle.get("n1_default", 32),
        "nb_wildcards":             int(params.get(f"nb_wildcards_{s}", params.get("nb_wildcards", 4))),
        "quota_n2_reg":             int(params.get(f"quota_n2_reg_{s}", params.get("quota_n2_reg", reg))),
        "quota_federal":            0 if regle.get("n2_mode") == N2_REG_ONLY else int(params.get(f"quota_fed_{s}", quota_total)),
        "quota_crege_nat":          0 if regle.get("n2_mode") == N2_REG_ONLY else ffe,
        "quota_crege_reg":          quota_total if regle.get("n2_mode") == N2_REG_ONLY else reg,
        "nb_remplacants":           int(params.get(f"nb_rempl_{s}", 10)),
        "n2_mode":                  regle.get("n2_mode", N2_QUOTA_LREGE),
        "n2_texte":                 regle.get("n2_texte", ""),
        "condition":                regle.get("condition", ""),
        "niveau_lrege":             _niveau_lrege(cat_id, arme_id, genre),
    }
    return cfg, s


def construire_genre(params: dict, genre: str,
                     df_nat=None, df_reg=None, df_ffe=None) -> dict:
    """Wrapper unifie -> construire_selection().

    Remplace les 5 anciennes fonctions construire_genre_seniors / _jeunes /
    _open_circuit / _ffe_n1n2_n3quota / _n1_ffe_n2_quota.
    """
    cfg, _ = build_cfg(params, genre)
    cat_id  = cfg["cat_id"]
    arme_id = cfg["arme_id"]
    return construire_selection(cat_id, arme_id, genre, cfg,
                                df_nat=df_nat, df_reg=df_reg, df_ffe=df_ffe)
