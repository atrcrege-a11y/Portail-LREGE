"""
services/export_plateforme.py — Pont SelecGE → Plateforme de confirmation.

Sérialise la structure interne (`construire_selection` pour l'individuel,
`construire_equipes_m15` pour les équipes M15) vers le contrat
`POST /api/import` de la plateforme, PUIS envoie le payload (token machine
dans l'URL). Le fichier Excel reste généré en parallèle.

Contrat plateforme (cf. import_selecge.py côté plateforme) :
    {
      "competition": {nom, categorie, format, arme, genre, date, lieu,
                      date_limite, arbitres_requis, type_arbitrage,
                      seuil1, seuil2, source_arbitres},
      "qualifies":   [{nom, prenom, club, section, rang, rang_label, equipe, genre}]
    }

Individuel : format='individuel', equipe=None.
Équipes M15 : format='equipe', equipe = libellé d'équipe + genre.
Équipes séniors : format='equipe', equipe = "<division> — <genre>".
`rang` = entier (tri) ; `rang_label` = chaîne brute "CL NAT 24" / "CL GE 3"
(préfixe conservé pour affichage). `genre` = 'H'|'D' par tireur (onglets H/D).
"""
import json
import os
import re
import urllib.request
import urllib.error

from crege_app.core.arbitrage import export_arbitrage_json

ARME_LABEL = {"E": "epee", "F": "fleuret", "S": "sabre"}
GENRE_LABEL = {"H": "Hommes", "D": "Dames"}


def _rang_int(rang_str):
    """'CL NAT 24' / 'CL GE 3' -> 24 / 3 ; None si pas de nombre."""
    m = re.search(r"(\d+)", str(rang_str or ""))
    return int(m.group(1)) if m else None


def _rang_label(rang_str):
    """Chaîne de rang brute (préfixe CL NAT/GE conservé) ; None si vide."""
    return (str(rang_str).strip() if rang_str not in (None, "") else None)


def _genre_des_donnees(data_h, data_d):
    """Liste [(genre, data)] des genres présents, et la chaîne genre globale."""
    presents = [(g, d) for g, d in (("H", data_h), ("D", data_d)) if d]
    genre = "HD" if len(presents) == 2 else (presents[0][0] if presents else "")
    return presents, genre


def _competition_dict(meta, params, fmt, genre, categorie_defaut=""):
    """Bloc competition commun (individuel + équipes)."""
    arme_id = params.get("arme_id") or params.get("arme") or ""
    arb = export_arbitrage_json(meta.get("arbitrage_config", {}))
    seuils = arb.get("seuils", {})
    categorie = meta.get("cat_id") or params.get("cat_id") or params.get("cat") or categorie_defaut
    return {
        "nom":             meta.get("competition", ""),
        "categorie":       categorie,
        "format":          fmt,
        "arme":            ARME_LABEL.get(arme_id, arme_id),
        "genre":           genre,
        "date":            meta.get("date", ""),
        "lieu":            meta.get("lieu", ""),
        "date_limite":     meta.get("date_limite_retour", ""),
        "arbitres_requis": 1 if arb.get("arbitres_requis") else 0,
        "type_arbitrage":  arb.get("type_arbitrage", "none"),
        "seuil1":          int(seuils.get("seuil1", 4)),
        "seuil2":          int(seuils.get("seuil2", 9)),
        "source_arbitres": arb.get("source", "aucun"),
    }


def _iter_tireurs(sections):
    """Aplati sections + sous_sections en (label_section, tireur)."""
    for sec in sections or []:
        label = sec.get("label", "")
        for t in sec.get("tireurs", []) or []:
            yield label, t
        for sous in sec.get("sous_sections", []) or []:
            for t in sous.get("tireurs", []) or []:
                yield label, t


def construire_payload(params, data_h, data_d):
    """Payload INDIVIDUEL depuis params + data_h/data_d (construire_selection)."""
    presents, genre = _genre_des_donnees(data_h, data_d)
    if not presents:
        raise ValueError("Aucune donnée à exporter (data_h et data_d vides)")

    meta = presents[0][1].get("meta", {})
    competition = _competition_dict(meta, params, "individuel", genre)

    qualifies = []
    for g, data in presents:
        for label, t in _iter_tireurs(data.get("sections", [])):
            nom = (t.get("nom") or "").strip()
            if not nom:
                continue
            qualifies.append({
                "nom":     nom,
                "prenom":  (t.get("prenom") or "").strip(),
                "club":    (t.get("club") or "").strip(),
                "section": label,
                "rang":    _rang_int(t.get("rang")),
                "rang_label": _rang_label(t.get("rang")),
                "equipe":  None,
                "genre":   g,
            })
    return {"competition": competition, "qualifies": qualifies}


def construire_payload_equipes_m15(params, data_h, data_d):
    """Payload ÉQUIPES M15 depuis params + data_h/data_d (construire_equipes_m15).

    Une compétition (format=equipe, genre HD si 2 genres). Chaque tireur porte
    son équipe = libellé + genre (les équipes H et D sont distinctes), avec
    section 'Titulaire' ou 'Remplaçant'.
    """
    presents, genre = _genre_des_donnees(data_h, data_d)
    if not presents:
        raise ValueError("Aucune donnée à exporter (data_h et data_d vides)")

    meta = presents[0][1].get("meta", {})
    competition = _competition_dict(meta, params, "equipe", genre, categorie_defaut="M15")

    qualifies = []
    for g, data in presents:
        suffixe = GENRE_LABEL.get(g, g)
        for eq in data.get("equipes", []) or []:
            equipe_nom = f"{eq.get('label', 'Equipe')} — {suffixe}"
            for t in eq.get("tireurs", []) or []:
                nom = (t.get("nom") or "").strip()
                if not nom:
                    continue
                qualifies.append({
                    "nom":     nom,
                    "prenom":  (t.get("prenom") or "").strip(),
                    "club":    (t.get("club") or "").strip(),
                    "section": "Titulaire",
                    "rang":    _rang_int(t.get("rang")),
                    "rang_label": _rang_label(t.get("rang")),
                    "equipe":  equipe_nom,
                    "genre":   g,
                })
        for t in data.get("remplacants", []) or []:
            nom = (t.get("nom") or "").strip()
            if not nom:
                continue
            qualifies.append({
                "nom":     nom,
                "prenom":  (t.get("prenom") or "").strip(),
                "club":    (t.get("club") or "").strip(),
                "section": "Remplaçant",
                "rang":    _rang_int(t.get("rang")),
                "rang_label": _rang_label(t.get("rang")),
                "equipe":  f"Remplaçants — {suffixe}",
                "genre":   g,
            })
    return {"competition": competition, "qualifies": qualifies}


def construire_payload_equipes_seniors(params, data):
    """Payload ÉQUIPES SÉNIORS (M17→Vétérans) depuis `data` (construire_equipes_seniors).

    Une compétition (format=equipe, genre HD si 2 genres). Chaque ÉQUIPE devient
    une ligne `qualifie` :
        - nom     = nom de l'équipe (colonne « Tireur » du mail/dashboard),
        - section = division (N1/N2/N3 FFE/N3/Remplaçant) — colonne « Section »,
        - equipe  = "<division> — <genre>" pour que la DIVISION ressorte dans le
                    mail de confirmation (qui affiche `equipe` en priorité).
    Les listes sont déjà filtrées (équipes sans nom ignorées) côté route.
    """
    meta = data.get("meta", {})

    # (gabarit de clé dans `data`, label division). {g}=h/d, {G}=H/D.
    DIVISIONS = [
        ("equipes_n1n2_{g}",   "N1"),
        ("equipes_n2_{G}",     "N2"),
        ("equipes_n3_ffe_{g}", "N3 FFE"),
        ("equipes_n3_{g}",     "N3"),
        ("remplacants_{g}",    "Remplaçant"),
    ]

    qualifies = []
    genres_presents = []
    for g in ("h", "d"):
        G = g.upper()
        genre_label = GENRE_LABEL.get(G, G)
        present = False
        for gabarit, division in DIVISIONS:
            for eq in data.get(gabarit.format(g=g, G=G), []) or []:
                nom_eq = (eq.get("nom_equipe") or "").strip()
                if not nom_eq:
                    continue
                present = True
                qualifies.append({
                    "nom":     nom_eq,
                    "prenom":  "",
                    "club":    (eq.get("club") or "").strip(),
                    "section": division,
                    "rang":    _rang_int(eq.get("rang")),
                    "rang_label": _rang_label(eq.get("rang")),
                    "equipe":  f"{division} — {genre_label}",
                    "genre":   G,
                })
        if present:
            genres_presents.append(G)

    genre = ("HD" if len(genres_presents) == 2
             else (genres_presents[0] if genres_presents else ""))
    competition = _competition_dict(meta, params, "equipe", genre,
                                    categorie_defaut="Seniors")
    return {"competition": competition, "qualifies": qualifies}


# -- Envoi réseau ------------------------------------------------------

def _base_url():
    return os.environ.get("PLATEFORME_URL", "").rstrip("/")


def _token():
    return os.environ.get("PLATEFORME_TOKEN", "")


def envoyer_payload(payload, url_base=None, token=None, timeout=20):
    """POST le payload vers {url_base}/api/import/{token}.

    Retourne (ok: bool, status: int, body: dict|str). Ne lève pas sur erreur
    HTTP : renvoie le détail pour affichage côté UI.
    """
    url_base = (url_base if url_base is not None else _base_url()).rstrip("/")
    token = token if token is not None else _token()
    if not url_base or not token:
        return False, 0, "PLATEFORME_URL ou PLATEFORME_TOKEN non configuré"

    url = f"{url_base}/api/import/{token}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                body = json.loads(raw)
            except ValueError:
                body = raw
            return True, resp.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            body = json.loads(raw)
        except ValueError:
            body = raw
        return False, e.code, body
    except urllib.error.URLError as e:
        return False, 0, f"Connexion impossible : {e.reason}"
