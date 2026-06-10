"""
Tests unitaires SelecMaster — fixtures synthétiques, sans BellePoule réel.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from tests.fixtures import html_cumulatif, html_competition, html_invalide, html_vide


# =============================================================================
# parser.py — format cumulatif
# =============================================================================

class TestParserCumulatif:

    def test_arme_epee(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(arme="E"))
        assert d["arme"] == "Épée"

    def test_arme_fleuret(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(arme="F"))
        assert d["arme"] == "Fleuret"

    def test_arme_sabre(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(arme="S"))
        assert d["arme"] == "Sabre"

    def test_genre_hommes(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(genre="H"))
        assert d["genre"] == "H"

    def test_genre_dames(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(genre="D"))
        assert d["genre"] == "D"

    def test_categorie_m11(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(categorie="M11"))
        assert d["categorie"] == "M11"

    def test_categorie_m13(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(categorie="M13"))
        assert d["categorie"] == "M13"

    def test_territoire_lorraine(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(territoire="Lorraine"))
        assert d["territoire"] == "Lorraine"

    def test_territoire_alsace(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(territoire="Alsace"))
        assert d["territoire"] == "Alsace"

    def test_territoire_champagne(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(territoire="Champagne-Ardenne"))
        assert d["territoire"] == "Champagne-Ardenne"

    def test_tireurs_extraits(self):
        from parser import parser_html
        tireurs = [
            {"nom": "MARTIN", "prenom": "Jean", "club": "NANCY", "annee": "2013",
             "pts_total": 30000, "participations": 3},
            {"nom": "DUPONT", "prenom": "Paul", "club": "METZ",  "annee": "2012",
             "pts_total": 20000, "participations": 2},
        ]
        d = parser_html(html_cumulatif(tireurs=tireurs))
        assert len(d["tireurs"]) == 2
        assert d["tireurs"][0]["nom"] == "MARTIN"
        assert d["tireurs"][0]["place"] == 1

    def test_participations_comptees(self):
        from parser import parser_html
        tireurs = [
            {"nom": "A", "prenom": "A", "club": "C", "annee": "2013",
             "pts_total": 10000, "participations": 2},
        ]
        d = parser_html(html_cumulatif(tireurs=tireurs, nb_competitions=3))
        assert d["tireurs"][0]["participations"] == 2

    def test_points_total(self):
        from parser import parser_html
        tireurs = [
            {"nom": "A", "prenom": "A", "club": "C", "annee": "2013",
             "pts_total": 25000, "participations": 3},
        ]
        d = parser_html(html_cumulatif(tireurs=tireurs))
        assert d["tireurs"][0]["points_total"] == 25000.0

    def test_detection_m11_dans_m13(self):
        from parser import parser_html
        tireurs = [
            {"nom": "JEUNE", "prenom": "X", "club": "C", "annee": "2015",
             "pts_total": 10000, "participations": 3},
            {"nom": "AINE",  "prenom": "Y", "club": "C", "annee": "2012",
             "pts_total": 8000,  "participations": 3},
        ]
        d = parser_html(html_cumulatif(categorie="M13", tireurs=tireurs))
        assert d["tireurs"][0]["est_m11_dans_m13"] is True
        assert d["tireurs"][1]["est_m11_dans_m13"] is False

    def test_nb_competitions(self):
        from parser import parser_html
        d = parser_html(html_cumulatif(nb_competitions=4))
        assert d["nb_competitions"] == 4


# =============================================================================
# parser.py — format compétition
# =============================================================================

class TestParserCompetition:

    def test_format_detecte(self):
        from parser import parser_html
        d = parser_html(html_competition())
        assert d.get("format") == "competition"

    def test_arme_sabre(self):
        from parser import parser_html
        d = parser_html(html_competition(arme="Sabre"))
        assert d["arme"] == "Sabre"

    def test_genre_dames(self):
        from parser import parser_html
        d = parser_html(html_competition(genre="Dames"))
        assert d["genre"] == "D"

    def test_territoire_depuis_cid(self):
        from parser import parser_html
        d = parser_html(html_competition(cid="Alsace"))
        assert d["territoire"] == "Alsace"

    def test_tireurs_extraits(self):
        from parser import parser_html
        t = [{"nom": "KLEIN", "prenom": "Anna", "club": "STRAS"},
             {"nom": "WEBER", "prenom": "Marie", "club": "MULH"}]
        d = parser_html(html_competition(tireurs=t))
        assert len(d["tireurs"]) == 2
        assert d["tireurs"][0]["nom"] == "KLEIN"


# =============================================================================
# parser.py — validations et erreurs
# =============================================================================

class TestParserValidations:

    def test_html_invalide_leve_parseur_error(self):
        from parser import parser_html, ParseurError
        with pytest.raises(ParseurError):
            parser_html(html_invalide())

    def test_html_vide_leve_parseur_error(self):
        from parser import parser_html, ParseurError
        with pytest.raises(ParseurError):
            parser_html(html_vide())

    def test_parseur_error_a_hint(self):
        from parser import parser_html, ParseurError
        try:
            parser_html(html_invalide())
        except ParseurError as e:
            assert isinstance(e.hint, str)

    def test_titre_sans_code_leve_erreur(self):
        """Un titre HTML sans code arme/genre/cat doit lever ParseurError."""
        from parser import parser_html, ParseurError
        html = b"""<html><head><title>Classement Lorraine</title></head>
        <body><table id="TableClsst">
        <tr><td>Place</td><td>Nom</td></tr>
        <tr><td>1</td><td>TEST</td></tr>
        </table></body></html>"""
        with pytest.raises(ParseurError, match="impossible de d"):
            parser_html(html)


# =============================================================================
# parser.py — détection territoire robuste
# =============================================================================

class TestDetectionTerritoire:

    def test_titre_lorraine_detecte(self):
        from parser import _detecter_territoire_titre
        assert _detecter_territoire_titre("EHM13, Origine du tireur Lorraine") == "Lorraine"

    def test_titre_alsace_detecte(self):
        from parser import _detecter_territoire_titre
        assert _detecter_territoire_titre("FDM11, Comité Alsace") == "Alsace"

    def test_titre_champagne_detecte(self):
        from parser import _detecter_territoire_titre
        assert _detecter_territoire_titre("SHM13, Champagne-Ardenne") == "Champagne-Ardenne"

    def test_club_alsace_dans_fichier_lorrain_ne_fausse_pas(self):
        """Un club nommé 'Alsace Escrime' dans un fichier Lorrain ne doit pas
        déclencher de faux positif dans la détection du TITRE."""
        from parser import _detecter_territoire_titre
        # Le titre ne contient que Lorraine — le club Alsace est dans le body
        titre = "EHM13, Origine du tireur Lorraine"
        assert _detecter_territoire_titre(titre) == "Lorraine"

    def test_cid_alsace_detecte(self):
        from parser import _detecter_territoire_cid
        assert _detecter_territoire_cid("Alsace") == "Alsace"

    def test_cid_lorraine_detecte(self):
        from parser import _detecter_territoire_cid
        assert _detecter_territoire_cid("Lorraine") == "Lorraine"

    def test_cid_vide_retourne_none(self):
        from parser import _detecter_territoire_cid
        assert _detecter_territoire_cid("") is None

    def test_fallback_texte_libre(self):
        from parser import _detecter_territoire
        assert _detecter_territoire("Comité départemental Lorraine escrime") == "Lorraine"

    def test_sans_territoire_retourne_none(self):
        from parser import _detecter_territoire_titre
        assert _detecter_territoire_titre("EHM13, Classement national") is None


# =============================================================================
# selection.py
# =============================================================================

class TestSelection:

    def _donnees(self, arme="Épée", n_tireurs=8, participations=3):
        return {
            "arme": arme,
            "genre": "H",
            "categorie": "M13",
            "territoire": "Lorraine",
            "tireurs": [
                {"place": i+1, "nom": f"T{i}", "prenom": "X", "club": "C",
                 "participations": participations, "points_total": 10000 - i*100,
                 "annee_naissance": "2012", "est_m11_dans_m13": False, "resultats": []}
                for i in range(n_tireurs)
            ],
        }

    def test_quota_standard_5(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(), bonus_organisateur=False)
        assert r["quota"] == 5

    def test_quota_bonus_6(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(), bonus_organisateur=True)
        assert r["quota"] == 6

    def test_top5_selectionnes(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(n_tireurs=8))
        sel = [t for t in r["tireurs"] if t["statut"] == "selectionne"]
        assert len(sel) == 5

    def test_remplacants_apres_quota(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(n_tireurs=8))
        rem = [t for t in r["tireurs"] if t["statut"] == "remplacant"]
        assert len(rem) >= 1

    def test_non_selectionnable_sous_seuil_participations(self):
        from selection import calculer_selection
        donnees = self._donnees()
        # Mettre le dernier tireur avec 2 participations seulement
        donnees["tireurs"][-1]["participations"] = 2
        r = calculer_selection(donnees)
        non_sel = [t for t in r["tireurs"] if t["statut"] == "non_selectionnable"]
        assert len(non_sel) == 1

    def test_sabre_pas_de_condition_participations(self):
        from selection import calculer_selection
        donnees = self._donnees(arme="Sabre", participations=1)
        r = calculer_selection(donnees)
        non_sel = [t for t in r["tireurs"] if t["statut"] == "non_selectionnable"]
        assert len(non_sel) == 0

    def test_condition_participations_false_pour_sabre(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(arme="Sabre"))
        assert r["condition_participations"] is False

    def test_condition_participations_true_pour_epee(self):
        from selection import calculer_selection
        r = calculer_selection(self._donnees(arme="Épée"))
        assert r["condition_participations"] is True

    def test_enrichir_alertes_m11_double(self):
        from selection import enrichir_alertes_m11
        sel_m13 = {
            "tireurs": [
                {"nom": "MARTIN", "prenom": "Jean", "est_m11_dans_m13": True,
                 "alerte_m11": None},
            ]
        }
        tireurs_m11 = [{"nom": "MARTIN", "prenom": "Jean"}]
        r = enrichir_alertes_m11(sel_m13, tireurs_m11)
        assert r["tireurs"][0]["alerte_m11"] == "double"

    def test_enrichir_alertes_m11_m13only(self):
        from selection import enrichir_alertes_m11
        sel_m13 = {
            "tireurs": [
                {"nom": "DUPONT", "prenom": "Paul", "est_m11_dans_m13": True,
                 "alerte_m11": None},
            ]
        }
        tireurs_m11 = [{"nom": "MARTIN", "prenom": "Jean"}]  # pas Dupont
        r = enrichir_alertes_m11(sel_m13, tireurs_m11)
        assert r["tireurs"][0]["alerte_m11"] == "m13only"

    def test_enrichir_double_meme_si_annee_non_detectee(self):
        # FLESCH : présente dans le classement M11 mais est_m11_dans_m13=False
        # (année non lue). La présence M11 doit suffire à marquer "double".
        from selection import enrichir_alertes_m11
        sel_m13 = {
            "tireurs": [
                {"nom": "FLESCH", "prenom": "Mathilde", "est_m11_dans_m13": False,
                 "alerte_m11": None},
            ]
        }
        tireurs_m11 = [{"nom": "FLESCH", "prenom": "Mathilde"}]
        r = enrichir_alertes_m11(sel_m13, tireurs_m11)
        assert r["tireurs"][0]["alerte_m11"] == "double"

    def test_enrichir_alertes_non_m11_reste_none(self):
        from selection import enrichir_alertes_m11
        sel_m13 = {
            "tireurs": [
                {"nom": "AINE", "prenom": "X", "est_m11_dans_m13": False,
                 "alerte_m11": None},
            ]
        }
        r = enrichir_alertes_m11(sel_m13, [])
        assert r["tireurs"][0]["alerte_m11"] is None


class TestSuiviAlerteM11:
    """Le suivi doit conserver alerte_m11 pour l'afficher en M13."""

    def test_initialiser_suivi_conserve_alerte_m11(self):
        import suivi
        ARME, CAT, TERR = "TestArme", "M13", "Lorraine"
        tireurs_h = [
            {"nom": "MARTIN", "prenom": "Jean", "club": "C1",
             "statut": "selectionne", "alerte_m11": "double"},
            {"nom": "DUPONT", "prenom": "Paul", "club": "C2",
             "statut": "selectionne", "alerte_m11": "m13only"},
            {"nom": "AINE", "prenom": "X", "club": "C3",
             "statut": "selectionne", "alerte_m11": None},
        ]
        try:
            suivi.initialiser_suivi(ARME, CAT, TERR, tireurs_h, [])
            s = suivi.get_suivi(ARME, CAT)
            alertes = {t["nom"]: t["alerte_m11"]
                       for t in s["territoires"][TERR]["tireurs"]}
            assert alertes == {"MARTIN": "double", "DUPONT": "m13only", "AINE": None}
        finally:
            suivi.supprimer_suivi(ARME, CAT)
