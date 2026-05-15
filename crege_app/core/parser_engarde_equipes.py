"""
parser_engarde_equipes.py — Parsers FFF et XML Engarde pour équipes.

Format FFF par_equipes (ex: CGE_FHS_equ.fff) :
  L1 : FFF;WIN;competition;CLUB_EQUIPE_PAR_DEF;par_equipes
  L2 : DATE;ARME;GENRE;CAT;NOM_COMP;CODE_COMP
  L3+: NOM,PRENOM,DDN,GENRE,NAT,,NOM_EQUIPE;...;LICENCE,REGION,CLUB,...;RANG_EQUIPE,

Format FFF individuel résultats (ex: EQUIPE_...fff) :
  L1 : FFF;WIN;competition;;individuel
  L2 : DATE;ARME;GENRE;CAT;NOM_COMP;CODE_COMP
  L3+: NOM_EQUIPE,,,GENRE,NAT,;...;,REGION,CLUB,SCORE,...;RANG,t

Format XML Engarde par équipes :
  <BaseCompetition>
    <Equipe ID="..." Nom="..." Club="..." NomClub="..." ClassementFinal="...">
      <Tireur .../>
    </Equipe>
  </BaseCompetition>
"""
import re
import xml.etree.ElementTree as ET
from collections import defaultdict


# ── Helpers communs ───────────────────────────────────────────────────

def _decode(raw: bytes) -> str:
    for enc in ('cp1252', 'latin-1', 'utf-8-sig', 'utf-8'):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode('latin-1', errors='replace')


def _info_header(ligne2: str) -> dict:
    """Parse la 2ème ligne FFF : date;arme;genre;cat;nom;code."""
    parts = ligne2.strip().split(';')
    return {
        'date':  parts[0] if len(parts) > 0 else '',
        'arme':  parts[1] if len(parts) > 1 else '',
        'genre': parts[2] if len(parts) > 2 else '',
        'cat':   parts[3] if len(parts) > 3 else '',
        'nom':   parts[4] if len(parts) > 4 else '',
    }


# ── Parser FFF par_equipes ────────────────────────────────────────────

def _parse_fff_par_equipes(texte: str) -> dict:
    """
    FFF par_equipes : chaque ligne = un tireur avec son équipe.
    On regroupe les tireurs par équipe et on reconstitue le classement.
    Retourne {equipes: [{rang, nom_equipe, club, tireurs:[]}], ...}
    """
    lignes  = texte.splitlines()
    if len(lignes) < 3:
        return {'format': 'fff_equipes', 'equipes': [], 'erreur': 'Fichier trop court'}

    header  = _info_header(lignes[1])
    equipes_map = {}   # rang_eq → {nom_equipe, club, tireurs}

    for l in lignes[2:]:
        l = l.strip()
        if not l:
            continue
        # Format : NOM,PRENOM,DDN,GENRE,NAT,,NOM_EQUIPE;...;LICENCE,REGION,CLUB,...;RANG_EQ,
        parties = l.split(';')
        if len(parties) < 4:
            continue

        partie_tireur = parties[0]  # NOM,PRENOM,DDN,GENRE,NAT,,NOM_EQUIPE
        partie_club   = parties[2]  # LICENCE,REGION,CLUB_COMPLET,...
        partie_rang   = parties[3]  # RANG_EQ,...

        cols_t = partie_tireur.split(',')
        nom_eq = cols_t[6].strip() if len(cols_t) > 6 else ''
        nom    = cols_t[0].strip()
        prenom = cols_t[1].strip()

        cols_c = partie_club.split(',')
        club_complet = cols_c[2].strip() if len(cols_c) > 2 else ''
        region       = cols_c[1].strip() if len(cols_c) > 1 else ''

        rang_eq = partie_rang.split(',')[0].strip()
        if not rang_eq.isdigit():
            continue
        rang_eq = int(rang_eq)

        if rang_eq not in equipes_map:
            equipes_map[rang_eq] = {
                'rang':       str(rang_eq),
                'nom_equipe': nom_eq,
                'club':       club_complet or region,
            }
        pass  # composition non stockée (peut changer)

    equipes = [equipes_map[r] for r in sorted(equipes_map.keys())]
    return {
        'format':   'fff_equipes',
        'header':   header,
        'equipes':  equipes,
        'nb':       len(equipes),
    }


# ── Parser FFF individuel équipes (classement final) ──────────────────

def _parse_fff_classement_equipes(texte: str) -> dict:
    """
    FFF individuel où chaque ligne = une équipe avec son rang final.
    Format : NOM_EQUIPE,,,GENRE,NAT,;...;,REGION,CLUB,SCORE,...;RANG,t
    """
    lignes = texte.splitlines()
    if len(lignes) < 3:
        return {'format': 'fff_classement', 'equipes': [], 'erreur': 'Fichier trop court'}

    header  = _info_header(lignes[1])
    equipes = []

    for l in lignes[2:]:
        l = l.strip()
        if not l:
            continue
        parties = l.split(';')
        if len(parties) < 4:
            continue

        nom_eq  = parties[0].split(',')[0].strip()
        rang_str = parties[3].split(',')[0].strip()

        cols_c  = parties[2].split(',')
        region  = cols_c[1].strip() if len(cols_c) > 1 else ''
        club    = cols_c[2].strip() if len(cols_c) > 2 else ''

        if not rang_str.isdigit() or not nom_eq:
            continue

        equipes.append({
            'rang':       rang_str,
            'nom_equipe': nom_eq,
            'club':       club or region,
        })

    # Trier par rang
    equipes.sort(key=lambda e: int(e['rang']))
    return {
        'format':   'fff_classement',
        'header':   header,
        'equipes':  equipes,
        'nb':       len(equipes),
    }


def parse_fff_equipes(chemin: str) -> dict:
    """Point d'entrée FFF : détecte le sous-format et parse."""
    with open(chemin, 'rb') as f:
        raw = f.read()
    texte = _decode(raw)
    lignes = texte.splitlines()

    if not lignes:
        return {'format': 'inconnu', 'erreur': 'Fichier vide'}

    l1 = lignes[0].lower()
    if 'par_equipes' in l1:
        return _parse_fff_par_equipes(texte)
    else:
        # Individuel : vérifier si les lignes ressemblent à des équipes
        # (pas de date de naissance = équipes, pas de tireurs individuels)
        # Heuristique : la 3ème ligne a un nom sans virgule séparant prénom
        return _parse_fff_classement_equipes(texte)


# ── Parser XML Engarde ────────────────────────────────────────────────

def parse_xml_equipes(chemin: str) -> dict:
    """
    Parse un fichier XML Engarde par équipes.
    Structure attendue :
      <BaseCompetition>
        <Equipe ID="1" Nom="CEVN" NomClub="CEVN" ClassementFinal="1">
          <Tireur Nom="CUNAT" Prenom="Sabin" .../>
        </Equipe>
        <Parametres Arme="f" Sexe="M" Categorie="senior" .../>
      </BaseCompetition>
    """
    try:
        tree = ET.parse(chemin)
        root = tree.getroot()
    except ET.ParseError as e:
        return {'format': 'xml', 'erreur': f'XML invalide : {e}', 'equipes': []}

    # Header depuis Parametres
    params = root.find('.//Parametres')
    arme_map = {'f': 'Fleuret', 'e': 'Épée', 's': 'Sabre',
                'F': 'Fleuret', 'E': 'Épée', 'S': 'Sabre'}
    # Infos depuis l'attribut racine CompetitionParEquipes
    arme_code = root.get('Arme', '')
    header = {
        'arme':  arme_map.get(arme_code, arme_code),
        'genre': root.get('Sexe', ''),
        'cat':   root.get('Categorie', ''),
        'nom':   root.get('TitreLong', root.get('TitreCourt', '')),
        'date':  root.get('Date', '').replace('.', '/'),   # "15.02.2026" → "15/02/2026"
        'lieu':  root.get('Lieu', ''),
    }
    if params is not None:
        if not header['arme']:  header['arme'] = arme_map.get(params.get('Arme',''), '')
        if not header['genre']: header['genre'] = params.get('Sexe', '')
        if not header['cat']:   header['cat']   = params.get('Categorie', '')
        if not header['nom']:   header['nom']   = params.get('TitreCompetition', '')

    # Équipes
    equipes_raw = []
    for eq in root.findall('.//Equipe'):
        rang_final = eq.get('Classement', eq.get('ClassementFinal', ''))
        nom_eq     = eq.get('Nom', eq.get('NomEquipe', ''))
        club       = eq.get('Club', eq.get('NomClub', ''))
        if not rang_final or not rang_final.isdigit():
            continue
        equipes_raw.append({
            'rang':       rang_final,
            'nom_equipe': nom_eq,
            'club':       club,
        })

    equipes = sorted(equipes_raw, key=lambda e: int(e['rang']))
    return {
        'format':  'xml',
        'header':  header,
        'equipes': equipes,
        'nb':      len(equipes),
    }


# ── Point d'entrée universel ──────────────────────────────────────────

def parser_engarde_equipes(chemin: str) -> dict:
    """Parse FFF ou XML automatiquement selon l'extension."""
    ext = chemin.lower().rsplit('.', 1)[-1]
    if ext in ('fff', ):
        return parse_fff_equipes(chemin)
    elif ext in ('xml', ):
        return parse_xml_equipes(chemin)
    else:
        # Essai heuristique sur le contenu
        with open(chemin, 'rb') as f:
            debut = f.read(100)
        if b'<' in debut and b'>' in debut:
            return parse_xml_equipes(chemin)
        return parse_fff_equipes(chemin)
