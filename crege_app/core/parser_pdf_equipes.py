"""
parser_pdf_equipes.py — Parsers PDF pour les équipes CDF.

Deux formats supportés :
  1. Engarde  : résultats championnat régional Grand Est
  2. FFE      : liste officielle équipes qualifiées CDF
"""
import re
import pdfplumber


GRAND_EST_KEYWORDS = ["grand est", "grand-est", "ges"]

def _est_grand_est_ligue(ligue: str) -> bool:
    return any(k in ligue.lower() for k in GRAND_EST_KEYWORDS)


def _parse_engarde(texte: str) -> list:
    """Parse Engarde : noms complets depuis liste initiale + ordre depuis classement final."""
    lignes = texte.splitlines()

    # Extraire liste initiale : ri → {nom_equipe, club}
    ri_map = {}
    pat_ri = re.compile(r'^(\d+)\s+#{4}\s+(.+)$')
    in_liste = False
    for l in lignes:
        if "équipes (présentes" in l.lower():
            in_liste = True
            continue
        if not in_liste:
            continue
        ls = l.strip()
        if ls.startswith("Document") or ls.startswith("r.i.") or not ls:
            continue
        if not ls[0].isdigit():
            continue
        m = pat_ri.match(ls)
        if m:
            ri = m.group(1)
            mots = m.group(2).strip().split()
            # Code club = dernier(s) token(s) tout-majuscules courts
            idx = len(mots)
            for j in range(len(mots)-1, -1, -1):
                if re.match(r'^[A-Z]+$', mots[j]) and len(mots[j]) <= 5:
                    idx = j
                else:
                    break
            nom  = " ".join(mots[:idx]).strip()
            club = " ".join(mots[idx:]).strip()
            if nom:
                ri_map[ri] = {"nom_equipe": nom, "club": club}

    # Lire classement final
    pat_rang = re.compile(r'^(\d+)\s+(.+)$')
    in_class = False
    equipes  = []
    for l in lignes:
        if "classement général" in l.lower():
            in_class = True
            continue
        if not in_class:
            continue
        ls = l.strip()
        if not ls or ls.startswith("Document") or ls.startswith("rang"):
            continue
        m = pat_rang.match(ls)
        if not (m and m.group(1).isdigit()):
            continue
        rang_f   = m.group(1)
        nom_court = m.group(2).strip().rsplit(None, 1)[0].strip()
        # Matcher contre ri_map
        meilleur, score_max = None, 0
        for info in ri_map.values():
            score = sum(1 for a, b in zip(info["nom_equipe"].upper(), nom_court.upper()) if a == b)
            if score > score_max:
                score_max, meilleur = score, info
        if meilleur and score_max >= 4:
            equipes.append({"rang": rang_f, "nom_equipe": meilleur["nom_equipe"], "club": meilleur["club"]})
        else:
            equipes.append({"rang": rang_f, "nom_equipe": nom_court, "club": ""})
    return equipes


def _parse_ffe(texte: str) -> dict:
    """Parse liste FFE. Filtre automatique Grand Est."""
    lignes = texte.splitlines()
    categorie = ""
    for l in lignes:
        if any(k in l for k in ["Epée","Epee","Fleuret","Sabre"]):
            if any(k in l for k in ["M17","M20","Senior","Sénior","Vétéran","Dame","Homme"]):
                categorie = l.strip(); break

    LIGUES = ["ILE DE FRANCE","HAUTS DE FRANCE","GRAND EST","AUVERGNE RHONE ALPES",
              "OCCITANIE","NOUVELLE AQUITAINE","BRETAGNE","NORMANDIE","PAYS DE LA LOIRE",
              "SUD","BOURGOGNE FRANCHE COMTE","CENTRE VAL DE LOIRE","CORSE",
              "GUADELOUPE","GUYANE","MARTINIQUE","LA REUNION","NOUVELLE CALEDONIE"]

    def extraire_ligue(rest):
        for lk in sorted(LIGUES, key=len, reverse=True):
            if rest.upper().endswith(lk):
                return rest[:-len(lk)].strip(), lk
        parts = rest.rsplit(None, 3)
        return (parts[0] if len(parts)>1 else rest), " ".join(parts[1:])

    pat = re.compile(r'^(\d+)\s+(.+)$')
    in_n1n2 = in_n3 = False
    niveau_courant = "N1"
    n1, n2, n3 = [], [], []
    for l in lignes:
        ls = l.strip()
        if not ls: continue
        ls_low = ls.lower()
        # "Nationale 1" → section N1
        if "nationale 1" in ls_low and "3" not in ls:
            in_n1n2, in_n3 = True, False; niveau_courant = "N1"; continue
        # "Nationale 2" seule → section N2
        if ls_low.startswith("nationale 2") and not in_n3:
            in_n1n2 = True; niveau_courant = "N2"; continue
        if "nationale 3" in ls_low: in_n1n2, in_n3 = False, True; continue
        if not (in_n1n2 or in_n3): continue
        if ls_low.startswith(("rang","club","ligue","[règlement","*mode","version","les équipes")): continue
        m = pat.match(ls)
        if not m: continue
        rang = m.group(1)
        club, ligue = extraire_ligue(m.group(2).strip())
        entry = {"rang": rang, "nom_equipe": club, "club": club, "ligue": ligue, "niveau": niveau_courant}
        if in_n3:          n3.append(entry)
        elif niveau_courant == "N2": n2.append(entry)
        else:              n1.append(entry)

    n1n2 = n1 + n2  # rétrocompat

    return {
        "n1":      n1,
        "n2":      n2,
        "n1n2":    n1n2,
        "n3":      n3,
        "n1n2_ge": [e for e in n1n2 if _est_grand_est_ligue(e["ligue"])],
        "n1_ge":   [e for e in n1   if _est_grand_est_ligue(e["ligue"])],
        "n2_ge":   [e for e in n2   if _est_grand_est_ligue(e["ligue"])],
        "n3_ge":   [e for e in n3   if _est_grand_est_ligue(e["ligue"])],
        "categorie": categorie,
    }


def detecter_format(texte: str) -> str:
    if "engarde-escrime.com" in texte.lower(): return "engarde"
    if "liste des équipes qualifiées" in texte.lower(): return "ffe"
    if "nationale 1" in texte.lower() and "ligue" in texte.lower(): return "ffe"
    return "inconnu"


def parser_pdf_equipes(chemin_pdf: str) -> dict:
    with pdfplumber.open(chemin_pdf) as pdf:
        texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
    fmt = detecter_format(texte)
    if fmt == "engarde":
        eq = _parse_engarde(texte)
        return {"format": "engarde", "equipes": eq, "nb": len(eq)}
    elif fmt == "ffe":
        d = _parse_ffe(texte)
        return {"format": "ffe", **d}
    return {"format": "inconnu", "erreur": "Format PDF non reconnu"}

def parser_pdf_equipes_pages(path: str) -> list:
    """Parse un PDF équipes multi-pages (vétérans).
    Retourne une liste de dicts — un par page — avec le texte réglementaire.
    """
    results = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lignes = [l.strip() for l in text.splitlines() if l.strip()]
            d = _parse_ffe_lignes(lignes)
            if d["n1n2"] or d["n3"]:
                results.append(d)
    return results


def _parse_ffe_lignes(lignes: list) -> dict:
    """Parse une liste de lignes texte (format FFE) et retourne le dict standard."""
    LIGUES = ["ILE DE FRANCE","HAUTS DE FRANCE","GRAND EST","AUVERGNE RHONE ALPES",
              "OCCITANIE","NOUVELLE AQUITAINE","BRETAGNE","NORMANDIE","PAYS DE LA LOIRE",
              "REGION SUD","BOURGOGNE FRANCHE COMTE","CENTRE VAL DE LOIRE","CORSE",
              "GUADELOUPE","GUYANE","MARTINIQUE","LA REUNION","NOUVELLE CALEDONIE",
              "HAUT DE FRANCE"]

    # Catégorie
    categorie = ""
    for l in lignes:
        if any(k in l for k in ["Epée","Epee","Fleuret","Sabre"]):
            if any(k in l for k in ["M17","M20","Sénior","Senior","Vétéran","Dame","Homme","Grand"]):
                categorie = l.strip(); break

    # Texte réglementaire (mention "pour pouvoir prétendre...")
    texte_reg = ""
    for i, l in enumerate(lignes):
        if "pour pouvoir pr" in l.lower():
            texte_reg = " ".join(lignes[i:i+4])
            break

    def extraire_ligue(rest):
        for lk in sorted(LIGUES, key=len, reverse=True):
            ru = rest.upper()
            if ru.endswith(lk) or ru == lk:
                club = rest[:len(rest)-len(lk)].strip() or lk
                return club, lk
        parts = rest.rsplit(None, 3)
        return (parts[0] if len(parts)>1 else rest), " ".join(parts[1:])

    pat = re.compile(r'^(\d+)\s+(.+)$')
    in_n1n2 = in_n3 = False
    niveau_courant = "N1"
    n1, n2, n3 = [], [], []
    for l in lignes:
        ls = l.strip()
        if not ls: continue
        ls_low = ls.lower()
        if "nationale 1" in ls_low and "3" not in ls:
            in_n1n2, in_n3 = True, False; niveau_courant = "N1"; continue
        if ls_low.startswith("nationale 2") and not in_n3:
            in_n1n2 = True; niveau_courant = "N2"; continue
        if "nationale 3" in ls_low: in_n1n2, in_n3 = False, True; continue
        if not (in_n1n2 or in_n3): continue
        if ls_low.startswith(("rang","club","ligue","[règlement","*mode","version",
                               "les équipes","pour pouvoir","saison","liste")): continue
        m = pat.match(ls)
        if not m: continue
        rang = m.group(1)
        club, ligue = extraire_ligue(m.group(2).strip())
        entry = {"rang": rang, "nom_equipe": club, "club": club,
                 "ligue": ligue, "niveau": niveau_courant}
        if in_n3: n3.append(entry)
        elif niveau_courant == "N2": n2.append(entry)
        else: n1.append(entry)

    n1n2 = n1 + n2
    return {
        "n1": n1, "n2": n2, "n1n2": n1n2, "n3": n3,
        "n1n2_ge": [e for e in n1n2 if _est_grand_est_ligue(e["ligue"])],
        "n1_ge":   [e for e in n1   if _est_grand_est_ligue(e["ligue"])],
        "n2_ge":   [e for e in n2   if _est_grand_est_ligue(e["ligue"])],
        "n3_ge":   [e for e in n3   if _est_grand_est_ligue(e["ligue"])],
        "categorie": categorie,
        "texte_reglementaire": texte_reg,
    }



def parser_pdf_indiv_veterans(path: str) -> dict:
    """Parse un PDF individuel vétérans multi-pages (V1/V2/V3).
    Retourne un dict {cat_id: {df, tireurs_ge, cat_label}} par catégorie.
    """
    import tempfile, os, pdfplumber
    from pypdf import PdfWriter, PdfReader
    from importer_classements_pdf import lire_classement_ffe_pdf
    from crege_app.core.utils import est_grand_est

    CATS_LABELS = {"Vétéran 1": "V1", "Vétéran 2": "V2",
                   "Vétéran 3": "V3", "Vétéran 4": "V4"}

    reader = PdfReader(path)
    results = {}

    for i, page_pdf in enumerate(reader.pages):
        # Identifier la catégorie
        with pdfplumber.open(path) as plumb:
            text = plumb.pages[i].extract_text() or ""
        lignes = [l.strip() for l in text.splitlines() if l.strip()]
        cat_label = next((l for l in lignes if l in CATS_LABELS), None)
        if not cat_label:
            continue
        cat_id = CATS_LABELS[cat_label]

        # Extraire la page en PDF temporaire
        writer = PdfWriter()
        writer.add_page(page_pdf)
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        tmp.close()  # ← FERMER le handle AVANT d'écrire
        
        with open(tmp_path, 'wb') as f:
            writer.write(f)

        df = lire_classement_ffe_pdf(tmp_path)
        
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass  # Fichier sera nettoyé par le système tempfile

        col_reg = "Region" if "Region" in df.columns else "Ligue Régionale"
        ge = df[df[col_reg].apply(est_grand_est)] if col_reg in df.columns else df.iloc[0:0]

        results[cat_id] = {
            "cat_id":    cat_id,
            "cat_label": cat_label,
            "df":        df,
            "tireurs_ge": ge,
            "nb_total":  len(df),
            "nb_ge":     len(ge),
        }

    return results
