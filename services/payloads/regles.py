"""
services/payloads/regles.py — Garde-fou de VALIDATION des payloads
avant envoi à la plateforme (objectif zéro erreur).

Chaque famille d'export a une règle : format, armes autorisées, genres
autorisés, motifs de sections attendues. Un payload qui ne colle pas
aux règles est REJETÉ avant l'appel réseau, avec le détail des écarts.
"""
import re


class ValidationPayloadError(ValueError):
    """Payload non conforme aux règles de sa famille."""


# (regex de section autorisée). Les labels de section sont ceux produits
# par les builders (veterans.py / sabre_laser.py).
REGLES = {
    "vet_indiv_epee": {
        "format": "individuel",
        "armes":  {"epee"},
        "genres": {"H", "D"},
        "sections": [
            r"^N1 FFE — V[1-3]$",
            r"^Quota LREGE( \((national|régional)\))? — V[1-3]$",
            r"^Remplaçants — V[1-3]$",
            r"^Open \(référence\) — V[1-4]$",
        ],
        # Un tireur ne peut apparaître qu'une fois (nom+prénom+genre)
        "unicite_tireur": True,
    },
    "vet_indiv_fs": {
        "format": "individuel",
        "armes":  {"fleuret", "sabre"},
        "genres": {"H", "D"},
        "sections": [r"^Open \(référence\) — V[1-4]$"],
        "unicite_tireur": False,   # un vétéran peut figurer dans 2 cats ? non,
                                   # mais listes de référence : tolérance
    },
    "vet_equipes_epee": {
        "format": "equipe",
        "armes":  {"epee"},
        "genres": {"H", "D"},
        "sections": [r"^N1/N2$", r"^N3$", r"^Remplaçant$"],
        "unicite_tireur": False,   # une équipe peut être N1/N2 ET N3 (réel)
    },
    "sl_cs": {
        "format": "individuel",
        "armes":  {"sabre laser"},
        "genres": {""},
        "sections": [
            r"^QUALIFIÉS — LISTE NATIONALE FFE$",
            r"^QUOTA RÉGIONAL — \d+ PLACES?$",
            r"^REMPLAÇANTS$",
        ],
        "unicite_tireur": True,
    },
    "sl_et": {
        "format": "individuel",
        "armes":  {"sabre laser"},
        "genres": {""},
        "sections": [
            r"^SÉLECTIONNÉS — \d+ PLACES? \(QUOTA GE\)$",
            r"^REMPLAÇANTS$",
        ],
        "unicite_tireur": True,
    },
    "sl_chore": {
        "format": "individuel",
        "armes":  {"sabre laser"},
        "genres": {""},
        "sections": [
            r"^(DUEL|BATAILLE|ENSEMBLE) — \d+ GROUPES?$",
            r"^REMPLAÇANTS (DUEL|BATAILLE|ENSEMBLE)$",
        ],
        "unicite_tireur": False,   # nom = participants du groupe
    },
}


def valider_payload(payload, regle_id):
    """Vérifie un payload contre sa règle. Lève ValidationPayloadError
    (message multi-lignes) si non conforme. Retourne payload si OK."""
    if regle_id not in REGLES:
        raise ValidationPayloadError(f"Règle inconnue : {regle_id}")
    regle = REGLES[regle_id]
    erreurs = []

    comp = payload.get("competition") or {}
    quals = payload.get("qualifies") or []

    # -- Bloc competition ------------------------------------------------
    if comp.get("format") != regle["format"]:
        erreurs.append(f"format={comp.get('format')!r}, attendu {regle['format']!r}")
    if comp.get("arme") not in regle["armes"]:
        erreurs.append(f"arme={comp.get('arme')!r}, attendu {sorted(regle['armes'])}")
    if not comp.get("nom"):
        erreurs.append("competition.nom vide")

    # -- Qualifiés -------------------------------------------------------
    if not quals:
        erreurs.append("aucun qualifié dans le payload")

    sections_re = [re.compile(p) for p in regle["sections"]]
    vus = set()
    for i, q in enumerate(quals):
        ident = f"qualifie[{i}] ({q.get('nom','?')})"
        if not (q.get("nom") or "").strip():
            erreurs.append(f"{ident} : nom vide")
        g = q.get("genre", "")
        if g not in regle["genres"]:
            erreurs.append(f"{ident} : genre={g!r}, attendu {sorted(regle['genres'])}")
        sec = q.get("section") or ""
        if not any(r.match(sec) for r in sections_re):
            erreurs.append(f"{ident} : section inattendue {sec!r}")
        if regle["unicite_tireur"]:
            cle = (q.get("nom", "").upper(), q.get("prenom", "").upper(), g)
            if cle in vus:
                erreurs.append(f"{ident} : doublon nom+prénom+genre")
            vus.add(cle)

    if erreurs:
        raise ValidationPayloadError(
            "Payload non conforme ({}) :\n  - ".format(regle_id)
            + "\n  - ".join(erreurs[:20])
            + ("" if len(erreurs) <= 20 else f"\n  … +{len(erreurs)-20} autres")
        )
    return payload
