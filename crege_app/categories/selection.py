"""
categories/selection.py — Moteur générique de sélection CDF/FDJ.

Principe : chaque combinaison (cat, arme, genre) est décrite par une
liste d'étapes ordonnées. La fonction construire_selection() exécute
ces étapes en séquence, en maintenant un ensemble noms_exclus pour
éviter les doublons inter-étapes.

Étapes disponibles :
  EtapeFFE(niveau)     — GES présents dans df_ffe au niveau donné (N1/N2/N3)
  EtapeQuotaLREGE()   — split ⅓/⅔ nat+rég depuis df_nat et df_reg
  EtapeRegOnly()       — 100% classement régional (M13)
  EtapeRemplacants()  — suivants du classement régional hors qualifiés
"""

import unicodedata, re as _re
import pandas as pd
from ..core.utils import filtrer_df, est_grand_est, COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION
from ..core.styles import get_palette

# ── Utilitaires ──────────────────────────────────────────────────────────────

_COLS_EMPTY = [COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION]

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().upper().strip()
    return _re.sub(r"[^A-Z]", "", s)

def _key(row):
    return (_norm(row.get(COL_NOM, "")), _norm(row.get(COL_PRENOM, "")))

def _tireur(r, rang_str):
    return {
        "rang":   rang_str,
        "nom":    str(r.get(COL_NOM, "")),
        "prenom": str(r.get(COL_PRENOM, r.get("Prenom", ""))),
        "club":   str(r.get(COL_CLUB, r.get("Nom club", ""))),
        "note":   "",
    }

def _empty_df():
    return pd.DataFrame(columns=_COLS_EMPTY)

# ── Classes d'étapes ─────────────────────────────────────────────────────────

class EtapeFFE:
    """GES présents dans df_ffe pour un niveau donné (N1, N2 ou N3)."""
    def __init__(self, niveau):
        self.niveau = niveau

    def build(self, ctx):
        df_ffe = ctx.get("df_ffe")
        if df_ffe is None or df_ffe.empty:
            return None
        if "Niveau" in df_ffe.columns:
            df_niv = df_ffe[df_ffe["Niveau"] == self.niveau].copy()
        else:
            df_niv = df_ffe.copy()
        ge = df_niv[df_niv[COL_REGION].apply(est_grand_est)]
        if ge.empty:
            return None
        # Récupérer rang depuis le classement national Excel si disponible
        nat_idx = ctx.get("nat_idx", {})
        tireurs = []
        for _, r in ge.iterrows():
            k = _key(r)
            rang_nat = nat_idx.get(k, int(r.get(COL_RANG, 0)))
            tireurs.append(_tireur(r, f"CL NAT {rang_nat}"))
            ctx["noms_exclus"].add(k)
        pal = ctx["pal"]
        couleur = pal["n1"] if self.niveau == "N1" else pal["n2"]
        label = f"TIREURS QUALIFIÉS — {self.niveau} (LISTE NATIONALE FFE)"
        textes = [
            f"Tireurs Grand Est qualifiés en {self.niveau} sur la liste nationale FFE",
            "⚠️  Sélection effectuée maintenant — Compétition les 19-20 décembre 2026",
        ]
        return {"label": label, "couleur": couleur, "textes": textes,
                "tireurs": tireurs, "avec_participation": True}


class EtapeQuotaLREGE:
    """Quota LREGE avec split ⅓ nat + ⅔ rég. Label = niveau_lrege du config."""
    def build(self, ctx):
        cfg      = ctx["cfg"]
        df_nat   = ctx.get("df_nat", _empty_df())
        df_reg   = ctx.get("df_reg", _empty_df())
        exclus   = ctx["noms_exclus"]
        quota_cn = cfg.get("quota_crege_nat", 0)
        quota_cr = cfg.get("quota_crege_reg", 0)
        niveau   = cfg.get("niveau_lrege", "")
        pal      = ctx["pal"]
        if quota_cn == 0 and quota_cr == 0:
            return None

        sous = []

        # ⅓ classement national
        if quota_cn > 0 and df_nat is not None and not df_nat.empty:
            ge_nat = df_nat[
                df_nat[COL_REGION].apply(est_grand_est) &
                ~df_nat.apply(lambda r: _key(r) in exclus, axis=1)
            ].head(quota_cn)
            tirs = []
            for _, r in ge_nat.iterrows():
                tirs.append(_tireur(r, f"CL NAT {r[COL_RANG]}"))
                exclus.add(_key(r))
            if tirs:
                sous.append({"label": f"Sur classement national (LREGE) : {quota_cn} place{'s' if quota_cn>1 else ''}",
                             "couleur": pal["n2"], "textes": [], "tireurs": tirs})

        # ⅔ classement régional
        if quota_cr > 0 and df_reg is not None and not df_reg.empty:
            ge_reg = df_reg[
                ~df_reg.apply(lambda r: _key(r) in exclus, axis=1)
            ].head(quota_cr)
            tirs = []
            for _, r in ge_reg.iterrows():
                tirs.append(_tireur(r, f"CL GE {r[COL_RANG]}"))
                exclus.add(_key(r))
            if tirs:
                sous.append({"label": f"Sur classement régional (LREGE) : {quota_cr} place{'s' if quota_cr>1 else ''}",
                             "couleur": pal["n2"], "textes": [], "tireurs": tirs})

        if not sous:
            return None
        total = quota_cn + quota_cr
        label = f"TIREURS QUALIFIÉS — QUOTA LREGE{(' — ' + niveau) if niveau else ''}"
        texte = f"Quota LREGE Grand Est{(' — ' + niveau) if niveau else ''} : {total} place{'s' if total>1 else ''}"
        return {"label": label, "couleur": pal["n2"],
                "textes": [texte], "tireurs": [],
                "sous_sections": sous, "avec_participation": True}


class EtapeRegOnly:
    """100% classement régional — quota total dans quota_crege_reg (M13)."""
    def build(self, ctx):
        cfg    = ctx["cfg"]
        df_reg = ctx.get("df_reg", _empty_df())
        exclus = ctx["noms_exclus"]
        quota  = cfg.get("quota_crege_reg", 0)
        pal    = ctx["pal"]
        if quota == 0 or df_reg is None or df_reg.empty:
            return None
        ge_reg = df_reg[~df_reg.apply(lambda r: _key(r) in exclus, axis=1)].head(quota)
        tirs = []
        for _, r in ge_reg.iterrows():
            tirs.append(_tireur(r, f"CL GE {r[COL_RANG]}"))
            exclus.add(_key(r))
        if not tirs:
            return None
        sous = [{"label": f"Sur classement régional (LREGE) : {quota} place{'s' if quota>1 else ''}",
                 "couleur": pal["n2"], "textes": [], "tireurs": tirs}]
        return {"label": "TIREURS QUALIFIÉS — QUOTA LREGE",
                "couleur": pal["n2"],
                "textes": [f"Quota LREGE Grand Est : {quota} places — classement régional uniquement"],
                "tireurs": [], "sous_sections": sous, "avec_participation": True}


class EtapeOpenCircuit:
    """Open circuit (Sabre M17/M20/M23, Seniors Sabre) : GES de df_ffe toute N1."""
    def build(self, ctx):
        df_ffe = ctx.get("df_ffe")
        if df_ffe is None or df_ffe.empty:
            return None
        # Prendre N1 uniquement (les 36 qualifiés)
        if "Niveau" in df_ffe.columns:
            df_n1 = df_ffe[df_ffe["Niveau"] == "N1"].copy()
        else:
            df_n1 = df_ffe.copy()
        ge = df_n1[df_n1[COL_REGION].apply(est_grand_est)]
        if ge.empty:
            return None
        nat_idx = ctx.get("nat_idx", {})
        tireurs = []
        for _, r in ge.iterrows():
            k = _key(r)
            rang_nat = nat_idx.get(k, int(r.get(COL_RANG, 0)))
            tireurs.append(_tireur(r, f"CL NAT {rang_nat}"))
            ctx["noms_exclus"].add(k)
        cfg = ctx["cfg"]
        cat_id = cfg.get("cat_id", "")
        is_sabre_senior = cat_id == "Seniors"
        pal = ctx["pal"]
        textes = [
            "Les 36 premiers du classement national FFE (Wild Cards intégrées)" if is_sabre_senior
            else "Les qualifiés GE sur la liste nationale FFE (N1 + WC intégrées)",
            "⚠️  Sélection effectuée maintenant — Compétition les 19-20 décembre 2026",
        ]
        return {"label": "TIREURS QUALIFIÉS — N1 (LISTE NATIONALE FFE)",
                "couleur": pal["n1"], "textes": textes,
                "tireurs": tireurs, "avec_participation": True}


class EtapeRemplacants:
    """Suivants du classement régional hors tous les qualifiés."""
    def build(self, ctx):
        cfg    = ctx["cfg"]
        df_reg = ctx.get("df_reg", _empty_df())
        exclus = ctx["noms_exclus"]
        nb     = cfg.get("nb_remplacants", 10)
        pal    = ctx["pal"]
        if df_reg is None or df_reg.empty:
            return None
        ge_rempl = df_reg[~df_reg.apply(lambda r: _key(r) in exclus, axis=1)].head(nb)
        tirs = [_tireur(r, f"CL GE {r[COL_RANG]}") for _, r in ge_rempl.iterrows()]
        tirs = [t for t in tirs if t["nom"].strip()]
        if not tirs:
            return None
        return {"label": "TIREURS REMPLAÇANTS",
                "couleur": pal.get("remplacants", "D9E1F2"),
                "textes": ["En cas de désistement d'un qualifié : le premier remplaçant est sélectionné"],
                "tireurs": tirs, "avec_participation": False}


# ── Matrice des étapes par (cat, arme, genre) ─────────────────────────────────

_E = EtapeFFE
_Q = EtapeQuotaLREGE
_R = EtapeRegOnly
_OC = EtapeOpenCircuit
_Rempl = EtapeRemplacants

ETAPES = {
    # M13 — 100% régional (pas de filtre nationalité)
    ("M13","E","H"): [_R(), _Rempl()],
    ("M13","E","D"): [_R(), _Rempl()],
    ("M13","F","H"): [_R(), _Rempl()],
    ("M13","F","D"): [_R(), _Rempl()],
    ("M13","S","H"): [],  # open — pas de liste
    ("M13","S","D"): [],

    # M15 — quota fédéral 40 + quota LREGE
    ("M15","E","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M15","F","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","F","D"): [_E("N1"), _Q(), _Rempl()],
    ("M15","S","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","S","D"): [_E("N1"), _Q(), _Rempl()],

    # M17/M20 Épée/Fleuret H — N1+N2 PDF + N3 quota
    ("M17","E","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M17","F","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M20","E","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M20","F","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],

    # M17/M20 Épée/Fleuret D — N1 PDF + N2 quota
    ("M17","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M17","F","D"): [_E("N1"), _Q(), _Rempl()],
    ("M20","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M20","F","D"): [_E("N1"), _Q(), _Rempl()],

    # M17/M20/M23 Sabre — open circuit (N1 liste FFE)
    ("M17","S","H"): [_OC(), _Rempl()],
    ("M17","S","D"): [_OC(), _Rempl()],
    ("M20","S","H"): [_OC(), _Rempl()],
    ("M20","S","D"): [_OC(), _Rempl()],
    ("M23","S","H"): [_OC(), _Rempl()],
    ("M23","S","D"): [_OC(), _Rempl()],

    # M23 Épée/Fleuret — quota LREGE (pas de liste FFE N1 distincte)
    ("M23","E","H"): [_Q(), _Rempl()],
    ("M23","E","D"): [_Q(), _Rempl()],
    ("M23","F","H"): [_Q(), _Rempl()],
    ("M23","F","D"): [_Q(), _Rempl()],

    # Seniors Épée/Fleuret — N1+N2 (et N3 pour FH) liste FFE + quota LREGE
    ("Seniors","E","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("Seniors","E","D"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("Seniors","F","H"): [_E("N1"), _E("N2"), _E("N3"), _Q(), _Rempl()],
    ("Seniors","F","D"): [_E("N1"), _E("N2"), _Q(), _Rempl()],

    # Seniors Sabre — open circuit (liste FFE N1 = 36 avec WC)
    ("Seniors","S","H"): [_OC(), _Rempl()],
    ("Seniors","S","D"): [_OC(), _Rempl()],
}


# ── Fonction principale ───────────────────────────────────────────────────────

def construire_selection(cat_id, arme_id, genre, cfg,
                         df_nat=None, df_reg=None, df_ffe=None) -> dict:
    """
    Point d'entrée unique pour toutes les sélections individuelles.

    Paramètres :
        cat_id  : "M13"|"M15"|"M17"|"M20"|"M23"|"Seniors"|"V1"...
        arme_id : "E"|"F"|"S"
        genre   : "H"|"D"
        cfg     : dict de configuration (depuis build_cfg)
        df_nat  : DataFrame classement national Excel (optionnel)
        df_reg  : DataFrame classement régional GE (optionnel)
        df_ffe  : DataFrame liste qualifiés FFE PDF (optionnel, avec col Niveau)
    """
    filtre_fr = cfg.get("nationalite_francaise", True)
    pal       = get_palette(cat_id)

    # Filtrer nationalité
    df_nat = filtrer_df(df_nat, filtre_fr) if df_nat is not None else _empty_df()
    df_reg = filtrer_df(df_reg, filtre_fr) if df_reg is not None else _empty_df()

    # Index rang national depuis Excel (pour labelliser les GES FFE)
    nat_idx = {}
    if df_nat is not None and not df_nat.empty:
        for _, r in df_nat.iterrows():
            k = _key(r)
            if k[0]:
                nat_idx[k] = int(r.get(COL_RANG, 0))

    # Contexte partagé entre les étapes
    ctx = {
        "cfg":         cfg,
        "df_nat":      df_nat,
        "df_reg":      df_reg,
        "df_ffe":      df_ffe,
        "nat_idx":     nat_idx,
        "noms_exclus": set(),
        "pal":         pal,
    }

    # Récupérer les étapes pour cette combinaison
    etapes = ETAPES.get((cat_id, arme_id, genre), [_Q(), _Rempl()])

    sections = []
    for etape in etapes:
        section = etape.build(ctx)
        if section:
            sections.append(section)

    return {
        "format":   "jeunes" if cat_id not in ("Seniors","V1","V2","V3","V4") else "seniors",
        "meta":     _make_meta(cfg),
        "sections": sections,
        "equipes":  [],
    }


def _make_meta(cfg):
    return {
        "region":                   "Grand Est",
        "cat_id":                   cfg.get("cat_id", ""),
        "cat_label":                cfg.get("cat_label", ""),
        "competition":              cfg.get("competition", ""),
        "date":                     cfg.get("date", ""),
        "lieu":                     cfg.get("lieu", ""),
        "discipline":               cfg.get("discipline", ""),
        "mail_retour":              cfg.get("mail_retour", "administration@crege.fr"),
        "date_limite_retour":       cfg.get("date_limite_retour", ""),
        "date_engagement_extranet": cfg.get("date_engagement_extranet", ""),
        "arbitrage_config":         cfg.get("arbitrage_config", {}),
    }
