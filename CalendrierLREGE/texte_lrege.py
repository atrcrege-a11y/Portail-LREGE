# -*- coding: utf-8 -*-
"""Portage littéral de LREGE_Texte et du vocabulaire de LREGE_Const.

Source : extension WordPress `calendrier-lrege` v1.0.1, fichiers
`includes/class-lrege-texte.php` et `includes/class-lrege-const.php`.

L'extension fait autorité sur les champs calculés : c'est elle qui publie le
calendrier et qui apparie les lignes d'un ré-import. Ce module doit donc rendre
*exactement* les mêmes valeurs — la non-régression est vérifiée par
`tests/test_publication.py` contre `tests/fixtures/php_reference.json`.

Différence assumée avec l'ancien `generer_calendrier.py` : un mois non reconnu
n'y retombait pas sur décembre en silence côté PHP, il rend 99991231
(« date illisible ») et remonte dans les anomalies d'import. C'est le
comportement repris ici.
"""
import re

# ── Vocabulaire (LREGE_Const) ────────────────────────────────────────────────

#: Clé de tri d'une date non interprétable — range la ligne en fin de calendrier.
TRI_KEY_ILLISIBLE = 99991231

#: Échelle FFE, du plus jeune au plus âgé.
ECHELLE = ['M7', 'M9', 'M11', 'M13', 'M15', 'M17', 'M20', 'Seniors', 'Vétérans']

#: Variantes acceptées dans le classeur => libellé publié.
ALIAS = {
    'm7': 'M7', 'm9': 'M9', 'm11': 'M11', 'm13': 'M13', 'm15': 'M15',
    'm17': 'M17', 'm20': 'M20',
    'senior': 'Seniors', 'seniors': 'Seniors', 'sen': 'Seniors',
    'sén': 'Seniors', 'séniors': 'Seniors',
    'vet': 'Vétérans', 'vét': 'Vétérans', 'vets': 'Vétérans',
    'veteran': 'Vétérans', 'veterans': 'Vétérans',
    'vétéran': 'Vétérans', 'vétérans': 'Vétérans',
}

#: Catégories hors échelle d'âge, affichées en tête de liste.
HORS_ECHELLE = {'para': 'Parasport', 'parasport': 'Parasport', 'paras': 'Parasport'}

#: Mois reconnus dans la colonne Date : abréviations du classeur ET noms complets.
MOIS = {
    'janv': 1, 'jan': 1, 'janvier': 1,
    'fév': 2, 'fev': 2, 'février': 2, 'fevrier': 2,
    'mars': 3,
    'avr': 4, 'avril': 4,
    'mai': 5,
    'juin': 6,
    'juil': 7, 'juillet': 7,
    'août': 8, 'aout': 8,
    'sept': 9, 'septembre': 9,
    'oct': 10, 'octobre': 10,
    'nov': 11, 'novembre': 11,
    'déc': 12, 'dec': 12, 'décembre': 12, 'decembre': 12,
}

# ── Nettoyage ────────────────────────────────────────────────────────────────

_ESPACES = re.compile(r'^[\s ]+|[\s ]+$')


def txt(v):
    """Équivalent de LREGE_Texte::txt() : str(v).strip(), espaces insécables compris."""
    if v is None or isinstance(v, bool):
        return ''
    return _ESPACES.sub('', str(v))


# ── Clé de tri ───────────────────────────────────────────────────────────────
# `\p{L}` du PCRE s'écrit `[^\W\d_]` en Python : une lettre unicode.

_LETTRE = r'[^\W\d_]'
_DATE_JOUR = re.compile(
    r'^(\d{1,2})(?:\s*-\s*\d{1,2})?\s+(%s+)\.?\s+(\d{4})' % _LETTRE, re.UNICODE)
_DATE_MOIS = re.compile(r'^(%s+)\.?\s+(\d{4})$' % _LETTRE, re.UNICODE)


def tri_key(d):
    """Clé chronologique AAAAMMJJ, tolérante aux formats du classeur.

    « 21-22 nov. 2026 » -> 20261121, « mai 2027 » -> 20270531 (fin de mois),
    illisible -> 99991231. Un mois non reconnu est déclaré illisible, il ne
    retombe pas sur décembre.
    """
    d = txt(d)
    m = _DATE_JOUR.match(d)
    if m:
        mo = m.group(2).lower()
        if mo not in MOIS:
            return TRI_KEY_ILLISIBLE
        return int('%04d%02d%02d' % (int(m.group(3)), MOIS[mo], int(m.group(1))))
    m = _DATE_MOIS.match(d)
    if m:
        mo = m.group(1).lower()
        if mo not in MOIS:
            return TRI_KEY_ILLISIBLE
        return int('%04d%02d%02d' % (int(m.group(2)), MOIS[mo], 31))
    return TRI_KEY_ILLISIBLE


def date_illisible(d):
    """Vrai si la date n'a pas pu être interprétée (à signaler, jamais à corriger)."""
    return tri_key(d) == TRI_KEY_ILLISIBLE


# ── Fragments d'expressions régulières construits depuis les alias ───────────
# Bornes les plus longues d'abord, tri stable : même ordre que le usort() du PHP.

_BORNE = '|'.join(sorted((re.escape(k) for k in ALIAS), key=len, reverse=True))
_PLAGE = re.compile(r'\b(%s)\s+(?:à|a)\s+(%s)\b' % (_BORNE, _BORNE), re.I | re.UNICODE)
_TOKEN = re.compile(r'^(%s)(\s+.+)?$' % _BORNE, re.I | re.UNICODE)


def developper(s):
    """« M13 à Seniors » -> « M13-M15-M17-M20-Seniors ».

    Laisse le texte intact si une borne est inconnue ou si l'ordre est inversé.
    """
    s = '' if s is None else str(s)
    if s == '':
        return s

    def rep(m):
        a = ALIAS.get(m.group(1).lower())
        b = ALIAS.get(m.group(2).lower())
        if not a or not b:
            return m.group(0)
        ia, ib = ECHELLE.index(a), ECHELLE.index(b)
        if ia > ib:
            return m.group(0)
        return '-'.join(ECHELLE[ia:ib + 1])

    return _PLAGE.sub(rep, s)


def _normaliser_token(t):
    """(rang, libellé) si le terme est une catégorie reconnue, sinon None."""
    t = txt(t)
    if t.lower() in HORS_ECHELLE:
        return (-1, HORS_ECHELLE[t.lower()])
    m = _TOKEN.match(t)
    if not m:
        return None
    base = ALIAS.get(m.group(1).lower())
    if not base:
        return None
    return (ECHELLE.index(base), base + (m.group(2) or ''))


def normaliser(s):
    """« VET + M13 » -> « M13-Vétérans », « PARA + M13 épée » -> « Parasport-M13 épée ».

    Une liste dont un seul terme n'est pas une catégorie reconnue est laissée
    telle quelle : on ne réécrit jamais un libellé qu'on ne comprend pas.
    """
    s = '' if s is None else str(s)
    if '+' not in s and txt(s).lower() not in HORS_ECHELLE:
        return s
    normes = [_normaliser_token(p) for p in s.split('+')]
    if any(n is None for n in normes):
        return s
    normes.sort(key=lambda n: n[0])      # tri stable, comme le usort() du PHP
    return '-'.join(lib for _, lib in normes)


# ── Catégories et index de filtre ────────────────────────────────────────────
# Seules les catégories d'âge FFE et Parasport sont reconnues : les libellés
# propres au sabre laser ne sont PAS assimilés à une catégorie d'âge.

_CAT_TOKEN = re.compile(
    r'\b(M\d{1,2}|S[ée]niors?|V[ée]t[ée]rans?|VET|PARA|Parasport)\b', re.I | re.UNICODE)


def categories(textes):
    """Catégories repérées dans des libellés, rendues dans l'ordre de l'échelle."""
    trouve = set()
    for t in textes:
        for m in _CAT_TOKEN.finditer('' if t is None else str(t)):
            v = m.group(1).lower()
            if v in HORS_ECHELLE:
                trouve.add(HORS_ECHELLE[v])
            elif ALIAS.get(v) in ECHELLE:
                trouve.add(ALIAS[v])
    return [c for c in ECHELLE if c in trouve]


def cats_index(cats):
    """« |M13|M15| » — index utilisé par le filtre par catégorie côté public."""
    return '|' + '|'.join(cats) + '|' if cats else ''
