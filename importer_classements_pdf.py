"""
importer_classements_pdf.py — Parseur PDF FFE pour listes de qualifiés
Format : Documents officiels FFE (Championnats de France individuels)
Structure : Nom | Prénom | Date naiss. | Adhérent | Comité Régional | Club
"""
import re
import pdfplumber
import pandas as pd


# ── Correspondance régions FFE → Grand Est ────────────────────────────
REGION_GRAND_EST = {"GRAND EST", "GES - GRAND EST"}


def _est_grand_est(region: str) -> bool:
    r = region.upper().strip()
    return r in REGION_GRAND_EST or "GRAND EST" in r


def _parse_page(page) -> tuple:
    """
    Parse une page via les positions X des mots.
    Retourne (tireurs: list[dict], niveau: str|None)
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return [], None

    # Regrouper par ligne (y arrondi à 5px)
    lines_dict = {}
    for w in words:
        y = round(w["top"] / 5) * 5
        lines_dict.setdefault(y, []).append(w)
    lines = [(y, sorted(ws, key=lambda w: w["x0"])) for y, ws in sorted(lines_dict.items())]

    # Trouver la ligne header Nom/Prénom
    header_y = None
    col_bounds = {}
    for y, ws in lines:
        texts = [w["text"] for w in ws]
        if "Nom" in texts and "Prénom" in texts:
            header_y = y
            for w in ws:
                col_bounds[w["text"]] = w["x0"]
            break

    if not header_y:
        return [], None

    # Détecter le niveau (Nationale 1, 2, 3…)
    niveau = None
    for y, ws in lines:
        if y >= header_y:
            break
        txt = " ".join(w["text"] for w in ws)
        m = re.search(r"Nationale\s+(\d+)", txt, re.IGNORECASE)
        if m:
            niveau = f"N{m.group(1)}"
            break

    # Bornes des colonnes
    col_nom      = col_bounds.get("Nom", 0)
    col_prenom   = col_bounds.get("Prénom", 150)
    col_date     = col_bounds.get("Date", 230)
    col_comite   = col_bounds.get("Comité", 330)
    col_club     = col_bounds.get("Club", 450)

    def words_in(ws, x_min, x_max):
        return " ".join(w["text"] for w in ws if x_min <= w["x0"] < x_max)

    tireurs = []
    for y, ws in lines:
        if y <= header_y:
            continue
        nom    = words_in(ws, col_nom,    col_prenom)
        prenom = words_in(ws, col_prenom, col_date)
        region = words_in(ws, col_comite, col_club)
        club   = words_in(ws, col_club,   9999)

        # Valider : nom commence par une majuscule accentuée possible
        if nom and re.match(r"^[A-ZÀ-Ÿ]", nom):
            tireurs.append({
                "rang":    len(tireurs) + 1,
                "nom":     nom.strip(),
                "prenom":  prenom.strip(),
                "region":  region.strip(),
                "club":    club.strip(),
            })

    return tireurs, niveau


def lire_classement_pdf(path: str) -> dict:
    """
    Lit un PDF FFE liste de qualifiés.
    Retourne un dict {niveau: DataFrame} avec niveaux = 'N1', 'N2', etc.
    Chaque DataFrame a les colonnes : Rang, Nom, Prenom, Region, Nom club
    """
    sections = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tireurs, niveau = _parse_page(page)
            if niveau and tireurs:
                if niveau not in sections:
                    sections[niveau] = []
                sections[niveau].extend(tireurs)

    result = {}
    for niveau, rows in sections.items():
        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "rang":   "Rang",
            "nom":    "Nom",
            "prenom": "Prenom",
            "region": "Region",
            "club":   "Nom club",
        })
        result[niveau] = df

    return result


def _parse_page_equipes(page) -> dict:
    """
    Parse une page de liste d'équipes FFE.
    Retourne {niveau: [equipes]} - "Nationale 1 & 2" → N1 et N2 séparés.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return {}

    lines_dict = {}
    for w in words:
        y = round(w["top"] / 5) * 5
        lines_dict.setdefault(y, []).append(w)
    lines = [(y, sorted(ws, key=lambda w: w["x0"])) for y, ws in sorted(lines_dict.items())]

    # Détecter la limite x Club|Ligue (grand saut sur première ligne de données)
    col_club_min  = 210
    col_ligue_min = 308  # défaut

    for y, ws in lines:
        if ws and re.match(r"^\d+$", ws[0]["text"]) and len(ws) >= 4:
            xs = [w["x0"] for w in ws]
            gaps = [(xs[i+1] - xs[i], i) for i in range(len(xs)-1)]
            max_gap, max_i = max(gaps, key=lambda g: g[0])
            if max_gap > 40:
                col_ligue_min = xs[max_i + 1] - 5
            break

    current_niveaux = []
    sections = {}
    in_data = False

    for y, ws in lines:
        line_txt = " ".join(w["text"] for w in ws)

        # Détecter header de section
        m = re.search(r"Nationale\s+(.*)", line_txt)
        if m and "Rang" not in line_txt and "Club" not in line_txt:
            raw = m.group(1).strip().rstrip("*").strip()
            nums = re.findall(r"\d+", raw)
            current_niveaux = [f"N{n}" for n in nums]
            in_data = False
            for niv in current_niveaux:
                sections.setdefault(niv, [])
            continue

        # Header colonnes (peut n'apparaître qu'une fois pour tout le tableau)
        if "Rang" in line_txt and "Club" in line_txt:
            in_data = True
            continue

        # Ligne de données — in_data activé dès qu'une section est détectée après le 1er header
        if current_niveaux and ws and re.match(r"^\d+$", ws[0]["text"]):
            rang  = int(ws[0]["text"])
            club  = " ".join(w["text"] for w in ws
                             if col_club_min <= w["x0"] < col_ligue_min)
            ligue = " ".join(w["text"] for w in ws
                             if w["x0"] >= col_ligue_min)
            equipe = {
                "rang": rang,
                "club": club.strip(),
                "ligue": ligue.strip(),
                "grand_est": _est_grand_est(ligue),
            }
            for niv in current_niveaux:
                sections[niv].append(equipe)

    return sections


def lire_classement_pdf_equipes(path: str) -> dict:
    """
    Lit un PDF FFE liste d'équipes.
    Retourne {niveau: list[dict(rang, club, ligue, grand_est)]}
    """
    all_sections = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            secs = _parse_page_equipes(page)
            for niv, equipes in secs.items():
                all_sections.setdefault(niv, []).extend(equipes)
    return all_sections


def extraire_ge_equipes(sections: dict) -> dict:
    """Filtre uniquement les équipes Grand Est."""
    return {
        niv: [e for e in equipes if e["grand_est"]]
        for niv, equipes in sections.items()
    }


# ════════════════════════════════════════════════════════════════════
# PARSER PDF ENGARDE — Classement général équipes (résultats régionaux)
# Format : rang | nom équipe | club | statut  (page "Classement général")
# ════════════════════════════════════════════════════════════════════

def _find_classement_page(pdf) -> list:
    """Retourne les pages contenant le classement général des équipes."""
    pages = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "Classement général" in text and "ordre des rangs" in text.lower():
            pages.append(page)
    return pages


def lire_classement_engarde_equipes(path: str) -> list:
    """
    Parse un PDF Engarde (export compétition) pour extraire le classement final des équipes.
    Retourne une liste de dict {rang, nom, club_abr} dans l'ordre du classement.
    Seules les lignes de tête d'équipe (commençant par un entier) sont extraites.
    """
    equipes = []
    with pdfplumber.open(path) as pdf:
        pages = _find_classement_page(pdf)
        if not pages:
            # Fallback : chercher la dernière page avec des rangs
            pages = [pdf.pages[-1]]

        for page in pages:
            lines = [l.strip() for l in (page.extract_text() or "").split("\n")
                     if l.strip()]
            # Ignorer header et pied de page
            for line in lines:
                # Ligne d'équipe : commence par un entier suivi du nom
                m = re.match(r"^(\d+)\s+([A-Z][A-Z0-9 '\-]+?)\s+([A-Z]{2,6})\s*", line)
                if m:
                    rang     = int(m.group(1))
                    nom      = m.group(2).strip()
                    club_abr = m.group(3).strip()
                    # Éviter les doublons (plusieurs pages)
                    if not any(e["rang"] == rang and e["nom"] == nom for e in equipes):
                        equipes.append({"rang": rang, "nom": nom, "club_abr": club_abr})

    return sorted(equipes, key=lambda e: e["rang"])


def lire_classement_ffe_pdf(path: str) -> pd.DataFrame:
    """
    Parse une liste de qualifiés CDF FFE au format PDF officiel (multi-pages, multi-niveaux).
    Chaque page peut contenir un niveau distinct (Nationale 1, Nationale 2, Nationale 3...).
    Colonnes : Nom | Prénom | Année naiss. | Adhérent | Ligue Régionale | Club
    Retourne un DataFrame avec colonnes standard + colonne 'Niveau' (N1/N2/N3).
    """
    import re as _re

    def words_in(ws, x_min, x_max):
        return " ".join(w["text"] for w in ws if w["x0"] >= x_min and w["x0"] < x_max)

    rows = []
    rang = 0
    niveau_courant = "N1"  # conservé d'une page à l'autre si pas de nouveau header

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            lines = {}
            for w in words:
                y = round(w["top"] / 4) * 4
                lines.setdefault(y, []).append(w)

            # Détecter le niveau sur cette page (Nationale 1, Nationale 2, Nationale 3)
            # Si pas de header trouvé, on conserve le niveau de la page précédente
            niveau_page = None
            for y in sorted(lines)[:15]:  # chercher dans les premières lignes
                ws_y = sorted(lines[y], key=lambda w: w["x0"])
                rt = " ".join(w["text"] for w in ws_y)
                m = _re.search(r"Nationale\s+(\d+)", rt, _re.IGNORECASE)
                if m:
                    n = int(m.group(1))
                    niveau_page = f"N{n}"
                    break
            if niveau_page is None:
                niveau_page = niveau_courant
            else:
                niveau_courant = niveau_page

            # Page de continuation sans header : démarrer directement dans la liste
            has_header = any(
                "Nom" in " ".join(w["text"] for w in sorted(lines[y], key=lambda w: w["x0"]))
                and "Prénom" in " ".join(w["text"] for w in sorted(lines[y], key=lambda w: w["x0"]))
                and "Ligue" in " ".join(w["text"] for w in sorted(lines[y], key=lambda w: w["x0"]))
                for y in sorted(lines)
            )
            in_list = not has_header
            for y in sorted(lines):
                ws_y = sorted(lines[y], key=lambda w: w["x0"])
                row_text = " ".join(w["text"] for w in ws_y)

                # Entête tableau
                if "Nom" in row_text and "Prénom" in row_text and "Ligue" in row_text:
                    in_list = True
                    continue
                # Fin de liste
                if in_list and (row_text.strip().startswith("*") or
                                "Version du" in row_text or "[Règlement" in row_text):
                    in_list = False
                    continue
                if not in_list:
                    continue

                nom    = words_in(ws_y,  19, 113).strip()
                prenom = words_in(ws_y, 113, 213).strip()
                adh    = words_in(ws_y, 260, 294).strip()
                ligue  = words_in(ws_y, 294, 423).strip()
                club   = words_in(ws_y, 423, 9999).strip()

                if not nom or not _re.match(r"\d{5,6}", adh):
                    continue

                rang += 1
                rows.append({
                    "Rang":       rang,
                    "Nom":        nom.upper().strip(),
                    "Prenom":     prenom.strip(),
                    "Nationalite": "",
                    "Region":     ligue,
                    "Nom club":   club,
                    "Adherent":   adh,
                    "Points":     0,
                    "Niveau":     niveau_page,
                })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def detecter_wildcards_ffe_pdf(path: str) -> bool:
    """
    Détecte si un PDF de liste FFE contient des Wild Cards confirmées.
    Retourne True si la mention [Wild Card] est présente sur la première page.
    """
    with pdfplumber.open(path) as pdf:
        page1_text = " ".join(w["text"] for w in pdf.pages[0].extract_words())
    return "Wild Card" in page1_text


def lire_classement_ffe_equipes_pdf(path: str) -> list:
    """
    Parse une liste d'équipes qualifiées CDF FFE (PDF officiel).
    Format : Rang | Club | Ligue Régionale, avec sections N1&2 et N3.
    Retourne une liste de dicts : rang, nom_equipe, ligue, niveau, grand_est.
    """
    import re as _re

    def words_in(ws, x_min, x_max):
        return " ".join(w["text"] for w in ws if w["x0"] >= x_min and w["x0"] < x_max)

    equipes = []
    niveau_courant = "N1N2"

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            lines = {}
            for w in words:
                y = round(w["top"] / 4) * 4
                lines.setdefault(y, []).append(w)

            in_tableau = False
            for y in sorted(lines):
                ws = sorted(lines[y], key=lambda w: w["x0"])
                row_text = " ".join(w["text"] for w in ws)

                if "Rang" in row_text and "Club" in row_text and "Ligue" in row_text:
                    in_tableau = True
                    continue

                if in_tableau and "Nationale" in row_text:
                    niveau_courant = "N3" if "3" in row_text else "N1N2"
                    continue

                if in_tableau and (row_text.strip().startswith("*") or
                                   "[Règlement" in row_text or "Version du" in row_text):
                    in_tableau = False
                    continue

                if not in_tableau:
                    continue

                rang  = words_in(ws, 140, 203).strip()
                club  = words_in(ws, 203, 308).strip()
                ligue = words_in(ws, 308, 9999).strip()

                if not rang or not _re.match(r"\d+", rang):
                    continue

                equipes.append({
                    "rang":       int(rang),
                    "nom_equipe": club,
                    "ligue":      ligue,
                    "niveau":     niveau_courant,
                    "grand_est":  "GRAND EST" in ligue.upper() or "GES" in ligue.upper(),
                })

    return equipes
