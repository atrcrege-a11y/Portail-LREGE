"""
core/parser.py
Parsing des fichiers XML Engarde et construction des structures de données.
Indépendant de tout type de compétition.
"""

import datetime
from collections import defaultdict
from .config import JOURS_SEMAINE


# ── Helpers dates

def parse_date_key(d):
    try:
        j, m, a = d.split(".")
        return (int(a), int(m), int(j))
    except Exception:
        return (0, 0, 0)


def date_avec_jour(d):
    try:
        j, m, a = d.split(".")
        dt = datetime.date(int(a), int(m), int(j))
        return f"{JOURS_SEMAINE[dt.weekday()]} {d}"
    except Exception:
        return d


# ── Parsing XML

def parse_xml(content_bytes, filename=""):
    """
    Parse un fichier XML Engarde.
    Retourne (meta, tireurs, arbitres).
    ET.fromstring(bytes) respecte l'encodage ISO-8859-1 déclaré
    et retourne des str Python unicode — pas besoin de ré-encoder.
    """
    import xml.etree.ElementTree as ET

    root = ET.fromstring(content_bytes)

    ARME = {"F": "Fleuret", "E": "Épée", "S": "Sabre"}
    SEXE = {"M": "Hommes", "F": "Dames", "MF": "Mixte"}

    def g(node, k, default=""):
        return node.attrib.get(k, default)

    meta = {
        "arme":        g(root, "Arme", "?"),
        "arme_label":  ARME.get(g(root, "Arme", "?"), "?"),
        "categorie":   g(root, "Categorie", "?").upper(),
        "sexe":        g(root, "Sexe", "?"),
        "sexe_label":  SEXE.get(g(root, "Sexe", "?"), "?"),
        "titre":       g(root, "TitreLong"),
        "date":        g(root, "Date"),
        "date_debut":  g(root, "DateDebut") or g(root, "Date"),
        "date_fin":    g(root, "DateFin")   or g(root, "Date"),
        "id":          g(root, "ID"),
        "type":        g(root, "Type", "I"),   # I=individuel, E=équipe
        "filename":    filename,
    }

    tireurs = []
    for t in root.iter("Tireur"):
        tireurs.append({
            "nom":       g(t, "Nom"),
            "prenom":    g(t, "Prenom"),
            "licence":   g(t, "Licence"),
            "club":      g(t, "Club"),
            "equipe":    g(t, "Equipe"),
            "region":    g(t, "Region"),
            "ligue":     g(t, "Ligue"),
            "dept":      g(t, "Departement"),
            "sexe":      g(t, "Sexe"),
            "naissance": g(t, "DateNaissance"),
        })

    arbitres = []
    for a in root.iter("Arbitre"):
        arbitres.append({
            "nom":       g(a, "Nom"),
            "prenom":    g(a, "Prenom"),
            "licence":   g(a, "Licence"),
            "club":      g(a, "Club"),
            "region":    g(a, "Region"),
            "ligue":     g(a, "Ligue"),
            "dept":      g(a, "Departement"),
            "categorie": g(a, "Categorie"),   # niveau arbitre : D, FD, R, FR...
        })

    return meta, tireurs, arbitres


# ── Construction des données agrégées

def construire_donnees(fichiers_list, cat_map_indiv, cat_map_equipe, par_arme=False):
    """
    Agrège les données de tous les fichiers XML.

    Paramètres :
      fichiers_list  : [(meta, tireurs, arbitres), ...]
      cat_map_indiv  : {cat_xml: cat_key} pour individuel
      cat_map_equipe : {cat_xml: cat_key} pour équipe
      par_arme       : si True, la cat_key devient "CAT|ARME" (ex: "M9|F")

    Retourne :
      groupes_indiv   : {date: {cat: {club: {"H": n, "D": n}}}}
      groupes_equipe  : {date: {cat: {club: {"equipes": set, "tireurs_H": n, "tireurs_D": n}}}}
      arbitres_all    : [arbitre enrichi avec date_source]
      titre           : str (premier TitreLong trouvé)
      ligue_info      : {club: {region, ligue, dept}}
      plage_dates     : str formatée (ex: "samedi 30.03.2024 au dimanche 31.03.2024")
      dates_ordonnees : [date_str, ...] triées
    """
    groupes_indiv  = defaultdict(lambda: defaultdict(
        lambda: defaultdict(lambda: {"H": 0, "D": 0})
    ))
    groupes_equipe = defaultdict(lambda: defaultdict(
        lambda: defaultdict(lambda: {"equipes": set(), "tireurs_H": 0, "tireurs_D": 0})
    ))

    ligue_info   = {}
    arbitres_all = []
    titre        = ""
    toutes_dates = set()

    for meta, tireurs, arbitres in fichiers_list:
        if not titre and meta.get("titre"):
            titre = meta["titre"]

        cat_raw   = meta["categorie"].upper()
        type_comp = meta["type"]
        date_src  = meta.get("date_debut") or meta.get("date", "")

        if date_src:
            toutes_dates.add(date_src)

        # Choisir le mapping selon le type
        cat_key = (cat_map_equipe if type_comp == "E" else cat_map_indiv).get(cat_raw)
        if cat_key is None:
            continue

        # Mode par arme : enrichir la clé avec l'arme (ex: "M9|F")
        if par_arme:
            arme_code = meta.get("arme", "?")
            cat_key = f"{cat_key}|{arme_code}"

        for t in tireurs:
            club  = t["club"].strip()
            sexe  = "H" if t["sexe"].upper() == "M" else "D"
            equipe = t["equipe"].strip()

            if club not in ligue_info:
                ligue_info[club] = {
                    "region": t["region"],
                    "ligue":  t["ligue"],
                    "dept":   t["dept"],
                }

            if type_comp == "E":
                g = groupes_equipe[date_src][cat_key][club]
                if equipe:
                    g["equipes"].add(equipe)
                # Détecter si l'épreuve est mixte (sexe MF au niveau du fichier)
                sexe_epreuve = meta.get("sexe", "").upper()
                if sexe_epreuve == "MF":
                    g["mixte"] = True
                    g["tireurs_MX"] = g.get("tireurs_MX", 0) + 1
                elif sexe == "H":
                    g["tireurs_H"] += 1
                else:
                    g["tireurs_D"] += 1
            else:
                g = groupes_indiv[date_src][cat_key][club]
                g[sexe] += 1

        for a in arbitres:
            club = a["club"].strip()
            arbitres_all.append({
                **a,
                "arme":        meta.get("arme", "?"),
                "arme_label":  meta.get("arme_label", "?"),
                "cat_comp":    cat_raw,
                "type_comp":   type_comp,
                "date_source": date_src,
            })
            if club not in ligue_info:
                ligue_info[club] = {
                    "region": a["region"],
                    "ligue":  a["ligue"],
                    "dept":   a["dept"],
                }

    dates_ordonnees = sorted(toutes_dates, key=parse_date_key)

    if dates_ordonnees:
        d_min, d_max = dates_ordonnees[0], dates_ordonnees[-1]
        plage_dates = (
            date_avec_jour(d_min) if d_min == d_max
            else f"{date_avec_jour(d_min)} au {date_avec_jour(d_max)}"
        )
    else:
        plage_dates = ""

    return (groupes_indiv, groupes_equipe, arbitres_all,
            titre, ligue_info, plage_dates, dates_ordonnees)
