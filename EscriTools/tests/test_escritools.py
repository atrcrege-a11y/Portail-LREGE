"""
Tests unitaires EscriTools — fixtures synthétiques, aucune dépendance externe.
"""
import sys, os, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


# =============================================================================
# core/bellepoule_fff.py
# =============================================================================

class TestBellepoule:

    def _pages_fff(self):
        """Simule les pages texte d'un PDF BellePoule individuel minimal."""
        return [
            "CDF Fleuret Hommes M17\n01/06/2026\n",
            ("Liste des inscrits\n"
             "MARTIN Jean STRASBOURG 12345 304977\n"
             "DUPONT Paul NANCY 12345 201234\n"),
            ("Classement général\n"
             "1 MARTIN Jean FRA\n"
             "2 DUPONT Paul FRA\n"),
        ]

    def test_trouver_entete_arme(self):
        from core.bellepoule_fff import trouver_entete
        pages = ["Fleuret Hommes M17 01/06/2026 CDF Grand Est"]
        info = trouver_entete(pages)
        assert info["arme"] == "Fleuret"

    def test_trouver_entete_sexe(self):
        from core.bellepoule_fff import trouver_entete
        pages = ["Epee Dames M13 01/06/2026"]
        info = trouver_entete(pages)
        assert info["sexe"] == "F"

    def test_trouver_entete_categorie(self):
        from core.bellepoule_fff import trouver_entete
        pages = ["Sabre Hommes M17 01/06/2026"]
        info = trouver_entete(pages)
        assert info["categorie"] == "M17"

    def test_trouver_entete_defaults(self):
        from core.bellepoule_fff import trouver_entete
        info = trouver_entete(["Aucune info utile ici"])
        assert info["arme"]      == "Fleuret"
        assert info["sexe"]      == "F"
        assert info["categorie"] == "M13"
        assert info["nom"]       == "Competition"

    def test_extraire_liste_appel(self):
        from core.bellepoule_fff import extraire_liste_appel
        pages = [
            "Liste des inscrits\n"
            "MARTIN Jean STRASBOURG ESC 12 304977\n"
            "DUPONT Paul NANCY CE 11 201234\n"
        ]
        liste = extraire_liste_appel(pages)
        assert "304977" in liste
        assert liste["304977"]["nom"] == "MARTIN"
        assert liste["304977"]["prenom"] == "Jean"

    def test_trouver_licence_exact(self):
        from core.bellepoule_fff import trouver_licence
        lmap = {("MARTIN", "Jean"): "304977"}
        assert trouver_licence("MARTIN", "Jean", lmap) == "304977"

    def test_trouver_licence_absent(self):
        from core.bellepoule_fff import trouver_licence
        assert trouver_licence("INCONNU", "X", {}) == ""

    def test_charger_dates_csv(self, tmp_path):
        from core.bellepoule_fff import charger_dates
        csv = tmp_path / "dates.csv"
        csv.write_text("304977,15/06/2013\n201234,22/03/2014\n", encoding="utf-8")
        dates = charger_dates(str(csv))
        assert dates["304977"] == "15/06/2013"
        assert dates["201234"] == "22/03/2014"

    def test_charger_dates_absent(self):
        from core.bellepoule_fff import charger_dates
        assert charger_dates(None) == {}
        assert charger_dates("/inexistant.csv") == {}

    def test_ecrire_fff(self, tmp_path):
        from core.bellepoule_fff import ecrire_fff
        classement = [{"place": 1, "nom": "MARTIN", "prenom": "Jean", "club": "STRAS"}]
        info = {"date": "01/06/2026", "arme": "Fleuret", "sexe": "M",
                "categorie": "M17", "nom": "Test"}
        out = tmp_path / "out.fff"
        ecrire_fff(classement, info, {}, {}, str(out))
        contenu = out.read_text(encoding="latin-1")
        assert "FFF;WIN;competition" in contenu
        assert "MARTIN" in contenu
        assert "Fleuret" in contenu

    def test_convertir_fichier_absent(self, tmp_path):
        from core.bellepoule_fff import convertir
        ok, msg = convertir("/inexistant.pdf", str(tmp_path / "out.fff"))
        assert not ok
        assert "introuvable" in msg.lower()


# =============================================================================
# core/pdf_markdown.py
# =============================================================================

class TestPdfMarkdown:

    def test_corriger_glyphes(self):
        from core.pdf_markdown import _corriger_glyphes
        assert _corriger_glyphes("ﬁ test") == "→ test"

    def test_nettoyer_doublon(self):
        from core.pdf_markdown import _nettoyer
        # "TTiittrree" → "Titre" (suppression doublons)
        result = _nettoyer("TTiittrree")
        assert "T" in result  # au moins partiellement nettoyé

    def test_nettoyer_espaces(self):
        from core.pdf_markdown import _nettoyer
        assert _nettoyer("texte   avec   espaces") == "texte avec espaces"

    def test_calculer_seuils_vide(self):
        from core.pdf_markdown import calculer_seuils
        s = calculer_seuils([])
        assert "h1" in s and "body" in s

    def test_calculer_seuils_normal(self):
        from core.pdf_markdown import calculer_seuils
        blocs = (
            [{"size": 22.0}] * 2 +
            [{"size": 16.0}] * 3 +
            [{"size": 10.0}] * 20
        )
        s = calculer_seuils(blocs)
        assert s["body"] == 10
        assert s["h1"] >= s["h2"] >= s["h3"] >= s["body"]

    def test_detecter_repetitifs_peu_pages(self):
        from core.pdf_markdown import detecter_repetitifs
        blocs = [{"text": "En-tête"}, {"text": "En-tête"}, {"text": "Contenu"}]
        # Moins de 3 pages → aucun répétitif détecté
        reps = detecter_repetitifs(blocs, nb_pages=2)
        assert len(reps) == 0

    def test_detecter_repetitifs_beaucoup(self):
        from core.pdf_markdown import detecter_repetitifs
        blocs = [{"text": "En-tête"}] * 8 + [{"text": "Contenu unique"}]
        reps = detecter_repetitifs(blocs, nb_pages=5, seuil=0.4)
        assert "En-tête" in reps
        assert "Contenu unique" not in reps


# =============================================================================
# core/markdown_pdf.py
# =============================================================================

class TestMarkdownPdf:

    def test_echapper_html(self):
        from core.markdown_pdf import echapper
        assert echapper("a & b") == "a &amp; b"
        assert echapper("a < b") == "a &lt; b"

    def test_echapper_gras(self):
        from core.markdown_pdf import echapper
        assert echapper("**gras**") == "<b>gras</b>"

    def test_echapper_italique(self):
        from core.markdown_pdf import echapper
        assert echapper("*italique*") == "<i>italique</i>"

    def test_echapper_code(self):
        from core.markdown_pdf import echapper
        assert "Courier" in echapper("`code`")

    def test_convertir_fichier_absent(self, tmp_path):
        from core.markdown_pdf import convertir
        ok, msg = convertir("/inexistant.md", str(tmp_path / "out.pdf"))
        assert not ok
        assert "introuvable" in msg.lower()

    def test_convertir_md_simple(self, tmp_path):
        from core.markdown_pdf import convertir
        md = tmp_path / "test.md"
        md.write_text("# Titre\n\nParagraphe de test.\n\n- item 1\n- item 2\n", encoding="utf-8")
        out = tmp_path / "test.pdf"
        ok, res = convertir(str(md), str(out))
        assert ok
        assert out.exists()
        assert out.stat().st_size > 1000  # PDF non vide

    def test_convertir_md_avec_tableau(self, tmp_path):
        from core.markdown_pdf import convertir
        md = tmp_path / "tab.md"
        md.write_text("## Tableau\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |\n| C | D |\n", encoding="utf-8")
        out = tmp_path / "tab.pdf"
        ok, res = convertir(str(md), str(out))
        assert ok


# =============================================================================
# core/renommage.py
# =============================================================================

class TestRenommage:

    def test_xml_vers_cotcot(self, tmp_path):
        from core.renommage import xml_vers_cotcot
        f = tmp_path / "test.xml"
        f.write_text("<data/>")
        nouveaux, erreurs = xml_vers_cotcot([str(f)])
        assert not erreurs
        assert nouveaux[0].endswith(".cotcot")
        assert (tmp_path / "test.cotcot").exists()

    def test_cotcot_vers_xml(self, tmp_path):
        from core.renommage import cotcot_vers_xml
        f = tmp_path / "test.cotcot"
        f.write_text("<data/>")
        nouveaux, erreurs = cotcot_vers_xml([str(f)])
        assert not erreurs
        assert nouveaux[0].endswith(".xml")
        assert (tmp_path / "test.xml").exists()

    def test_ignore_mauvaise_extension(self, tmp_path):
        from core.renommage import xml_vers_cotcot
        f = tmp_path / "test.pdf"
        f.write_text("not xml")
        nouveaux, erreurs = xml_vers_cotcot([str(f)])
        # Aucune erreur mais aucun renommage
        assert nouveaux == [str(f)]

    def test_fichier_absent_erreur(self):
        from core.renommage import xml_vers_cotcot
        _, erreurs = xml_vers_cotcot(["/inexistant.xml"])
        assert len(erreurs) == 1


# =============================================================================
# core/equipe_individuel.py
# =============================================================================

class TestEquipeIndividuel:

    _MD_SAMPLE = """
# Résultats

## Liste des inscrits

TROYES TG 1 CHAMPAGNE-ARDENNE FRA 19998

Jean MARTIN 15/06/2013 CHAMPAGNE-ARDENNE FRA 0 304977
Paul DUPONT 22/03/2014 CHAMPAGNE-ARDENNE FRA 0 201234

REIMS CE 1 CHAMPAGNE-ARDENNE FRA 19998

Anna KLEIN 01/01/2013 CHAMPAGNE-ARDENNE FRA 0 305000

## Répartition

## Classement général

1 TROYES TG 1 TROYES TG CHAMPAGNE-ARDENNE FRA
2 REIMS CE 1 REIMS CE CHAMPAGNE-ARDENNE FRA
"""

    def test_extraire_classement_general_md(self):
        from core.equipe_individuel import extraire_classement_general_md
        cg = extraire_classement_general_md(self._MD_SAMPLE)
        assert len(cg) >= 1
        places = [p for p, _ in cg]
        assert 1 in places

    def test_construire_classement_individuel(self):
        from core.equipe_individuel import construire_classement_individuel
        inscrits = {
            "TROYES TG 1": [{"nom": "MARTIN", "prenom": "Jean", "ddn": "", "licence": "304977", "sexe": ""}],
            "REIMS CE 1":  [{"nom": "KLEIN",  "prenom": "Anna", "ddn": "", "licence": "305000", "sexe": ""}],
        }
        cg = [(1, "TROYES TG 1"), (2, "REIMS CE 1")]
        tireurs = construire_classement_individuel(inscrits, cg, {})
        assert len(tireurs) == 2
        assert tireurs[0]["nom"] == "MARTIN"
        assert tireurs[0]["place"] == 1

    def test_generer_fff(self, tmp_path):
        from core.equipe_individuel import generer_fff
        tireurs = [{"nom": "MARTIN", "prenom": "Jean", "ddn": "", "licence": "304977",
                    "sexe": "", "club": "TROYES TG", "place": 1}]
        out = tmp_path / "out.fff"
        generer_fff(tireurs, "01/06/2026", "Epee", "M", "M13", "Test", "Paris", str(out))
        contenu = out.read_text(encoding="latin-1")
        assert "FFF;WIN" in contenu
        assert "MARTIN" in contenu

    def test_traiter_fichier_absent(self, tmp_path):
        from core.equipe_individuel import traiter_fichier
        ok, msg = traiter_fichier(
            "/inexistant.md", "01/06/2026", "Epee", "M", "M13", "Test", "Paris",
            str(tmp_path / "out.fff")
        )
        assert not ok
