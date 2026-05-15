"""
sabre_laser/selection.py — Construction des sections de sélection Sabre Laser.

Logique : mixte, quota unique, pas de N1/N2/N3, pas de Wild Cards.
Sections :
  1. QUALIFIÉS NATIONAUX  — tireurs GE dans la liste FFE qualifiés CDF
  2. QUOTA RÉGIONAL       — tireurs GE du classement régional (hors déjà qualifiés)
  3. REMPLAÇANTS          — tireurs suivants au classement régional
"""
import pandas as pd
from .config import (
    COL_RANG, COL_NOM, COL_PRENOM, COL_ADHERENT,
    COL_REGION, COL_CLUB, COL_GRAND_EST, COL_NOTE,
    COL_PARTICIPANTS, COL_SOUS_CAT,
    get_discipline, get_quota_ge, get_calendrier, get_niveau,
)


def _tireur_dict(row, rang_override=None) -> dict:
    return {
        "rang":   rang_override if rang_override is not None else int(row.get(COL_RANG, 0)),
        "nom":    str(row.get(COL_NOM, "")).upper().strip(),
        "prenom": str(row.get(COL_PRENOM, "")).strip(),
        "club":   str(row.get(COL_CLUB, "")).strip(),
        "note":   "",
    }


def construire_selection_sl(
    disc_id:        str,
    niveau_id:      str,
    df_national:    pd.DataFrame,   # liste FFE qualifiés (ou classement national)
    df_regional:    pd.DataFrame,   # classement régional GE
    df_demifin:     pd.DataFrame = None,  # classement demi-finale nationale (optionnel)
    quota_ge:       int = None,     # override du quota (sinon lu dans config)
    nb_remplacants: int = 5,
    date:           str = "",
    lieu:           str = "",
    competition:    str = "",
    mail_retour:    str = "administration@crege.fr",
    date_limite:    str = "",
    date_extranet:  str = "",
    arbitrage_config: dict = None,
) -> dict:
    """
    Construit les données de sélection pour une discipline/niveau Sabre Laser.
    Retourne un dict compatible avec le générateur Excel.
    """
    disc  = get_discipline(disc_id)
    quota = quota_ge if quota_ge is not None else get_quota_ge(disc_id, niveau_id)
    cal   = get_calendrier(disc_id, niveau_id)

    date = date or cal.get("date", "")
    lieu = lieu or cal.get("lieu", "")
    competition = competition or disc.get("label", "Sabre Laser")

    # ── Index demi-finale : nom_norm → rang ───────────────────────────
    def _norm_nom(s):
        import unicodedata as _u, re as _r
        s = _u.normalize("NFKD", str(s).upper()).encode("ascii", "ignore").decode()
        return _r.sub(r"[^A-Z]", "", s)

    _demifin_idx = {}   # (NOM_NORM, PRENOM_NORM) → rang
    _demifin_nom = {}   # NOM_NORM → rang (fallback)
    if df_demifin is not None and not df_demifin.empty:
        for _, row in df_demifin.iterrows():
            k  = (_norm_nom(row.get(COL_NOM, "")), _norm_nom(row.get(COL_PRENOM, "")))
            rg = int(row.get(COL_RANG, 0))
            if k[0] and rg:
                _demifin_idx[k] = rg
                _demifin_nom.setdefault(k[0], rg)

    def _rang_df(nom, prenom):
        k = (_norm_nom(nom), _norm_nom(prenom))
        return _demifin_idx.get(k) or _demifin_nom.get(k[0])

    # ── 1. Qualifiés nationaux : GE dans la liste FFE ─────────────────
    qualifies_ge   = []
    # Clés d'exclusion : adhérent (prioritaire) + nom/prénom normalisé (fallback)
    adherents_qualifies = set()
    noms_qualifies      = set()

    def _cle_nom(nom, prenom):
        """Clé de déduplication nom/prénom normalisée."""
        import unicodedata, re
        def norm(s):
            s = unicodedata.normalize("NFKD", str(s).upper()).encode("ascii", "ignore").decode()
            return re.sub(r"[^A-Z]", "", s)
        return (norm(nom), norm(prenom))

    def _deja_qualifie(row):
        """True si ce tireur est déjà dans la liste nationale.
        Tri-clé : adhérent (prioritaire) > nom+prénom normalisé > nom seul.
        """
        adh = str(row.get(COL_ADHERENT, "")).strip()
        if adh and adh not in ("", "nan") and adh in adherents_qualifies:
            return True
        nom    = str(row.get(COL_NOM, "")).strip()
        prenom = str(row.get(COL_PRENOM, "")).strip()
        # Clé nom+prénom normalisée
        cle_complete = _cle_nom(nom, prenom)
        if cle_complete in noms_qualifies:
            return True
        # Clé nom seul (fallback si prénom absent ou divergent)
        if prenom == "" or prenom == "nan":
            cle_nom_seul = _cle_nom(nom, "")
            if any(k[0] == cle_nom_seul[0] for k in noms_qualifies):
                return True
        return False

    if df_national is not None and not df_national.empty:
        ge_nat = df_national[df_national[COL_GRAND_EST] == True].copy()
        for rang_local, (_, row) in enumerate(ge_nat.iterrows(), 1):
            nom_t    = str(row.get(COL_NOM, "")).strip()
            prenom_t = str(row.get(COL_PRENOM, "")).strip()
            # Rang = position en demi-finale si disponible, sinon rang de la liste FFE
            rang_df = _rang_df(nom_t, prenom_t)
            rang_val = rang_df if rang_df else int(row.get(COL_RANG, rang_local))
            t = _tireur_dict(row, rang_override=rang_val)
            qualifies_ge.append(t)
            adh = str(row.get(COL_ADHERENT, "")).strip()
            if adh and adh not in ("", "nan"):
                adherents_qualifies.add(adh)
            noms_qualifies.add(_cle_nom(nom_t, prenom_t))
            noms_qualifies.add(_cle_nom(nom_t, ""))

        # Trier par rang demi-finale
        qualifies_ge.sort(key=lambda t: t["rang"] if isinstance(t["rang"], int) else 9999)

    # ── 2. Quota régional : classement régional GE (hors déjà qualifiés) ──
    quota_regional = []
    remplacants    = []

    if df_regional is not None and not df_regional.empty:
        ge_reg = df_regional[df_regional[COL_GRAND_EST] == True].copy()
        ge_reg = ge_reg.sort_values(COL_RANG).reset_index(drop=True)

        rang_reg = 0
        for _, row in ge_reg.iterrows():
            if _deja_qualifie(row):
                continue

            rang_reg += 1
            rang_brut = int(row.get(COL_RANG, rang_reg))
            t = _tireur_dict(row, rang_override=f"GE {rang_brut}")

            if rang_reg <= quota:
                quota_regional.append(t)
            elif rang_reg <= quota + nb_remplacants:
                t["note"] = f"Remplaçant {rang_reg - quota}"
                remplacants.append(t)
    sections = []

    from .config import get_palette
    pal = get_palette(disc_id)

    if qualifies_ge:
        sections.append({
            "label":   "QUALIFIÉS — LISTE NATIONALE FFE",
            "couleur": pal["section1"],
            "textes":  [f"{len(qualifies_ge)} tireur(s) Grand Est qualifié(s) via la liste FFE nationale"],
            "tireurs": qualifies_ge,
            "avec_participation": True,
        })

    if quota_regional:
        sections.append({
            "label":   f"QUOTA RÉGIONAL — {quota} PLACE{'S' if quota > 1 else ''}",
            "couleur": pal["section2"],
            "textes":  [f"Classement régional Grand Est — {quota} quota(s) LREGE"],
            "tireurs": quota_regional,
            "avec_participation": True,
        })
    elif quota > 0:
        sections.append({
            "label":   f"QUOTA RÉGIONAL — {quota} PLACE{'S' if quota > 1 else ''}",
            "couleur": pal["section2"],
            "textes":  ["Aucun classement régional chargé — quota non pourvu"],
            "tireurs": [],
            "avec_participation": False,
        })

    if remplacants:
        sections.append({
            "label":   "REMPLAÇANTS",
            "couleur": pal["section3"],
            "textes":  ["En attente selon désistements"],
            "tireurs": remplacants,
            "avec_participation": False,
        })

    # ── Métadonnées ───────────────────────────────────────────────────
    niveau_label = next(
        (n["label"] for n in disc.get("niveaux", []) if n["id"] == niveau_id),
        niveau_id
    )

    meta = {
        "region":                   "Grand Est",
        "cat_id":                   "laser",
        "cat_label":                disc.get("label_court", disc.get("label", "")),
        "competition":              competition,
        "discipline":               f"{disc['label']} — {niveau_label}",
        "date":                     date,
        "lieu":                     lieu,
        "mail_retour":              mail_retour,
        "date_limite_retour":       date_limite,
        "date_engagement_extranet": date_extranet,
        "arbitrage_config":         arbitrage_config or {},
        # Infos spécifiques SL
        "disc_id":                  disc_id,
        "niveau_id":                niveau_id,
        "quota_ge":                 quota,
        "nb_qualifies_national":    len(qualifies_ge),
        "nb_quota_regional":        len(quota_regional),
    }

    return {"meta": meta, "sections": sections}


# ── Sélection Épreuve Technique ───────────────────────────────────────

def construire_selection_et(
    disc_id:        str,
    niveau_id:      str,
    df_regional:    pd.DataFrame,
    quota_ge:       int = None,
    nb_remplacants: int = 5,
    date:           str = "",
    lieu:           str = "",
    competition:    str = "",
    mail_retour:    str = "administration@crege.fr",
    date_limite:    str = "",
    date_extranet:  str = "",
    arbitrage_config: dict = None,
) -> dict:
    """Sélection Épreuve Technique — classement régional GE, format texte."""
    from .config import get_palette
    disc   = get_discipline(disc_id)
    quota  = quota_ge if quota_ge is not None else get_quota_ge(disc_id, niveau_id)
    cal    = get_calendrier(disc_id, niveau_id)
    pal    = get_palette(disc_id)
    date   = date or cal.get("date", "")
    lieu   = lieu or cal.get("lieu", "")
    competition = competition or disc.get("label", "Épreuve Technique")

    tireurs_sel  = []
    remplacants  = []

    if df_regional is not None and not df_regional.empty:
        df_sorted = df_regional.sort_values(COL_RANG).reset_index(drop=True)
        for _, row in df_sorted.iterrows():
            rang  = int(row.get(COL_RANG, 0))
            if rang == 0:
                continue
            club  = str(row.get(COL_CLUB, "")).strip()
            score = str(row.get(COL_NOTE, "")).strip()
            t = {
                "rang":    rang,
                "nom":     str(row.get(COL_NOM, "")).strip(),
                "prenom":  str(row.get(COL_PRENOM, "")).strip(),
                "club":    club,
                "note":    "",        # col5 Participation : vide pour sélectionnés
                "note_extra": score,  # col6 Note : score
            }
            if rang <= quota:
                tireurs_sel.append(t)
            elif rang <= quota + nb_remplacants:
                t["note"] = f"Remplaçant {rang - quota}"
                t["note_extra"] = score
                remplacants.append(t)

    sections = []
    if tireurs_sel:
        sections.append({
            "label":   f"SÉLECTIONNÉS — {quota} PLACE{'S' if quota > 1 else ''} (QUOTA GE)",
            "couleur": pal["section1"],
            "textes":  [f"Classement régional Grand Est — Épreuve Technique"],
            "tireurs": tireurs_sel,
            "avec_participation": False,  # pas de col Participation pour ET
        })
    if remplacants:
        sections.append({
            "label":   "REMPLAÇANTS",
            "couleur": pal["section3"],
            "textes":  ["En attente selon désistements"],
            "tireurs": remplacants,
            "avec_participation": False,
        })

    niveau_label = next((n["label"] for n in disc.get("niveaux", []) if n["id"] == niveau_id), niveau_id)
    meta = {
        "region": "Grand Est", "cat_id": "laser",
        "cat_label": disc.get("label_court", ""),
        "competition": competition,
        "discipline": f"{disc['label']} — {niveau_label}",
        "date": date, "lieu": lieu,
        "mail_retour": mail_retour,
        "date_limite_retour": date_limite,
        "date_engagement_extranet": date_extranet,
        "arbitrage_config": arbitrage_config or {},
        "disc_id": disc_id, "niveau_id": niveau_id, "quota_ge": quota,
        "type": "et",
    }
    return {"meta": meta, "sections": sections}


# ── Sélection Chorégraphie ────────────────────────────────────────────

def construire_selection_chore(
    disc_id:         str,
    niveau_id:       str,
    df_regional:     pd.DataFrame,
    quota_ge:        int = None,
    quota_duel:      int = None,
    quota_bataille:  int = None,
    quota_ensemble:  int = None,
    nb_remplacants:  int = 3,
    date:            str = "",
    lieu:            str = "",
    competition:     str = "",
    mail_retour:     str = "administration@crege.fr",
    date_limite:     str = "",
    date_extranet:   str = "",
    arbitrage_config: dict = None,
) -> dict:
    """
    Sélection Chorégraphie — 3 sous-catégories (Duel, Bataille, Ensemble).
    quota_ge = total. quota_duel/bataille/ensemble = répartition (modifiable).
    Si non spécifiés → répartition auto proportionnelle.
    """
    from .config import get_palette
    disc  = get_discipline(disc_id)
    quota = quota_ge if quota_ge is not None else get_quota_ge(disc_id, niveau_id)
    cal   = get_calendrier(disc_id, niveau_id)
    pal   = get_palette(disc_id)
    date  = date or cal.get("date", "")
    lieu  = lieu or cal.get("lieu", "")
    competition = competition or disc.get("label", "Chorégraphie")

    # Répartition des quotas par sous-catégorie
    # Si non spécifiée → prendre autant que disponible jusqu'au quota total
    q_duel     = quota_duel     if quota_duel     is not None else quota
    q_bataille = quota_bataille if quota_bataille is not None else quota
    q_ensemble = quota_ensemble if quota_ensemble is not None else quota

    sections = []
    SOUS_CATS = [
        ("Duel",     q_duel,     pal["section1"]),
        ("Bataille", q_bataille, pal["section2"]),
        ("Ensemble", q_ensemble, pal["section3"]),
    ]

    total_selectionnes = 0

    if df_regional is not None and not df_regional.empty:
        for sc_nom, q_sc, couleur in SOUS_CATS:
            df_sc = df_regional[
                df_regional[COL_SOUS_CAT].str.lower() == sc_nom.lower()
            ].sort_values(COL_RANG).reset_index(drop=True)

            if df_sc.empty:
                continue

            # Quota restant global
            restant = quota - total_selectionnes
            q_effectif = min(q_sc, restant) if restant > 0 else 0

            groupes_sel  = []
            groupes_rem  = []

            for _, row in df_sc.iterrows():
                rang  = int(row.get(COL_RANG, 0))
                if rang == 0: continue
                score = str(row.get(COL_NOTE, "")).strip()
                g = {
                    "rang":       rang,
                    "nom":        str(row.get(COL_PARTICIPANTS, "")).strip(),
                    "prenom":     "",
                    "club":       str(row.get(COL_CLUB, "")).strip(),
                    "note":       "",       # vide pour sélectionnés → col5 = "Oui"
                    "note_extra": score,    # score en col6
                }
                if rang <= q_effectif:
                    groupes_sel.append(g)
                elif rang <= q_effectif + nb_remplacants:
                    g["note"] = f"Remplaçant {rang - q_effectif}"
                    groupes_rem.append(g)

            total_selectionnes += len(groupes_sel)

            if groupes_sel or q_effectif > 0:
                label_sel = f"{sc_nom.upper()} — {q_effectif} GROUPE{'S' if q_effectif > 1 else ''}"
                sections.append({
                    "label":   label_sel,
                    "couleur": couleur,
                    "textes":  [f"{sc_nom} : {len(groupes_sel)} groupe(s) sélectionné(s) sur {q_effectif} place(s)"],
                    "tireurs": groupes_sel,
                    "avec_participation": True,
                    "mode_groupe": True,
                })
                if groupes_rem:
                    sections.append({
                        "label":   f"REMPLAÇANTS {sc_nom.upper()}",
                        "couleur": pal["section3"],
                        "textes":  ["En attente selon désistements"],
                        "tireurs": groupes_rem,
                        "avec_participation": False,
                        "mode_groupe": True,
                    })

    niveau_label = next((n["label"] for n in disc.get("niveaux", []) if n["id"] == niveau_id), niveau_id)
    meta = {
        "region": "Grand Est", "cat_id": "laser",
        "cat_label": disc.get("label_court", ""),
        "competition": competition,
        "discipline": f"{disc['label']} — {niveau_label}",
        "date": date, "lieu": lieu,
        "mail_retour": mail_retour,
        "date_limite_retour": date_limite,
        "date_engagement_extranet": date_extranet,
        "arbitrage_config": arbitrage_config or {},
        "disc_id": disc_id, "niveau_id": niveau_id, "quota_ge": quota,
        "quota_duel": q_duel, "quota_bataille": q_bataille, "quota_ensemble": q_ensemble,
        "type": "chore",
    }
    return {"meta": meta, "sections": sections}
