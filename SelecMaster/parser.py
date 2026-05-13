"""
parser.py — Lecture des fichiers HTML de classement BellePoule (Master M11/M13)
"""
import re
from bs4 import BeautifulSoup


TERRITOIRES = {
    "alsace": "Alsace",
    "lorraine": "Lorraine",
    "champagne": "Champagne-Ardenne",
    "champagne-ardenne": "Champagne-Ardenne",
    "champagne ardenne": "Champagne-Ardenne",
    "grand est": "Grand Est",
}

ARMES = {
    "E": "Épée",
    "F": "Fleuret",
    "S": "Sabre",
}

GENRES = {
    "H": "H",
    "D": "D",
}

CATEGORIES = {
    "M11": "M11",
    "M13": "M13",
}


def _detecter_territoire(texte):
    texte_lower = texte.lower()
    for cle, val in TERRITOIRES.items():
        if cle in texte_lower:
            return val
    return None


def _parser_titre(titre):
    """
    Extrait arme, genre, catégorie depuis le titre du fichier.
    Ex: 'EHM13, Origine du tireur Lorraine' → ('Épée', 'H', 'M13', 'Lorraine')
    Ex: 'EDM11, Comité Inter-Départemental Lorraine' → ('Épée', 'D', 'M11', 'Lorraine')
    """
    arme, genre, categorie, territoire = None, None, None, None

    # Code arme/genre/cat en début : EHM13, FDM11, etc.
    match = re.match(r'^([EFS])([HD])(M1[13])', titre.strip())
    if match:
        arme = ARMES.get(match.group(1))
        genre = GENRES.get(match.group(2))
        categorie = CATEGORIES.get(match.group(3))

    territoire = _detecter_territoire(titre)
    return arme, genre, categorie, territoire


def _trouver_classement_competition(soup):
    """
    Cherche le div contenant le classement général dans un fichier résultat.
    Retourne le tableau <table class='List'> avec colonne 'place', ou None.
    """
    for div in soup.find_all('div', class_='Round'):
        h1 = div.find('h1')
        if h1 and 'classement' in h1.get_text(strip=True).lower():
            table = div.find('table', class_='List')
            if table:
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                if 'place' in headers:
                    return table
    return None


def _detecter_format(soup):
    """Retourne 'cumulatif' ou 'competition' selon le format BellePoule."""
    if soup.find('table', id='TableClsst'):
        return 'cumulatif'
    if _trouver_classement_competition(soup):
        return 'competition'
    return 'cumulatif'  # fallback


def _parser_titre_competition(soup):
    """
    Extrait arme, genre, catégorie depuis les <h1> du format compétition.
    Ex: h1[0]="CDA Petites Catégories" h1[1]="15/03/2026" h1[2]="Sabre - Dames - M13"
    """
    h1s = [h.get_text(strip=True) for h in soup.find_all('h1')]
    arme, genre, categorie, territoire = None, None, None, None

    for h in h1s:
        h_lower = h.lower()
        # Arme
        if 'sabre' in h_lower:   arme = 'Sabre'
        if 'épée' in h_lower or 'epee' in h_lower: arme = 'Épée'
        if 'fleuret' in h_lower: arme = 'Fleuret'
        # Genre
        if 'dames' in h_lower:   genre = 'D'
        if 'hommes' in h_lower:  genre = 'H'
        # Catégorie
        if 'm13' in h_lower:     categorie = 'M13'
        if 'm11' in h_lower:     categorie = 'M11'

    # Territoire depuis colonne CID dans le tableau
    return arme, genre, categorie


def _parser_format_competition(soup):
    """
    Parse un fichier HTML résultat de compétition BellePoule (sabre Alsace).
    Retourne les mêmes champs que parser_html() pour compatibilité totale.
    """
    arme, genre, categorie = _parser_titre_competition(soup)

    table = _trouver_classement_competition(soup)
    if not table:
        raise ValueError("Tableau de classement introuvable (Classement général).")

    rows = table.find_all('tr')

    # Détecter territoire depuis la première ligne de données (colonne CID)
    territoire = None
    tireurs = []
    vus = set()

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if not cells or not cells[0].isdigit():
            continue

        # place | nom | prénom | club | CID | région | nation
        place  = int(cells[0])
        nom    = cells[1] if len(cells) > 1 else ''
        prenom = cells[2] if len(cells) > 2 else ''
        club   = cells[3] if len(cells) > 3 else ''
        cid    = cells[4] if len(cells) > 4 else ''

        if not territoire and cid:
            territoire = _detecter_territoire(cid)

        # Dédupliquer (ex: ex-aequo en double dans certains exports)
        cle = (place, nom.upper(), prenom.upper())
        if cle not in vus:
            vus.add(cle)
            tireurs.append({
                "place":           place,
                "nom":             nom,
                "prenom":          prenom,
                "club":            club,
                "annee_naissance": '',
                "points_total":    0.0,
                "participations":  1,
                "resultats":       [],
                "est_m11_dans_m13": False,
            })

    return {
        "arme":              arme,
        "genre":             genre,
        "categorie":         categorie,
        "territoire":        territoire,
        "dates_competitions": [],
        "nb_competitions":   1,
        "tireurs":           tireurs,
        "format":            "competition",
    }


def parser_html(contenu_bytes):
    """
    Parse un fichier HTML de classement BellePoule.
    Retourne un dict avec métadonnées + liste de tireurs.
    """
    # Essayer utf-8 puis latin-1
    try:
        content = contenu_bytes.decode('utf-8')
    except UnicodeDecodeError:
        content = contenu_bytes.decode('latin-1')

    soup = BeautifulSoup(content, 'html.parser')

    # Détecter le format et dispatcher
    fmt = _detecter_format(soup)
    if fmt == 'competition':
        return _parser_format_competition(soup)

    # Titre (format cumulatif)
    titre = soup.title.string if soup.title else ""
    arme, genre, categorie, territoire = _parser_titre(titre)

    # Titre alternatif dans le body si titre absent
    if not territoire:
        body_text = soup.get_text()
        territoire = _detecter_territoire(body_text)

    table = soup.find('table', id='TableClsst')
    if not table:
        raise ValueError("Tableau 'TableClsst' introuvable dans le fichier HTML.")

    rows = table.find_all('tr')

    # Trouver la ligne d'en-tête des données (Place, Nom, Prénom...)
    header_idx = None
    dates_competitions = []

    for i, row in enumerate(rows):
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if cells and cells[0] == 'Place':
            header_idx = i
        # Récupérer les dates des compétitions
        if cells and cells[0].startswith('Date'):
            dates_competitions = cells[1:]

    if header_idx is None:
        raise ValueError("Ligne d'en-tête 'Place' introuvable dans le tableau.")

    nb_competitions = len(dates_competitions)

    # Parser les tireurs (lignes après l'en-tête)
    tireurs = []
    for row in rows[header_idx + 1:]:
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if not cells or not cells[0].isdigit():
            continue

        # Structure : Place | Nom | Prénom | Club | Année Nais. | Points total | Rang1 | Pts1 | Rang2 | Pts2 ...
        place = int(cells[0])
        nom = cells[1]
        prenom = cells[2]
        club = cells[3]
        annee_naissance = cells[4] if len(cells) > 4 else ""
        points_total = cells[5].replace(',', '.') if len(cells) > 5 else "0"
        try:
            points_total = float(points_total)
        except ValueError:
            points_total = 0.0

        # Compter les participations (paires Rang/Pts non vides)
        participations = 0
        resultats_competitions = []
        idx = 6
        for _ in range(nb_competitions):
            if idx + 1 < len(cells):
                rang = cells[idx]
                pts = cells[idx + 1]
                if rang and pts:
                    participations += 1
                    try:
                        resultats_competitions.append({
                            "rang": int(rang),
                            "points": float(pts.replace(',', '.'))
                        })
                    except ValueError:
                        resultats_competitions.append({"rang": None, "points": 0.0})
                else:
                    resultats_competitions.append(None)
            idx += 2

        # Détection M11 dans fichier M13 (année naissance >= année M11)
        est_m11_dans_m13 = False
        if categorie == "M13" and annee_naissance:
            try:
                # M11 = nés en 2015 ou 2016 pour saison 2025-2026
                annee = int(annee_naissance)
                if annee >= 2015:
                    est_m11_dans_m13 = True
            except ValueError:
                pass

        tireurs.append({
            "place": place,
            "nom": nom,
            "prenom": prenom,
            "club": club,
            "annee_naissance": annee_naissance,
            "points_total": points_total,
            "participations": participations,
            "resultats": resultats_competitions,
            "est_m11_dans_m13": est_m11_dans_m13,
        })

    return {
        "arme": arme,
        "genre": genre,
        "categorie": categorie,
        "territoire": territoire,
        "dates_competitions": dates_competitions,
        "nb_competitions": nb_competitions,
        "tireurs": tireurs,
    }
