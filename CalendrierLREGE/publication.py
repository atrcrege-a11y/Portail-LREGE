# -*- coding: utf-8 -*-
"""Modèle et stockage des lignes de publication du calendrier régional.

`data/publication.json` est le sur-ensemble strict du classeur : les dix champs
lus par l'extension WordPress `calendrier-lrege`, plus `notes`, `contact`,
`email` et `ecart_accepte`.

Ce fichier est indépendant de `data/calendrier.json`, qui reste la source
d'import FFE et n'est pas migré.
"""
import json, os, uuid
from datetime import datetime

# Champs calculés : même logique que l'extension WordPress, qui fait autorité.
from texte_lrege import (
    txt, tri_key, date_illisible, developper, normaliser, categories,
    cats_index, TRI_KEY_ILLISIBLE,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLICATION_FILE = os.path.join(BASE_DIR, 'data', 'publication.json')

#: Version du modèle, écrite sur chaque ligne pour les migrations ultérieures.
PUBLICATION_VERSION = 1

#: Les 14 champs du modèle cible, avec leur valeur par défaut.
#: L'ordre est celui du §3 du plan : les 10 champs lus par l'extension,
#: puis les 4 champs propres au module de saisie.
CHAMPS_DEFAUT = {
    'date_texte':    '',     # tel qu'il sera écrit au classeur (« 26-27 sept. 2026 »)
    'jours':         '',     # « sam-dim », « dim », « sam »
    'bloc':          '',     # Épée | Fleuret | … | Transverse | Stage | Alsace | …
    'type':          '',     # ER1, ER2, CR, CDL 1, CHDL, CID, Zone, Master, Tournoi club…
    'categories':    '',     # TEXTE LIBRE, jamais réécrit (« M13 à Seniors »)
    'lieu':          '',
    'club':          '',
    'statut':        '',     # vide | « À confirmer »
    'est_tournoi':   False,
    'armes':         [],     # tournois : [{arme, categories}] ; officiels : [arme, …]
    # ── au-delà de ce que lit l'extension ────────────────────────────────────
    'notes':         '',     # annotations col. I du Chronologique, chevauchements retirés
    'contact':       '',     # col. J des onglets Tournois
    'email':         '',     # col. K des onglets Tournois
    'ecart_accepte': False,  # ligne volontairement différente de la source
}


def ligne_vide(**kw):
    """Ligne neuve : les 14 champs à leur valeur par défaut, plus `id`.

    Les valeurs mutables des défauts sont copiées, jamais partagées.
    """
    ligne = {'id': str(uuid.uuid4()), '__version__': PUBLICATION_VERSION}
    for champ, defaut in CHAMPS_DEFAUT.items():
        ligne[champ] = list(defaut) if isinstance(defaut, list) else defaut
    for champ, valeur in kw.items():
        ligne[champ] = valeur
    return ligne


def _normaliser(ligne):
    """Complète une ligne lue sur disque : champs manquants, id, version.

    Même principe que la migration de `load_events()` : compatibilité
    ascendante, aucune valeur existante n'est réécrite.
    """
    for champ, defaut in CHAMPS_DEFAUT.items():
        if champ not in ligne:
            ligne[champ] = list(defaut) if isinstance(defaut, list) else defaut
    ligne.setdefault('id', str(uuid.uuid4()))
    ligne.setdefault('__version__', 0)
    return ligne


def load_lignes():
    """Lit `data/publication.json`. Fichier absent → liste vide."""
    if not os.path.exists(PUBLICATION_FILE):
        return []
    with open(PUBLICATION_FILE, encoding='utf-8') as f:
        lignes = json.load(f)
    return [_normaliser(l) for l in lignes]


def _backup_publication():
    """Copie horodatée de publication.json dans data/backups/.

    Retourne le nom du fichier de sauvegarde, ou None si le fichier n'existe
    pas encore (première écriture).
    """
    if not os.path.exists(PUBLICATION_FILE):
        return None
    backup_dir = os.path.join(os.path.dirname(PUBLICATION_FILE), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    name = 'publication_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json'
    with open(PUBLICATION_FILE, encoding='utf-8') as src:
        contenu = src.read()
    with open(os.path.join(backup_dir, name), 'w', encoding='utf-8') as dst:
        dst.write(contenu)
    return name


def save_lignes(lignes, backup=True):
    """Écriture atomique de `data/publication.json`, sauvegarde préalable.

    Contrairement à `save_events()`, la sauvegarde horodatée est faite ici, à
    *chaque* écriture, et non seulement avant les opérations destructives :
    ces lignes sont saisies à la main, elles n'ont pas de source à ré-importer.

    Retourne le nom de la sauvegarde, ou None s'il n'y avait rien à sauver.
    """
    os.makedirs(os.path.dirname(PUBLICATION_FILE), exist_ok=True)
    nom_backup = _backup_publication() if backup else None
    tmp_file = PUBLICATION_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(lignes, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, PUBLICATION_FILE)
    return nom_backup


# ── Champs calculés ──────────────────────────────────────────────────────────
# Même logique que l'extension WordPress, qui fait autorité : voir texte_lrege.py.
# Les champs calculés ne sont pas dans CHAMPS_DEFAUT : ils sont posés par
# `champs_calcules()` et recalculables à tout moment depuis la saisie.

def cle_source(ligne):
    """Clé d'appariement d'une ligne : `date_texte|bloc|type|club`.

    C'est la clé brute, sans suffixe de doublon. L'attribution effective des
    clés sur un lot de lignes passe par `attribuer_cles_source()`.
    """
    return '|'.join(txt(ligne.get(c, '')) for c in ('date_texte', 'bloc', 'type', 'club'))


def attribuer_cles_source(lignes):
    """Pose `cle_source` sur chaque ligne, suffixée `#2`, `#3`… en cas de doublon.

    Reprend la boucle de `LREGE_Classeur::finaliser()` : l'ordre d'entrée décide
    quelle ligne garde la clé nue. Retourne la liste des clés de base vues
    plusieurs fois — un doublon est signalé, jamais corrigé d'office.
    """
    vues = set()
    doublons = []
    for ligne in lignes:
        base = cle_source(ligne)
        cle, n = base, 1
        while cle in vues:
            n += 1
            cle = base + '#' + str(n)
        if n > 1:
            doublons.append(base)
        vues.add(cle)
        ligne['cle_source'] = cle
    return doublons


def champs_calcules(ligne):
    """Pose les champs calculés d'une ligne. **Ne réécrit aucune saisie.**

    Rend `tri_key`, `cats`, `cats_index`, et la forme *publiée* des libellés :
    `categories_publiees` et, pour les tournois, `armes_publiees`.

    `categories` et `armes` restent le texte du classeur, tel qu'il y est écrit
    (§3 du plan : « TEXTE LIBRE, jamais réécrit ») — c'est ce qui permet au
    générateur du Lot 3 de régénérer le classeur à l'identique. La forme
    publiée, elle, est un calcul au même titre que `tri_key` : portage de
    `LREGE_Donnees::normaliser_ligne()`, plages développées et additions
    normalisées. Idempotent. `cle_source` n'en fait pas partie : elle dépend du
    lot entier, voir `attribuer_cles_source()`.

    `armes` a deux formes : liste de dictionnaires {arme, categories} pour les
    tournois de club, liste de noms d'armes pour les officiels (§3 du plan).
    Seule la première porte des catégories à publier ; une entrée sans arme est
    écartée de `armes_publiees`, jamais de `armes`.
    """
    ligne['categories_publiees'] = normaliser(developper(ligne.get('categories', '')))
    textes = [ligne['categories_publiees']]

    armes = ligne.get('armes') or []
    if armes and isinstance(armes[0], dict):
        publiees = []
        for a in armes:
            if txt(a.get('arme', '')) == '':
                continue
            publiees.append({
                'arme': a.get('arme', ''),
                'categories': normaliser(developper(a.get('categories', ''))),
            })
        ligne['armes_publiees'] = publiees
        textes += [a['categories'] for a in publiees]

    cats = categories(textes)
    ligne['cats'] = cats
    ligne['cats_index'] = cats_index(cats)
    ligne['tri_key'] = tri_key(ligne.get('date_texte', ''))
    return ligne
