"""
selection.py — Logique de sélection Master Grand Est M11/M13
"""

SEUIL_PARTICIPATIONS = 3
NB_SELECTIONNES_PAR_TERRITOIRE = 5


def _cle_tireur(t):
    return (t["nom"].strip().upper(), t["prenom"].strip().upper())


def enrichir_alertes_m11(selection_m13, tireurs_m11):
    cles_m11 = {_cle_tireur(t) for t in tireurs_m11}
    for t in selection_m13["tireurs"]:
        # Présence dans le classement M11 = double qualification (vérité terrain),
        # indépendamment de l'année de naissance lue dans le fichier M13.
        if _cle_tireur(t) in cles_m11:
            t["alerte_m11"] = "double"
        elif t.get("est_m11_dans_m13"):
            # M11 par l'âge mais classé en M13 uniquement.
            t["alerte_m11"] = "m13only"
        else:
            t["alerte_m11"] = None
    return selection_m13


def calculer_selection(donnees, bonus_organisateur=False):
    """
    bonus_organisateur : booléen choisi par l'utilisateur dans l'interface.
    """
    arme = donnees.get("arme", "")
    condition_participations = arme in ("Épée", "Fleuret")
    quota = NB_SELECTIONNES_PAR_TERRITOIRE + (1 if bonus_organisateur else 0)

    selectionnables = []
    non_selectionnables = []
    for t in donnees["tireurs"]:
        if condition_participations and t["participations"] < SEUIL_PARTICIPATIONS:
            non_selectionnables.append({
                **t,
                "statut": "non_selectionnable",
                "raison": f"{t['participations']}/3 épreuve(s)",
                "alerte_m11": None,
            })
        else:
            selectionnables.append(t)

    resultats = []
    for i, t in enumerate(selectionnables):
        statut = "selectionne" if i < quota else "remplacant"
        resultats.append({**t, "statut": statut, "raison": "", "alerte_m11": None})

    resultats.extend(non_selectionnables)

    return {
        **donnees,
        "bonus_organisateur": bonus_organisateur,
        "quota": quota,
        "condition_participations": condition_participations,
        "tireurs": resultats,
    }
