"""
parser.py — Lecture des fichiers HTML de classement BellePoule (Master M11/M13)
"""
import re
from bs4 import BeautifulSoup


def saison_debut(aujourdhui=None):
    """Année de début de la saison en cours (bascule au 1er septembre)."""
    import datetime as _dt
    t = aujourdhui or _dt.date.today()
    return t.year if t.month >= 9 else t.year - 1


def annee_min_m11(aujourdhui=None):
    """Année de naissance minimale M11 : saison 2025-2026 → nés >= 2015.
    Dérivée automatiquement (début de saison - 10) — plus de mise à jour annuelle."""
    return saison_debut(aujourdhui) - 10



TERRITOIRES = {
    "alsace": "Alsace",
    "lorraine": "Lorraine",
    "champagne": "Champagne-Ardenne",
    "champagne-ardenne": "Champagne-Ardenne",
    "champagne ardenne": "Champagne-Ardenne",
    "grand est": "Grand Est",
}

# Patterns exacts pour détection dans le titre structuré (ex: "EHM13, Origine du tireur Lorraine")
# Priorité : plus spécifique en premier
_TERRITOIRE_PATTERNS = [
    ("champagne-ardenne", "Champagne-Ardenne"),
    ("champagne ardenne", "Champagne-Ardenne"),
    ("champagne",         "Champagne-Ardenne"),
    ("grand est",         "Grand Est"),
    ("lorraine",          "Lorraine"),
    ("alsace",            "Alsace"),
]

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


def _detecter_territoire_titre(titre: str):
    """
    Détection stricte dans le titre structuré BellePoule.
    Cherche le territoire APRÈS la virgule (ex: "EHM13, Origine du tireur Lorraine").
    Évite les faux positifs dus aux noms de clubs.
    """
    # Chercher dans la partie après la virgule si présente
    parties = titre.split(",", 1)
    zone = parties[1] if len(parties) > 1 else titre
    zone_lower = zone.lower()
    for pattern, val in _TERRITOIRE_PATTERNS:
        if pattern in zone_lower:
            return val
    return None


def _detecter_territoire_cid(cid: str):
    """
    Détection dans le champ CID du tableau compétition (ex: "Lorraine", "Alsace").
    Le CID est un champ structuré court — peu de risque de faux positif.
    """
    cid_lower = cid.strip().lower()
    for pattern, val in _TERRITOIRE_PATTERNS:
        if pattern in cid_lower:
            return val
    return None


def _detecter_territoire(texte: str):
    """
    Détection en dernier recours dans le texte libre.
    UNIQUEMENT utilisée si titre + CID n'ont rien trouvé.
    Risque de faux positif (nom de club contenant un territoire) — accepté en fallback.
    """
    texte_lower = texte.lower()
    for pattern, val in _TERRITOIRE_PATTERNS:
        if pattern in texte_lower:
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

    territoire = _detecter_territoire_titre(titre)
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
        raise ParseurError(
            "Tableau 'Classement général' introuvable dans le fichier compétition.",
            hint="Vérifiez que le fichier contient bien un classement général BellePoule."
        )
    if not arme or not genre or not categorie:
        manquants = [n for n, v in [("arme", arme), ("genre", genre), ("catégorie", categorie)] if not v]
        raise ParseurError(
            f"Impossible de détecter : {', '.join(manquants)} dans le fichier compétition.",
            hint="Les titres H1 doivent contenir 'Épée/Fleuret/Sabre', 'Hommes/Dames', 'M11/M13'."
        )

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
            territoire = _detecter_territoire_cid(cid)

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


class ParseurError(ValueError):
    """
    Erreur de parsing BellePoule avec message lisible pour l'utilisateur.
    Contient un champ `hint` pour guider la correction.
    """
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint

    def __str__(self):
        base = super().__str__()
        return f"{base} — {self.hint}" if self.hint else base


def _valider_html(soup):
    """
    Vérifie que le fichier HTML est bien un export BellePoule reconnu.
    Lève ParseurError avec un message précis si un élément attendu est absent.
    """
    # Vérifier qu'il y a bien du contenu
    if not soup or not soup.body:
        raise ParseurError(
            "Le fichier HTML est vide ou illisible.",
            hint="Vérifiez que le fichier n'est pas corrompu."
        )
    # Vérifier la présence d'un marqueur BellePoule
    has_bellepoule = (
        soup.find('table', id='TableClsst') is not None
        or soup.find('div', class_='Round') is not None
        or any('bellepoule' in str(s).lower() for s in soup.find_all('script'))
    )
    if not has_bellepoule:
        raise ParseurError(
            "Ce fichier ne ressemble pas à un export BellePoule.",
            hint="Utilisez le fichier HTML de classement exporté depuis BellePoule."
        )


def parser_html(contenu_bytes):
    """
    Parse un fichier HTML de classement BellePoule.
    Retourne un dict avec métadonnées + liste de tireurs.
    Lève ParseurError avec un message précis si le fichier est invalide.
    """
    # Décodage
    try:
        content = contenu_bytes.decode('utf-8')
    except UnicodeDecodeError:
        content = contenu_bytes.decode('latin-1')
    except Exception as e:
        raise ParseurError(
            f"Impossible de lire le fichier : {e}",
            hint="Vérifiez que le fichier est bien un HTML BellePoule."
        )

    try:
        soup = BeautifulSoup(content, 'html.parser')
    except Exception as e:
        raise ParseurError(f"Erreur de parsing HTML : {e}")

    # Validation générale
    _valider_html(soup)

    # Détecter le format et dispatcher
    fmt = _detecter_format(soup)
    if fmt == 'competition':
        return _parser_format_competition(soup)

    # Titre (format cumulatif)
    titre = soup.title.string if soup.title else ""
    arme, genre, categorie, territoire = _parser_titre(titre)

    # Fallback : cherche dans le body UNIQUEMENT si le titre n'a rien trouvé
    # Limité au premier ko pour éviter les faux positifs sur les noms de clubs
    if not territoire:
        body_text = soup.get_text()[:2000]
        territoire = _detecter_territoire(body_text)

    # Validation : titre doit avoir permis de détecter arme/genre/catégorie
    manquants = []
    if not arme:      manquants.append("arme (E/F/S)")
    if not genre:     manquants.append("genre (H/D)")
    if not categorie: manquants.append("catégorie (M11/M13)")
    if manquants:
        raise ParseurError(
            f"Titre HTML non reconnu — impossible de détecter : {', '.join(manquants)}.",
            hint=f"Titre lu : '{titre}'. Attendu : 'EHM13, Origine du tireur Lorraine' ou similaire."
        )

    table = soup.find('table', id='TableClsst')
    if not table:
        raise ParseurError(
            "Tableau de classement 'TableClsst' introuvable.",
            hint="Ce fichier est peut-être un résultat de compétition et non un classement cumulatif."
        )

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
        raise ParseurError(
            "Ligne d'en-tête 'Place' introuvable dans le tableau BellePoule.",
            hint="La structure du tableau a peut-être changé. Vérifiez la version de BellePoule."
        )
    if len(rows) <= header_idx + 1:
        raise ParseurError(
            "Aucun tireur trouvé dans le tableau.",
            hint="Le fichier est peut-être vide ou le classement n'a pas encore été généré."
        )

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
                # M11 = nés à partir de (début de saison - 10) — ex. saison
                # 2025-2026 → nés >= 2015. Calculé automatiquement.
                annee = int(annee_naissance)
                if annee >= annee_min_m11():
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

    if not tireurs:
        raise ParseurError(
            "Aucun tireur extrait du fichier.",
            hint="Vérifiez que le classement contient bien des données de tireurs."
        )

    return {
        "arme": arme,
        "genre": genre,
        "categorie": categorie,
        "territoire": territoire,
        "dates_competitions": dates_competitions,
        "nb_competitions": nb_competitions,
        "tireurs": tireurs,
    }
