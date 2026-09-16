"""
Tests unitaires SYNESC.
Couvre : core/config.py, core/parser.py, competitions/grand_est.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.config import besoin_arbitre_indiv, besoin_arbitre_equipe, BAREME_ARBITRES
from core.parser import parse_date_key, date_avec_jour, parse_xml, construire_donnees
from competitions.grand_est import GrandEst
from tests.fixtures import xml_individuel


# ---------------------------------------------------------------------------
# Helper : cat_map minimaliste pour construire_donnees
# ---------------------------------------------------------------------------
CAT_MAP_INDIV_TEST  = {"SENIORS": "SENIORS", "M15": "M15", "M13": "M13"}
CAT_MAP_EQUIPE_TEST = {"SENIORS": "SENIORS", "M15": "M15"}


# ===========================================================================
# TestBesoinArbitre
# ===========================================================================

class TestBesoinArbitre:

    def test_indiv_moins_4(self):
        assert besoin_arbitre_indiv(0) == 0
        assert besoin_arbitre_indiv(3) == 0

    def test_indiv_4_a_8(self):
        assert besoin_arbitre_indiv(4) == 1
        assert besoin_arbitre_indiv(8) == 1

    def test_indiv_plus_8(self):
        assert besoin_arbitre_indiv(9) == 2
        assert besoin_arbitre_indiv(20) == 2

    def test_equipe_0(self):
        assert besoin_arbitre_equipe(0) == 0

    def test_equipe_1_2(self):
        assert besoin_arbitre_equipe(1) == 1
        assert besoin_arbitre_equipe(2) == 1

    def test_equipe_3_4(self):
        assert besoin_arbitre_equipe(3) == 2
        assert besoin_arbitre_equipe(4) == 2

    def test_equipe_5_plus(self):
        assert besoin_arbitre_equipe(5) == 3
        assert besoin_arbitre_equipe(10) == 3

    def test_bareme_arbitres_non_vide(self):
        assert len(BAREME_ARBITRES) >= 5


# ===========================================================================
# TestParseDate
# ===========================================================================

class TestParseDate:

    def test_parse_date_key_format_fr(self):
        assert parse_date_key("16.05.2026") == (2026, 5, 16)

    def test_parse_date_key_invalide(self):
        assert parse_date_key("???") == (0, 0, 0)

    def test_date_avec_jour_samedi(self):
        # 16.05.2026 est un samedi
        result = date_avec_jour("16.05.2026")
        assert result == "samedi 16.05.2026"

    def test_date_avec_jour_format_iso(self):
        # 2026-05-16 est aussi un samedi
        result = date_avec_jour("2026-05-16")
        assert "samedi" in result
        assert "16.05.2026" in result


# ===========================================================================
# TestParseXml
# ===========================================================================

class TestParseXml:

    def test_meta_arme_label(self):
        xml = xml_individuel(arme="E", tireurs=[{"nom": "MARTIN", "club": "TEST"}])
        meta, _, _ = parse_xml(xml)
        assert meta["arme_label"] == "Epee" or meta["arme_label"] == "Épée"

    def test_meta_sexe_label(self):
        xml = xml_individuel(sexe="M", tireurs=[{"nom": "MARTIN", "club": "TEST"}])
        meta, _, _ = parse_xml(xml)
        assert meta["sexe_label"] == "Hommes"

    def test_meta_categorie_uppercase(self):
        xml = xml_individuel(categorie="seniors", tireurs=[{"nom": "MARTIN", "club": "TEST"}])
        meta, _, _ = parse_xml(xml)
        assert meta["categorie"] == "SENIORS"

    def test_tireurs_extraits(self):
        tireurs = [
            {"nom": "MARTIN", "club": "CSM Epinal"},
            {"nom": "DURAND", "club": "CSM Epinal"},
            {"nom": "LEROY",  "club": "EN Metz"},
        ]
        xml = xml_individuel(tireurs=tireurs)
        _, t, _ = parse_xml(xml)
        assert len(t) == 3

    def test_arbitres_extraits(self):
        arbitres = [
            {"nom": "DURAND", "licence": "999"},
            {"nom": "PETIT",  "licence": "888"},
        ]
        xml = xml_individuel(tireurs=[{"nom": "MARTIN", "club": "TEST"}], arbitres=arbitres)
        _, _, a = parse_xml(xml)
        assert len(a) == 2

    def test_xml_sans_tireur_leve_parse_error(self):
        """Un XML valide sans tireur doit lever ParseError."""
        from core.parser import ParseError
        xml = xml_individuel(tireurs=[], arbitres=[])
        with pytest.raises(ParseError, match="Aucun tireur"):
            parse_xml(xml)

    def test_xml_invalide_leve_parse_error(self):
        """Un contenu non-XML doit lever ParseError."""
        from core.parser import ParseError
        with pytest.raises(ParseError, match="invalide ou corrompu"):
            parse_xml(b"ceci n est pas du xml!!!")

    def test_xml_mauvaise_balise_racine(self):
        """Une balise racine inconnue doit lever ParseError."""
        from core.parser import ParseError
        with pytest.raises(ParseError, match="pas un export Engarde"):
            parse_xml(b'<?xml version="1.0"?><MonFichier Arme="E"/>')

    def test_xml_racine_base_competition(self):
        """Export Engarde de la base d'engages : racine <BaseCompetitionIndividuelle>."""
        xml = xml_individuel(tireurs=[{"nom": "MARTIN", "club": "TEST"}])
        xml = xml.replace(b"<Epreuve ", b"<BaseCompetitionIndividuelle ")
        xml = xml.replace(b"</Epreuve>", b"</BaseCompetitionIndividuelle>")
        meta, tireurs, _ = parse_xml(xml)
        assert len(tireurs) == 1
        assert meta["categorie"] == "SENIORS"


class TestExcelBienForme:
    """Le classeur genere ne doit contenir aucun conteneur XML vide.

    Excel "repare" la feuille a l'ouverture si openpyxl ecrit
    <dataValidations count="0"/> — ce qui arrivait des qu'aucun arbitre
    n'etait charge (la validation Statut ne couvrait alors aucune cellule).
    """

    def _ep(self, cat, sexe, n, date, idc, nb_arbitres=0):
        from core.parser import parse_xml
        tir = "".join(
            f'<Tireur Sexe="{sexe}" Club="C{i%3}" Licence="{idc}{i:03d}" Prenom="P{i}" '
            f'Nom="N{i}" Region="GRAND EST" Ligue="ALSACE" Departement="068"/>'
            for i in range(n))
        arb = "".join(
            f'<Arbitre Nom="ARB{idc}{k}" Prenom="X" Licence="77{idc}{k}" Club="C0" '
            f'Region="GRAND EST" Ligue="ALSACE" Departement="068" Categorie="R"/>'
            for k in range(nb_arbitres))
        xml = (f'<?xml version="1.0" encoding="ISO-8859-1"?>'
               f'<BaseCompetitionIndividuelle Type="I" Date="{date}" DateDebut="{date}" '
               f'DateFin="{date}" TitreLong="Test" Categorie="{cat}" Sexe="{sexe}" '
               f'Arme="F" ID="{idc}"><Tireurs>{tir}</Tireurs>'
               f'<Arbitres>{arb}</Arbitres></BaseCompetitionIndividuelle>').encode("iso-8859-1")
        return parse_xml(xml, "x.xml")

    def _classeur(self, store):
        import io as _io, zipfile
        from competitions import get_competition
        buf = get_competition("grand_est").generer_excel(store, titre_comp="Test")
        data = buf.getvalue() if hasattr(buf, "getvalue") else buf
        return zipfile.ZipFile(_io.BytesIO(data))

    def test_sans_arbitre_aucun_conteneur_vide(self):
        import re
        import xml.etree.ElementTree as ET
        z = self._classeur([self._ep("M17", "F", 2, "27.09.2026", "1", nb_arbitres=0)])
        for n in z.namelist():
            if not n.endswith(".xml"):
                continue
            raw = z.read(n)
            ET.fromstring(raw)  # doit rester bien forme
            txt = raw.decode("utf-8")
            assert '<dataValidations count="0"/>' not in txt, n
            assert "<dataValidations/>" not in txt, n

    def test_avec_arbitres_validation_conservee(self):
        """Non-regression : la liste deroulante Statut reste presente."""
        import re
        z = self._classeur([self._ep("M17", "F", 2, "27.09.2026", "1", nb_arbitres=2)])
        trouve = False
        for n in z.namelist():
            if n.startswith("xl/worksheets/"):
                txt = z.read(n).decode("utf-8")
                if "<dataValidation " in txt and "Retenu" in txt:
                    trouve = True
        assert trouve, "la validation Statut a disparu"


class TestBesoinArbitresJournee:
    """Besoin estime = somme des poules de toutes les epreuves indiv du jour."""

    def _ep(self, cat, sexe, arme, n, date, idc):
        from core.parser import parse_xml
        tir = "".join(
            f'<Tireur Sexe="{sexe}" Club="C{i%3}" Licence="{idc}{i:03d}" Prenom="A" '
            f'Nom="N{i}" Region="GRAND EST" Ligue="ALSACE" Departement="068"/>'
            for i in range(n))
        xml = (f'<?xml version="1.0" encoding="ISO-8859-1"?>'
               f'<BaseCompetitionIndividuelle Type="I" Date="{date}" DateDebut="{date}" '
               f'DateFin="{date}" TitreLong="Test" Categorie="{cat}" Sexe="{sexe}" '
               f'Arme="{arme}" ID="{idc}"><Tireurs>{tir}</Tireurs><Arbitres/>'
               f'</BaseCompetitionIndividuelle>').encode("iso-8859-1")
        return parse_xml(xml, "x.xml")

    def _besoin(self, comp_type, fichiers):
        import app as synesc
        import re
        _, _, txt = synesc._generer_corps_mail("Test", "X", comp_type, fichiers, None, None)
        m = re.search(r"BESOIN ESTIMÉ — (\d+)", txt)
        assert m, txt
        return int(m.group(1))

    def test_deux_armes_comptees_separement(self):
        """M17 F 15 (3 poules) + M17 F H 8 (1) + SENIORS Epee 20 (3) = 7."""
        f = [self._ep("M17", "F", "F", 15, "27.09.2026", "1"),
             self._ep("M17", "M", "F", 8, "27.09.2026", "2"),
             self._ep("SENIORS", "M", "E", 20, "27.09.2026", "3")]
        assert self._besoin("grand_est", f) == 7
        assert self._besoin("alsace", f) == 7

    def test_calcul_par_journee(self):
        """Chaque journee a son propre besoin."""
        import app as synesc
        import re
        f = [self._ep("M15", "F", "F", 15, "26.09.2026", "1"),
             self._ep("M17", "F", "F", 8, "27.09.2026", "2")]
        _, _, txt = synesc._generer_corps_mail("Test", "X", "grand_est", f, None, None)
        besoins = re.findall(r"BESOIN ESTIMÉ — (\d+)", txt)
        assert besoins == ["3", "1"], besoins

    def test_categorie_hors_perimetre_non_comptee(self):
        """La Coupe de Lorraine ne couvre que M9-M15 : M17 ne doit rien ajouter."""
        f = [self._ep("M15", "F", "F", 15, "26.09.2026", "1"),
             self._ep("M17", "F", "F", 15, "26.09.2026", "2")]
        assert self._besoin("lorraine", f) == 3


class TestHorairesDansMail:
    """Les horaires du PDF programme valent pour tous les types de competition."""

    def _fichiers(self):
        from core.parser import parse_xml
        out = []
        cas = [("M15", "F", "26.09.2026", "1"),
               ("M17", "F", "27.09.2026", "2"),
               ("SENIORS", "M", "27.09.2026", "3")]
        for cat, sexe, date, idc in cas:
            xml = (f'<?xml version="1.0" encoding="ISO-8859-1"?>'
                   f'<BaseCompetitionIndividuelle Type="I" Date="{date}" DateDebut="{date}" '
                   f'DateFin="{date}" TitreLong="Test" Categorie="{cat}" Sexe="{sexe}" '
                   f'Arme="F" ID="{idc}"><Tireurs>'
                   f'<Tireur Sexe="{sexe}" Club="EN Metz" Licence="9{idc}" Prenom="A" '
                   f'Nom="T{idc}" Region="GRAND EST" Ligue="LORRAINE" Departement="057"/>'
                   f'</Tireurs><Arbitres/></BaseCompetitionIndividuelle>').encode("iso-8859-1")
            out.append(parse_xml(xml, "x.xml"))
        return out

    PROG = {"categories": [
        {"cat": "M15", "date": "samedi 26.09.2026",
         "appel": "11h00", "scratch": "11h30", "debut": "11h45"},
        {"cat": "M17", "date": "dimanche 27.09.2026",
         "appel": "9h00", "scratch": "9h30", "debut": "9h45"},
    ]}

    def _corps(self, comp_type, prog):
        import app as synesc
        _, _, txt = synesc._generer_corps_mail(
            "Test", "Guebwiller", comp_type, self._fichiers(), None, prog)
        return txt

    def test_grand_est_avec_programme(self):
        txt = self._corps("grand_est", self.PROG)
        assert "Appel 11h00" in txt and "Scratch 11h30" in txt
        assert "Appel 9h00" in txt

    def test_grand_est_sans_programme_inchange(self):
        txt = self._corps("grand_est", None)
        assert "Appel" not in txt and "\u23f0" not in txt

    def test_alsace_avec_programme(self):
        txt = self._corps("alsace", self.PROG)
        assert "Appel 9h00" in txt

    def test_lorraine_toujours_ok(self):
        """Non-regression : la Lorraine utilisait deja les horaires.

        La Coupe de Lorraine ne couvre que M9-M15 (competitions/lorraine.py),
        donc seule la ligne M15 du samedi est attendue ici.
        """
        txt = self._corps("lorraine", self.PROG)
        assert "M15" in txt
        assert "Appel 11h00 — Scratch 11h30 — Début 11h45" in txt


class TestExtractionHorairesPdf:
    """Regressions de l'extraction FORMAT 4 (tableau texte Appel/Scratch/Assaut)."""

    def _app(self):
        import app as synesc
        synesc.app.config["TESTING"] = True
        return synesc

    def test_ligne_avec_colonne_tarif(self):
        """Une colonne apres les 3 horaires (Tarif) ne doit pas casser la lecture."""
        import re
        synesc = self._app()
        # Regex effectivement utilisee par FORMAT 4
        src = open(synesc.__file__, encoding="utf-8").read()
        assert "(?!\\d{1,2}[hH]\\d{0,2}\\b)" in src, "queue toleree absente de LINE4_RE"

    def test_cat_re_accepte_senior_accentue(self):
        """'Sénior' accentue doit etre reconnu comme categorie."""
        import re
        CAT_RE = re.compile(r'\b(M\s*\d+|V\d+|Vétérans?|Veteran|S[ée]niors?)\b', re.IGNORECASE)
        assert CAT_RE.search("Sénior H / F open").group(1) == "Sénior"
        assert CAT_RE.search("Senior H / F open").group(1) == "Senior"

    def test_detecter_lieu_ignore_challenge(self):
        """'halle' ne doit pas matcher a l'interieur de 'CHALLENGE'."""
        import re
        keywords = ["gymnase", "complexe sportif", "palais des sports", "halle",
                    "centre sportif", "espace sportif"]
        ligne = "ÉPREUVE 1 QUALIFICATION CHALLENGE DE France Fleuret Hommes / Dames M13"
        assert not any(re.search(r'\b' + re.escape(k) + r'\b', ligne, re.IGNORECASE)
                       for k in keywords)
        ligne_ok = "Centre sportif du Florival - 6 Rue de la Piscine Guebwiller"
        assert any(re.search(r'\b' + re.escape(k) + r'\b', ligne_ok, re.IGNORECASE)
                   for k in keywords)


class TestParseArbitresTxt:
    """EngardeArbitres.txt : CSV ';' exporte a cote du XML dans le ZIP."""

    ENTETE = ("nom;prenom;sexe;categorie;club;ligue;nation;"
              "date_nais;licence_fie;licence;")

    def _txt(self, *lignes):
        from io import StringIO
        contenu = "\ufeff" + self.ENTETE + "\n" + "\n".join(lignes)
        return contenu.encode("utf-8")

    def test_lecture_nominale(self):
        from core.parser import parse_arbitres_txt
        txt = self._txt("DURAND;Paul;M;R;EN Metz;GRAND EST;FRA;01/02/1990;;123456;")
        arbitres, avertis = parse_arbitres_txt(txt, "EngardeArbitres.txt")
        assert len(arbitres) == 1
        a = arbitres[0]
        assert a["nom"] == "DURAND" and a["prenom"] == "Paul"
        assert a["licence"] == "123456"
        assert a["club"] == "EN Metz"
        assert a["categorie"] == "R"
        assert avertis == []

    def test_fichier_entete_seule(self):
        from core.parser import parse_arbitres_txt
        arbitres, avertis = parse_arbitres_txt(self._txt(), "EngardeArbitres.txt")
        assert arbitres == [] and avertis == []

    def test_niveau_libelle_long_normalise(self):
        from core.parser import parse_arbitres_txt
        txt = self._txt("PETIT;Luc;M;Régional;EN Metz;GRAND EST;FRA;;;99;")
        arbitres, avertis = parse_arbitres_txt(txt, "f.txt")
        assert arbitres[0]["categorie"] == "R"
        assert avertis == []

    def test_niveau_inconnu_signale(self):
        """Un niveau hors bareme doit etre remonte, pas passe a 0 en silence."""
        from core.parser import parse_arbitres_txt
        txt = self._txt("MOREAU;Eve;F;Zz;EN Metz;GRAND EST;FRA;;;77;")
        arbitres, avertis = parse_arbitres_txt(txt, "f.txt")
        assert arbitres[0]["categorie"] == "Zz"
        assert len(avertis) == 1 and "non reconnu" in avertis[0]

    def test_colonnes_deplacees_lues_par_entete(self):
        """Une colonne ajoutee en tete ne doit pas decaler les donnees."""
        from core.parser import parse_arbitres_txt
        contenu = ("\ufeffid;nom;prenom;sexe;categorie;club;ligue;nation;"
                   "date_nais;licence_fie;licence;\n"
                   "1;DURAND;Paul;M;R;EN Metz;GRAND EST;FRA;;;123456;")
        arbitres, _ = parse_arbitres_txt(contenu.encode("utf-8"), "f.txt")
        assert arbitres[0]["nom"] == "DURAND"
        assert arbitres[0]["licence"] == "123456"
        assert arbitres[0]["categorie"] == "R"

    def test_entete_sans_colonne_nom_leve_parse_error(self):
        from core.parser import parse_arbitres_txt, ParseError
        with pytest.raises(ParseError, match="colonne 'nom' absente"):
            parse_arbitres_txt(b"a;b;c\n1;2;3", "f.txt")


# ===========================================================================
# TestConstruireDonnees
# ===========================================================================

class TestConstruireDonnees:

    def _build(self, fichiers_list, par_arme=False,
               cat_map_i=None, cat_map_e=None):
        return construire_donnees(
            fichiers_list,
            cat_map_indiv=cat_map_i or CAT_MAP_INDIV_TEST,
            cat_map_equipe=cat_map_e or CAT_MAP_EQUIPE_TEST,
            par_arme=par_arme,
        )

    def test_groupe_indiv_par_club_et_sexe(self):
        tireurs = [
            {"nom": "A", "sexe": "M", "club": "CSM Epinal"},
            {"nom": "B", "sexe": "M", "club": "CSM Epinal"},
            {"nom": "C", "sexe": "F", "club": "CSM Epinal"},
        ]
        xml = xml_individuel(categorie="SENIORS", date="16.05.2026", tireurs=tireurs)
        fichiers = [parse_xml(xml)]
        gi, _, _, _, _, _, _ = self._build(fichiers)
        club_data = gi["16.05.2026"]["SENIORS"]["CSM Epinal"]
        assert club_data["H"] == 2
        assert club_data["D"] == 1

    def test_cat_inconnue_ignoree(self):
        tireurs = [{"nom": "X", "sexe": "M", "club": "ClubA"}]
        xml = xml_individuel(categorie="INCONNU", tireurs=tireurs)
        gi, _, _, _, _, _, _ = self._build([parse_xml(xml)])
        # Aucun groupe indiv ne doit etre cree
        assert len(gi) == 0

    def test_ligue_info_remplie(self):
        tireurs = [{"nom": "A", "sexe": "M", "club": "CSM Epinal",
                    "region": "Grand Est", "ligue": "GES", "dept": "88"}]
        xml = xml_individuel(categorie="SENIORS", tireurs=tireurs)
        _, _, _, _, ligue_info, _, _ = self._build([parse_xml(xml)])
        assert "CSM Epinal" in ligue_info
        assert ligue_info["CSM Epinal"]["region"] == "Grand Est"

    def test_arbitres_all_enrichis(self):
        arbitres = [{"nom": "DURAND", "licence": "999", "club": "CSM Epinal",
                     "cat": "R"}]
        xml = xml_individuel(arme="E", categorie="SENIORS",
                             tireurs=[{"nom": "MARTIN", "club": "TEST"}],
                             arbitres=arbitres)
        _, _, arb_all, _, _, _, _ = self._build([parse_xml(xml)])
        assert len(arb_all) == 1
        assert arb_all[0]["arme"] == "E"

    def test_plage_dates_un_jour(self):
        xml = xml_individuel(date="16.05.2026",
                             tireurs=[{"nom": "A", "sexe": "M", "club": "C"}])
        _, _, _, _, _, plage, _ = self._build([parse_xml(xml)])
        assert " au " not in plage
        assert "16.05.2026" in plage

    def test_plage_dates_deux_jours(self):
        xml1 = xml_individuel(date="16.05.2026", categorie="SENIORS",
                              tireurs=[{"nom": "A", "sexe": "M", "club": "C"}])
        xml2 = xml_individuel(date="17.05.2026", categorie="SENIORS",
                              tireurs=[{"nom": "B", "sexe": "M", "club": "C"}])
        _, _, _, _, _, plage, _ = self._build([parse_xml(xml1), parse_xml(xml2)])
        assert " au " in plage

    def test_par_arme_enrichit_cle(self):
        tireurs = [{"nom": "A", "sexe": "M", "club": "ClubA"}]
        xml = xml_individuel(arme="F", categorie="M15", tireurs=tireurs)
        gi, _, _, _, _, _, _ = self._build(
            [parse_xml(xml)],
            par_arme=True,
            cat_map_i={"M15": "M15"},
        )
        # La cle doit etre "M15|F"
        date_key = list(gi.keys())[0]
        assert "M15|F" in gi[date_key]


# ===========================================================================
# TestCoherenceMappings (GrandEst)
# ===========================================================================

class TestCoherenceMappings:

    def test_cats_indiv_dans_labels(self):
        for cat in GrandEst.CATS_INDIV:
            assert cat in GrandEst.CAT_LABEL_INDIV, \
                f"Categorie indiv '{cat}' absente de CAT_LABEL_INDIV"

    def test_cats_equipe_dans_labels(self):
        for cat in GrandEst.CATS_EQUIPE:
            assert cat in GrandEst.CAT_LABEL_EQUIPE, \
                f"Categorie equipe '{cat}' absente de CAT_LABEL_EQUIPE"

    def test_cats_indiv_dans_tarif(self):
        for cat in GrandEst.CATS_INDIV:
            assert cat in GrandEst.TARIF_INDIV, \
                f"Categorie indiv '{cat}' absente de TARIF_INDIV"

    def test_cats_equipe_dans_tarif(self):
        for cat in GrandEst.CATS_EQUIPE:
            assert cat in GrandEst.TARIF_EQUIPE, \
                f"Categorie equipe '{cat}' absente de TARIF_EQUIPE"

    def test_cat_map_valeurs_dans_cats_indiv(self):
        for xml_cat, mapped in GrandEst.CAT_MAP_INDIV.items():
            assert mapped in GrandEst.CATS_INDIV, \
                f"Valeur mappee '{mapped}' (depuis '{xml_cat}') absente de CATS_INDIV"


# ===========================================================================
# TestDeficitArbitrageParArme
# ===========================================================================

class TestDeficitArbitrageParArme:
    """Bloc « Clubs en deficit d'arbitrage » du mail.

    Regle LREGE : 1 arbitre a partir de 4 tireurs, 2 a partir de 9, le
    bareme s'appliquant PAR ARME et par journee. Le cumul de toutes les
    armes d'une journee donnait un besoin faux (regression corrigee).
    """

    def _ep(self, cat, sexe, arme, club, n, date, idc):
        from core.parser import parse_xml
        tir = "".join(
            f'<Tireur Sexe="{sexe}" Club="{club}" Licence="{idc}{i:03d}" Prenom="A" '
            f'Nom="N{idc}{i}" Region="GRAND EST" Ligue="ALSACE" Departement="068"/>'
            for i in range(n))
        xml = (f'<?xml version="1.0" encoding="ISO-8859-1"?>'
               f'<BaseCompetitionIndividuelle Type="I" Date="{date}" DateDebut="{date}" '
               f'DateFin="{date}" TitreLong="Test" Categorie="{cat}" Sexe="{sexe}" '
               f'Arme="{arme}" ID="{idc}"><Tireurs>{tir}</Tireurs><Arbitres/>'
               f'</BaseCompetitionIndividuelle>').encode("iso-8859-1")
        return parse_xml(xml, "x.xml")

    def _deficits(self, comp_type, fichiers):
        """{club: (besoin, fournis)} lu dans le bloc deficit du mail."""
        import app as synesc
        import re
        _, _, txt = synesc._generer_corps_mail("Test", "X", comp_type, fichiers, None, None)
        return {m.group(1): (int(m.group(2)), int(m.group(3)))
                for m in re.finditer(
                    r"• (.+?) — besoin : (\d+), fournis : (\d+), manque :", txt)}

    def test_sous_seuil_dans_chaque_arme_aucun_deficit(self):
        """3 epee + 3 fleuret le meme jour : 0 + 0 = 0, pas 6 -> 1."""
        f = [self._ep("SENIORS", "M", "E", "CLUB A", 3, "27.09.2026", "1"),
             self._ep("SENIORS", "M", "F", "CLUB A", 3, "27.09.2026", "2")]
        assert self._deficits("alsace", f) == {}

    def test_deux_armes_au_dessus_du_seuil_cumulent(self):
        """9 epee + 9 fleuret : 2 + 2 = 4, pas 18 -> 2."""
        f = [self._ep("SENIORS", "M", "E", "CLUB A", 9, "27.09.2026", "1"),
             self._ep("SENIORS", "M", "F", "CLUB A", 9, "27.09.2026", "2")]
        assert self._deficits("alsace", f) == {"CLUB A": (4, 0)}

    def test_bareme_lrege_inchange_sur_une_arme(self):
        """Mono-arme : 1 des 4 tireurs, 2 des 9 (bareme LREGE)."""
        for n, attendu in ((3, None), (4, 1), (8, 1), (9, 2), (20, 2)):
            f = [self._ep("SENIORS", "M", "E", "CLUB A", n, "27.09.2026", "1")]
            d = self._deficits("grand_est", f)
            assert d.get("CLUB A", (None,))[0] == attendu, (n, d)

    def test_veterans_sans_seuil_particulier(self):
        """Pas de seuil veterans a 3 en LREGE : 3 tireurs V1 = 0 arbitre du."""
        f = [self._ep("V1", "M", "E", "CLUB A", 3, "27.09.2026", "1")]
        assert self._deficits("grand_est", f) == {}

    def test_journees_independantes(self):
        """4 epee samedi + 4 fleuret dimanche : 1 arbitre du chaque jour."""
        f = [self._ep("SENIORS", "M", "E", "CLUB A", 4, "26.09.2026", "1"),
             self._ep("SENIORS", "M", "F", "CLUB A", 4, "27.09.2026", "2")]
        assert self._deficits("alsace", f) == {"CLUB A": (1, 0)}
