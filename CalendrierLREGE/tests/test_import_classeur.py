# -*- coding: utf-8 -*-
"""Lot 2 — reprise du classeur 2026-2027 vers publication.json.

Le classeur réel est joint en fixture : c'est le seul jeu d'essai qui vaille
pour ce lot, et il fige la baseline du critère de fin (§4 du plan).

Deux références se recoupent ici :

- `fixtures/php_reference.json`, produit par l'extension WordPress, dit ce que
  le lecteur doit rendre à l'identique sur les dix champs qu'elle lit ;
- le classeur lui-même, pour les colonnes qu'elle ignore — `notes`, `contact`,
  `email`, onglets par arme.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import import_classeur as ic
import publication as pub
from texte_lrege import developper, normaliser

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
CLASSEUR = os.environ.get('LREGE_CLASSEUR') or os.path.join(
    FIXTURES, 'Calendrier_LREGE_2026-2027.xlsx')

with open(os.path.join(FIXTURES, 'php_reference.json'), encoding='utf-8') as _f:
    REF = json.load(_f)['classeur']

#: Les quatre écarts attendus avec l'extension : la ligne Master, reprise sur
#: les onglets par arme (décision 1 du §5). Ils ne dépendent pas des
#: corrections du §7 — la décision 1 s'applique toujours.
ECARTS_DECISION_1 = {'date_texte', 'jours', 'tri_key', 'cle_source'}


@pytest.fixture(scope='module')
def lu():
    lignes, rapport = ic.lire_classeur(CLASSEUR)
    return lignes, rapport


@pytest.fixture(scope='module')
def brut():
    """Lecture sans les corrections du §7 — celle qui se compare à l'extension."""
    lignes, rapport = ic.lire_classeur(CLASSEUR, appliquer_corrections=False)
    return lignes, rapport


def _ligne(lignes, **critères):
    trouvees = [l for l in lignes
                if all(l.get(k) == v for k, v in critères.items())]
    assert len(trouvees) == 1, '%r -> %d ligne(s)' % (critères, len(trouvees))
    return trouvees[0]


# ─────────────────────────────────────────────────────────────────────────────
# Critère de fin du Lot 2 (§4 du plan)
# ─────────────────────────────────────────────────────────────────────────────

class TestCritereDeFin:

    def test_45_lignes_publiables(self, lu):
        lignes, rapport = lu
        assert (rapport['lignes'], rapport['officielles'], rapport['tournois']) \
            == (45, 36, 9)
        assert len(lignes) == 45

    def test_annotations_contacts_et_emails(self, lu, brut):
        """Critère de fin du Lot 2 : 11 annotations reprises, 9 contacts, 9 e-mails.

        Le compte a bougé depuis, sans que le lecteur change : le classeur en
        porte 12, le §7 en retire trois désormais périmées (L41 depuis
        l'arbitrage du CHDL, L19 et L20 depuis la décision 8). La lecture
        brute reste le juge — c'est elle qui dit ce que le classeur contient.
        """
        assert brut[1]['notes'] == 12
        assert (lu[1]['notes'], lu[1]['contacts'], lu[1]['emails']) == (9, 9, 9)

    def test_master_repris_sur_les_onglets_par_arme(self, lu):
        """23 mai 2027, Épée + Fleuret + Sabre, Wassy — décision 1 du §5."""
        m = _ligne(lu[0], type='Master')
        assert m['date_texte'] == '23 mai 2027'
        assert m['jours'] == 'dim'
        assert m['tri_key'] == 20270523
        assert m['armes'] == ['Épée', 'Fleuret', 'Sabre']
        assert m['lieu'] == 'Wassy'

    def test_zone_m15_a_epee_et_fleuret(self, lu):
        z = _ligne(lu[0], type='Zone')
        assert z['date_texte'] == '6-7 fév. 2027'
        assert z['armes'] == ['Épée', 'Fleuret']
        assert z['categories'] == 'M15'


# ─────────────────────────────────────────────────────────────────────────────
# Conformité à l'extension WordPress
# ─────────────────────────────────────────────────────────────────────────────

class TestConformiteExtension:

    CHAMPS = ('date_texte', 'jours', 'bloc', 'type', 'lieu', 'club', 'statut',
              'est_tournoi', 'tri_key', 'cle_source', 'cats', 'cats_index')

    def test_memes_lignes_dans_le_meme_ordre(self, brut):
        lignes, _ = brut
        assert len(lignes) == len(REF['lignes']) == 45
        assert [l['tri_key'] for l in lignes] == sorted(l['tri_key'] for l in lignes)

    def test_dix_champs_identiques_sauf_decision_1(self, brut):
        ecarts = {}
        for obtenu, attendu in zip(brut[0], REF['lignes']):
            for champ in self.CHAMPS:
                if obtenu[champ] != attendu[champ]:
                    ecarts.setdefault(attendu['type'], set()).add(champ)
        assert ecarts == {'Master': ECARTS_DECISION_1}

    def test_categories_publiees_identiques(self, brut):
        """Le brut du classeur, normalisé, rend exactement ce que publie le PHP."""
        ecarts = []
        for obtenu, attendu in zip(brut[0], REF['lignes']):
            publiee = normaliser(developper(obtenu['categories']))
            if publiee != attendu['categories']:
                ecarts.append('%s : attendu %r, obtenu %r (brut %r)'
                              % (attendu['cle_source'], attendu['categories'],
                                 publiee, obtenu['categories']))
        assert ecarts == []

    def test_categories_conservees_en_texte_libre(self, lu):
        """§3 du plan : `categories` n'est jamais réécrit à la lecture."""
        assert _ligne(lu[0], bloc='Fleuret', type='ER1')['categories'] == 'M13 à Seniors'
        assert _ligne(lu[0], date_texte='14-15 nov. 2026')['categories'] == 'VET + M13'
        assert _ligne(lu[0], bloc='Parasport', type='ER1')['categories'] == 'PARA'

    def test_armes_de_tournoi_identiques(self, brut):
        for obtenu, attendu in zip(brut[0], REF['lignes']):
            if attendu['est_tournoi']:
                assert obtenu['armes'] == attendu['armes'], attendu['cle_source']

    def test_aucun_doublon_de_cle_source(self, lu):
        assert lu[1]['doublons'] == []
        cles = [l['cle_source'] for l in lu[0]]
        assert len(set(cles)) == 45


# ─────────────────────────────────────────────────────────────────────────────
# Colonnes que l'extension ne lit pas
# ─────────────────────────────────────────────────────────────────────────────

class TestColonnesHorsExtension:

    def test_annotations_sans_chevauchement(self, brut):
        """Lecture brute : les 12 annotations du classeur, chevauchements retirés."""
        notes = [l['notes'] for l in brut[0] if l['notes']]
        assert len(notes) == 12
        assert not any(ic.MARQUEUR_CHEVAUCHEMENT in n for n in notes)
        assert 'AG Ligue + championnats départementaux' in notes
        assert 'CONFLIT M15 : CID M15 le même week-end' in notes
        assert 'Source : « 30-janv » — année et second jour absents' in notes

    def test_annotations_perimees_retirees(self, lu, brut):
        """Trois annotations tombent avec ce qui les a rendues fausses.

        L41 depuis l'arbitrage du CHDL ; L19 et L20 depuis la décision 8 —
        `CDL 2` ne portant plus le M15, le conflit du 12-13 déc. n'a plus
        d'objet, et les deux annotations qui se répondaient tombent ensemble.
        """
        assert brut[1]['notes'] == 12
        assert lu[1]['notes'] == 9
        assert _ligne(lu[0], type='CHDL')['notes'] == ''
        assert _ligne(lu[0], type='CDL 2')['notes'] == ''
        assert _ligne(lu[0], type='CID')['notes'] == ''
        assert not any('CONFLIT M15' in l['notes'] for l in lu[0])

    def test_contacts_et_emails_sur_les_bons_clubs(self, lu):
        t = _ligne(lu[0], club='Souffel escrime club')
        assert t['contact'] == 'Luc heintzelmann - president'
        assert t['email'] == 'souffel.escrime.club@gmail.com'
        assert all(l['contact'] and l['email'] for l in lu[0] if l['est_tournoi'])
        assert not any(l['contact'] or l['email'] for l in lu[0] if not l['est_tournoi'])

    def test_tournoi_porte_son_nom_et_pas_categories(self, lu):
        t = _ligne(lu[0], club='Sarreguemines')
        assert t['type'] == 'coupe de Moselle 1ère manche'
        assert t['bloc'] == 'Lorraine' and t['est_tournoi'] is True
        assert t['categories'] == ''
        assert [a['arme'] for a in t['armes']] == ['Fleuret', 'Épée', 'Sabre']

    def test_lieux_repeches_sur_l_onglet_transverse(self, lu):
        lignes, rapport = lu
        assert len(rapport['repechages']) == 4
        repeches = {_ligne(lignes, type=t)['lieu']
                    for t in ('CDL 1', 'CDL 2', 'CDL 3', 'CHDL')}
        assert repeches == {'VANDOEUVRE', 'EPINAL', 'THIONVILLE SET', 'ST DIE'}

    def test_onglet_transverse_derivable_du_bloc(self, lu):
        """Le Lot 3 n'a pas besoin d'un champ de plus pour régénérer l'onglet.

        L'onglet `Transverse` contient exactement les lignes de bloc
        « Coupe de Lorraine » ; AG, CID, Zone et Master (bloc « Autres »)
        n'y figurent pas.
        """
        cdl = {l['type'] for l in lu[0] if l['bloc'] == 'Coupe de Lorraine'}
        autres = {l['type'] for l in lu[0] if l['bloc'] == 'Autres'}
        assert cdl == {'CDL 1', 'CDL 2', 'CDL 3', 'CHDL'}
        assert autres == {'AG + Ch. dép.', 'CID', 'Zone', 'Master'}

    def test_armes_officielles_derivent_les_onglets(self, lu):
        for l in lu[0]:
            if l['est_tournoi']:
                continue
            if l['bloc'] in ('Coupe de Lorraine', 'Autres'):
                continue
            attendu = 'Para' if l['bloc'] == 'Parasport' else l['bloc']
            assert l['armes'] == [attendu], l['cle_source']


# ─────────────────────────────────────────────────────────────────────────────
# Corrections en attente (§7 du plan)
# ─────────────────────────────────────────────────────────────────────────────

class TestCorrections:

    def test_chdl_arbitre_au_1_2_mai(self, lu):
        c = _ligne(lu[0], type='CHDL')
        assert c['date_texte'] == '1-2 mai 2027'
        assert c['jours'] == 'sam-dim'
        assert c['tri_key'] == 20270501

    def test_tournoi_des_3_villes_en_abrege_et_ecart_accepte(self, lu):
        t = _ligne(lu[0], club='Laxou - Luneville - Toul')
        assert t['date_texte'] == '3-4 avr. 2027'
        assert t['ecart_accepte'] is True
        assert [l['cle_source'] for l in lu[0] if l['ecart_accepte']] \
            == [t['cle_source']]

    def test_m15_rattache_a_cdl_1(self, lu):
        """Arbitré le 11/09/2026 : l'onglet `Transverse` faisait foi.

        Le M15 relève de la 1re manche de Coupe de Lorraine, pas de la 2e.
        Le double tiret de `Transverse!D3` est une faute de saisie, corrigée
        avec — sans quoi les deux côtés resteraient en écart.
        """
        assert _ligne(lu[0], type='CDL 1')['categories'] == 'M9-M11-M13-M15'
        assert _ligne(lu[0], type='CDL 2')['categories'] == 'M9-M11-M13'
        assert lu[1]['ecarts'] == []

    def test_journal_complet(self, lu):
        """Régression : le journal du §7 ne doit pas écraser celui de la décision 1."""
        journal = lu[1]['corrections']
        assert len(journal) == 11
        assert any('Chronologique!A41' in j for j in journal)
        assert any('Tournois Lorraine!A5' in j for j in journal)
        assert any('Chronologique!E12' in j for j in journal)
        assert any('Chronologique!E19' in j for j in journal)
        assert any('Transverse!D3' in j for j in journal)
        assert len([j for j in journal if 'Chronologique!I' in j]) == 3
        assert any("date_texte : 'mai 2027' -> '23 mai 2027'" in j for j in journal)

    def test_aucune_correction_sur_une_ligne_restituee(self, lu):
        """Toute correction du §7 porte sur une cellule réellement lue.

        `Chronologique!A46` a été retirée de la table : cette ligne-là est
        régénérée depuis la ligne de publication, pas corrigée.
        """
        assert lu[1]['corrections_hors_lecture'] == []
        assert not any(o == ic.ONGLET_CHRONO and cel.startswith('A')
                       and int(cel[1:]) in (46,)
                       for o, cel, _a, _c, _e, _m in ic.CORRECTIONS_CELLULES)

    def test_correction_non_appliquee_si_la_cellule_a_bouge(self):
        c = ic._Corrections(actives=True)
        assert c.cellule('Transverse', 'A', 6, 'une autre valeur') == 'une autre valeur'
        assert c.journal == []
        assert len(c.non_appliquees) == 1 and 'Transverse!A6' in c.non_appliquees[0]

    def test_sans_corrections_le_classeur_est_lu_tel_quel(self, brut):
        lignes, rapport = brut
        assert rapport['corrections'] == [j for j in rapport['corrections']
                                          if 'décision 1' in j]
        assert _ligne(lignes, type='CHDL')['date_texte'] \
            == '3-4 avr. 2027 ou 1-2 mai 2027'
        assert not any(l['ecart_accepte'] for l in lignes)


# ─────────────────────────────────────────────────────────────────────────────
# Signalements — jamais de correction d'office
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalements:

    def test_ecart_de_categories_signale_pas_corrige(self, brut):
        """Sans les corrections, l'écart CDL 1 / CDL 2 est signalé, jamais comblé.

        C'est ce signalement qui a permis l'arbitrage du 11/09/2026 : le
        lecteur ne choisit pas de côté, il montre les deux.
        """
        lignes, rapport = brut
        ecarts = rapport['ecarts']
        assert len(ecarts) == 2
        assert all('catégories' in e for e in ecarts)
        assert _ligne(lignes, type='CDL 1')['categories'] == 'M9-M11-M13'
        assert _ligne(lignes, type='CDL 2')['categories'] == 'M9-M11-M13-M15'

    def test_30_lignes_sans_lieu(self, lu):
        """Baseline du Lot 5 : 30 lignes sans lieu après repêchage."""
        assert lu[1]['sans_lieu'] == 30

    def test_aucune_date_illisible_apres_corrections(self, lu):
        assert [a for a in lu[1]['anomalies'] if 'non interprétable' in a] == []

    def test_statuts_a_confirmer_remontes(self, lu):
        assert len(lu[1]['a_confirmer']) == 7

    def test_lisez_moi_ignore(self, lu):
        assert lu[1]['onglets_ignores'] == ['Lisez-moi']
        assert 'Lisez-moi' not in lu[1]['onglets_lus']


# ─────────────────────────────────────────────────────────────────────────────
# Outils de lecture
# ─────────────────────────────────────────────────────────────────────────────

class TestOutils:

    @pytest.mark.parametrize('brut,attendu', [
        ('', ''),
        ('Chevauche : Épée ER1 (Seniors + Vétérans)', ''),
        ('AG Ligue + championnats départementaux', 'AG Ligue + championnats départementaux'),
        ('CONFLIT M15 : CID M15 le même week-end — Chevauche : Sabre laser CR2 D1',
         'CONFLIT M15 : CID M15 le même week-end'),
        ('Trois épreuves le même jour — à confirmer', 'Trois épreuves le même jour — à confirmer'),
    ])
    def test_note_utile(self, brut, attendu):
        assert ic.note_utile(brut) == attendu

    @pytest.mark.parametrize('bloc,type_,attendu', [
        ('Épée', 'ER1', 'Épée'),
        ('Para', 'ER1', 'Parasport'),
        ('Transverse', 'CDL 1', 'Coupe de Lorraine'),
        ('Transverse', 'CHDL', 'Coupe de Lorraine'),
        ('Transverse', 'CID', 'Autres'),
        ('Transverse', 'Master', 'Autres'),
        ('Tournoi Alsace', 'Tournoi club', 'Alsace'),
        ('Tournoi Champagne-Ardenne', 'Tournoi club', 'Champagne-Ardenne'),
    ])
    def test_bloc_publie(self, bloc, type_, attendu):
        assert ic.bloc_publie(bloc, type_) == attendu

    def test_date_en_texte(self):
        import datetime
        assert ic.date_en_texte(datetime.datetime(2027, 5, 23)) == '23 mai 2027'
        assert ic.date_en_texte(datetime.datetime(2026, 9, 26)) == '26 sept. 2026'
        assert ic.date_en_texte('26-27 sept. 2026') == '26-27 sept. 2026'

    def test_champs_calcules_ne_reecrit_pas_la_saisie(self):
        l = pub.ligne_vide(date_texte='26-27 sept. 2026', categories='M13 à Seniors')
        pub.champs_calcules(l)
        assert l['categories'] == 'M13 à Seniors'        # inchangé
        assert l['categories_publiees'] == 'M13-M15-M17-M20-Seniors'
        assert l['cats_index'] == '|M13|M15|M17|M20|Seniors|'
        assert l['tri_key'] == 20260926


class TestRestitutionDuChronologique:
    """La ligne de tournoi du Chronologique est dérivée, pas lue."""

    def test_restitution_du_chronologique_derivable(self, brut):
        """Les 9 lignes de tournoi sont reproduites, à la correction du §7 près.

        C'est ce qui autorise le Lot 3 à régénérer ces lignes plutôt qu'à
        corriger `Chronologique!A46` : sans quoi la même date serait écrite à
        deux endroits, et pourrait de nouveau diverger.
        """
        import openpyxl
        from texte_lrege import txt

        lignes, _ = brut
        par_cle = {}
        for l in lignes:
            if l['est_tournoi']:
                par_cle.setdefault(l['club'], []).append(l)

        ws = openpyxl.load_workbook(CLASSEUR, data_only=True)[ic.ONGLET_CHRONO]
        vus, ecarts = 0, []
        for r in range(3, ws.max_row + 1):
            reel = [txt(ws.cell(r, c).value) for c in range(1, 9)]
            if not reel[2].startswith('Tournoi '):
                continue
            vus += 1
            cands = par_cle.get(reel[6], [])
            l = cands[0] if len(cands) == 1 else \
                next((c for c in cands if c['date_texte'] == reel[0]), None)
            assert l is not None, 'ligne %d : club %r non apparié' % (r, reel[6])
            genere = ic.rendu_chronologique_tournoi(l)
            if genere != reel:
                ecarts.append('L%d %s : %r != %r' % (r, l['club'], reel, genere))

        assert vus == 9
        # Seul écart admis : la date du Tournoi des 3 villes, objet du §7.
        assert len(ecarts) == 1 and 'Laxou' in ecarts[0]

    def test_restitution_exacte_apres_corrections(self, lu):
        """Corrections appliquées, la restitution vaut la ligne du classeur."""
        t = _ligne(lu[0], club='Laxou - Luneville - Toul')
        assert ic.rendu_chronologique_tournoi(t)[:4] == [
            '3-4 avr. 2027', 'sam-dim', 'Tournoi Lorraine', 'Tournoi club']


# ─────────────────────────────────────────────────────────────────────────────
# Écriture
# ─────────────────────────────────────────────────────────────────────────────

def test_importer_ecrit_publication_json(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, 'PUBLICATION_FILE', str(tmp_path / 'publication.json'))
    rapport = ic.importer(CLASSEUR)
    assert rapport['ecrit'] is True
    lignes = pub.load_lignes()
    assert len(lignes) == 45
    assert all('_source' not in l for l in lignes)
    assert all(set(pub.CHAMPS_DEFAUT) <= set(l) for l in lignes)
    assert all(l['categories_publiees'] is not None for l in lignes)
    assert sum(1 for l in lignes if l['notes']) == 9
    assert sum(1 for l in lignes if l['contact']) == 9
