"""
services/payloads/veterans.py — Payloads plateforme VÉTÉRANS.

Source unique = le classeur Excel généré par les générateurs existants
(crege_app/generateur/indiv_veterans*.py, equipes_veterans.py), généré
en mémoire puis parsé (parse_workbook). La catégorie V est portée par le
label de section (ex. « N1 FFE — V1 ») : 1 compétition par famille.

Familles :
  - indiv épée   : 8 feuilles V1-V4 × H/D (H V1-V3 = N1 FFE + quota +
                   remplaçants ; D et V4 = open, liste de référence)
  - indiv F/S    : open, liste de référence (décision 2026-07-03 : envoyée)
  - équipes épée : N1/N2 + N3 par feuille EH/ED × V1-V2/V3-V4
  - équipes F/S  : open placeholders vides → PAS d'export (rien d'envoyable)
"""
import re
import unicodedata

from services.export_plateforme import (
    _rang_int, _rang_label, _competition_dict, GENRE_LABEL,
)
from .parse_workbook import parse_workbook


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


# ── Feuilles individuelles : "Homme Veteran 1" / "Dame Grand Vétéran" ──

_RE_FEUILLE_INDIV = re.compile(
    r"^(HOMME|DAME)S?\s+(GRAND\s+)?VETERANE?\s*(\d)?", re.IGNORECASE)


def _genre_cat_feuille_indiv(nom_feuille):
    """'Homme Veteran 2' -> ('H','V2') ; 'Dame Grand Vétéran' -> ('D','V4')."""
    m = _RE_FEUILLE_INDIV.match(_norm(nom_feuille))
    if not m:
        return None, None
    genre = "H" if m.group(1) == "HOMME" else "D"
    if m.group(3):
        cat = f"V{m.group(3)}"
    elif m.group(2):          # "Grand Vétéran" sans numéro = V4
        cat = "V4"
    else:
        return genre, None
    return genre, cat


def _section_canonique_indiv(label_brut, cat):
    """Label de section parsé -> label canonique payload (cat portée)."""
    n = _norm(label_brut)
    if n.startswith("TIREURS QUALIFIES") and "N1" in n:
        return f"N1 FFE — {cat}"
    if "SUR CLASSEMENT NATIONAL" in n:
        return f"Quota LREGE (national) — {cat}"
    if "SUR CLASSEMENT REGIONAL" in n:
        return f"Quota LREGE (régional) — {cat}"
    if n.startswith("TIREURS QUALIFIES") and "QUOTA" in n:
        return f"Quota LREGE — {cat}"
    if n.startswith("TIREURS REMPLACANTS"):
        return f"Remplaçants — {cat}"
    if (n.startswith("TIREURS GRAND EST") or n.startswith("TIREUSES GRAND EST")
            or n.startswith("EPREUVE OPEN")):
        return f"Open (référence) — {cat}"
    return None    # section inconnue → rejetée par la validation


def _payload_indiv(params, wb, meta, arme_defaut):
    """Cœur commun indiv épée / indiv F/S."""
    feuilles = parse_workbook(wb)
    qualifies = []
    genres_presents = set()
    inconnues = []

    for nom_feuille, sections in feuilles.items():
        genre, cat = _genre_cat_feuille_indiv(nom_feuille)
        if genre is None or cat is None:
            inconnues.append(f"feuille non reconnue : {nom_feuille!r}")
            continue
        for sec in sections:
            if not sec["rows"]:
                continue           # bandeau open sans liste, quota vide…
            canon = _section_canonique_indiv(sec["label"], cat)
            if canon is None:
                inconnues.append(
                    f"section non reconnue ({nom_feuille}) : {sec['label']!r}")
                continue
            for r in sec["rows"]:
                rang_brut = r.get("rang", "")
                qualifies.append({
                    "nom":        r["nom"].strip(),
                    "prenom":     (r.get("prenom") or "").strip(),
                    "club":       (r.get("club") or "").strip(),
                    "section":    canon,
                    "rang":       _rang_int(rang_brut),
                    "rang_label": _rang_label(rang_brut),
                    "equipe":     None,
                    "genre":      genre,
                })
            genres_presents.add(genre)

    if inconnues:
        raise ValueError("Classeur vétérans : " + " ; ".join(inconnues))

    genre_comp = ("HD" if genres_presents == {"H", "D"}
                  else "".join(sorted(genres_presents)))
    competition = _competition_dict(
        meta, {**params, "arme_id": params.get("arme_id", arme_defaut)},
        "individuel", genre_comp, categorie_defaut="Vétérans")
    return {"competition": competition, "qualifies": qualifies}


def construire_payload_indiv_veterans(params, wb, meta):
    """Payload INDIV VÉTÉRANS ÉPÉE depuis le Workbook généré + meta
    (meta = data['meta'] passé au générateur, même source que l'Excel)."""
    return _payload_indiv(params, wb, meta, "E")


def construire_payload_indiv_veterans_fs(params, wb, meta, arme):
    """Payload INDIV VÉTÉRANS FLEURET/SABRE (listes open de référence)."""
    return _payload_indiv({**params, "arme_id": arme}, wb, meta, arme)


# ── Équipes épée ──────────────────────────────────────────────────────

_RE_FEUILLE_EQ = re.compile(r"^E(H|D)\s+(GRANDS?\s+)?VETERANS?", re.IGNORECASE)


def _genre_groupe_feuille_eq(nom_feuille):
    """'EH Vétérans (V1-V2)' -> ('H','V1-V2') ; 'ED Grands Vétérans (V3-V4)'
    -> ('D','V3-V4')."""
    n = _norm(nom_feuille)
    m = _RE_FEUILLE_EQ.match(n)
    if not m:
        return None, None
    genre = m.group(1)
    groupe = "V3-V4" if (m.group(2) or "V3" in n) else "V1-V2"
    return genre, groupe


def construire_payload_equipes_veterans(params, wb, meta):
    """Payload ÉQUIPES VÉTÉRANS ÉPÉE. Une ligne qualifie par ÉQUIPE
    (motif identique aux équipes séniors : section = division, equipe =
    « division — genre groupe » pour l'affichage mail/dashboard)."""
    feuilles = parse_workbook(wb)
    qualifies = []
    genres_presents = set()
    inconnues = []

    for nom_feuille, sections in feuilles.items():
        genre, groupe = _genre_groupe_feuille_eq(nom_feuille)
        if genre is None:
            inconnues.append(f"feuille non reconnue : {nom_feuille!r}")
            continue
        genre_label = GENRE_LABEL.get(genre, genre)
        for sec in sections:
            if not sec["rows"]:
                continue                      # section open EDGV, quota vide
            n = _norm(sec["label"])
            if "N1/N2" in n:
                division = "N1/N2"
            elif "N3" in n:
                division = "N3"
            elif "REMPLACANTE" in n or "REMPLACANT" in n:
                division = "Remplaçant"
            elif n.startswith("EPREUVE OPEN") or "OPEN" in n:
                continue                      # open : rien d'envoyable
            else:
                inconnues.append(
                    f"section non reconnue ({nom_feuille}) : {sec['label']!r}")
                continue
            for r in sec["rows"]:
                nom_eq = r["nom_equipe"].strip()
                if not nom_eq:
                    continue
                qualifies.append({
                    "nom":        nom_eq,
                    "prenom":     "",
                    "club":       (r.get("club") or "").strip(),
                    "section":    division,
                    "rang":       _rang_int(r.get("rang")),
                    "rang_label": _rang_label(r.get("rang")),
                    "equipe":     f"{division} — {genre_label} {groupe}",
                    "genre":      genre,
                })
            genres_presents.add(genre)

    if inconnues:
        raise ValueError("Classeur équipes vétérans : " + " ; ".join(inconnues))

    genre_comp = ("HD" if genres_presents == {"H", "D"}
                  else "".join(sorted(genres_presents)))
    competition = _competition_dict(
        meta, {**params, "arme_id": params.get("arme_id", "E")},
        "equipe", genre_comp, categorie_defaut="Vétérans")
    return {"competition": competition, "qualifies": qualifies}
