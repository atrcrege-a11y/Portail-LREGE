#!/usr/bin/env python3
"""
EscriTools - LREGE Grand Est
Application unifiee : BellePoule -> FFF  |  PDF -> Markdown
"""

import sys, re, os, csv
from pathlib import Path
from collections import Counter
from datetime import datetime
# tkinter importé plus bas

try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber


# =============================================================================
# LOGIQUE BELLEPOULE -> FFF
# =============================================================================

ARME_MAP = {"fleuret": "Fleuret", "epee": "Epee", "epee": "Epee", "sabre": "Sabre"}
SEXE_MAP = {"dames": "F", "femmes": "F", "hommes": "M", "messieurs": "M", "mixte": "M"}


def fff_extraire_pages(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                pages.append(t)
    return pages


def fff_trouver_entete(pages):
    info = {"arme": None, "sexe": None, "categorie": None, "date": None, "nom": None}
    for page_text in pages[:4]:
        lignes = page_text.splitlines()
        for l in lignes:
            ll = l.lower()
            for mot, val in ARME_MAP.items():
                if mot in ll and info["arme"] is None: info["arme"] = val
            if "ep" in ll and info["arme"] is None:
                if re.search(r'ep[e\xe9]{2}', ll): info["arme"] = "Epee"
            for mot, val in SEXE_MAP.items():
                if mot in ll and info["sexe"] is None: info["sexe"] = val
            m = re.search(r'\b(M\d+|Senior|Veteran|V\d+|Junior|Cadet|Benjamin|Poussin)\b', l, re.I)
            if m and info["categorie"] is None: info["categorie"] = m.group(1).upper()
            m = re.search(r'(\d{2}/\d{2}/\d{4})', l)
            if m and info["date"] is None: info["date"] = m.group(1)
        for l in lignes:
            if re.search(r'\b(CDA|CDL|CEG|CDF|CDR|CI)\b', l):
                nom = re.sub(r'(.)\1', r'\1', l.strip())
                nom = re.sub(r'\s+', ' ', nom).strip()
                if nom and info["nom"] is None: info["nom"] = nom
                break
        if all(v is not None for v in info.values()): break
    if info["date"]      is None: info["date"]      = datetime.today().strftime("%d/%m/%Y")
    if info["arme"]      is None: info["arme"]      = "Fleuret"
    if info["sexe"]      is None: info["sexe"]      = "F"
    if info["categorie"] is None: info["categorie"] = "M13"
    if info["nom"]       is None: info["nom"]       = "Competition"
    return info


def fff_extraire_liste_appel(pages):
    tireurs, in_s = {}, False
    for page_text in pages:
        if "liste des inscrits" in page_text.lower(): in_s = True
        if not in_s: continue
        for ligne in page_text.splitlines():
            tokens = ligne.strip().split()
            if len(tokens) < 3: continue
            if not re.match(r'^\d{5,7}$', tokens[-1]): continue
            licence = tokens[-1]
            if not re.match(r'^\d+$', tokens[-2]): continue
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
            if not nom_p or prenom is None: continue
            tireurs[licence] = {"nom": " ".join(nom_p), "prenom": prenom, "club": " ".join(club_p)}
    return tireurs


def fff_extraire_classement(pages):
    classement, target = [], []
    for i, pt in enumerate(pages):
        if "classement g" in pt.lower() and ("ral" in pt.lower() or "eral" in pt.lower()):
            target.append(i)
    if not target:
        for i, pt in enumerate(pages):
            if "classement" in pt.lower() and "place" in pt.lower(): target.append(i)
    if not target: return classement
    for ligne in pages[target[-1]].splitlines():
        tokens = ligne.strip().split()
        if not tokens or not tokens[0].isdigit(): continue
        place = int(tokens[0]); tokens = tokens[1:]
        if not tokens or not re.match(r'^[A-Z]{3}$', tokens[-1]): continue
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
        if not nom_p: continue
        if prenom is None:
            if len(nom_p) > 1: prenom = nom_p.pop()
            else: continue
        classement.append({"place": place, "nom": " ".join(nom_p).upper(),
                           "prenom": prenom, "club": " ".join(club_p)})
    return classement


def fff_trouver_licence(nom, prenom, licences_map):
    lic = licences_map.get((nom, prenom))
    if lic: return lic
    for (n, p), lic in licences_map.items():
        if p == prenom and (n.startswith(nom[:6]) or nom.startswith(n[:6])): return lic
    parts = nom.split()
    if len(parts) >= 2:
        lic = licences_map.get((parts[0], parts[1]))
        if lic: return lic
    for (n, p), lic in licences_map.items():
        if p == prenom and n.split()[0] == nom.split()[0]: return lic
    return ""


def fff_charger_dates(csv_path):
    dates = {}
    if not csv_path or not os.path.isfile(csv_path): return dates
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(1024); f.seek(0)
            sep = ";" if sample.count(";") > sample.count(",") else ","
            for row in csv.reader(f, delimiter=sep):
                if len(row) < 2: continue
                lic, ddn = row[0].strip(), row[1].strip()
                if re.match(r'^\d{2}/\d{2}/\d{4}$', ddn) and re.match(r'^\d{5,7}$', lic):
                    dates[lic] = ddn
    except Exception: pass
    return dates


def convertir_fff(pdf_path, output_path, log, csv_path=None):
    if not os.path.isfile(pdf_path):
        return False, f"Fichier introuvable : {pdf_path}"
    log(f"   -> Lecture du PDF...")
    pages = fff_extraire_pages(pdf_path)
    log(f"   -> {len(pages)} pages extraites")
    info = fff_trouver_entete(pages)
    log(f"   -> {info['arme']} | {info['sexe']} | {info['categorie']} | {info['date']}")
    log(f"   -> Competition : {info['nom']}")
    liste = fff_extraire_liste_appel(pages)
    licences_map = {(d["nom"], d["prenom"]): lic for lic, d in liste.items()}
    log(f"   -> {len(liste)} tireurs dans la liste d'appel")
    dates = fff_charger_dates(csv_path)
    if csv_path: log(f"   -> {len(dates)} dates de naissance chargees")
    classement = fff_extraire_classement(pages)
    log(f"   -> {len(classement)} tireurs au classement final")
    if not classement: return False, "Aucun classement general trouve."
    manquants = [f"{t['nom']} {t['prenom']}" for t in classement
                 if not fff_trouver_licence(t["nom"], t["prenom"], licences_map)]
    if manquants: log(f"ATTENTION licences manquantes : {', '.join(manquants)}")
    else: log("   -> Toutes les licences associees")
    lignes = [
        "FFF;WIN;competition; ;individuel",
        f"{info['date']};{info['arme']};{info['sexe']};{info['categorie']};{info['nom']};{info['nom']}"
    ]
    for t in classement:
        lic  = fff_trouver_licence(t["nom"], t["prenom"], licences_map)
        app  = liste.get(lic, {}) if lic else {}
        club = app.get("club") or t["club"]
        ddn  = dates.get(lic, "")
        lignes.append(
            f"{t['nom']},{t['prenom']},{ddn},{info['sexe']},FRA,;"
            f",,;{lic},,{club},{t['place']},,;{t['place']},t"
        )
    contenu = "\r\n".join(lignes) + "\r\n"
    with open(output_path, "w", encoding="latin-1", errors="replace") as f:
        f.write(contenu)
    return True, output_path


# =============================================================================
# LOGIQUE PDF -> MARKDOWN
# =============================================================================

# Glyphes connus encodés comme caractères non-texte dans certains PDFs
GLYPH_MAP = {
    "fi": "→",   # flèche encodée en ligature fi
    "fl": "→",
    "ﬁ": "→",
    "ﬂ": "→",
}

def _corriger_glyphes(texte):
    """Remplace les glyphes mal encodés par leur équivalent textuel."""
    for glyph, remplacement in GLYPH_MAP.items():
        texte = texte.replace(glyph, remplacement)
    # Nettoyer les → consécutifs (artefacts de flèche multiple)
    texte = re.sub(r'(→\s*){2,}', '→ ', texte)
    return texte


def _detecter_frontiere_colonnes(words):
    """
    Détecte s'il y a 2 colonnes sur la page en cherchant une ligne
    avec un grand écart horizontal (ex: "Problème | Recommandation").
    Retourne la position X de la frontière ou None.
    """
    lignes_y = {}
    for w in words:
        key = round(w["top"] / 2) * 2
        lignes_y.setdefault(key, []).append(w)

    # Chercher la ligne avec le plus grand écart entre 2 mots consécutifs
    meilleur_ecart = 0
    frontiere = None
    for mots in lignes_y.values():
        mots_tries = sorted(mots, key=lambda w: w["x0"])
        for i in range(len(mots_tries) - 1):
            ecart = mots_tries[i+1]["x0"] - mots_tries[i]["x1"]
            if ecart > meilleur_ecart:
                meilleur_ecart = ecart
                frontiere = (mots_tries[i]["x1"] + mots_tries[i+1]["x0"]) / 2

    # Seuil : écart > 60pt = vraisemblablement 2 colonnes
    return frontiere if meilleur_ecart > 60 else None


def _reconstruire_colonnes(words, frontiere):
    """
    Regroupe les mots en lignes et les sépare en 2 colonnes
    selon la frontière X. Gère les mots qui chevauchent la frontière
    en les assignant selon le centre du mot.
    Retourne une liste de (texte_col_gauche, texte_col_droite).
    """
    lignes_y = {}
    for w in words:
        key = round(w["top"] / 2) * 2
        lignes_y.setdefault(key, []).append(w)

    resultats = []
    for y in sorted(lignes_y):
        mots = sorted(lignes_y[y], key=lambda w: w["x0"])
        col_g, col_d = [], []
        for w in mots:
            texte  = _corriger_glyphes(w["text"])
            centre = (w["x0"] + w["x1"]) / 2
            if centre < frontiere:
                col_g.append(texte)
            else:
                col_d.append(texte)
        g = " ".join(col_g).strip()
        d = " ".join(col_d).strip()
        resultats.append((g, d, y))

    return resultats


def _colonnes_vers_tableau_md(lignes_colonnes):
    """
    Convertit les paires (gauche, droite) en tableau Markdown.
    Détecte la ligne d'en-tête (première ligne non vide avec les 2 colonnes).
    Fusionne les lignes de continuation (col droite vide = suite du texte précédent).
    """
    # Filtrer les lignes vides
    lignes = [(g, d) for g, d, _ in lignes_colonnes if g or d]
    if not lignes:
        return ""

    # Première ligne = en-tête
    entete = lignes[0]
    rows   = []
    buf_g, buf_d = "", ""

    for g, d in lignes[1:]:
        if g and d:
            # Nouvelle ligne complète : vider le buffer
            if buf_g or buf_d:
                rows.append((buf_g.strip(), buf_d.strip()))
            buf_g, buf_d = g, d
        elif not g and d:
            # Continuation de la colonne droite
            buf_d += " " + d
        elif g and not d:
            # Continuation de la colonne gauche
            buf_g += " " + g
        else:
            # Ligne vide : vider le buffer
            if buf_g or buf_d:
                rows.append((buf_g.strip(), buf_d.strip()))
                buf_g, buf_d = "", ""

    if buf_g or buf_d:
        rows.append((buf_g.strip(), buf_d.strip()))

    if not rows:
        return ""

    # Construire le Markdown
    h1 = entete[0] or "Colonne 1"
    h2 = entete[1] or "Colonne 2"
    lignes_md = [
        f"| {h1} | {h2} |",
        "| --- | --- |",
    ]
    for g, d in rows:
        lignes_md.append(f"| {g} | {d} |")

    return "\n".join(lignes_md)


def md_extraire_blocs(page):
    """
    Extrait les blocs de texte d'une page.
    Si 2 colonnes détectées, reconstruit les tableaux proprement.
    """
    try:
        mots = page.extract_words(extra_attrs=["size", "fontname"])
    except Exception:
        return []
    if not mots: return []

    frontiere = _detecter_frontiere_colonnes(mots)

    groupes = {}
    for m in mots:
        key = round(m["top"] / 3) * 3
        groupes.setdefault(key, []).append(m)

    blocs = []
    for top in sorted(groupes):
        ligne = sorted(groupes[top], key=lambda w: w["x0"])

        if frontiere:
            # Assigner chaque mot à sa colonne selon le centre
            col_g = [w for w in ligne if (w["x0"]+w["x1"])/2 < frontiere]
            col_d = [w for w in ligne if (w["x0"]+w["x1"])/2 >= frontiere]
            texte_g = _corriger_glyphes(" ".join(w["text"] for w in col_g)).strip()
            texte_d = _corriger_glyphes(" ".join(w["text"] for w in col_d)).strip()
            # Stocker les deux colonnes séparément
            for texte, mots_col, col in [(texte_g, col_g, "g"), (texte_d, col_d, "d")]:
                if not texte: continue
                try:
                    size = max(float(w.get("size", 0) or 0) for w in mots_col)
                except Exception:
                    size = 10.0
                fonts = " ".join(w.get("fontname", "") or "" for w in mots_col).lower()
                bold  = any(k in fonts for k in ("bold", "heavy", "black", "demi"))
                x0    = min(w["x0"] for w in mots_col)
                blocs.append({"text": texte, "size": size, "bold": bold,
                               "x0": x0, "top": top, "col": col,
                               "has_cols": True, "frontiere": frontiere})
        else:
            texte = _corriger_glyphes(" ".join(w["text"] for w in ligne)).strip()
            if not texte: continue
            try:
                size = max(float(w.get("size", 0) or 0) for w in ligne)
            except Exception:
                size = 10.0
            fonts = " ".join(w.get("fontname", "") or "" for w in ligne).lower()
            bold  = any(k in fonts for k in ("bold", "heavy", "black", "demi"))
            x0    = min(w["x0"] for w in ligne)
            blocs.append({"text": texte, "size": size, "bold": bold,
                           "x0": x0, "top": top, "col": None, "has_cols": False})

    return blocs


def md_calculer_seuils(tous_blocs):
    tailles = [round(b["size"]) for b in tous_blocs if b["size"] > 6]
    if not tailles:
        return {"h1": 18, "h2": 14, "h3": 12, "body": 10}
    freq      = Counter(tailles)
    body_size = freq.most_common(1)[0][0]
    titres    = sorted(set(t for t in tailles if t > body_size + 1), reverse=True)
    s = {"body": body_size}
    if len(titres) >= 1: s["h1"] = titres[0]
    if len(titres) >= 2: s["h2"] = titres[1]
    if len(titres) >= 3: s["h3"] = titres[2]
    s.setdefault("h1", body_size + 6)
    s.setdefault("h2", body_size + 3)
    s.setdefault("h3", body_size + 1)
    return s


def md_nettoyer(texte):
    lettres = [c for c in texte if c.isalpha()]
    if len(lettres) >= 6:
        paires = sum(1 for i in range(0, len(lettres)-1, 2) if lettres[i] == lettres[i+1])
        if paires >= max(2, len(lettres) // 3):
            texte = re.sub(r'(.)\1', r'\1', texte)
    return re.sub(r'\s{2,}', ' ', texte).strip()


FILTRES_MD = re.compile(
    r'(bellepoule|betton\.escrime|http[s]?://|^page\s+\d+|^\d+\s*/\s*\d+$'
    r'|^(cda|cdl|ceg|cdf|cdr|petites|cat.gories)$)',
    re.IGNORECASE)


def md_detecter_repetitifs(tous_blocs, nb_pages, seuil=0.4):
    if nb_pages <= 2: return set()
    cpt = Counter(md_nettoyer(b["text"]) for b in tous_blocs)
    return {t for t, n in cpt.items() if n >= max(2, nb_pages * seuil) and len(t) < 120}


def md_page_en_md(page, seuils, repetitifs):
    blocs = md_extraire_blocs(page)
    if not blocs: return ""

    # Détecter si la page a des colonnes
    has_cols   = any(b.get("has_cols") for b in blocs)
    frontiere  = blocs[0].get("frontiere") if has_cols else None

    x0s  = [b["x0"] for b in blocs if round(b["size"]) <= seuils["body"] + 1 and b.get("col") != "d"]
    x0_b = sorted(x0s)[len(x0s)//4] if x0s else 50

    sortie, para = [], []

    def vider():
        if para: sortie.append(" ".join(para)); para.clear()

    def ajouter_titre(niveau, texte):
        vider()
        prefix = "#" * niveau
        sortie.append(f"\n{prefix} {texte}\n")

    def est_titre(b):
        size, bold = round(b["size"]), b["bold"]
        if size >= seuils["h1"] or (bold and size > seuils["body"] + 3): return 1
        if size >= seuils["h2"] or (bold and size > seuils["body"] + 2): return 2
        if size >= seuils["h3"] or (bold and size > seuils["body"] + 0.5): return 3
        return 0

    if has_cols:
        # ── Mode 2 colonnes : regrouper par lignes Y et reconstruire en tableau ──
        # Séparer les blocs titres (col gauche uniquement, grande taille) des lignes de tableau
        tops_traites = set()
        # D'abord extraire les titres hors-tableau (col=None ou grand texte)
        blocs_tableau_g = {}  # top -> texte col gauche
        blocs_tableau_d = {}  # top -> texte col droite

        for b in blocs:
            texte = md_nettoyer(b["text"])
            if not texte or FILTRES_MD.search(texte.lower()) or texte in repetitifs:
                continue
            niv = est_titre(b)
            col = b.get("col")
            top = b["top"]

            if niv and col != "d":
                # Titre dans colonne gauche = titre réel du document
                # Sauf si c'est juste un fragment de ligne (trop court et col=g uniquement)
                ajouter_titre(niv, texte)
                tops_traites.add(top)
            elif col == "g":
                blocs_tableau_g[top] = blocs_tableau_g.get(top, "") + " " + texte
            elif col == "d":
                blocs_tableau_d[top] = blocs_tableau_d.get(top, "") + " " + texte

        # Construire le tableau à partir des paires g/d
        tops_tableau = sorted(set(list(blocs_tableau_g.keys()) + list(blocs_tableau_d.keys())))
        if tops_tableau:
            lignes_paires = []
            for top in tops_tableau:
                if top not in tops_traites:
                    g = blocs_tableau_g.get(top, "").strip()
                    d = blocs_tableau_d.get(top, "").strip()
                    lignes_paires.append((g, d))

            # Regrouper en tableaux continus (séparés par lignes sans contenu)
            tableau_courant = []
            tableaux = []
            for g, d in lignes_paires:
                if g or d:
                    tableau_courant.append((g, d))
                else:
                    if tableau_courant:
                        tableaux.append(tableau_courant)
                        tableau_courant = []
            if tableau_courant:
                tableaux.append(tableau_courant)

            for tbl in tableaux:
                if len(tbl) < 2:
                    # Pas assez de lignes pour un tableau → paragraphes
                    for g, d in tbl:
                        if g: sortie.append(g)
                        if d: sortie.append(d)
                    continue
                # Première ligne = en-tête
                h1, h2 = tbl[0]
                if not h1: h1 = "Colonne 1"
                if not h2: h2 = "Colonne 2"
                sortie.append(f"\n| {h1} | {h2} |")
                sortie.append(f"| --- | --- |")
                # Fusionner les lignes de continuation
                buf_g, buf_d = "", ""
                for g, d in tbl[1:]:
                    if g and d:
                        if buf_g or buf_d:
                            sortie.append(f"| {buf_g.strip()} | {buf_d.strip()} |")
                        buf_g, buf_d = g, d
                    elif g and not d:
                        buf_g += " " + g
                    elif d and not g:
                        buf_d += " " + d
                if buf_g or buf_d:
                    sortie.append(f"| {buf_g.strip()} | {buf_d.strip()} |")
                sortie.append("")
    else:
        # ── Mode colonne unique (comportement original) ──────────────────────
        for b in blocs:
            texte = md_nettoyer(b["text"])
            if not texte: continue
            t = texte.strip()
            if FILTRES_MD.search(t.lower()) or t in repetitifs:
                vider(); continue
            niv = est_titre(b)
            if niv:
                ajouter_titre(niv, texte)
            else:
                m = re.match(r'^[\-\*\u2022\u2013\u2014\u25aa\u25b8\u25ba\u2192\u00b7]\s+(.+)$', texte)
                if m:
                    vider()
                    indent = "  " if b["x0"] - x0_b > 30 else ""
                    sortie.append(f"{indent}- {m.group(1)}")
                elif re.match(r'^\d+\.\s+', texte):
                    vider(); sortie.append(f"- {texte}")
                else:
                    para.append(texte)
        vider()

    return "\n".join(sortie)


def md_nettoyer(texte):
    lettres = [c for c in texte if c.isalpha()]
    if len(lettres) >= 6:
        paires = sum(1 for i in range(0, len(lettres)-1, 2) if lettres[i] == lettres[i+1])
        if paires >= max(2, len(lettres) // 3):
            texte = re.sub(r'(.)\1', r'\1', texte)
    return re.sub(r'\s{2,}', ' ', texte).strip()


FILTRES_MD = re.compile(
    r'(bellepoule|betton\.escrime|http[s]?://|^page\s+\d+|^\d+\s*/\s*\d+$'
    r'|^(cda|cdl|ceg|cdf|cdr|petites|cat.gories)$)',
    re.IGNORECASE)


def md_detecter_repetitifs(tous_blocs, nb_pages, seuil=0.4):
    if nb_pages <= 2: return set()
    cpt = Counter(md_nettoyer(b["text"]) for b in tous_blocs)
    return {t for t, n in cpt.items() if n >= max(2, nb_pages * seuil) and len(t) < 120}


def md_page_en_md(page, seuils, repetitifs):
    blocs = md_extraire_blocs(page)
    if not blocs: return ""
    try:
        tableaux_md = []
        for tbl in (page.extract_tables() or []):
            if not tbl or len(tbl) < 2: continue
            tbl = [[c or "" for c in row] for row in tbl]
            n   = max(len(r) for r in tbl)
            ent = tbl[0] + [""] * (n - len(tbl[0]))
            lmd = ["| " + " | ".join(str(c).replace("\n", " ").strip() for c in ent) + " |"]
            lmd += ["| " + " | ".join(["---"] * n) + " |"]
            for row in tbl[1:]:
                row = row + [""] * (n - len(row))
                lmd.append("| " + " | ".join(str(c).replace("\n"," ").strip() for c in row) + " |")
            tableaux_md.append("\n".join(lmd))
    except Exception:
        tableaux_md = []
    x0s  = [b["x0"] for b in blocs if round(b["size"]) <= seuils["body"] + 1]
    x0_b = sorted(x0s)[len(x0s)//4] if x0s else 50
    sortie, para = [], []
    def vider():
        if para: sortie.append(" ".join(para)); para.clear()
    for b in blocs:
        texte = md_nettoyer(b["text"])
        if not texte: continue
        t = texte.strip()
        if FILTRES_MD.search(t.lower()) or t in repetitifs:
            vider(); continue
        size, bold = round(b["size"]), b["bold"]
        if size >= seuils["h1"] or (bold and size > seuils["body"] + 3):
            vider(); sortie.append(f"\n# {texte}\n")
        elif size >= seuils["h2"] or (bold and size > seuils["body"] + 2):
            vider(); sortie.append(f"\n## {texte}\n")
        elif size >= seuils["h3"] or (bold and size > seuils["body"] + 0.5):
            vider(); sortie.append(f"\n### {texte}\n")
        else:
            m = re.match(r'^[\-\*\u2022\u2013\u2014\u25aa\u25b8\u25ba\u2192\u00b7]\s+(.+)$', texte)
            if m:
                vider()
                indent = "  " if b["x0"] - x0_b > 30 else ""
                sortie.append(f"{indent}- {m.group(1)}")
            else:
                m2 = re.match(r'^((?:Art(?:icle)?\.?\s*)?\d+[\.\)]|[IVXivx]+[\.\)]|[A-Za-z][\.\)])\s+', texte)
                if m2:
                    vider(); sortie.append(f"- {texte}")
                else:
                    para.append(texte)
    vider()
    for t in tableaux_md:
        sortie.append(f"\n{t}\n")
    return "\n".join(sortie)


def convertir_md(pdf_path, log=print):
    with pdfplumber.open(pdf_path) as pdf:
        nb = len(pdf.pages)
        log(f"   -> {nb} pages")
        log("   -> Analyse de la structure...")
        tous = []
        for p in pdf.pages: tous.extend(md_extraire_blocs(p))
        seuils = md_calculer_seuils(tous)
        reps   = md_detecter_repetitifs(tous, nb)
        log(f"   -> Seuils : H1>={seuils['h1']} H2>={seuils['h2']} "
            f"H3>={seuils['h3']} corps={seuils['body']}")
        if reps: log(f"   -> {len(reps)} lignes repetitives filtrees")
        sections = []
        for p in pdf.pages:
            md = md_page_en_md(p, seuils, reps)
            if md.strip(): sections.append(md)
    contenu = "\n\n".join(sections)
    contenu = re.sub(r'([^#\|\-\n].{20,}[^.!?:])\n([a-z\(])', r'\1 \2', contenu)
    contenu = re.sub(r'\n{4,}', '\n\n\n', contenu)
    contenu = re.sub(r'\n{3,}(#{1,3} )', r'\n\n\1', contenu)
    # Fusionner les titres fragmentés sur 2 lignes consécutives de même niveau
    # ex: "# Projet 1 —\n\n# Para-escrime" -> "# Projet 1 — Para-escrime"
    for niveau in ['###', '##', '#']:
        pattern = re.escape(niveau) + r' (.+)\n\n' + re.escape(niveau) + r' (.+)'
        def fusionner(m):
            a, b = m.group(1).strip(), m.group(2).strip()
            # Fusionner seulement si le premier fragment semble incomplet
            # (se termine par —, :, virgule, ou est très court)
            if a.endswith(('—', ':', ',', '/')) or len(a) < 20:
                return f'{niveau} {a} {b}'
            return m.group(0)
        contenu = re.sub(pattern, fusionner, contenu)
    return contenu.strip()


# =============================================================================
# LOGIQUE MARKDOWN -> PDF
# =============================================================================

import re, os, uuid
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                HRFlowable, ListFlowable, ListItem,
                                Table, TableStyle, Preformatted)
from reportlab.lib.enums import TA_LEFT

BLEU       = colors.HexColor("#1F3864")
BLEU_CLAIR = colors.HexColor("#2e5da8")
GRIS       = colors.HexColor("#555555")
GRIS_CLAIR = colors.HexColor("#f4f4f4")
NOIR       = colors.HexColor("#1a1a1a")

def mkstyle(name, **kw):
    return ParagraphStyle(name + "_" + uuid.uuid4().hex[:6], **kw)

sH1   = mkstyle("h1",   fontSize=22, textColor=BLEU, spaceAfter=6, spaceBefore=18,
                         fontName="Helvetica-Bold", leading=26)
sH2   = mkstyle("h2",   fontSize=16, textColor=BLEU_CLAIR, spaceAfter=4, spaceBefore=14,
                         fontName="Helvetica-Bold", leading=20)
sH3   = mkstyle("h3",   fontSize=13, textColor=BLEU, spaceAfter=3, spaceBefore=10,
                         fontName="Helvetica-BoldOblique", leading=16)
sPara = mkstyle("para", fontSize=10, textColor=NOIR, spaceAfter=4, spaceBefore=2,
                         fontName="Helvetica", leading=14)
sCode = mkstyle("code", fontSize=9, fontName="Courier", spaceAfter=6, leading=13,
                         backColor=GRIS_CLAIR, leftIndent=10, rightIndent=10)
sListe= mkstyle("lst",  fontSize=10, textColor=NOIR, fontName="Helvetica", leading=14)


def echapper(txt):
    txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    txt = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', txt)
    txt = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', txt)
    txt = re.sub(r'`(.+?)`',       r'<font name="Courier">\1</font>', txt)
    return txt


def md_vers_pdf(md_path, output_path, log=print):
    if not os.path.isfile(md_path):
        return False, f"Fichier introuvable : {md_path}"

    contenu = Path(md_path).read_text(encoding="utf-8")
    lignes  = contenu.splitlines()
    log(f"   -> {len(lignes)} lignes")

    story          = []
    liste_en_cours = []
    i              = 0

    def vider_liste():
        if liste_en_cours:
            items = [ListItem(Paragraph(t, sListe), leftIndent=20, bulletColor=BLEU)
                     for t in liste_en_cours]
            story.append(ListFlowable(items, bulletType="bullet",
                                      leftIndent=10, bulletFontSize=8))
            story.append(Spacer(1, 4))
            liste_en_cours.clear()

    while i < len(lignes):
        ligne = lignes[i]

        if ligne.startswith("# ") and not ligne.startswith("## "):
            vider_liste()
            story.append(Spacer(1, 6))
            story.append(Paragraph(echapper(ligne[2:].strip()), sH1))
            story.append(HRFlowable(width="100%", thickness=2, color=BLEU, spaceAfter=6))

        elif ligne.startswith("## ") and not ligne.startswith("### "):
            vider_liste()
            story.append(Paragraph(echapper(ligne[3:].strip()), sH2))
            story.append(HRFlowable(width="100%", thickness=0.5, color=BLEU_CLAIR, spaceAfter=4))

        elif ligne.startswith("### "):
            vider_liste()
            story.append(Paragraph(echapper(ligne[4:].strip()), sH3))

        elif re.match(r'^-{3,}$', ligne.strip()):
            vider_liste()
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=1, color=GRIS, spaceAfter=8))

        elif ligne.strip().startswith("```"):
            vider_liste()
            bloc = []
            i += 1
            while i < len(lignes) and not lignes[i].strip().startswith("```"):
                bloc.append(lignes[i])
                i += 1
            if bloc:
                story.append(Preformatted("\n".join(bloc), sCode))

        elif ligne.strip().startswith("|") and "|" in ligne[1:]:
            vider_liste()
            rows_raw = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                cells = [c.strip() for c in lignes[i].strip().strip("|").split("|")]
                rows_raw.append(cells)
                i += 1
            rows = [r for r in rows_raw
                    if not all(re.match(r'^-+$', c) for c in r if c)]
            if rows:
                nb_cols = max(len(r) for r in rows)
                data    = [r + [""] * (nb_cols - len(r)) for r in rows]
                col_w   = (A4[0] - 4*cm) / nb_cols
                t = Table(data, colWidths=[col_w]*nb_cols)
                t.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0), BLEU),
                    ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
                    ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0), (-1,-1), 9),
                    ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
                    ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, GRIS_CLAIR]),
                    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("TOPPADDING",    (0,0), (-1,-1), 5),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                    ("LEFTPADDING",   (0,0), (-1,-1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))
            continue

        elif re.match(r'^\s*[\-\*] ', ligne):
            m = re.match(r'^\s*[\-\*] (.+)$', ligne)
            if m:
                liste_en_cours.append(echapper(m.group(1).strip()))

        elif not ligne.strip():
            vider_liste()
            if story and not isinstance(story[-1], Spacer):
                story.append(Spacer(1, 4))

        else:
            vider_liste()
            texte = echapper(ligne.strip())
            if texte:
                story.append(Paragraph(texte, sPara))

        i += 1

    vider_liste()
    log(f"   -> {len(story)} elements")

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm,
                            title=Path(md_path).stem)
    doc.build(story)
    return True, output_path



def convertir_md_pdf_lot(md_paths, output_dir, fusion, log=print):
    succes, erreurs = [], []
    if fusion:
        textes = []
        for p in md_paths:
            try:
                t = Path(p).read_text(encoding="utf-8")
                textes.append(f"---\n\n# {Path(p).stem}\n\n{t}")
            except Exception as e:
                erreurs.append((p, str(e)))
        if textes:
            tmp = os.path.join(output_dir, "_fusion_tmp.md")
            Path(tmp).write_text("\n\n".join(textes), encoding="utf-8")
            nom = os.path.join(output_dir, "fusion.pdf")
            log(f"Fusion de {len(textes)} fichiers...")
            ok, res = md_vers_pdf(tmp, nom, log)
            os.remove(tmp)
            if ok: succes.append(res)
            else:  erreurs.append(("fusion", res))
    else:
        for p in md_paths:
            log(f"\n--- {os.path.basename(p)} ---")
            nom = os.path.join(output_dir, Path(p).stem + ".pdf")
            ok, res = md_vers_pdf(p, nom, log)
            if ok: succes.append(res)
            else:  erreurs.append((p, res))
    return succes, erreurs

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# =============================================================================
# INTERFACE GRAPHIQUE
# =============================================================================

def make_log(parent):
    txt = scrolledtext.ScrolledText(parent, width=72, height=12,
                                    font=("Consolas", 9), wrap="word")
    txt.pack(fill="both", expand=True, padx=12, pady=(4, 10))
    return txt


def log_write(txt, msg, root):
    txt.insert(tk.END, msg + "\n")
    txt.see(tk.END)
    root.update_idletasks()


def row_field(parent, label, var, cmd, row, btn_txt="Parcourir..."):
    tk.Label(parent, text=label).grid(row=row*2, column=0, columnspan=2,
                                      sticky="w", pady=(8, 1))
    tk.Entry(parent, textvariable=var, width=52).grid(
        row=row*2+1, column=0, sticky="ew", padx=(0, 6))
    tk.Button(parent, text=btn_txt, command=cmd).grid(row=row*2+1, column=1)
    parent.columnconfigure(0, weight=1)


# ── Onglet BellePoule -> FFF ─────────────────────────────────────────────────

class TabFFF(tk.Frame):
    def __init__(self, parent, root):
        super().__init__(parent)
        self.root = root
        self.var_pdf = tk.StringVar()
        self.var_out = tk.StringVar()
        self.var_csv = tk.StringVar()
        self._build()

    def _build(self):
        tk.Label(self, text="Convertit un PDF BellePoule en fichier .fff compatible WIN (FFE).",
                 fg="gray", wraplength=580, justify="left").pack(
            anchor="w", padx=14, pady=(10, 6))

        # Fichiers
        fr = tk.LabelFrame(self, text="Fichiers", padx=10, pady=6)
        fr.pack(fill="x", padx=14, pady=(0, 8))
        row_field(fr, "PDF BellePoule :", self.var_pdf, self._pdf, 0)
        row_field(fr, "Fichier de sortie .fff :", self.var_out, self._out, 1)

        # CSV
        tk.Label(fr, text="Dates de naissance (CSV optionnel) :").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 1))
        fr_csv = tk.Frame(fr)
        fr_csv.grid(row=5, column=0, columnspan=2, sticky="ew")
        tk.Entry(fr_csv, textvariable=self.var_csv, width=44).pack(side="left", padx=(0, 6))
        tk.Button(fr_csv, text="Parcourir...", command=self._csv).pack(side="left", padx=(0, 4))
        tk.Button(fr_csv, text="X", command=lambda: self.var_csv.set(""),
                  fg="red", width=2).pack(side="left")
        tk.Label(fr, text="Format : licence,date_naissance  ex: 304977,15/06/2013",
                 fg="gray", font=("Segoe UI", 8)).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # Bouton
        self.btn = tk.Button(self, text="Convertir en .fff", command=self._lancer,
                             bg="#2e7d32", fg="white",
                             font=("Segoe UI", 10, "bold"), pady=7)
        self.btn.pack(pady=8)

        # Log
        fr_log = tk.LabelFrame(self, text="Journal", padx=2, pady=2)
        fr_log.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log = make_log(fr_log)

    def _log(self, msg): log_write(self.log, msg, self.root)

    def _pdf(self):
        c = filedialog.askopenfilename(title="PDF BellePoule",
            filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")])
        if c:
            self.var_pdf.set(c)
            self.var_out.set(str(Path(c).with_suffix(".fff")))

    def _out(self):
        c = filedialog.asksaveasfilename(title="Enregistrer le .fff",
            defaultextension=".fff", filetypes=[("FFF", "*.fff"), ("Tous", "*.*")])
        if c: self.var_out.set(c)

    def _csv(self):
        c = filedialog.askopenfilename(title="CSV dates de naissance",
            filetypes=[("CSV", "*.csv"), ("Tous", "*.*")])
        if c: self.var_csv.set(c)

    def _lancer(self):
        pdf = self.var_pdf.get().strip()
        out = self.var_out.get().strip()
        if not pdf:
            messagebox.showwarning("Attention", "Selectionnez un fichier PDF."); return
        if not out:
            messagebox.showwarning("Attention", "Choisissez le fichier de sortie."); return
        self.log.delete("1.0", tk.END)
        self.btn.config(state="disabled")
        self._log(f"=== BellePoule -> FFF ===")
        self._log(f"Fichier : {os.path.basename(pdf)}")
        ok, res = convertir_fff(pdf, out, self._log,
                                csv_path=self.var_csv.get().strip() or None)
        if ok:
            self._log(f"Termine : {os.path.basename(res)}")
            messagebox.showinfo("Succes", f"Fichier genere :\n{res}")
        else:
            self._log(f"ERREUR : {res}")
            messagebox.showerror("Erreur", res)
        self.btn.config(state="normal")


# ── Onglet PDF -> Markdown ────────────────────────────────────────────────────

class TabMD(tk.Frame):
    def __init__(self, parent, root):
        super().__init__(parent)
        self.root     = root
        self.var_pdfs = []
        self.var_sortie = tk.StringVar()
        self.var_fusion = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        tk.Label(self, text="Convertit un ou plusieurs PDFs en Markdown structure "
                 "(titres, listes et tableaux detectes automatiquement).",
                 fg="gray", wraplength=580, justify="left").pack(
            anchor="w", padx=14, pady=(10, 6))

        # Fichiers
        fr = tk.LabelFrame(self, text="Fichiers PDF", padx=10, pady=6)
        fr.pack(fill="x", padx=14, pady=(0, 8))

        fr_lst = tk.Frame(fr)
        fr_lst.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.lst = tk.Listbox(fr_lst, width=56, height=4, selectmode=tk.EXTENDED)
        self.lst.pack(side="left")
        sb = tk.Scrollbar(fr_lst, orient="vertical", command=self.lst.yview)
        sb.pack(side="left", fill="y")
        self.lst.config(yscrollcommand=sb.set)

        fr_b = tk.Frame(fr)
        fr_b.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        for txt, cmd in [("Ajouter PDF(s)...", self._ajouter),
                         ("Retirer", self._retirer),
                         ("Vider", self._vider)]:
            tk.Button(fr_b, text=txt, command=cmd).pack(side="left", padx=(0, 6))

        row_field(fr, "Dossier / fichier de sortie :", self.var_sortie, self._sortie, 1)

        tk.Checkbutton(fr, text="Fusionner tous les PDFs dans un seul fichier .md",
                       variable=self.var_fusion).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # Bouton
        self.btn = tk.Button(self, text="Convertir en Markdown", command=self._lancer,
                             bg="#1565c0", fg="white",
                             font=("Segoe UI", 10, "bold"), pady=7, state="disabled")
        self.btn.pack(pady=8)

        # Log
        fr_log = tk.LabelFrame(self, text="Journal", padx=2, pady=2)
        fr_log.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log = make_log(fr_log)

    def _log(self, msg): log_write(self.log, msg, self.root)

    def _ajouter(self):
        chemins = filedialog.askopenfilenames(title="Selectionner des PDFs",
            filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")])
        for c in chemins:
            if c not in self.var_pdfs:
                self.var_pdfs.append(c)
                self.lst.insert(tk.END, os.path.basename(c))
        self._refresh()
        if chemins and not self.var_sortie.get():
            self.var_sortie.set(os.path.dirname(chemins[0]))

    def _retirer(self):
        for i in reversed(self.lst.curselection()):
            self.lst.delete(i); self.var_pdfs.pop(i)
        self._refresh()

    def _vider(self):
        self.lst.delete(0, tk.END); self.var_pdfs.clear(); self._refresh()

    def _sortie(self):
        if len(self.var_pdfs) == 1 and not self.var_fusion.get():
            c = filedialog.asksaveasfilename(title="Enregistrer le .md",
                defaultextension=".md",
                initialfile=Path(self.var_pdfs[0]).stem + ".md",
                filetypes=[("Markdown", "*.md"), ("Tous", "*.*")])
            if c: self.var_sortie.set(c)
        else:
            d = filedialog.askdirectory(title="Dossier de sortie")
            if d: self.var_sortie.set(d)

    def _refresh(self):
        n = len(self.var_pdfs)
        self.btn.config(
            state="normal" if n else "disabled",
            text=f"Convertir ({n} PDF{'s' if n>1 else ''}) en Markdown" if n else "Convertir en Markdown")

    def _lancer(self):
        if not self.var_pdfs: return
        sortie = self.var_sortie.get().strip()
        if not sortie:
            messagebox.showwarning("Attention", "Choisissez un fichier ou dossier de sortie."); return
        self.log.delete("1.0", tk.END)
        self.btn.config(state="disabled")
        self._log("=== PDF -> Markdown ===")
        fusion = self.var_fusion.get()
        try:
            if len(self.var_pdfs) == 1 and not fusion:
                p   = self.var_pdfs[0]
                out = sortie if sortie.endswith(".md") else \
                      os.path.join(sortie, Path(p).stem + ".md")
                self._log(f"Fichier : {os.path.basename(p)}")
                c = convertir_md(p, log=self._log)
                if c.strip():
                    Path(out).write_text(c, encoding="utf-8")
                    self._log(f"Termine : {os.path.basename(out)}")
                    messagebox.showinfo("Succes", f"Fichier genere :\n{out}")
                else:
                    self._log("ERREUR : Aucun texte extrait.")
                    messagebox.showerror("Erreur", "Aucun texte extrait (PDF scanne ou protege ?).")
            else:
                outdir  = sortie if os.path.isdir(sortie) else os.path.dirname(sortie)
                succes, erreurs = [], []
                if fusion:
                    blocs = []
                    for p in self.var_pdfs:
                        self._log(f"\n--- {os.path.basename(p)} ---")
                        try:
                            c = convertir_md(p, log=self._log)
                            if c.strip(): blocs.append(f"---\n\n# {Path(p).stem}\n\n{c}")
                            else: erreurs.append((p, "Vide"))
                        except Exception as e: erreurs.append((p, str(e)))
                    if blocs:
                        nom = os.path.join(outdir, "fusion.md")
                        Path(nom).write_text(re.sub(r'\n{4,}','\n\n\n',"\n\n".join(blocs)), encoding="utf-8")
                        succes.append(nom)
                        self._log(f"Fusion : {nom}")
                else:
                    for p in self.var_pdfs:
                        self._log(f"\n--- {os.path.basename(p)} ---")
                        nom = os.path.join(outdir, Path(p).stem + ".md")
                        try:
                            c = convertir_md(p, log=self._log)
                            if c.strip():
                                Path(nom).write_text(c, encoding="utf-8")
                                succes.append(nom); self._log(f"OK : {os.path.basename(nom)}")
                            else: erreurs.append((p, "Vide"))
                        except Exception as e: erreurs.append((p, str(e)))
                msg = f"{len(succes)} fichier(s) genere(s)"
                if erreurs:
                    msg += "\nErreurs :\n" + "\n".join(f"  {os.path.basename(p)}: {e}" for p, e in erreurs)
                (messagebox.showinfo if succes else messagebox.showerror)("Termine", msg)
        except Exception as e:
            self._log(f"ERREUR : {e}")
            messagebox.showerror("Erreur inattendue", str(e))
        self._refresh()


# ── Onglet Markdown -> PDF ───────────────────────────────────────────────────

class TabMDPDF(tk.Frame):
    def __init__(self, parent, root):
        super().__init__(parent)
        self.root     = root
        self.var_mds  = []
        self.var_sortie = tk.StringVar()
        self.var_fusion = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        tk.Label(self, text="Convertit un ou plusieurs fichiers .md en PDF soigné "
                 "(titres, listes, tableaux, gras, italique).",
                 fg="gray", wraplength=580, justify="left").pack(
            anchor="w", padx=14, pady=(10, 6))

        fr = tk.LabelFrame(self, text="Fichiers Markdown", padx=10, pady=6)
        fr.pack(fill="x", padx=14, pady=(0, 8))

        fr_lst = tk.Frame(fr)
        fr_lst.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.lst = tk.Listbox(fr_lst, width=56, height=4, selectmode=tk.EXTENDED)
        self.lst.pack(side="left")
        sb = tk.Scrollbar(fr_lst, orient="vertical", command=self.lst.yview)
        sb.pack(side="left", fill="y")
        self.lst.config(yscrollcommand=sb.set)

        fr_b = tk.Frame(fr)
        fr_b.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        for txt, cmd in [("Ajouter .md...", self._ajouter),
                         ("Retirer", self._retirer),
                         ("Vider", self._vider)]:
            tk.Button(fr_b, text=txt, command=cmd).pack(side="left", padx=(0, 6))

        row_field(fr, "Dossier / fichier de sortie :", self.var_sortie, self._sortie, 1)

        tk.Checkbutton(fr, text="Fusionner tous les .md dans un seul fichier PDF",
                       variable=self.var_fusion).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.btn = tk.Button(self, text="Convertir en PDF", command=self._lancer,
                             bg="#6a1b9a", fg="white",
                             font=("Segoe UI", 10, "bold"), pady=7, state="disabled")
        self.btn.pack(pady=8)

        fr_log = tk.LabelFrame(self, text="Journal", padx=2, pady=2)
        fr_log.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log = make_log(fr_log)

    def _log(self, msg): log_write(self.log, msg, self.root)

    def _ajouter(self):
        chemins = filedialog.askopenfilenames(title="Selectionner des fichiers Markdown",
            filetypes=[("Markdown", "*.md"), ("Tous", "*.*")])
        for c in chemins:
            if c not in self.var_mds:
                self.var_mds.append(c)
                self.lst.insert(tk.END, os.path.basename(c))
        self._refresh()
        if chemins and not self.var_sortie.get():
            self.var_sortie.set(os.path.dirname(chemins[0]))

    def _retirer(self):
        for i in reversed(self.lst.curselection()):
            self.lst.delete(i); self.var_mds.pop(i)
        self._refresh()

    def _vider(self):
        self.lst.delete(0, tk.END); self.var_mds.clear(); self._refresh()

    def _sortie(self):
        if len(self.var_mds) == 1 and not self.var_fusion.get():
            c = filedialog.asksaveasfilename(title="Enregistrer le PDF",
                defaultextension=".pdf",
                initialfile=Path(self.var_mds[0]).stem + ".pdf",
                filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")])
            if c: self.var_sortie.set(c)
        else:
            d = filedialog.askdirectory(title="Dossier de sortie")
            if d: self.var_sortie.set(d)

    def _refresh(self):
        n = len(self.var_mds)
        self.btn.config(
            state="normal" if n else "disabled",
            text=f"Convertir ({n} fichier{'s' if n>1 else ''}) en PDF" if n else "Convertir en PDF")

    def _lancer(self):
        if not self.var_mds: return
        sortie = self.var_sortie.get().strip()
        if not sortie:
            messagebox.showwarning("Attention", "Choisissez un fichier ou dossier de sortie."); return
        self.log.delete("1.0", tk.END)
        self.btn.config(state="disabled")
        self._log("=== Markdown -> PDF ===")
        fusion = self.var_fusion.get()
        try:
            if len(self.var_mds) == 1 and not fusion:
                p   = self.var_mds[0]
                out = sortie if sortie.endswith(".pdf") else                       os.path.join(sortie, Path(p).stem + ".pdf")
                self._log(f"Fichier : {os.path.basename(p)}")
                ok, res = md_vers_pdf(p, out, self._log)
                if ok:
                    self._log(f"Termine : {os.path.basename(res)}")
                    messagebox.showinfo("Succes", f"PDF genere :\n{res}")
                else:
                    self._log(f"ERREUR : {res}")
                    messagebox.showerror("Erreur", res)
            else:
                outdir = sortie if os.path.isdir(sortie) else os.path.dirname(sortie)
                succes, erreurs = convertir_md_pdf_lot(self.var_mds, outdir, fusion, self._log)
                msg = f"{len(succes)} fichier(s) genere(s)"
                if erreurs:
                    msg += "\nErreurs :\n" + "\n".join(f"  {os.path.basename(p)}: {e}" for p, e in erreurs)
                (messagebox.showinfo if succes else messagebox.showerror)("Termine", msg)
        except Exception as e:
            self._log(f"ERREUR : {e}")
            messagebox.showerror("Erreur inattendue", str(e))
        self._refresh()


# =============================================================================
# FENETRE PRINCIPALE
# =============================================================================

def lancer_app():
    root = tk.Tk()
    root.title("EscriTools — LREGE Grand Est")
    root.resizable(True, True)
    root.minsize(640, 580)

    # Style onglets
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[14, 6])

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    tab1 = TabFFF(nb, root)
    tab2 = TabMD(nb, root)
    tab3 = TabMDPDF(nb, root)
    nb.add(tab1, text="  BellePoule → FFF  ")
    nb.add(tab2, text="  PDF → Markdown  ")
    nb.add(tab3, text="  Markdown → PDF  ")

    # Pied de page
    tk.Label(root, text="EscriTools v1.0  —  LREGE Grand Est",
             fg="gray", font=("Segoe UI", 8)).pack(side="bottom", pady=(0, 6))

    root.mainloop()


if __name__ == "__main__":
    lancer_app()


