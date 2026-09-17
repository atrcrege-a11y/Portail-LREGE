# -*- coding: utf-8 -*-
"""Lot 2 — reprise du classeur 2026-2027 vers `data/publication.json`.

Lit **toutes** les colonnes du classeur, y compris celles que l'extension
WordPress ignore : `notes` (col. I du Chronologique), `contact` et `email`
(col. J et K des onglets Tournois), et les onglets par arme.

Ce que le lecteur reproduit à l'identique — vérifié contre
`tests/fixtures/php_reference.json`, produit par l'extension elle-même :

- les **officiels** viennent du `Chronologique`, une ligne par ligne de l'onglet ;
- les **tournois** viennent des onglets `Tournois <territoire>`, jamais du
  Chronologique (dont les lignes de tournoi sont une restitution : leur date
  peut diverger, cf. `Tournoi des 3 villes`) ;
- `bloc` est le bloc **publié** : `Para` -> `Parasport`, `Transverse` ->
  `Coupe de Lorraine` si le type est un CDL/CHDL sinon `Autres`,
  `Tournoi Alsace` -> `Alsace` ;
- `type` d'un tournoi est le **nom du tournoi** (col. D), pas « Tournoi club » ;
- le `lieu` absent du Chronologique est repêché sur l'onglet du bloc.

Ce que le lecteur ajoute, hors périmètre de l'extension :

- `notes`, `contact`, `email` ;
- `armes` des lignes officielles, dérivées des onglets par arme
  (décision 1 du §5 du plan) ;
- `ecart_accepte`, posé par les corrections du §7 qui écartent volontairement
  une ligne de sa source.

Correspondance onglet <-> bloc pour le Lot 3, vérifiée sur le classeur réel
(`test_import_classeur.py::test_onglet_transverse_derivable_du_bloc`) :
l'onglet `Transverse` contient exactement les lignes de bloc
`Coupe de Lorraine` ; les lignes `Autres` (AG, CID, Zone, Master) n'y sont pas.
Aucun champ supplémentaire n'est donc nécessaire pour régénérer les onglets.

Note pour la recette du Lot 4 : le lecteur nettoie les espaces de bord, comme
l'extension. Six cellules du classeur 2026-2027 en portent (`Chronologique!F14`
et `F46`, `Tournois Alsace!J6`, `Tournois Lorraine!E4`, `J4` et `E5`) : la
comparaison cellule à cellule doit porter sur des valeurs nettoyées, faute de
quoi elle remontera six écarts qui n'en sont pas.

`categories` et `armes` conservent le texte du classeur : la forme publiée par
l'extension est un champ calculé (`categories_publiees`, `armes_publiees`),
posé par `publication.champs_calcules()` qui ne réécrit aucune saisie.
"""
import argparse
import datetime
import os
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import publication as pub
from texte_lrege import txt, date_illisible

# ── Structure du classeur ────────────────────────────────────────────────────

ONGLET_CHRONO = 'Chronologique'
ONGLET_IGNORE = 'Lisez-moi'                       # décision 4 du §5

#: Onglets « une ligne = une épreuve », colonnes A→E.
ONGLETS_ARME = ['Épée', 'Fleuret', 'Sabre', 'Sabre laser', 'Para',
                'Transverse', 'Escrime artistique', 'Stages']

#: Onglets des armes proprement dites — ceux qui alimentent `armes[]`.
ARMES = ['Épée', 'Fleuret', 'Sabre', 'Sabre laser', 'Para']

#: Onglets tournois, colonnes A→M, dans l'ordre de lecture du classeur.
ONGLETS_TOURNOI = [('Tournois Alsace', 'Alsace'),
                   ('Tournois Lorraine', 'Lorraine'),
                   ('Tournois Champagne-Ardenne', 'Champagne-Ardenne')]

LIGNE_ENTETE = 2                                  # les données commencent en 3

# Chronologique : A date, B jours, C bloc, D type, E cats, F lieu, G club,
#                 H statut, I annotations + chevauchements
C_DATE, C_JOURS, C_BLOC, C_TYPE, C_CATS, C_LIEU, C_CLUB, C_STATUT, C_NOTES = range(1, 10)
# Onglets par arme : A date, B jours, C type, D cats, E lieu
A_DATE, A_JOURS, A_TYPE, A_CATS, A_LIEU = range(1, 6)
# Onglets tournois : A date, B jours, C club, D nom, E lieu, F fleuret, G épée,
#                    H sabre, I autres, J contact, K e-mail, L statut, M chevauch.
(T_DATE, T_JOURS, T_CLUB, T_NOM, T_LIEU, T_FLEURET, T_EPEE, T_SABRE,
 T_AUTRES, T_CONTACT, T_EMAIL, T_STATUT, T_CHEV) = range(1, 14)

#: Colonnes d'armes des onglets tournois, dans l'ordre où l'extension les rend.
COLONNES_ARMES_TOURNOI = [(T_FLEURET, 'Fleuret'), (T_EPEE, 'Épée'),
                          (T_SABRE, 'Sabre'), (T_AUTRES, 'Autres')]

#: Marqueur des chevauchements calculés — retirés du champ `notes` (décision 3).
MARQUEUR_CHEVAUCHEMENT = 'Chevauche :'

#: Types du bloc Transverse publiés sous « Coupe de Lorraine » (§2 du plan).
PREFIXES_COUPE_DE_LORRAINE = ('CDL', 'CHDL')

#: Types pour lesquels les onglets par arme font foi sur le Chronologique,
#: date et jours compris — décision 1 du §5 (L47 Master, L30 Zone M15).
ONGLETS_FONT_FOI = {'Master', 'Zone'}

#: Forme canonique des mois telle qu'écrite au classeur, pour les rares
#: cellules saisies en vraie date (`Épée!A13` et ses jumelles : « 23-mai-07 »).
MOIS_TEXTE = {1: 'jan.', 2: 'fév.', 3: 'mars', 4: 'avr.', 5: 'mai', 6: 'juin',
              7: 'juil.', 8: 'août', 9: 'sept.', 10: 'oct.', 11: 'nov.', 12: 'déc.'}

JOURS_COURTS = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim']


# ── Corrections en attente (§7 du plan) ──────────────────────────────────────
# Chaque correction est gardée par la valeur attendue : si la cellule a changé
# au classeur, la correction n'est pas appliquée, elle est signalée.
# Deux colonnes passent par cette table : la date (col. A partout) et les
# catégories (col. E du Chronologique, col. D des onglets par arme).
# `ecart_accepte` marque les lignes volontairement écartées de leur source,
# pour que le ré-import du recensement cesse de proposer le retour en arrière.

# `Chronologique!A46` ne figure pas ici : la ligne de tournoi du Chronologique
# est une restitution, entièrement dérivée de la ligne de publication (voir
# `rendu_chronologique_tournoi()`). Corriger la cellule reviendrait à écrire
# deux fois la même information, donc à rouvrir la dérive que le §7 corrige.
CORRECTIONS_CELLULES = [
    # (onglet, cellule, valeur attendue, valeur cible, ecart_accepte, motif)
    # ── Catégories ──
    # Le M15 n'était pas sur la même manche de Coupe de Lorraine au
    # Chronologique et à l'onglet `Transverse`. Arbitré le 11/09/2026 :
    # il relève de CDL 1, l'onglet faisait donc foi.
    (ONGLET_CHRONO, 'E12', 'M9-M11-M13', 'M9-M11-M13-M15', False,
     'M15 rattaché à CDL 1, arbitré le 11/09/2026'),
    (ONGLET_CHRONO, 'E19', 'M9-M11-M13-M15', 'M9-M11-M13', False,
     'M15 retiré de CDL 2, arbitré le 11/09/2026'),
    ('Transverse', 'D3', 'M9-M11-M13--M15', 'M9-M11-M13-M15', False,
     'double tiret de saisie — forme canonique'),
    # ── Dates ──
    (ONGLET_CHRONO, 'A41', '3-4 avr. 2027 ou 1-2 mai 2027', '1-2 mai 2027', False,
     'CHDL arbitré aux 1-2 mai 2027 le 10/09/2026'),
    ('Transverse', 'A6', '3-4 avr. 2027 ou 1-2 mai 2027', '1-2 mai 2027', False,
     'CHDL arbitré aux 1-2 mai 2027 le 10/09/2026'),
    ('Tournois Lorraine', 'A5', '3-4 avril 2027', '3-4 avr. 2027', True,
     'abréviation canonique — cle_source stable ; écart assumé avec la réponse '
     'du recensement du 04/09/2026 (1-2 mai), périmée depuis l\'arbitrage'),
]

#: Corrections portant sur l'annotation, une fois les chevauchements retirés.
#: Trois annotations périmées, retirées pour la raison qui les a rendues fausses.
CORRECTIONS_NOTES = [
    (ONGLET_CHRONO, 'I41', 'Championnat — deux dates encore ouvertes', '',
     'annotation périmée depuis l\'arbitrage du 10/09/2026'),
    # Le conflit M15 du 12-13 déc. 2026 n'a plus d'objet : depuis la décision 8,
    # `CDL 2` ne porte plus le M15, le CID est donc seul à le porter ce
    # week-end-là. Les deux annotations se répondaient, elles tombent ensemble.
    (ONGLET_CHRONO, 'I19', 'CONFLIT M15 : CID M15 le même week-end', '',
     'conflit levé par la décision 8 — CDL 2 ne porte plus le M15'),
    (ONGLET_CHRONO, 'I20',
     'CONFLIT M15 : Coupe de Lorraine CDL2 (M9 à M15) le même week-end', '',
     'conflit levé par la décision 8 — CDL 2 ne porte plus le M15'),
]


# ── Outils ───────────────────────────────────────────────────────────────────

def date_en_texte(v):
    """Cellule date -> texte du classeur. Une cellule déjà textuelle est rendue telle quelle."""
    if isinstance(v, datetime.datetime):
        return '%d %s %d' % (v.day, MOIS_TEXTE[v.month], v.year)
    if isinstance(v, datetime.date):
        return '%d %s %d' % (v.day, MOIS_TEXTE[v.month], v.year)
    return txt(v)


def note_utile(valeur):
    """Annotation seule : tout ce qui précède « Chevauche : » (décision 3 du §5).

    Une cellule qui ne contient que des chevauchements rend une chaîne vide.
    """
    t = txt(valeur)
    i = t.find(MARQUEUR_CHEVAUCHEMENT)
    if i >= 0:
        t = t[:i]
    return t.rstrip().rstrip('—-–').rstrip()


def bloc_publie(bloc_classeur, type_):
    """Bloc tel que l'extension le publie, depuis la colonne C du Chronologique."""
    b = txt(bloc_classeur)
    if b == 'Para':
        return 'Parasport'
    if b == 'Transverse':
        t = txt(type_).upper()
        for p in PREFIXES_COUPE_DE_LORRAINE:
            if t.startswith(p):
                return 'Coupe de Lorraine'
        return 'Autres'
    if b.startswith('Tournoi '):
        return b[len('Tournoi '):]
    return b


#: Préfixe de chaque arme dans la colonne « Catégories / Épreuves » du
#: Chronologique. `Autres` est rendu tel quel : il porte déjà son libellé
#: (« Para : … », « Laser : … »).
PREFIXE_ARME_CHRONO = {'Fleuret': 'F : ', 'Épée': 'É : ', 'Sabre': 'S : ',
                       'Autres': ''}


def rendu_chronologique_tournoi(ligne):
    """Colonnes A→H de la ligne de tournoi du Chronologique, dérivées.

    La ligne de tournoi du Chronologique n'est pas une source : c'est une
    restitution de l'onglet `Tournois <territoire>`, dont elle peut diverger —
    c'est précisément ce que corrige le §7 du plan pour le Tournoi des 3 villes.
    Elle est donc régénérée, jamais corrigée cellule par cellule.

    Vérifié sur le classeur 2026-2027 : les 9 lignes sont reproduites à
    l'identique, la seule exception étant celle que le §7 corrige
    (`test_restitution_du_chronologique_derivable`).
    """
    return [ligne['date_texte'], ligne['jours'], 'Tournoi ' + ligne['bloc'],
            'Tournoi club',
            ' | '.join(PREFIXE_ARME_CHRONO[a['arme']] + a['categories']
                       for a in ligne['armes']),
            ligne['lieu'], ligne['club'], ligne['statut']]


def _valeurs(ws, ligne, nb_colonnes):
    return [ws.cell(ligne, c).value for c in range(1, nb_colonnes + 1)]


def _vide(valeurs):
    return all(v is None or txt(v) == '' for v in valeurs)


# ── Lecture ──────────────────────────────────────────────────────────────────

class _Corrections:
    """Applique les corrections du §7 et tient le journal de ce qui a été fait."""

    def __init__(self, actives):
        self.actives = actives
        self.journal = []
        self.ecarts_acceptes = set()          # (onglet, ligne) du classeur
        self.non_appliquees = []
        self.vues = set()                     # (onglet, cellule) effectivement lues

    def _passe(self, table, onglet, cellule, valeur, avec_ecart):
        for entree in table:
            if avec_ecart:
                o, cel, attendu, cible, ecart, motif = entree
            else:
                o, cel, attendu, cible, motif = entree
                ecart = False
            if o != onglet or cel != cellule:
                continue
            self.vues.add((o, cel))
            if valeur != attendu:
                self.non_appliquees.append(
                    '%s!%s : attendu %r, trouvé %r — correction non appliquée'
                    % (onglet, cellule, attendu, valeur))
                return valeur
            if not self.actives:
                return valeur
            self.journal.append('%s!%s : %r -> %r (%s)'
                                % (onglet, cellule, attendu, cible, motif))
            if ecart:
                self.ecarts_acceptes.add((onglet, int(''.join(
                    ch for ch in cellule if ch.isdigit()))))
            return cible
        return valeur

    def cellule(self, onglet, colonne_lettre, ligne, valeur):
        return self._passe(CORRECTIONS_CELLULES, onglet,
                           '%s%d' % (colonne_lettre, ligne), valeur, True)

    def note(self, onglet, colonne_lettre, ligne, valeur):
        return self._passe(CORRECTIONS_NOTES, onglet,
                           '%s%d' % (colonne_lettre, ligne), valeur, False)

    def accepte(self, onglet, ligne):
        return (onglet, ligne) in self.ecarts_acceptes

    def jamais_lues(self):
        """Corrections du §7 dont la cellule n'est pas lue par le lecteur.

        Ce n'est pas une erreur : la date d'un tournoi vient de son onglet
        Tournois, la ligne du Chronologique n'en est qu'une restitution. Ces
        cellules-là restent à reprendre par le générateur du Lot 3.
        """
        restant = []
        for o, cel, attendu, cible, _ecart, motif in CORRECTIONS_CELLULES:
            if (o, cel) not in self.vues:
                restant.append('%s!%s : %r -> %r (%s) — cellule non lue '
                               '(restitution du Chronologique, à reprendre au Lot 3)'
                               % (o, cel, attendu, cible, motif))
        for o, cel, attendu, cible, motif in CORRECTIONS_NOTES:
            if (o, cel) not in self.vues:
                restant.append('%s!%s : %r -> %r (%s) — cellule non lue'
                               % (o, cel, attendu, cible, motif))
        return restant


def _lire_onglets_arme(wb, corrections):
    """Onglets par arme -> {onglet: [{ligne, date_texte, jours, type, categories, lieu}]}."""
    par_onglet = {}
    for nom in ONGLETS_ARME:
        if nom not in wb.sheetnames:
            continue
        ws = wb[nom]
        lignes = []
        for r in range(LIGNE_ENTETE + 1, ws.max_row + 1):
            v = _valeurs(ws, r, 5)
            if _vide(v):
                continue
            date = corrections.cellule(nom, 'A', r, date_en_texte(v[A_DATE - 1]))
            lignes.append({
                'ligne': r,
                'date_texte': date,
                'date_source_datee': isinstance(v[A_DATE - 1], (datetime.date, datetime.datetime)),
                'jours': txt(v[A_JOURS - 1]),
                'type': txt(v[A_TYPE - 1]),
                'categories': corrections.cellule(nom, 'D', r,
                                                  txt(v[A_CATS - 1])),
                'lieu': txt(v[A_LIEU - 1]),
            })
        par_onglet[nom] = lignes
    return par_onglet


def _apparier(candidats, date_texte, cats):
    """Ligne d'onglet correspondant à une ligne du Chronologique de même type.

    Départage par la date, puis par les catégories, puis par l'unicité du type.
    """
    if not candidats:
        return None
    if len(candidats) == 1:
        return candidats[0]
    exact = [c for c in candidats if c['date_texte'] == date_texte]
    if len(exact) == 1:
        return exact[0]
    par_cats = [c for c in candidats if c['categories'] == cats]
    if len(par_cats) == 1:
        return par_cats[0]
    return None


def _lire_tournois(wb, corrections, rapport):
    lignes = []
    for nom, territoire in ONGLETS_TOURNOI:
        if nom not in wb.sheetnames:
            rapport['anomalies'].append('onglet « %s » absent du classeur' % nom)
            continue
        ws = wb[nom]
        for r in range(LIGNE_ENTETE + 1, ws.max_row + 1):
            v = _valeurs(ws, r, 13)
            if _vide(v) or txt(v[T_CLUB - 1]) == '':
                continue                       # pied de page / « aucun tournoi »
            date = corrections.cellule(nom, 'A', r, date_en_texte(v[T_DATE - 1]))
            armes = []
            for col, arme in COLONNES_ARMES_TOURNOI:
                cats = txt(v[col - 1])
                if cats:
                    armes.append({'arme': arme, 'categories': cats})
            ligne = pub.ligne_vide(
                date_texte=date,
                jours=txt(v[T_JOURS - 1]),
                bloc=territoire,
                type=txt(v[T_NOM - 1]),
                categories='',                 # porté par `armes`, comme l'extension
                lieu=txt(v[T_LIEU - 1]),
                club=txt(v[T_CLUB - 1]),
                statut=txt(v[T_STATUT - 1]),
                est_tournoi=True,
                armes=armes,
                notes='',                      # col. M : chevauchements seuls
                contact=txt(v[T_CONTACT - 1]),
                email=txt(v[T_EMAIL - 1]),
                ecart_accepte=corrections.accepte(nom, r),
            )
            ligne['_source'] = '%s!%d' % (nom, r)
            lignes.append(ligne)
            chev = txt(v[T_CHEV - 1])
            if chev and MARQUEUR_CHEVAUCHEMENT not in chev:
                rapport['anomalies'].append(
                    '%s!M%d : la colonne « Chevauchements » contient autre chose '
                    'qu\'un chevauchement — %r' % (nom, r, chev))
    return lignes


def lire_classeur(chemin, appliquer_corrections=True):
    """Lit le classeur et rend `(lignes, rapport)`.

    `appliquer_corrections=False` neutralise les corrections en attente du §7 :
    c'est cette lecture-là que le contrôle de recette du Lot 4 devra comparer au
    classeur régénéré. La décision 1 du §5 (Master et Zone repris sur les
    onglets par arme) s'applique dans les deux cas — ce n'est pas une correction
    en attente mais une décision de modèle ; elle est journalisée comme telle.
    """
    wb = openpyxl.load_workbook(chemin, data_only=True)
    rapport = {
        'fichier': os.path.basename(chemin),
        'onglets_lus': [n for n in wb.sheetnames if n != ONGLET_IGNORE],
        'onglets_ignores': [n for n in wb.sheetnames if n == ONGLET_IGNORE],
        'corrections': [], 'corrections_non_appliquees': [],
        'corrections_hors_lecture': [],
        'ecarts': [], 'repechages': [], 'anomalies': [], 'doublons': [],
        'a_confirmer': [],
    }
    if ONGLET_CHRONO not in wb.sheetnames:
        raise ValueError('onglet « %s » absent de %s' % (ONGLET_CHRONO, chemin))

    corrections = _Corrections(appliquer_corrections)
    onglets = _lire_onglets_arme(wb, corrections)
    apparies = {nom: set() for nom in onglets}

    chrono = wb[ONGLET_CHRONO]
    officielles = []
    for r in range(LIGNE_ENTETE + 1, chrono.max_row + 1):
        v = _valeurs(chrono, r, 9)
        if _vide(v):
            continue
        bloc_brut = txt(v[C_BLOC - 1])
        if bloc_brut.startswith('Tournoi '):
            continue                # les tournois sont lus sur leur propre onglet
        date = corrections.cellule(ONGLET_CHRONO, 'A', r, date_en_texte(v[C_DATE - 1]))
        type_ = txt(v[C_TYPE - 1])
        cats = corrections.cellule(ONGLET_CHRONO, 'E', r, txt(v[C_CATS - 1]))
        note = corrections.note(ONGLET_CHRONO, 'I', r, note_utile(v[C_NOTES - 1]))
        ligne = pub.ligne_vide(
            date_texte=date,
            jours=txt(v[C_JOURS - 1]),
            bloc=bloc_publie(bloc_brut, type_),
            type=type_,
            categories=cats,
            lieu=txt(v[C_LIEU - 1]),
            club=txt(v[C_CLUB - 1]),
            statut=txt(v[C_STATUT - 1]),
            est_tournoi=False,
            armes=[],
            notes=note,
            ecart_accepte=corrections.accepte(ONGLET_CHRONO, r),
        )
        ligne['_source'] = '%s!%d' % (ONGLET_CHRONO, r)

        # Onglets où la ligne figure : celui de son bloc, plus les onglets
        # d'arme pour les lignes transverses (Master, Zone).
        candidats_onglets = [bloc_brut] if bloc_brut in onglets else []
        if bloc_brut == 'Transverse':
            candidats_onglets += ARMES
        trouves = []
        for nom in candidats_onglets:
            cand = [c for c in onglets.get(nom, []) if c['type'] == type_]
            m = _apparier(cand, date, cats)
            if m is None:
                if len(cand) > 1:
                    rapport['anomalies'].append(
                        '%s!%d [%s|%s] : %d lignes de même type dans l\'onglet « %s », '
                        'appariement impossible' % (ONGLET_CHRONO, r, bloc_brut,
                                                    type_, len(cand), nom))
                continue
            trouves.append((nom, m))
            apparies[nom].add(m['ligne'])

        for nom, m in trouves:
            _confronter(ligne, nom, m, type_, r, rapport, appliquer_corrections)
            if nom in ARMES:
                ligne['armes'].append(nom)

        officielles.append(ligne)
        if ligne['statut']:
            rapport['a_confirmer'].append(
                '%s — %s %s : statut %r' % (ligne['date_texte'], ligne['bloc'],
                                            ligne['type'], ligne['statut']))

    tournois = _lire_tournois(wb, corrections, rapport)

    for nom, lst in onglets.items():
        for c in lst:
            if c['ligne'] not in apparies[nom]:
                rapport['anomalies'].append(
                    '%s!%d [%s|%s] : aucune ligne du Chronologique ne lui correspond'
                    % (nom, c['ligne'], c['type'], c['categories']))

    lignes = officielles + tournois
    for l in lignes:
        pub.champs_calcules(l)
    lignes.sort(key=lambda l: l['tri_key'])          # tri stable : ordre de lecture
    rapport['doublons'] = pub.attribuer_cles_source(lignes)

    for l in lignes:
        if date_illisible(l['date_texte']):
            rapport['anomalies'].append(
                '%s : date non interprétable %r' % (l['_source'], l['date_texte']))
        if not l['lieu']:
            rapport['anomalies'].append('%s : lieu manquant' % l['_source'])

    rapport['corrections'] = corrections.journal + rapport['corrections']
    rapport['corrections_non_appliquees'] = corrections.non_appliquees
    rapport['corrections_hors_lecture'] = corrections.jamais_lues()
    rapport['lignes'] = len(lignes)
    rapport['officielles'] = len(officielles)
    rapport['tournois'] = len(tournois)
    rapport['notes'] = sum(1 for l in lignes if l['notes'])
    rapport['contacts'] = sum(1 for l in lignes if l['contact'])
    rapport['emails'] = sum(1 for l in lignes if l['email'])
    rapport['sans_lieu'] = sum(1 for l in lignes if not l['lieu'])
    return lignes, rapport


def _confronter(ligne, onglet, m, type_, r, rapport, appliquer_corrections):
    """Confronte la ligne du Chronologique à celle de l'onglet.

    Le Chronologique fait foi, sauf pour les types de `ONGLETS_FONT_FOI`
    (décision 1 du §5). Le `lieu` absent est repêché. Tout le reste est
    signalé, jamais corrigé d'office.
    """
    source = '%s!%d' % (ONGLET_CHRONO, r)
    cible = '%s!%d' % (onglet, m['ligne'])

    if type_ in ONGLETS_FONT_FOI:
        for champ in ('date_texte', 'jours'):
            if m[champ] and m[champ] != ligne[champ]:
                rapport['corrections'].append(
                    '%s %s : %r -> %r (décision 1 du §5 — « %s » fait foi, %s)'
                    % (source, champ, ligne[champ], m[champ], onglet, cible))
                ligne[champ] = m[champ]
    else:
        if m['date_texte'] and m['date_texte'] != ligne['date_texte']:
            rapport['ecarts'].append(
                '%s vs %s : date %r au Chronologique, %r à l\'onglet'
                % (source, cible, ligne['date_texte'], m['date_texte']))
        if m['jours'] and m['jours'] != ligne['jours']:
            rapport['ecarts'].append(
                '%s vs %s : jours %r au Chronologique, %r à l\'onglet'
                % (source, cible, ligne['jours'], m['jours']))

    if m['categories'] and m['categories'] != ligne['categories']:
        rapport['ecarts'].append(
            '%s vs %s : catégories %r au Chronologique, %r à l\'onglet'
            % (source, cible, ligne['categories'], m['categories']))

    if m['lieu'] and not ligne['lieu']:
        ligne['lieu'] = m['lieu']
        rapport['repechages'].append('%s : lieu %r repêché sur %s'
                                     % (source, m['lieu'], cible))
    elif m['lieu'] and m['lieu'] != ligne['lieu']:
        rapport['ecarts'].append(
            '%s vs %s : lieu %r au Chronologique, %r à l\'onglet'
            % (source, cible, ligne['lieu'], m['lieu']))


# ── Import ───────────────────────────────────────────────────────────────────

def importer(chemin, appliquer_corrections=True, ecrire=True):
    """Lit le classeur et écrit `data/publication.json`. Rend le rapport."""
    lignes, rapport = lire_classeur(chemin, appliquer_corrections)
    for l in lignes:
        l.pop('_source', None)
    rapport['ecrit'] = False
    if ecrire:
        rapport['backup'] = pub.save_lignes(lignes)
        rapport['ecrit'] = True
    return rapport


def _resume(rapport):
    out = ['%s : %d lignes (%d officielles + %d tournois), %d annotations, '
           '%d contacts, %d e-mails'
           % (rapport['fichier'], rapport['lignes'], rapport['officielles'],
              rapport['tournois'], rapport['notes'], rapport['contacts'],
              rapport['emails'])]
    for titre, cle in (('Corrections appliquées', 'corrections'),
                       ('Corrections NON appliquées', 'corrections_non_appliquees'),
                       ('Corrections hors lecture', 'corrections_hors_lecture'),
                       ('Lieux repêchés', 'repechages'),
                       ('Écarts signalés (non corrigés)', 'ecarts'),
                       ('Doublons de cle_source', 'doublons'),
                       ('À confirmer', 'a_confirmer'),
                       ('Anomalies', 'anomalies')):
        items = rapport.get(cle) or []
        if items:
            out.append('\n%s (%d) :' % (titre, len(items)))
            out += ['  - %s' % i for i in items]
    return '\n'.join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description='Reprise du classeur vers publication.json')
    p.add_argument('classeur')
    p.add_argument('--sans-corrections', action='store_true',
                   help='lecture fidèle au classeur, sans les corrections du §7')
    p.add_argument('--dry-run', action='store_true',
                   help='affiche le rapport sans écrire publication.json')
    a = p.parse_args(argv)
    rapport = importer(a.classeur, not a.sans_corrections, not a.dry_run)
    print(_resume(rapport))
    if rapport['ecrit']:
        print('\npublication.json écrit (sauvegarde : %s)' % rapport.get('backup'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
