"""
services/payloads/sabre_laser.py — Payloads plateforme SABRE LASER.

Les `construire_selection_sl/et/chore` retournent déjà {"meta","sections"}
(même forme que l'individuel générique) : sérialisation directe, sans
parsing du classeur (décision 2026-07-03).

4 compétitions DISTINCTES : CS Seniors, CS M17, ET Seniors, Chorégraphie.
arme = "sabre laser" (libre), genre = "" (mixte, pas de H/D).
Chorégraphie : 1 groupe = 1 ligne qualifie (participants dans `nom`),
sous-épreuves Duel/Bataille/Ensemble portées par la section.
"""
from services.export_plateforme import (
    _rang_int, _rang_label, _competition_dict, _iter_tireurs,
)

# disc_id -> (categorie plateforme, règle de validation)
_DISC_INFO = {
    "combat_sportif_senior": ("Seniors", "sl_cs"),
    "combat_sportif_m17":    ("M17",     "sl_cs"),
    "epreuve_technique":     ("Seniors", "sl_et"),
    "combat_choregraphie":   ("Seniors", "sl_chore"),
}


def regle_sl(disc_id):
    """Id de règle de validation pour une discipline SL."""
    return _DISC_INFO.get(disc_id, (None, "sl_cs"))[1]


def construire_payload_sabre_laser(params, data, disc_id):
    """Payload d'UNE compétition SL depuis data = construire_selection_*.

    params : dict UI (peut surcharger competition/categorie) ;
    data   : {"meta", "sections"} ; disc_id : id discipline SL.
    """
    meta = data.get("meta", {})
    categorie, _ = _DISC_INFO.get(disc_id, ("Seniors", "sl_cs"))

    competition = _competition_dict(
        {**meta, "cat_id": ""},               # cat_id 'laser' non parlant
        {**params, "arme_id": "sabre laser"},  # hors ARME_LABEL -> conservé
        "individuel", "", categorie_defaut=categorie)
    competition["categorie"] = params.get("categorie") or categorie

    qualifies = []
    for label, t in _iter_tireurs(data.get("sections", [])):
        nom = (t.get("nom") or "").strip()
        if not nom:
            continue
        qualifies.append({
            "nom":        nom,
            "prenom":     (t.get("prenom") or "").strip(),
            "club":       (t.get("club") or "").strip(),
            "section":    label,
            "rang":       _rang_int(t.get("rang")),
            "rang_label": _rang_label(t.get("rang")),
            "equipe":     None,
            "genre":      "",
        })
    return {"competition": competition, "qualifies": qualifies}
