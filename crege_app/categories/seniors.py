"""
categories/seniors.py — Seniors et Vétérans (V1→V4).
"""
from .base import BaseCategorie
from ..core.utils import filtrer_df, est_grand_est, COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION
from ..core.styles import COULEUR_N1, COULEUR_N2, get_palette


def _construire_seniors(df_national, df_regional, config: dict, df_ffe=None) -> dict:
    """Logique commune Seniors / Vétérans.

    df_ffe : DataFrame du PDF FFE (colonnes Rang/Nom/Prenom/Region/Niveau).
             Si fourni, les sections FFE sont construites depuis ce PDF.
             Sinon, on utilise df_national directement.
    """
    quota_n1     = config.get("quota_n1", 32)
    quota_n2     = config.get("quota_n2_reg", 0)
    filtre_fr    = config.get("nationalite_francaise", True)
    cat_id       = config.get("cat_id", "Seniors")
    arme_id      = config.get("arme_id", "E")
    niveau_lrege = config.get("niveau_lrege", "N3")
    is_sabre     = arme_id == "S" and cat_id == "Seniors"
    nb_wc        = config.get("nb_wildcards", 4) if (cat_id == "Seniors" and not is_sabre) else 0
    pal          = get_palette(cat_id, arme_id)

    import pandas as pd, unicodedata, re as _re
    _COLS = [COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION]
    _empty = pd.DataFrame(columns=_COLS)
    df_nat = filtrer_df(df_national, filtre_fr) if df_national is not None else _empty
    df_reg = filtrer_df(df_regional, filtre_fr) if df_regional is not None else _empty

    def _norm(s):
        s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().upper().strip()
        return _re.sub(r"[^A-Z]", "", s)

    sections = []
    noms_qualifies = set()  # tuples normalisés des GES déjà en section FFE

    # ── Mode PDF FFE : Fleuret/Épée Seniors avec liste N1/N2/N3 ─────
    if df_ffe is not None and not df_ffe.empty:
        # Index rang national depuis Excel national
        nat_idx = {}
        for _, r in df_nat.iterrows():
            k = (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, "")))
            if k[0]:
                nat_idx[k] = int(r[COL_RANG])

        niveaux_pdf = sorted(df_ffe["Niveau"].unique()) if "Niveau" in df_ffe.columns else ["N1"]
        for niv in niveaux_pdf:
            df_niv = df_ffe[df_ffe["Niveau"] == niv] if "Niveau" in df_ffe.columns else df_ffe
            ge_niv = df_niv[df_niv[COL_REGION].apply(est_grand_est)]
            if ge_niv.empty:
                continue
            tireurs = []
            for _, r in ge_niv.iterrows():
                k = (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, "")))
                rang_nat = nat_idx.get(k, int(r[COL_RANG]))
                tireurs.append({
                    "rang":   f"CL NAT {rang_nat}",
                    "nom":    str(r[COL_NOM]),
                    "prenom": str(r.get(COL_PRENOM, r.get("Prenom", ""))),
                    "club":   str(r.get(COL_CLUB, r.get("Nom club", ""))),
                    "note":   "",
                })
                noms_qualifies.add(k)
            date_comp = config.get("date", "")
            date_txt  = f" — Compétition le {date_comp}" if date_comp else ""
            couleur = pal["n1"] if niv == "N1" else pal["n2"]
            sections.append({
                "label":   f"TIREURS QUALIFIÉS — {niv} (LISTE NATIONALE FFE)",
                "couleur": couleur,
                "textes":  [
                    f"Tireurs Grand Est qualifiés en {niv} sur la liste nationale FFE",
                    f"⚠️  Sélection effectuée maintenant{date_txt}",
                ],
                "tireurs": tireurs,
                "avec_participation": True,
            })

    # ── Mode classement national direct : Sabre, Épée, Vétérans ─────
    else:
        ge_n1 = df_nat[df_nat[COL_REGION].apply(est_grand_est)]
        if not is_sabre:
            ge_n1 = ge_n1.head(quota_n1)
        tireurs_n1 = [
            {"rang": f"CL NAT {r[COL_RANG]}", "nom": r[COL_NOM],
             "prenom": r[COL_PRENOM], "club": r[COL_CLUB], "note": ""}
            for _, r in ge_n1.iterrows()
        ]
        noms_qualifies = {(_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, ""))) for _, r in ge_n1.iterrows()}

        if nb_wc > 0:
            ge_zone_wc = df_nat[
                (df_nat[COL_RANG] > quota_n1) &
                (df_nat[COL_RANG] <= quota_n1 + nb_wc) &
                df_nat[COL_REGION].apply(est_grand_est)
            ]
            if not ge_zone_wc.empty:
                for i in range(1, nb_wc + 1):
                    tireurs_n1.append({"rang": f"WC {i}/{nb_wc}", "nom": "", "prenom": "", "club": "", "note": "Wild Card DTN"})
            else:
                nb_wc = 0

        date_comp = config.get("date", "")
        date_txt  = f" — Compétition le {date_comp}" if date_comp else ""
        if is_sabre:
            label_n1  = "TIREURS QUALIFIÉS — N1 (LISTE NATIONALE FFE)"
            textes_n1 = config.get("textes_n1", [
                "Les 36 premiers du classement national FFE (Wild Cards intégrées)",
                "Les absents non remplacés : le suivant au classement national est sélectionné",
                f"⚠️  Sélection effectuée maintenant{date_txt}",
            ])
        else:
            label_n1  = "TIREURS QUALIFIÉS — N1 (LISTE NATIONALE FFE)"
            textes_n1 = config.get("textes_n1", [
                f"Les {quota_n1} premiers du classement national",
                f"+ jusqu'à {nb_wc} Wild Card{'s' if nb_wc > 1 else ''} attribuée{'s' if nb_wc > 1 else ''} par la DTN",
                "Les absents non remplacés par WC : le suivant au classement national est sélectionné",
                f"⚠️  Sélection effectuée maintenant{date_txt}",
            ])
        if tireurs_n1:
            sections.append({
                "label": label_n1, "couleur": pal["n1"],
                "textes": textes_n1, "tireurs": tireurs_n1,
                "avec_participation": True,
            })

    # ── Quota LREGE (N2 ou N3 selon arme) — split ⅓ nat + ⅔ rég ────
    quota_cn = config.get("quota_crege_nat", 0)
    quota_cr = config.get("quota_crege_reg", quota_n2)
    noms_lrege = set()

    if quota_cn > 0 or quota_cr > 0:
        sous_sections = []

        # Places classement national (hors déjà qualifiés FFE)
        tireurs_cn = []
        if quota_cn > 0 and not df_nat.empty:
            ge_nat = df_nat[
                df_nat[COL_REGION].apply(est_grand_est) &
                ~df_nat.apply(lambda r: (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, ""))) in noms_qualifies, axis=1)
            ]
            for _, r in ge_nat.head(quota_cn).iterrows():
                k = (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, "")))
                tireurs_cn.append({"rang": f"CL NAT {r[COL_RANG]}", "nom": r[COL_NOM],
                                    "prenom": r[COL_PRENOM], "club": r[COL_CLUB], "note": ""})
                noms_lrege.add(k)
        if tireurs_cn:
            sous_sections.append({
                "label": f"Sur classement national (LREGE) : {quota_cn} place{'s' if quota_cn > 1 else ''}",
                "couleur": pal["n2"], "textes": [], "tireurs": tireurs_cn,
            })

        # Places classement régional (hors déjà qualifiés FFE + national)
        noms_exclus_reg = noms_qualifies | noms_lrege
        tireurs_cr = []
        if quota_cr > 0 and not df_reg.empty:
            df_reg_filtre = df_reg[
                ~df_reg.apply(lambda r: (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, ""))) in noms_exclus_reg, axis=1)
            ].head(quota_cr)
            for _, r in df_reg_filtre.iterrows():
                k = (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, "")))
                tireurs_cr.append({"rang": f"CL GE {r[COL_RANG]}", "nom": r[COL_NOM],
                                   "prenom": r[COL_PRENOM], "club": r[COL_CLUB], "note": ""})
                noms_lrege.add(k)
        if tireurs_cr:
            sous_sections.append({
                "label": f"Sur classement régional (LREGE) : {quota_cr} place{'s' if quota_cr > 1 else ''}",
                "couleur": pal["n2"], "textes": [], "tireurs": tireurs_cr,
            })

        if sous_sections:
            sections.append({
                "label":        f"TIREURS QUALIFIÉS — QUOTA LREGE {niveau_lrege}",
                "couleur":      pal["n2"],
                "textes":       [f"Quota LREGE Grand Est — {quota_cn} place{'s' if quota_cn>1 else ''} classement national + {quota_cr} place{'s' if quota_cr>1 else ''} classement régional"],
                "tireurs":      [],
                "sous_sections": sous_sections,
                "avec_participation": True,
            })

    # ── Remplaçants : suivants du classement régional hors qualifiés ─
    noms_exclus_rempl = noms_qualifies | noms_lrege
    nb_rempl = config.get("nb_remplacants", 10)
    df_rempl = df_reg[
        ~df_reg.apply(lambda r: (_norm(r[COL_NOM]), _norm(r.get(COL_PRENOM, ""))) in noms_exclus_rempl, axis=1)
    ].head(nb_rempl)
    tireurs_rempl = [
        {"rang": f"CL GE {r[COL_RANG]}", "nom": r[COL_NOM],
         "prenom": r[COL_PRENOM], "club": r[COL_CLUB], "note": ""}
        for _, r in df_rempl.iterrows()
    ]
    if tireurs_rempl:
        sections.append({
            "label":   "TIREURS REMPLAÇANTS",
            "couleur": pal.get("remplacants", "D9E1F2"),
            "textes":  ["En cas de désistement d'un qualifié : le premier remplaçant est sélectionné"],
            "tireurs": tireurs_rempl,
            "avec_participation": False,
        })

    return {
        "format": "seniors",
        "meta": {
            "region": "Grand Est",
            "cat_id":                   cat_id,
            "cat_label":                config.get("cat_label", cat_id),
            "competition":              config.get("competition", "Championnat de France"),
            "date":                     config.get("date", ""),
            "lieu":                     config.get("lieu", ""),
            "discipline":               config.get("discipline", ""),
            "mail_retour":              config.get("mail_retour", "administration@crege.fr"),
            "date_limite_retour":       config.get("date_limite_retour", ""),
            "date_engagement_extranet": config.get("date_engagement_extranet", ""),
            "arbitrage_config":         config.get("arbitrage_config", {}),
        },
        "sections": sections,
        "equipes": [],
    }


def _make_seniors_class(cat_id, label, competitions, nationalite_fr=True):
    class _Cat(BaseCategorie):
        CAT_ID         = cat_id
        LABEL          = label
        FORMAT         = "seniors"
        COMPETITIONS   = competitions
        NATIONALITE_FR = nationalite_fr

        def construire(self, df_national, df_regional, config: dict) -> dict:
            return _construire_seniors(df_national, df_regional, config)

        def generer(self, data: dict):
            from ..generateur.excel import generer_feuille_simple
            from openpyxl import Workbook
            wb = Workbook(); ws = wb.active; ws.title = "Sélection"
            generer_feuille_simple(ws, data)
            return wb

    _Cat.__name__ = cat_id
    return _Cat


# Nationalité française obligatoire pour toutes les catégories ci-dessous
# (confirmé règlement FFE — Seniors + Vétérans V1/V2/V3/V4)
Seniors = _make_seniors_class("Seniors", "Seniors",            ["Championnat de France"], True)
V1      = _make_seniors_class("V1",      "Vétérans V1",        ["Championnat de France"], True)
V2      = _make_seniors_class("V2",      "Vétérans V2",        ["Championnat de France"], True)
V3      = _make_seniors_class("V3",      "Grands Vétérans V3", ["Championnat de France"], True)
V4      = _make_seniors_class("V4",      "Grands Vétérans V4", ["Championnat de France"], True)
