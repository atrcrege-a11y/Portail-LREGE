"""
categories/selection.py -- Moteur generique de selection CDF/FDJ.

Principe : chaque combinaison (cat, arme, genre) est decrite par une
liste d'etapes ordonnees. La fonction construire_selection() execute
ces etapes en sequence, en maintenant un ensemble noms_exclus pour
eviter les doublons inter-etapes.

Etapes disponibles :
  EtapeFFE(niveau)    -- GES presents dans df_ffe au niveau donne (N1/N2/N3)
  EtapeQuotaLREGE()   -- split 1/3 + 2/3 nat+reg depuis df_nat et df_reg
  EtapeRegOnly()      -- 100% classement regional (M13)
  EtapeRemplacants()  -- suivants du classement regional hors qualifies
"""

import unicodedata, re as _re
import pandas as pd
from ..core.utils import filtrer_df, est_grand_est, COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION
from ..core.styles import get_palette

# -- Utilitaires -------------------------------------------------------

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

# -- Classes d'etapes --------------------------------------------------

class EtapeFFE:
    """GES presents dans df_ffe pour un niveau donne (N1, N2 ou N3)."""
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
        nat_idx = ctx.get("nat_idx", {})
        tireurs = []
        for _, r in ge.iterrows():
            k = _key(r)
            rang_nat = nat_idx.get(k, int(r.get(COL_RANG, 0)))
            tireurs.append(_tireur(r, f"CL NAT {rang_nat}"))
            ctx["noms_exclus"].add(k)
        cfg       = ctx["cfg"]
        pal       = ctx["pal"]
        date_comp = cfg.get("date", "")
        date_txt  = f" -- Competition le {date_comp}" if date_comp else ""
        couleur = pal["n1"] if self.niveau == "N1" else pal["n2"]
        label = f"TIREURS QUALIFIES -- {self.niveau} (LISTE NATIONALE FFE)"
        textes = [
            f"Tireurs Grand Est qualifies en {self.niveau} sur la liste nationale FFE",
            f"Attention : Selection effectuee maintenant{date_txt}",
        ]
        return {"label": label, "couleur": couleur, "textes": textes,
                "tireurs": tireurs, "avec_participation": True}


class EtapeQuotaLREGE:
    """Quota LREGE avec split 1/3 nat + 2/3 reg. Label = niveau_lrege du config."""
    def build(self, ctx):
        cfg      = ctx["cfg"]
        df_nat   = ctx.get("df_nat")
        df_reg   = ctx.get("df_reg")
        exclus   = ctx["noms_exclus"]
        quota_cn = cfg.get("quota_crege_nat", 0)
        quota_cr = cfg.get("quota_crege_reg", 0)
        total    = quota_cn + quota_cr
        niveau   = cfg.get("niveau_lrege", "")
        pal      = ctx["pal"]
        if total == 0:
            return None

        sous = []

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
                sous.append({
                    "label":   f"Sur classement national ({quota_cn} place{'s' if quota_cn>1 else ''})",
                    "couleur": pal["n2"], "textes": [], "tireurs": tirs,
                })

        if quota_cr > 0 and df_reg is not None and not df_reg.empty:
            ge_reg = df_reg[
                ~df_reg.apply(lambda r: _key(r) in exclus, axis=1)
            ].head(quota_cr)
            tirs = []
            for _, r in ge_reg.iterrows():
                tirs.append(_tireur(r, f"CL GE {r[COL_RANG]}"))
                exclus.add(_key(r))
            if tirs:
                sous.append({
                    "label":   f"Sur classement regional ({quota_cr} place{'s' if quota_cr>1 else ''})",
                    "couleur": pal["n2"], "textes": [], "tireurs": tirs,
                })

        if not sous:
            return None

        label = f"TIREURS QUALIFIES -- QUOTA LREGE{(' -- ' + niveau) if niveau else ''}"
        texte = (f"Quota LREGE Grand Est{(' -- ' + niveau) if niveau else ''} : "
                 f"{total} place{'s' if total>1 else ''} "
                 f"({quota_cn} classement national + {quota_cr} classement regional)")
        return {"label": label, "couleur": pal["n2"],
                "textes": [texte], "tireurs": [],
                "sous_sections": sous, "avec_participation": True}


class EtapeRegOnly:
    """100% classement regional -- quota total dans quota_crege_reg (M13)."""
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
        sous = [{"label": f"Sur classement regional (LREGE) : {quota} place{'s' if quota>1 else ''}",
                 "couleur": pal["n2"], "textes": [], "tireurs": tirs}]
        return {"label": "TIREURS QUALIFIES -- QUOTA LREGE",
                "couleur": pal["n2"],
                "textes": [f"Quota LREGE Grand Est : {quota} places -- classement regional uniquement"],
                "tireurs": [], "sous_sections": sous, "avec_participation": True}


class EtapeOpenCircuit:
    """Open circuit (Sabre M17/M20/M23, Seniors Sabre) : GES de df_ffe pour un niveau.

    Une instance par niveau (N1, N2) -- le fichier de reference (palettes mai 2026)
    montre une section N2 distincte quand le PDF FFE en contient (M20/Seniors sabre).
    """
    def __init__(self, niveau="N1"):
        self.niveau = niveau

    def build(self, ctx):
        df_ffe = ctx.get("df_ffe")
        if df_ffe is None or df_ffe.empty:
            return None
        if "Niveau" in df_ffe.columns:
            df_niv = df_ffe[df_ffe["Niveau"] == self.niveau].copy()
        elif self.niveau == "N1":
            df_niv = df_ffe.copy()
        else:
            return None
        ge = df_niv[df_niv[COL_REGION].apply(est_grand_est)]
        if ge.empty:
            return None
        nat_idx = ctx.get("nat_idx", {})
        tireurs = []
        for _, r in ge.iterrows():
            k = _key(r)
            rang_nat = nat_idx.get(k, int(r.get(COL_RANG, 0)))
            tireurs.append(_tireur(r, f"CL NAT {rang_nat}"))
            ctx["noms_exclus"].add(k)
        def _sort_key(t):
            try:
                return int(str(t["rang"]).split()[-1])
            except Exception:
                return 9999
        tireurs.sort(key=_sort_key)
        cfg             = ctx["cfg"]
        cat_id          = cfg.get("cat_id", "")
        is_sabre_senior = cat_id == "Seniors"
        pal             = ctx["pal"]
        date_comp       = cfg.get("date", "")
        date_txt        = f" -- Competition le {date_comp}" if date_comp else ""
        if self.niveau == "N2":
            couleur = pal["n2"]
            textes  = ["Competition open -- sous condition d'avoir participe a au moins une epreuve nationale"]
        else:
            couleur = pal["n1"]
            textes  = [
                "Les 36 premiers du classement national FFE (Wild Cards integrees)" if is_sabre_senior
                else "Les qualifies GE sur la liste nationale FFE (N1 + WC integrees)",
                f"Attention : Selection effectuee maintenant{date_txt}",
            ]
        return {"label": f"TIREURS QUALIFIES -- {self.niveau} (LISTE NATIONALE FFE)",
                "couleur": couleur, "textes": textes,
                "tireurs": tireurs, "avec_participation": True}


class EtapeRemplacants:
    """Suivants du classement regional hors tous les qualifies."""
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
        return {"label": "TIREURS REMPLACANTS",
                "couleur": pal.get("remplacants", "D9E1F2"),
                "textes": ["En cas de desistement d'un qualifie : le premier remplacant est selectionne"],
                "tireurs": tirs, "avec_participation": False}


# -- Matrice des etapes par (cat, arme, genre) -------------------------
# REFERENCE : cette table EST la regle de selection.
# Pour toute modification reglementaire, c'est ici qu'il faut intervenir.

_E     = EtapeFFE
_Q     = EtapeQuotaLREGE
_R     = EtapeRegOnly
_OC    = EtapeOpenCircuit
_Rempl = EtapeRemplacants

ETAPES = {
    # M13 -- 100% regional (pas de filtre nationalite)
    ("M13","E","H"): [_R(), _Rempl()],
    ("M13","E","D"): [_R(), _Rempl()],
    ("M13","F","H"): [_R(), _Rempl()],
    ("M13","F","D"): [_R(), _Rempl()],
    ("M13","S","H"): [],
    ("M13","S","D"): [],

    # M15 -- quota federal 40 + quota LREGE (variable, saisi dans l'UI)
    ("M15","E","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M15","F","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","F","D"): [_E("N1"), _Q(), _Rempl()],
    ("M15","S","H"): [_E("N1"), _Q(), _Rempl()],
    ("M15","S","D"): [_E("N1"), _Q(), _Rempl()],

    # M17/M20 Epee/Fleuret H -- N1+N2 PDF FFE + N3 quota LREGE
    ("M17","E","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M17","F","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M20","E","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],
    ("M20","F","H"): [_E("N1"), _E("N2"), _Q(), _Rempl()],

    # M17/M20 Epee/Fleuret D -- N1 PDF FFE + N2 quota LREGE
    ("M17","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M17","F","D"): [_E("N1"), _Q(), _Rempl()],
    ("M20","E","D"): [_E("N1"), _Q(), _Rempl()],
    ("M20","F","D"): [_E("N1"), _Q(), _Rempl()],

    # M17/M20/M23 Sabre -- open circuit (liste FFE PDF, pas de quota)
    ("M17","S","H"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("M17","S","D"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("M20","S","H"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("M20","S","D"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("M23","S","H"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("M23","S","D"): [_OC("N1"), _OC("N2"), _Rempl()],

    # M23 Epee/Fleuret -- quota LREGE (pas de liste FFE PDF distincte)
    ("M23","E","H"): [_Q(), _Rempl()],
    ("M23","E","D"): [_Q(), _Rempl()],
    ("M23","F","H"): [_Q(), _Rempl()],
    ("M23","F","D"): [_Q(), _Rempl()],

    # Seniors Epee -- N1+N2+N3 liste FFE + quota LREGE N3
    ("Seniors","E","H"): [_E("N1"), _E("N2"), _E("N3"), _Q(), _Rempl()],
    ("Seniors","E","D"): [_E("N1"), _E("N2"), _E("N3"), _Q(), _Rempl()],

    # Seniors Fleuret -- N1+N2+N3 liste FFE (FH) / N1+N2 (FD) + quota LREGE
    ("Seniors","F","H"): [_E("N1"), _E("N2"), _E("N3"), _Q(), _Rempl()],
    ("Seniors","F","D"): [_E("N1"), _E("N2"), _Q(), _Rempl()],

    # Seniors Sabre -- open circuit (liste FFE N1 = 36 avec WC)
    ("Seniors","S","H"): [_OC("N1"), _OC("N2"), _Rempl()],
    ("Seniors","S","D"): [_OC("N1"), _OC("N2"), _Rempl()],

    # Veterans V1/V2/V3/V4 -- quota LREGE 1/3 national + 2/3 regional
    # Nationalite francaise obligatoire (confirme REGLES.md regle #7)
    ("V1","E","H"): [_Q(), _Rempl()], ("V1","E","D"): [_Q(), _Rempl()],
    ("V1","F","H"): [_Q(), _Rempl()], ("V1","F","D"): [_Q(), _Rempl()],
    ("V1","S","H"): [_Q(), _Rempl()], ("V1","S","D"): [_Q(), _Rempl()],
    ("V2","E","H"): [_Q(), _Rempl()], ("V2","E","D"): [_Q(), _Rempl()],
    ("V2","F","H"): [_Q(), _Rempl()], ("V2","F","D"): [_Q(), _Rempl()],
    ("V2","S","H"): [_Q(), _Rempl()], ("V2","S","D"): [_Q(), _Rempl()],
    ("V3","E","H"): [_Q(), _Rempl()], ("V3","E","D"): [_Q(), _Rempl()],
    ("V3","F","H"): [_Q(), _Rempl()], ("V3","F","D"): [_Q(), _Rempl()],
    ("V3","S","H"): [_Q(), _Rempl()], ("V3","S","D"): [_Q(), _Rempl()],
    ("V4","E","H"): [_Q(), _Rempl()], ("V4","E","D"): [_Q(), _Rempl()],
    ("V4","F","H"): [_Q(), _Rempl()], ("V4","F","D"): [_Q(), _Rempl()],
    ("V4","S","H"): [_Q(), _Rempl()], ("V4","S","D"): [_Q(), _Rempl()],
}


# -- Fonction principale -----------------------------------------------

def construire_selection(cat_id, arme_id, genre, cfg,
                         df_nat=None, df_reg=None, df_ffe=None) -> dict:
    """
    Point d'entree unique pour toutes les selections individuelles.

    Parametres :
        cat_id  : "M13"|"M15"|"M17"|"M20"|"M23"|"Seniors"|"V1"...
        arme_id : "E"|"F"|"S"
        genre   : "H"|"D"
        cfg     : dict de configuration (depuis build_cfg)
        df_nat  : DataFrame classement national Excel (optionnel)
        df_reg  : DataFrame classement regional GE (optionnel)
        df_ffe  : DataFrame liste qualifies FFE PDF (optionnel, avec col Niveau)
    """
    filtre_fr = cfg.get("nationalite_francaise", True)
    pal       = get_palette(cat_id, arme_id)

    df_nat = filtrer_df(df_nat, filtre_fr) if df_nat is not None else _empty_df()
    df_reg = filtrer_df(df_reg, filtre_fr) if df_reg is not None else _empty_df()

    nat_idx = {}
    if df_nat is not None and not df_nat.empty:
        for _, r in df_nat.iterrows():
            k = _key(r)
            if k[0]:
                nat_idx[k] = int(r.get(COL_RANG, 0))

    ctx = {
        "cfg":         cfg,
        "df_nat":      df_nat,
        "df_reg":      df_reg,
        "df_ffe":      df_ffe,
        "nat_idx":     nat_idx,
        "noms_exclus": set(),
        "pal":         pal,
    }

    etapes = ETAPES.get((cat_id, arme_id, genre), [_Q(), _Rempl()])

    sections = []
    for etape in etapes:
        section = etape.build(ctx)
        if section:
            sections.append(section)

    return {
        "format":   "jeunes" if cat_id not in ("Seniors","V1","V2","V3","V4","Veterans") else "seniors",
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
