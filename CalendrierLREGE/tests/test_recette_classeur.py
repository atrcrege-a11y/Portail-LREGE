# -*- coding: utf-8 -*-
"""Lot 4 — contrôle de recette élargi.

Ce que ces cas vérifient, au-delà du critère de fin du §4 lui-même (qui est
porté par `test_export_classeur.py`, lequel importe la comparaison d'ici) :

- l'alignement se fait sur le contenu, pas sur l'indice de ligne — une ligne
  déplacée vaut un retrait et un ajout, jamais une cascade de trente écarts ;
- les colonnes hors comparaison (I du Chronologique, M des Tournois) et
  l'onglet `Lisez-moi` restent invisibles, décisions 3 et 4 du §5 ;
- la normalisation de la décision 7 tient : espaces de bord et vraie date
  Excel ne font pas écart ;
- un écart non documenté est remonté comme tel, et un écart attendu qui
  disparaît aussi — la recette porte sur la liste, pas sur le nombre.
"""
import datetime
import os
import shutil
import sys

import openpyxl
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import import_classeur as ic
import recette_classeur as rc

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
CLASSEUR = os.environ.get('LREGE_CLASSEUR') or os.path.join(
    FIXTURES, 'Calendrier_LREGE_2026-2027.xlsx')


@pytest.fixture(scope='module')
def regenere(tmp_path_factory):
    """Le classeur régénéré sans les corrections du §7, gardé sur disque."""
    chemin = str(tmp_path_factory.mktemp('lot4') / 'regenere.xlsx')
    rc.regenerer(CLASSEUR, sortie=chemin)
    return chemin


def _copie_modifiee(source, cible, modifs, supprimer=None, deplacer=None):
    """Copie du classeur avec quelques cellules changées — support des cas."""
    shutil.copy(source, cible)
    wb = openpyxl.load_workbook(cible)
    for onglet, cellule, valeur in modifs:
        wb[onglet][cellule] = valeur
    if supprimer:
        onglet, r = supprimer
        wb[onglet].delete_rows(r)
    if deplacer:
        onglet, depuis, vers = deplacer
        ws = wb[onglet]
        ligne = [ws.cell(depuis, c).value for c in range(1, ws.max_column + 1)]
        ws.delete_rows(depuis)
        ws.insert_rows(vers)
        for c, v in enumerate(ligne, start=1):
            ws.cell(vers, c).value = v
    wb.save(cible)
    return cible


# ─────────────────────────────────────────────────────────────────────────────
# Identité et natures d'écart
# ─────────────────────────────────────────────────────────────────────────────

class TestComparaison:

    def test_un_classeur_est_identique_a_lui_meme(self, regenere):
        assert rc.comparer(regenere, regenere) == []

    def test_cellule_modifiee_rendue_avec_avant_et_apres(self, regenere, tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'a.xlsx'),
                                [('Épée', 'E3', 'MULHOUSE')])
        ecarts = rc.comparer_detaille(regenere, autre)
        assert len(ecarts) == 1
        e = ecarts[0]
        assert (e.nature, e.onglet, e.ligne, e.colonne) == (rc.CELLULE, 'Épée', 3, 5)
        assert e.apres == 'MULHOUSE' and e.avant != 'MULHOUSE'
        assert str(e).startswith("Épée!E3 : ")

    def test_ligne_retiree_ne_fait_pas_cascader_les_suivantes(self, regenere,
                                                             tmp_path):
        """Le premier essai du Lot 3 remontait 31 écarts là où il y en a un."""
        autre = _copie_modifiee(regenere, str(tmp_path / 'b.xlsx'), [],
                                supprimer=('Chronologique', 10))
        ecarts = rc.comparer_detaille(regenere, autre)
        assert [e.nature for e in ecarts] == [rc.RETRAIT]
        assert ecarts[0].ligne == 10

    def test_ligne_deplacee_vaut_un_retrait_et_un_ajout(self, regenere, tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'c.xlsx'), [],
                                deplacer=('Chronologique', 10, 20))
        natures = [e.nature for e in rc.comparer_detaille(regenere, autre)]
        assert sorted(natures) == [rc.AJOUT, rc.RETRAIT]

    def test_resume_de_ligne_porte_les_quatre_premieres_colonnes(self, regenere,
                                                                 tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'd.xlsx'), [],
                                supprimer=('Chronologique', 3))
        e = rc.comparer_detaille(regenere, autre)[0]
        assert e.resume.count(' | ') == 3
        assert str(e).startswith('Chronologique L3 : ligne retirée — ')


class TestNormalisation:
    """Décision 7 du §5 bis — ce qui ne doit pas faire écart."""

    def test_espaces_de_bord_ignores(self, regenere, tmp_path):
        wb = openpyxl.load_workbook(regenere)
        valeur = wb['Chronologique']['C3'].value
        assert valeur, 'la fixture a changé de forme'
        autre = _copie_modifiee(regenere, str(tmp_path / 'e.xlsx'),
                                [('Chronologique', 'C3', '  %s  ' % valeur)])
        assert rc.comparer(regenere, autre) == []

    def test_vraie_date_excel_comparee_a_son_texte(self, tmp_path):
        """`Épée!A13` et ses jumelles : une date saisie, pas du texte."""
        jour = datetime.datetime(2026, 10, 3)
        chemins = []
        for nom, valeur in (('date.xlsx', jour),
                            ('texte.xlsx', ic.date_en_texte(jour))):
            chemin = str(tmp_path / nom)
            wb = openpyxl.Workbook()
            wb.active.title = 'Épée'
            wb['Épée']['A3'] = valeur
            wb.save(chemin)
            chemins.append(chemin)
        assert ic.date_en_texte(jour) == '3 oct. 2026'
        assert rc.comparer(*chemins) == []


class TestPerimetre:
    """Ce qui est volontairement hors comparaison (décisions 3 et 4 du §5)."""

    def test_colonne_i_du_chronologique_hors_comparaison(self, regenere, tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'g.xlsx'),
                                [('Chronologique', 'I3', 'chevauchement')])
        assert rc.comparer(regenere, autre) == []

    def test_colonne_m_des_onglets_tournois_hors_comparaison(self, regenere,
                                                             tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'h.xlsx'),
                                [('Tournois Alsace', 'M3', 'chevauchement')])
        assert rc.comparer(regenere, autre) == []

    def test_colonnes_lues_jusqu_a_la_derniere_conservee(self, regenere, tmp_path):
        """K des Tournois : l'extension ne la lit pas, la recette si."""
        autre = _copie_modifiee(regenere, str(tmp_path / 'i.xlsx'),
                                [('Tournois Alsace', 'K3', 'autre@exemple.fr')])
        assert [e.colonne for e in rc.comparer_detaille(regenere, autre)] == [11]

    def test_onglet_lisez_moi_hors_comparaison(self, regenere, tmp_path):
        """Il n'existe plus au classeur produit — sa disparition n'est pas un écart."""
        autre = str(tmp_path / 'j.xlsx')
        shutil.copy(regenere, autre)
        wb = openpyxl.load_workbook(autre)
        wb.create_sheet(ic.ONGLET_IGNORE)['A1'] = 'notice'
        wb.save(autre)
        assert rc.comparer(regenere, autre) == []
        assert rc.comparer(autre, regenere) == []

    def test_onglet_present_d_un_seul_cote_signale(self, regenere, tmp_path):
        autre = str(tmp_path / 'k.xlsx')
        shutil.copy(regenere, autre)
        wb = openpyxl.load_workbook(autre)
        wb.create_sheet('Tournois Bourgogne')['A1'] = 'territoire inconnu'
        wb.save(autre)
        ajout = rc.comparer_detaille(regenere, autre)
        assert [(e.nature, e.onglet) for e in ajout] \
            == [(rc.ONGLET_AJOUTE, 'Tournois Bourgogne')]
        retrait = rc.comparer_detaille(autre, regenere)
        assert [(e.nature, e.onglet) for e in retrait] \
            == [(rc.ONGLET_RETIRE, 'Tournois Bourgogne')]

    def test_les_douze_onglets_sont_compares(self, regenere):
        assert len(rc.onglets_compares(CLASSEUR, regenere)) == 12


# ─────────────────────────────────────────────────────────────────────────────
# Classement des écarts et critère de fin du §4
# ─────────────────────────────────────────────────────────────────────────────

class TestClassement:

    def test_ecart_attendu_reconnu_ecart_inattendu_remonte(self, regenere,
                                                           tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'l.xlsx'),
                                [('Épée', 'E3', 'MULHOUSE')])
        ecarts = rc.comparer_detaille(CLASSEUR, autre)
        r = rc.classer(ecarts, rc.ECARTS_ATTENDUS)
        assert len(r['documentes']) == len(rc.ECARTS_ATTENDUS)
        assert [str(e) for e in r['non_documentes']] \
            == ["Épée!E3 : '' -> 'MULHOUSE'"]
        assert r['attendus_absents'] == []

    def test_attendu_disparu_est_signale(self, regenere):
        ecarts = rc.comparer_detaille(CLASSEUR, regenere)
        r = rc.classer(ecarts, rc.ECARTS_ATTENDUS + ['Épée!Z99 : rien'])
        assert r['attendus_absents'] == ['Épée!Z99 : rien']

    def test_un_attendu_ne_couvre_qu_un_ecart(self):
        """Deux écarts identiques, un seul attendu : le second est remonté."""
        e = rc.Ecart(rc.CELLULE, 'Épée', 3, 5, '', 'X', None)
        r = rc.classer([e, e], [str(e)])
        assert len(r['documentes']) == 1 and len(r['non_documentes']) == 1


class TestRecette:

    def test_recette_sans_corrections_conforme(self):
        r = rc.recette(CLASSEUR)
        assert r['conforme']
        assert [str(e) for e in r['documentes']] == rc.ECARTS_ATTENDUS
        assert r['natures'][rc.CELLULE] == 8
        assert r['natures'][rc.AJOUT] == 2 and r['natures'][rc.RETRAIT] == 2
        assert r['lignes'] == 45

    def test_recette_avec_corrections_conforme(self):
        r = rc.recette(CLASSEUR, corrections=True)
        assert r['conforme']
        assert [str(e) for e in r['documentes']] == rc.ECARTS_ATTENDUS_CORRIGES

    def test_regeneration_depuis_publication_json_conforme(self):
        """Le critère qui autorise la régénération intégrale (§4, Lot 4)."""
        r = rc.recette(CLASSEUR, depuis='publication')
        assert r['conforme']
        assert [str(e) for e in r['documentes']] == rc.ECARTS_ATTENDUS_CORRIGES

    def test_ecart_inattendu_rend_la_recette_non_conforme(self, regenere,
                                                          tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'm.xlsx'),
                                [('Épée', 'E3', 'MULHOUSE')])
        r = rc.recette(CLASSEUR, autre, attendus=rc.ECARTS_ATTENDUS)
        assert not r['conforme'] and len(r['non_documentes']) == 1

    def test_deux_classeurs_fournis_aucun_attendu_par_defaut(self, regenere):
        """Comparaison brute : rien n'est absous d'office."""
        r = rc.recette(CLASSEUR, regenere)
        assert not r['conforme']
        assert len(r['non_documentes']) == len(rc.ECARTS_ATTENDUS)
        assert r['lignes'] is None

    def test_rappel_des_annotations_perdues(self):
        """La comparaison ne peut pas les voir : le rapport le dit en clair."""
        r = rc.recette(CLASSEUR)
        assert r['annotations'] == 12
        assert 'annotation' in rc._resume(r) and 'décision 3' in rc._resume(r)

    def test_sortie_conservee_si_demandee(self, tmp_path):
        chemin = str(tmp_path / 'garde.xlsx')
        r = rc.recette(CLASSEUR, sortie=chemin)
        assert os.path.exists(chemin) and r['compare'] == chemin


class TestLigneDeCommande:

    def test_code_retour_0_si_conforme(self):
        assert rc.main([CLASSEUR]) == 0

    def test_code_retour_1_si_ecart_non_documente(self, regenere, tmp_path):
        autre = _copie_modifiee(regenere, str(tmp_path / 'n.xlsx'),
                                [('Épée', 'E3', 'MULHOUSE')])
        assert rc.main([CLASSEUR, autre, '--attendus', 'lot3']) == 1

    def test_liste_attendus_nommee(self):
        assert rc.ATTENDUS['lot3'] is rc.ECARTS_ATTENDUS
        assert rc.ATTENDUS['lot3-corrige'] is rc.ECARTS_ATTENDUS_CORRIGES
        assert rc.ATTENDUS['aucun'] == []
