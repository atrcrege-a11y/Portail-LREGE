# -*- coding: utf-8 -*-
"""Lot 4 — contrôle de recette élargi : comparaison de deux classeurs.

L'extension WordPress ne lit qu'une partie des colonnes ; son écran de
comparaison passerait donc au vert alors que des données auraient disparu du
classeur. Ce module compare **tous les onglets et toutes les colonnes
conservées** — Chronologique A→H, onglets par arme A→E, onglets Tournois A→L
(décision 3 du §5 : les colonnes de chevauchements I et M sont supprimées,
elles sont hors comparaison ; décision 4 : l'onglet `Lisez-moi` n'existe plus).

Trois natures d'écart : cellule modifiée, ligne ajoutée, ligne retirée.
L'alignement se fait **sur le contenu des lignes**, pas sur leur indice
(`difflib.SequenceMatcher` sur des tuples de ligne) : une ligne déplacée est
rendue comme un retrait et un ajout, et non comme une cascade de dizaines
d'écarts cellule à cellule.

Normalisation avant comparaison (décision 7 du §5 bis) : les dates saisies en
vraie date Excel sont rendues en texte (`import_classeur.date_en_texte`) et les
espaces de bord sont retirés (`texte_lrege.txt`).

L'identité n'est pas nue : la régénération produit des écarts voulus, chacun
adossé à une décision. Ils sont énumérés un par un ci-dessous
(`ECARTS_ATTENDUS`, `ECARTS_ATTENDUS_CORRIGES`) — c'est leur liste, et non leur
nombre, qui fait la recette. `tests/test_export_classeur.py` les importe d'ici :
deux copies dériveraient.

Ce que la comparaison ne peut pas voir, et qu'il ne faut pas confondre avec une
identité : **les annotations ne sont plus au classeur**, `publication.json` en
est le seul détenteur (décision 3). Un aller-retour classeur → modèle →
classeur les perd. Le rapport le rappelle en clair.

Usage :

    python recette_classeur.py original.xlsx regenere.xlsx
    python recette_classeur.py original.xlsx --corrections
    python recette_classeur.py original.xlsx --depuis publication
"""
import argparse
import difflib
import os
import sys
import tempfile
from collections import namedtuple

import openpyxl
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import export_classeur as ec
import import_classeur as ic
import publication as pub
from texte_lrege import txt

#: Colonnes conservées par onglet (décision 3 du §5).
COLONNES = dict({ic.ONGLET_CHRONO: 8},
                **{n: 5 for n in ic.ONGLETS_ARME})
COLONNES.update({n: 12 for n, _ in ic.ONGLETS_TOURNOI})

#: Hors comparaison : l'onglet n'existe plus au classeur produit (décision 4).
ONGLETS_HORS_COMPARAISON = {ic.ONGLET_IGNORE}

CELLULE, AJOUT, RETRAIT = 'cellule', 'ajout', 'retrait'
ONGLET_AJOUTE, ONGLET_RETIRE = 'onglet ajouté', 'onglet retiré'


# ─────────────────────────────────────────────────────────────────────────────
# Écarts
# ─────────────────────────────────────────────────────────────────────────────

class Ecart(namedtuple('Ecart', 'nature onglet ligne colonne avant apres resume')):
    """Un écart, sous forme exploitable et sous forme lisible.

    `str(ecart)` rend la ligne de rapport ; c'est elle que les listes
    d'écarts attendus énumèrent, et elle ne doit pas changer de forme sans
    que ces listes changent avec.
    """

    __slots__ = ()

    def __str__(self):
        if self.nature == CELLULE:
            return '%s!%s%d : %r -> %r' % (self.onglet,
                                           get_column_letter(self.colonne),
                                           self.ligne, self.avant, self.apres)
        if self.nature == RETRAIT:
            return '%s L%d : ligne retirée — %s' % (self.onglet, self.ligne,
                                                    self.resume)
        if self.nature == AJOUT:
            return '%s L%d : ligne ajoutée — %s' % (self.onglet, self.ligne,
                                                    self.resume)
        return '%s : %s' % (self.onglet, self.nature)


def _cellule(onglet, ligne, colonne, avant, apres):
    return Ecart(CELLULE, onglet, ligne, colonne, avant, apres, None)


def _ligne(nature, onglet, ligne, valeurs):
    return Ecart(nature, onglet, ligne, None, None, None, _resume_ligne(valeurs))


# ─────────────────────────────────────────────────────────────────────────────
# Lecture normalisée
# ─────────────────────────────────────────────────────────────────────────────

def valeur_comparable(ws, r, c):
    """Valeur comparable : date rendue en texte, espaces de bord retirés."""
    return txt(ic.date_en_texte(ws.cell(r, c).value))


def lignes_comparables(ws, nb_colonnes):
    """Les lignes de l'onglet, colonnes conservées, lignes vides de fin ôtées."""
    lignes = [tuple(valeur_comparable(ws, r, c)
                    for c in range(1, nb_colonnes + 1))
              for r in range(1, ws.max_row + 1)]
    while lignes and not any(lignes[-1]):
        lignes.pop()
    return lignes


def _resume_ligne(ligne):
    """Les quatre premières colonnes : de quoi identifier la ligne déplacée."""
    return ' | '.join(ligne[:4])


def _nb_colonnes(nom, wa, wb_):
    """Colonnes conservées de l'onglet ; pour un onglet inconnu, sa largeur."""
    if nom in COLONNES:
        return COLONNES[nom]
    return max(wa[nom].max_column, wb_[nom].max_column)


# ─────────────────────────────────────────────────────────────────────────────
# Comparaison
# ─────────────────────────────────────────────────────────────────────────────

def comparer_onglet(nom, wsa, wsb, nb_colonnes):
    """Écarts d'un onglet, alignés sur le contenu des lignes."""
    ecarts = []
    la, lb = lignes_comparables(wsa, nb_colonnes), lignes_comparables(wsb, nb_colonnes)
    opcodes = difflib.SequenceMatcher(None, la, lb, autojunk=False).get_opcodes()
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            continue
        # Bloc de même hauteur : lignes modifiées en place, cellule par cellule.
        if tag == 'replace' and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                for c in range(nb_colonnes):
                    if la[i1 + k][c] != lb[j1 + k][c]:
                        ecarts.append(_cellule(nom, i1 + k + 1, c + 1,
                                               la[i1 + k][c], lb[j1 + k][c]))
            continue
        for i in range(i1, i2):
            ecarts.append(_ligne(RETRAIT, nom, i + 1, la[i]))
        for j in range(j1, j2):
            ecarts.append(_ligne(AJOUT, nom, j + 1, lb[j]))
    return ecarts


def comparer_detaille(chemin_a, chemin_b):
    """Écarts entre deux classeurs, sous forme d'objets `Ecart`.

    Les onglets sont pris dans l'ordre du classeur B ; un onglet présent d'un
    seul côté est signalé, jamais comparé à vide.
    """
    a = openpyxl.load_workbook(chemin_a, data_only=True)
    b = openpyxl.load_workbook(chemin_b, data_only=True)
    ecarts = []
    for nom in b.sheetnames:
        if nom in ONGLETS_HORS_COMPARAISON:
            continue
        if nom not in a.sheetnames:
            ecarts.append(Ecart(ONGLET_AJOUTE, nom, None, None, None, None, None))
            continue
        ecarts += comparer_onglet(nom, a[nom], b[nom], _nb_colonnes(nom, a, b))
    for nom in a.sheetnames:
        if nom not in b.sheetnames and nom not in ONGLETS_HORS_COMPARAISON:
            ecarts.append(Ecart(ONGLET_RETIRE, nom, None, None, None, None, None))
    return ecarts


def comparer(chemin_a, chemin_b):
    """Les mêmes écarts, en lignes de rapport — forme historique du Lot 3."""
    return [str(e) for e in comparer_detaille(chemin_a, chemin_b)]


def onglets_compares(chemin_a, chemin_b):
    a = openpyxl.load_workbook(chemin_a, read_only=True)
    b = openpyxl.load_workbook(chemin_b, read_only=True)
    noms = [n for n in b.sheetnames
            if n in a.sheetnames and n not in ONGLETS_HORS_COMPARAISON]
    a.close()
    b.close()
    return noms


# ─────────────────────────────────────────────────────────────────────────────
# Écarts attendus — la recette du §4, entrée par entrée
# ─────────────────────────────────────────────────────────────────────────────

#: Les écarts attendus entre le classeur d'origine et sa régénération, hors
#: corrections du §7. Aucun n'est une perte : six cellules vides sont
#: renseignées, deux lignes appliquent une décision déjà actée, deux cellules
#: tranchent un écart interne au classeur.
ECARTS_ATTENDUS = [
    # Lieu consolidé : le modèle ne tient qu'un `lieu` par ligne, le générateur
    # l'écrit partout où la ligne paraît. Les six cellules étaient vides, le
    # lieu n'était écrit qu'à l'onglet Transverse.
    "Chronologique!F12 : '' -> 'VANDOEUVRE'",
    "Chronologique!F19 : '' -> 'EPINAL'",
    "Chronologique!F36 : '' -> 'THIONVILLE SET'",
    "Chronologique!F41 : '' -> 'ST DIE'",
    # Décision 6 du §5 bis : la ligne de tournoi du Chronologique est une
    # restitution de l'onglet `Tournois Lorraine`, qui porte le 3-4 avril. Le
    # Chronologique la donnait au 1-2 mai — c'est la dérive qu'arbitre le §7.
    'Chronologique L43 : ligne ajoutée — 3-4 avril 2027 | sam-dim | Tournoi Lorraine | Tournoi club',
    'Chronologique L46 : ligne retirée — 1-2 mai 2027 | sam-dim | Tournoi Lorraine | Tournoi club',
    # Décision 1 du §5 : les onglets par arme font foi sur le Master.
    'Chronologique L47 : ligne retirée — mai 2027 | ? | Transverse | Master',
    'Chronologique L47 : ligne ajoutée — 23 mai 2027 | dim | Transverse | Master',
    # Lieu consolidé, suite : la Zone paraît aussi sur les onglets de ses armes.
    "Épée!E11 : '' -> 'en BFC'",
    "Fleuret!E7 : '' -> 'en BFC'",
    # Relevé du Lot 2 : le M15 n'est pas sur la même manche au Chronologique et
    # à l'onglet Transverse. Sans les corrections, c'est le Chronologique qui
    # est repris, donc l'onglet qui bouge. L'arbitrage du 11/09/2026 — le M15
    # relève de CDL 1 — passe par les corrections du §7, ci-dessous.
    "Transverse!D3 : 'M9-M11-M13--M15' -> 'M9-M11-M13'",
    "Transverse!D4 : 'M9-M11-M13' -> 'M9-M11-M13-M15'",
]

#: Les mêmes, plus les corrections du §7. Trois différences de forme :
#: `Chronologique!F41` n'y figure plus (la ligne CHDL change de date, elle est
#: rendue comme un déplacement, ST DIE compris) ; l'arbitrage du M15 déplace
#: l'écart du côté du Chronologique ; et la quatrième correction du §7 porte
#: sur `Chronologique!I41`, colonne supprimée, donc invisible ici.
ECARTS_ATTENDUS_CORRIGES = [
    # M15 rattaché à CDL 1 (11/09/2026) : le Chronologique le prend à la 1re
    # manche et le rend à la 2e ; le double tiret de l'onglet est redressé.
    "Chronologique!E12 : 'M9-M11-M13' -> 'M9-M11-M13-M15'",
    "Chronologique!F12 : '' -> 'VANDOEUVRE'",
    "Chronologique!E19 : 'M9-M11-M13-M15' -> 'M9-M11-M13'",
    "Chronologique!F19 : '' -> 'EPINAL'",
    "Chronologique!F36 : '' -> 'THIONVILLE SET'",
    # CHDL arbitré aux 1-2 mai 2027 : la ligne quitte sa place d'avril, et le
    # Tournoi des 3 villes prend celle-ci, à la date abrégée du §7.
    'Chronologique L41 : ligne retirée — 3-4 avr. 2027 ou 1-2 mai 2027 | sam-dim | Transverse | CHDL',
    'Chronologique L42 : ligne ajoutée — 3-4 avr. 2027 | sam-dim | Tournoi Lorraine | Tournoi club',
    'Chronologique L45 : ligne ajoutée — 1-2 mai 2027 | sam-dim | Transverse | CHDL',
    'Chronologique L46 : ligne retirée — 1-2 mai 2027 | sam-dim | Tournoi Lorraine | Tournoi club',
    'Chronologique L47 : ligne retirée — mai 2027 | ? | Transverse | Master',
    'Chronologique L47 : ligne ajoutée — 23 mai 2027 | dim | Transverse | Master',
    "Épée!E11 : '' -> 'en BFC'",
    "Fleuret!E7 : '' -> 'en BFC'",
    "Transverse!D3 : 'M9-M11-M13--M15' -> 'M9-M11-M13-M15'",
    "Transverse!A6 : '3-4 avr. 2027 ou 1-2 mai 2027' -> '1-2 mai 2027'",
    "Tournois Lorraine!A5 : '3-4 avril 2027' -> '3-4 avr. 2027'",
]

#: Listes nommées, pour la ligne de commande.
ATTENDUS = {'lot3': ECARTS_ATTENDUS,
            'lot3-corrige': ECARTS_ATTENDUS_CORRIGES,
            'aucun': []}


def classer(ecarts, attendus):
    """Range les écarts en documentés / non documentés, et dit ceux qui manquent.

    Un écart attendu qui ne paraît plus est signalé au même titre qu'un écart
    inattendu : la recette porte sur la liste, pas sur le nombre.
    """
    rendus = [str(e) for e in ecarts]
    restants = list(attendus)
    documentes, non_documentes = [], []
    for e, rendu in zip(ecarts, rendus):
        if rendu in restants:
            restants.remove(rendu)
            documentes.append(e)
        else:
            non_documentes.append(e)
    return {'documentes': documentes,
            'non_documentes': non_documentes,
            'attendus_absents': restants}


# ─────────────────────────────────────────────────────────────────────────────
# Recette : classeur d'origine contre classeur régénéré
# ─────────────────────────────────────────────────────────────────────────────

def regenerer(original, depuis='classeur', corrections=False, sortie=None):
    """Écrit un classeur régénéré et rend `(chemin, lignes)`.

    `depuis='classeur'` relit `original` — c'est la boucle du Lot 3, elle ne
    touche pas à `publication.json`. `depuis='publication'` part du modèle
    stocké, qui est ce que produira la régénération intégrale.
    """
    if depuis == 'publication':
        lignes = pub.load_lignes()
    else:
        lignes, _ = ic.lire_classeur(original, appliquer_corrections=corrections)
    lignes = [dict(l) for l in lignes]
    for l in lignes:
        l.pop('_source', None)
    chemin = sortie or os.path.join(tempfile.mkdtemp(prefix='recette_'),
                                    'regenere.xlsx')
    ec.ecrire_classeur(lignes, chemin, backup=False)
    return chemin, lignes


def recette(original, compare=None, depuis='classeur', corrections=False,
            attendus=None, sortie=None):
    """Compare `original` à `compare`, ou à sa régénération, et classe les écarts."""
    lignes = None
    if compare is None:
        compare, lignes = regenerer(original, depuis, corrections, sortie)
        if attendus is None:
            attendus = (ECARTS_ATTENDUS_CORRIGES
                        if (corrections or depuis == 'publication')
                        else ECARTS_ATTENDUS)
    elif attendus is None:
        attendus = []

    ecarts = comparer_detaille(original, compare)
    rapport = classer(ecarts, attendus)
    rapport.update({
        'origine': original, 'compare': compare, 'ecarts': ecarts,
        'onglets': onglets_compares(original, compare),
        'lignes': len(lignes) if lignes is not None else None,
        'natures': {n: sum(1 for e in ecarts if e.nature == n)
                    for n in (CELLULE, AJOUT, RETRAIT, ONGLET_AJOUTE,
                              ONGLET_RETIRE)},
        'annotations': (sum(1 for l in lignes if l.get('notes'))
                        if lignes is not None else None),
    })
    rapport['conforme'] = (not rapport['non_documentes']
                           and not rapport['attendus_absents'])
    return rapport


def _resume(rapport):
    n = rapport['natures']
    out = ['%s  ->  %s' % (os.path.basename(rapport['origine']),
                           os.path.basename(rapport['compare'])),
           '%d onglet(s) comparé(s), toutes colonnes conservées%s'
           % (len(rapport['onglets']),
              '' if rapport['lignes'] is None
              else ', %d ligne(s) au modèle' % rapport['lignes']),
           '',
           'Écarts : %d  —  %d cellule(s), %d ligne(s) ajoutée(s), '
           '%d ligne(s) retirée(s)'
           % (len(rapport['ecarts']), n[CELLULE], n[AJOUT], n[RETRAIT])]
    if n[ONGLET_AJOUTE] or n[ONGLET_RETIRE]:
        out.append('  dont onglets : %d ajouté(s), %d retiré(s)'
                   % (n[ONGLET_AJOUTE], n[ONGLET_RETIRE]))

    if rapport['documentes']:
        out.append('\nDocumentés (%d) — décisions actées, §5 ter du plan :'
                   % len(rapport['documentes']))
        out += ['  . ' + str(e) for e in rapport['documentes']]
    if rapport['non_documentes']:
        out.append('\nNON DOCUMENTÉS (%d) :' % len(rapport['non_documentes']))
        out += ['  ! ' + str(e) for e in rapport['non_documentes']]
    if rapport['attendus_absents']:
        out.append('\nAttendus non retrouvés (%d) :'
                   % len(rapport['attendus_absents']))
        out += ['  ? ' + str(e) for e in rapport['attendus_absents']]

    out.append('\n%s' % ('Recette conforme : aucun écart hors de la liste.'
                         if rapport['conforme']
                         else 'RECETTE NON CONFORME.'))
    if rapport['annotations']:
        out.append('Rappel : %d ligne(s) portent une annotation, qu\'aucun '
                   'classeur ne porte plus (décision 3).\n'
                   'publication.json en est le seul détenteur — la comparaison '
                   'ne peut pas le voir.' % rapport['annotations'])
    return '\n'.join(out)


def main(argv=None):
    p = argparse.ArgumentParser(
        description='Compare deux classeurs — tous onglets, toutes colonnes '
                    'conservées (Lot 4).')
    p.add_argument('original', help='classeur de référence')
    p.add_argument('compare', nargs='?',
                   help='second classeur ; régénéré à la volée si absent')
    p.add_argument('--depuis', choices=('classeur', 'publication'),
                   default='classeur',
                   help='source de la régénération (défaut : relecture du classeur)')
    p.add_argument('--corrections', action='store_true',
                   help='applique les corrections en attente du §7 à la relecture')
    p.add_argument('--attendus', choices=sorted(ATTENDUS),
                   help='liste d\'écarts attendus à appliquer')
    p.add_argument('--sortie', help='conserve le classeur régénéré à ce chemin')
    a = p.parse_args(argv)
    rapport = recette(a.original, a.compare, a.depuis, a.corrections,
                      ATTENDUS[a.attendus] if a.attendus else None, a.sortie)
    print(_resume(rapport))
    return 0 if rapport['conforme'] else 1


if __name__ == '__main__':
    sys.exit(main())
