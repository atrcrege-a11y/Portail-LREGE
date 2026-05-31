"""
core/bellepoule_fff.py — Conversion PDF BellePoule (individuel) → fichier .fff WIN/FFE.

Flux : PDF → pages texte → (en-tête, liste appel, classement) → .fff
"""
import re
import os
import csv
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

ARME_MAP = {"fleuret": "Fleuret", "epee": "Epee", "sabre": "Sabre"}
SEXE_MAP = {"dames": "F", "femmes": "F", "hommes": "M", "messieurs": "M", "mixte": "M"}


def extraire_pages(pdf_path: str) -> list[str]:
    """Extrait le texte de chaque page du PDF BellePoule."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                pages.append(t)
    return pages


def trouver_entete(pages: list[str]) -> dict:
    """
    Détecte arme, sexe, catégorie, date et nom de la compétition
    dans les premières pages du PDF.
    Retourne des valeurs par défaut si un champ est absent.
    """
    info = {"arme": None, "sexe": None, "categorie": None, "date": None, "nom": None}
    for page_text in pages[:4]:
        lignes = page_text.splitlines()
        for l in lignes:
            ll = l.lower()
            for mot, val in ARME_MAP.items():
                if mot in ll and info["arme"] is None:
                    info["arme"] = val
            if "ep" in ll and info["arme"] is None:
                if re.search(r'ep[eé]{2}', ll):
                    info["arme"] = "Epee"
            for mot, val in SEXE_MAP.items():
                if mot in ll and info["sexe"] is None:
                    info["sexe"] = val
            m = re.search(r'\b(M\d+|Senior|Veteran|V\d+|Junior|Cadet|Benjamin|Poussin)\b', l, re.I)
            if m and info["categorie"] is None:
                info["categorie"] = m.group(1).upper()
            m = re.search(r'(\d{2}/\d{2}/\d{4})', l)
            if m and info["date"] is None:
                info["date"] = m.group(1)
        for l in lignes:
            if re.search(r'\b(CDA|CDL|CEG|CDF|CDR|CI)\b', l):
                nom = re.sub(r'(.)\1', r'\1', l.strip())
                nom = re.sub(r'\s+', ' ', nom).strip()
                if nom and info["nom"] is None:
                    info["nom"] = nom
                break
        if all(v is not None for v in info.values()):
            break

    info.setdefault("date",      datetime.today().strftime("%d/%m/%Y"))
    info.setdefault("arme",      "Fleuret")
    info.setdefault("sexe",      "F")
    info.setdefault("categorie", "M13")
    info.setdefault("nom",       "Competition")
    for k, v in info.items():
        if v is None:
            info[k] = {"date": datetime.today().strftime("%d/%m/%Y"),
                       "arme": "Fleuret", "sexe": "F",
                       "categorie": "M13", "nom": "Competition"}[k]
    return info


def extraire_liste_appel(pages: list[str]) -> dict:
    """
    Extrait la liste des inscrits (section 'Liste des inscrits').
    Retourne {licence: {nom, prenom, club}}.
    """
    tireurs, in_s = {}, False
    for page_text in pages:
        if "liste des inscrits" in page_text.lower():
            in_s = True
        if not in_s:
            continue
        for ligne in page_text.splitlines():
            tokens = ligne.strip().split()
            if len(tokens) < 3:
                continue
            if not re.match(r'^\d{5,7}$', tokens[-1]):
                continue
            licence = tokens[-1]
            if not re.match(r'^\d+$', tokens[-2]):
                continue
            tokens = tokens[:-2]
            nom_p, prenom, club_p = [], None, []
            for tok in tokens:
                if prenom is None:
                    if re.match(r'^[A-Z\xc0-\xd6\xd8-\xde][A-Z\xc0-\xd6\xd8-\xde\-]*$', tok):
                        nom_p.append(tok)
                    else:
                        prenom = tok
                else:
                    club_p.append(tok)
            if not nom_p or prenom is None:
                continue
            tireurs[licence] = {
                "nom":    " ".join(nom_p),
                "prenom": prenom,
                "club":   " ".join(club_p),
            }
    return tireurs


def extraire_classement(pages: list[str]) -> list[dict]:
    """
    Extrait le classement général final du PDF.
    Retourne [{place, nom, prenom, club}].
    """
    classement, target = [], []
    for i, pt in enumerate(pages):
        if "classement g" in pt.lower() and ("ral" in pt.lower() or "eral" in pt.lower()):
            target.append(i)
    if not target:
        for i, pt in enumerate(pages):
            if "classement" in pt.lower() and "place" in pt.lower():
                target.append(i)
    if not target:
        return classement

    for ligne in pages[target[-1]].splitlines():
        tokens = ligne.strip().split()
        if not tokens or not tokens[0].isdigit():
            continue
        place = int(tokens[0])
        tokens = tokens[1:]
        if not tokens or not re.match(r'^[A-Z]{3}$', tokens[-1]):
            continue
        tokens = tokens[:-1]
        nom_p, prenom, club_p = [], None, []
        for tok in tokens:
            if prenom is None:
                if re.match(r'^[A-Z\xc0-\xd6\xd8-\xde][A-Z\xc0-\xd6\xd8-\xde\-]*$', tok):
                    nom_p.append(tok)
                else:
                    prenom = tok
            else:
                club_p.append(tok)
        if not nom_p:
            continue
        if prenom is None:
            if len(nom_p) > 1:
                prenom = nom_p.pop()
            else:
                continue
        classement.append({
            "place":  place,
            "nom":    " ".join(nom_p).upper(),
            "prenom": prenom,
            "club":   " ".join(club_p),
        })
    return classement


def trouver_licence(nom: str, prenom: str, licences_map: dict) -> str:
    """Recherche tolérante de licence par nom/prénom."""
    lic = licences_map.get((nom, prenom))
    if lic:
        return lic
    for (n, p), lic in licences_map.items():
        if p == prenom and (n.startswith(nom[:6]) or nom.startswith(n[:6])):
            return lic
    parts = nom.split()
    if len(parts) >= 2:
        lic = licences_map.get((parts[0], parts[1]))
        if lic:
            return lic
    for (n, p), lic in licences_map.items():
        if p == prenom and n.split()[0] == nom.split()[0]:
            return lic
    return ""


def charger_dates(csv_path: str | None) -> dict:
    """
    Charge les dates de naissance depuis un CSV (licence,date_naissance).
    Retourne {} si le fichier est absent ou invalide.
    """
    dates = {}
    if not csv_path or not os.path.isfile(csv_path):
        return dates
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(1024)
            f.seek(0)
            sep = ";" if sample.count(";") > sample.count(",") else ","
            for row in csv.reader(f, delimiter=sep):
                if len(row) < 2:
                    continue
                lic, ddn = row[0].strip(), row[1].strip()
                if re.match(r'^\d{2}/\d{2}/\d{4}$', ddn) and re.match(r'^\d{5,7}$', lic):
                    dates[lic] = ddn
    except Exception:
        pass
    return dates


def ecrire_fff(classement: list, info: dict, licences_map: dict,
               dates: dict, output_path: str) -> None:
    """Génère le fichier .fff WIN/FFE depuis le classement."""
    from core.format_export import ecrire_fff as _ecrire
    tireurs = []
    for t in classement:
        lic = trouver_licence(t["nom"], t["prenom"], licences_map)
        tireurs.append({**t, "licence": lic, "ddn": dates.get(lic, "")})
    _ecrire(tireurs, info, output_path)


def convertir(pdf_path: str, output_path: str, log=print, csv_path: str | None = None) -> tuple[bool, str]:
    """
    Pipeline complet BellePoule PDF individuel → .fff.
    Retourne (succès, chemin_sortie_ou_message_erreur).
    """
    if not os.path.isfile(pdf_path):
        return False, f"Fichier introuvable : {pdf_path}"
    try:
        log("   -> Lecture du PDF...")
        pages = extraire_pages(pdf_path)
        log(f"   -> {len(pages)} pages extraites")

        info = trouver_entete(pages)
        log(f"   -> {info['arme']} | {info['sexe']} | {info['categorie']} | {info['date']}")
        log(f"   -> Compétition : {info['nom']}")

        liste = extraire_liste_appel(pages)
        licences_map = {(d["nom"], d["prenom"]): lic for lic, d in liste.items()}
        log(f"   -> {len(liste)} tireurs dans la liste d'appel")

        dates = charger_dates(csv_path)
        if csv_path:
            log(f"   -> {len(dates)} dates de naissance chargées")

        classement = extraire_classement(pages)
        log(f"   -> {len(classement)} tireurs au classement final")
        if not classement:
            return False, "Aucun classement général trouvé."

        manquants = [
            f"{t['nom']} {t['prenom']}" for t in classement
            if not trouver_licence(t["nom"], t["prenom"], licences_map)
        ]
        if manquants:
            log(f"ATTENTION licences manquantes : {', '.join(manquants)}")
        else:
            log("   -> Toutes les licences associées")

        ecrire_fff(classement, info, licences_map, dates, output_path)
        return True, output_path

    except Exception as e:
        return False, f"Erreur inattendue : {e}"
