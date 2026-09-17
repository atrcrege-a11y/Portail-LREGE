# -*- coding: utf-8 -*-
"""Lot 1 — modèle et stockage de publication.json, et conformité au PHP.

Le fichier de référence `fixtures/php_reference.json` est produit par
l'extension WordPress `calendrier-lrege` v1.0.1 elle-même (voir
`fixtures/gen_ref.php`) : dates, catégories, clés d'appariement, et les 45
lignes réelles du classeur 2026-2027. Un écart ici veut dire que le module de
saisie publierait ou apparierait autrement que l'extension.
"""
import json, os, shutil, sys, subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import publication as pub
import texte_lrege as tl

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'fixtures', 'php_reference.json')

# Le garde-fou ci-dessous n'a de sens que si PHP CLI est réellement appelable :
# LREGE_EXT_DIR seul ne suffit pas (php peut être absent du PATH).
PHP = shutil.which('php')

with open(FIXTURE, encoding='utf-8') as _f:
    REF = json.load(_f)


# ─────────────────────────────────────────────────────────────────────────────
# Conformité au PHP — critère de fin du Lot 1
# ─────────────────────────────────────────────────────────────────────────────

class TestConformitePHP:

    @pytest.mark.parametrize('cas', REF['dates'], ids=lambda c: repr(c['in']))
    def test_tri_key(self, cas):
        assert tl.tri_key(cas['in']) == cas['tri_key']
        assert tl.date_illisible(cas['in']) is cas['illisible']

    @pytest.mark.parametrize('cas', REF['categories'], ids=lambda c: repr(c['in']))
    def test_categories_et_index(self, cas):
        dev = tl.developper(cas['in'])
        assert dev == cas['developpe']
        nor = tl.normaliser(dev)
        assert nor == cas['normalise']
        cats = tl.categories([nor])
        assert cats == cas['cats']
        assert tl.cats_index(cats) == cas['cats_index']

    @pytest.mark.parametrize('cas', REF['cats_index'], ids=lambda c: repr(c['in']))
    def test_cats_index_sur_liste(self, cas):
        assert tl.cats_index(cas['in']) == cas['cats_index']

    def test_cle_source_et_doublons(self):
        lignes = [dict(l) for l in REF['cle_source']['lignes']]
        doublons = pub.attribuer_cles_source(lignes)
        assert [l['cle_source'] for l in lignes] == REF['cle_source']['attendu']
        assert doublons == REF['cle_source']['doublons']

    def test_classeur_reel_2026_2027(self):
        """Les 45 lignes du classeur, telles que l'extension les calcule."""
        ref = REF['classeur']['lignes']
        lignes = [{k: v for k, v in l.items()
                   if k not in ('tri_key', 'cle_source', 'cats', 'cats_index')}
                  for l in ref]
        for l in lignes:
            pub.champs_calcules(l)
        pub.attribuer_cles_source(lignes)

        ecarts = []
        for obtenu, attendu in zip(lignes, ref):
            for champ in ('tri_key', 'cle_source', 'cats', 'cats_index',
                          'categories', 'categories_publiees'):
                # `categories_publiees` se compare au `categories` du PHP :
                # c'est la même valeur, la forme publiée par l'extension.
                ref = attendu['categories' if champ == 'categories_publiees' else champ]
                if obtenu[champ] != ref:
                    ecarts.append('%s — %s : attendu %r, obtenu %r'
                                  % (attendu['cle_source'], champ,
                                     ref, obtenu[champ]))
        assert ecarts == []
        assert len(lignes) == 45

    def test_aucune_date_illisible_dans_le_classeur(self):
        """Les deux dates volontairement ouvertes du §7 du plan mises à part."""
        illisibles = [l['date_texte'] for l in REF['classeur']['lignes']
                      if tl.date_illisible(l['date_texte'])]
        assert illisibles == []


@pytest.mark.skipif(not os.environ.get('LREGE_EXT_DIR') or not PHP,
                    reason="fixture PHP non vérifiable : LREGE_EXT_DIR non défini "
                           "ou php introuvable dans le PATH")
def test_fixture_a_jour():
    """Regénère la référence depuis le PHP et vérifie qu'elle n'a pas bougé.

    À lancer quand l'extension évolue :
        LREGE_EXT_DIR=/chemin/calendrier-lrege \\
        LREGE_CLASSEUR=/chemin/Calendrier_LREGE_2026-2027.xlsx \\
        pytest tests/test_publication.py
    """
    ext = os.environ['LREGE_EXT_DIR']
    gen = os.path.join(os.path.dirname(FIXTURE), 'gen_ref.php')
    classeur = os.environ.get('LREGE_CLASSEUR', '')
    out = subprocess.run([PHP, gen, ext, classeur],
                         capture_output=True, text=True, check=True).stdout
    produit = json.loads(out)
    for section in ('dates', 'categories', 'cats_index', 'cle_source'):
        assert produit[section] == REF[section], "section « %s » : le PHP a changé" % section


# ─────────────────────────────────────────────────────────────────────────────
# Modèle et stockage
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, 'PUBLICATION_FILE', str(tmp_path / 'publication.json'))
    return tmp_path


class TestModele:

    def test_ligne_vide_a_les_14_champs(self):
        l = pub.ligne_vide()
        assert set(pub.CHAMPS_DEFAUT) <= set(l)
        assert len(pub.CHAMPS_DEFAUT) == 14
        assert l['id'] and l['__version__'] == pub.PUBLICATION_VERSION

    def test_ligne_vide_ne_partage_pas_ses_listes(self):
        a, b = pub.ligne_vide(), pub.ligne_vide()
        a['armes'].append({'arme': 'Épée', 'categories': 'M13'})
        assert b['armes'] == []

    def test_load_fichier_absent(self, data):
        assert pub.load_lignes() == []

    def test_migration_ascendante(self, data):
        """Une ligne écrite avant l'ajout d'un champ le reçoit à la lecture."""
        with open(str(data / 'publication.json'), 'w', encoding='utf-8') as f:
            json.dump([{'date_texte': '1-2 mai 2027', 'bloc': 'Épée'}], f)
        l = pub.load_lignes()[0]
        assert l['contact'] == '' and l['ecart_accepte'] is False and l['armes'] == []
        assert l['date_texte'] == '1-2 mai 2027' and l['bloc'] == 'Épée'
        assert l['id'] and l['__version__'] == 0


class TestEcriture:

    def test_aller_retour(self, data):
        lignes = [pub.ligne_vide(date_texte='1-2 mai 2027', bloc='Sabre',
                                 notes='deux dates ouvertes', contact='Dupont')]
        pub.save_lignes(lignes)
        relu = pub.load_lignes()
        assert relu[0]['notes'] == 'deux dates ouvertes'
        assert relu[0]['contact'] == 'Dupont'
        assert relu[0]['id'] == lignes[0]['id']

    def test_pas_de_tmp_residuel(self, data):
        pub.save_lignes([pub.ligne_vide()])
        assert not os.path.exists(str(data / 'publication.json.tmp'))
        assert os.path.exists(str(data / 'publication.json'))

    def test_backup_a_chaque_ecriture(self, data):
        assert pub.save_lignes([pub.ligne_vide(date_texte='1 mai 2027')]) is None
        nom = pub.save_lignes([pub.ligne_vide(date_texte='2 mai 2027')])
        assert nom and nom.startswith('publication_') and nom.endswith('.json')
        backups = os.listdir(str(data / 'backups'))
        assert len(backups) == 1
        with open(str(data / 'backups' / backups[0]), encoding='utf-8') as f:
            assert json.load(f)[0]['date_texte'] == '1 mai 2027'

    def test_backup_desactivable(self, data):
        pub.save_lignes([pub.ligne_vide()])
        pub.save_lignes([pub.ligne_vide()], backup=False)
        assert not os.path.exists(str(data / 'backups'))

    def test_accents_non_echappes(self, data):
        pub.save_lignes([pub.ligne_vide(bloc='Épée', categories='Vétérans')])
        with open(str(data / 'publication.json'), encoding='utf-8') as f:
            brut = f.read()
        assert 'Épée' in brut and '\\u' not in brut


class TestChampsCalcules:

    def test_idempotent(self):
        l = pub.ligne_vide(date_texte='26-27 sept. 2026', categories='M13 à M17')
        a = pub.champs_calcules(dict(l))
        b = pub.champs_calcules(dict(a))
        assert a == b
        assert a['categories'] == 'M13 à M17'          # saisie conservée
        assert a['categories_publiees'] == 'M13-M15-M17'
        assert a['cats_index'] == '|M13|M15|M17|'
        assert a['tri_key'] == 20260926

    def test_armes_de_tournoi_publiees_sans_toucher_a_la_saisie(self):
        saisie = [{'arme': 'Fleuret', 'categories': 'M7 à M13'},
                  {'arme': '', 'categories': 'ignorée'}]
        l = pub.ligne_vide(date_texte='3-4 avr. 2027', est_tournoi=True,
                           armes=[dict(a) for a in saisie])
        pub.champs_calcules(l)
        assert l['armes'] == saisie                    # saisie conservée
        assert l['armes_publiees'] == [{'arme': 'Fleuret',
                                        'categories': 'M7-M9-M11-M13'}]
        assert l['cats_index'] == '|M7|M9|M11|M13|'

    def test_armes_officielles_laissees_telles_quelles(self):
        l = pub.ligne_vide(date_texte='23 mai 2027', armes=['Épée', 'Fleuret', 'Sabre'])
        pub.champs_calcules(l)
        assert l['armes'] == ['Épée', 'Fleuret', 'Sabre']
        assert 'armes_publiees' not in l          # rien à publier pour les officiels

    def test_date_illisible_signalee_pas_corrigee(self):
        l = pub.ligne_vide(date_texte='3-4 pluviose 2027')
        pub.champs_calcules(l)
        assert l['tri_key'] == pub.TRI_KEY_ILLISIBLE
        assert l['date_texte'] == '3-4 pluviose 2027'
