"""
Tests unitaires SuiviMaster — fixtures synthétiques.
"""
import sys, os, pickle, io, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from tests.fixtures import excel_selecmaster, excel_invalide, excel_retour


# =============================================================================
# Constantes format Excel
# =============================================================================

class TestConstantesFormat:

    def test_prefix_rang_defini(self):
        from suivi import EXCEL_PREFIX_RANG
        assert EXCEL_PREFIX_RANG == "M "

    def test_label_selectionnes_defini(self):
        from suivi import EXCEL_LABEL_SELECTIONNES
        assert "SÉLECTIONN" in EXCEL_LABEL_SELECTIONNES.upper()

    def test_label_remplacants_defini(self):
        from suivi import EXCEL_LABEL_REMPLACANTS
        assert "REMPLAÇ" in EXCEL_LABEL_REMPLACANTS.upper() or "REMPLACANT" in EXCEL_LABEL_REMPLACANTS.upper()

    def test_armes_map_complete(self):
        from suivi import EXCEL_ARMES_MAP
        valeurs = set(EXCEL_ARMES_MAP.values())
        assert "Épée" in valeurs
        assert "Fleuret" in valeurs
        assert "Sabre" in valeurs


# =============================================================================
# lire_excel_selecmaster()
# =============================================================================

class TestLireExcel:

    def test_tireurs_hommes_extraits(self):
        from suivi import lire_excel_selecmaster
        sel_h = [{"nom": "MARTIN", "prenom": "Jean", "club": "NANCY"}]
        xlsx  = excel_selecmaster(selectionnes_h=sel_h, remplacants_h=[],
                                   selectionnes_d=[], remplacants_d=[])
        r = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        h = [t for t in r["tireurs"] if t["genre"] == "H"]
        assert len(h) == 1
        assert h[0]["nom"] == "MARTIN"

    def test_tireurs_dames_extraits(self):
        from suivi import lire_excel_selecmaster
        sel_d = [{"nom": "WEBER", "prenom": "Anna", "club": "METZ"}]
        xlsx  = excel_selecmaster(selectionnes_h=[{"nom":"A","prenom":"B","club":"C"}],
                                   remplacants_h=[], selectionnes_d=sel_d, remplacants_d=[])
        r = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        d = [t for t in r["tireurs"] if t["genre"] == "D"]
        assert len(d) == 1
        assert d[0]["nom"] == "WEBER"

    def test_statut_selectionne(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster()
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        sel  = [t for t in r["tireurs"] if t["statut"] == "selectionne"]
        assert len(sel) >= 1

    def test_statut_remplacant(self):
        from suivi import lire_excel_selecmaster
        rem_h = [{"nom": "REM", "prenom": "X", "club": "C"}]
        xlsx  = excel_selecmaster(remplacants_h=rem_h)
        r     = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        rem   = [t for t in r["tireurs"] if t["statut"] == "remplacant"]
        assert len(rem) >= 1

    def test_arme_detectee_epee(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster(arme="Épée")
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        assert r["arme"] == "Épée"

    def test_arme_detectee_fleuret(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster(arme="Fleuret")
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        assert r["arme"] == "Fleuret"

    def test_arme_detectee_sabre(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster(arme="Sabre")
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        assert r["arme"] == "Sabre"

    def test_categorie_detectee(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster(categorie="M11")
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        assert r["categorie"] == "M11"

    def test_confirmation_initiale_attente(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster()
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        for t in r["tireurs"]:
            assert t["confirmation"] == "attente"

    def test_excel_invalide_leve_erreur(self):
        from suivi import lire_excel_selecmaster, ExcelParseError
        with pytest.raises(ExcelParseError):
            lire_excel_selecmaster(excel_invalide(), "Lorraine", "Lorraine")

    def test_erreur_a_hint(self):
        from suivi import lire_excel_selecmaster, ExcelParseError
        try:
            lire_excel_selecmaster(excel_invalide(), "Lorraine", "Lorraine")
        except ExcelParseError as e:
            assert isinstance(e.hint, str) and len(e.hint) > 0

    def test_rang_attribue_sequentiellement(self):
        from suivi import lire_excel_selecmaster
        sel_h = [
            {"nom": "A", "prenom": "X", "club": "C"},
            {"nom": "B", "prenom": "Y", "club": "C"},
            {"nom": "C", "prenom": "Z", "club": "C"},
        ]
        xlsx = excel_selecmaster(selectionnes_h=sel_h, remplacants_h=[],
                                  selectionnes_d=[], remplacants_d=[])
        r    = lire_excel_selecmaster(xlsx, "Lorraine", "Lorraine")
        sel  = [t for t in r["tireurs"] if t["statut"] == "selectionne" and t["genre"] == "H"]
        rangs = [t["rang"] for t in sel]
        assert rangs == list(range(1, len(sel) + 1))


# =============================================================================
# Versioning pickle
# =============================================================================

class TestVersioningPickle:

    def test_db_version_definie(self):
        from suivi import DB_VERSION
        assert isinstance(DB_VERSION, int) and DB_VERSION >= 1

    def test_chargement_ancien_format_ne_crash_pas(self, tmp_path, monkeypatch):
        """Un pickle sans __version__ (v1) doit être migré sans KeyError."""
        import suivi
        ancien_pkl = tmp_path / ".suivi_test.pkl"
        # Simuler un ancien _db sans __version__
        ancien = {
            "Épée|M13": {
                "arme": "Épée", "categorie": "M13",
                "territoire_organisateur": "Lorraine",
                "created_at": None, "updated_at": None,
                "territoires": {
                    "Lorraine": [
                        {"rang": 1, "nom": "A", "prenom": "B", "club": "C",
                         "genre": "H", "statut": "selectionne",
                         "confirmation": "attente", "confirmation_at": None}
                        # manque: "appele", "note"
                    ]
                },
                "audit": [],
            }
        }
        with open(str(ancien_pkl), "wb") as f:
            pickle.dump(ancien, f)

        monkeypatch.setattr(suivi, "_SUIVI_FILE", str(ancien_pkl))
        monkeypatch.setattr(suivi, "_db", {})
        suivi._charger()

        # Vérifier que les champs manquants ont été ajoutés
        session = suivi._db.get("Épée|M13", {})
        tireurs = session.get("territoires", {}).get("Lorraine", [])
        assert len(tireurs) == 1
        assert "appele" in tireurs[0]
        assert "note" in tireurs[0]

    def test_sauvegarder_inclut_version(self, tmp_path, monkeypatch):
        import suivi
        pkl = tmp_path / ".suivi_test.pkl"
        monkeypatch.setattr(suivi, "_SUIVI_FILE", str(pkl))
        monkeypatch.setattr(suivi, "_db", {})
        suivi._sauvegarder()

        with open(str(pkl), "rb") as f:
            sauve = pickle.load(f)
        assert sauve.get("__version__") == suivi.DB_VERSION

    def test_migration_ajoute_version(self, tmp_path, monkeypatch):
        import suivi
        pkl = tmp_path / ".suivi_test.pkl"
        ancien = {"Épée|M13": {"arme": "Épée", "categorie": "M13",
                                "territoires": {}, "audit": [],
                                "created_at": None, "updated_at": None,
                                "territoire_organisateur": ""}}
        with open(str(pkl), "wb") as f:
            pickle.dump(ancien, f)

        monkeypatch.setattr(suivi, "_SUIVI_FILE", str(pkl))
        monkeypatch.setattr(suivi, "_db", {})
        suivi._charger()
        assert suivi._db.get("__version__") == suivi.DB_VERSION


# =============================================================================
# initialiser_depuis_excel()
# =============================================================================

class TestInitialiserDepuisExcel:

    def setup_method(self):
        """Reset _db avant chaque test."""
        import suivi
        suivi._db = {"__version__": suivi.DB_VERSION}

    def test_initialisation_basique(self):
        import suivi
        xlsx = excel_selecmaster(arme="Épée", categorie="M13")
        r    = suivi.initialiser_depuis_excel(xlsx, "Lorraine", "Lorraine")
        assert r["arme"] == "Épée"
        assert r["categorie"] == "M13"
        assert r["nb_tireurs"] > 0

    def test_preservation_confirmations(self):
        """Un re-import doit préserver les confirmations existantes."""
        import suivi
        sel_h = [{"nom": "MARTIN", "prenom": "Jean", "club": "C"}]
        xlsx  = excel_selecmaster(selectionnes_h=sel_h, remplacants_h=[],
                                   selectionnes_d=[], remplacants_d=[])

        suivi.initialiser_depuis_excel(xlsx, "Lorraine", "Lorraine")

        # Confirmer manuellement
        cle = "Épée|M13"
        for t in suivi._db[cle]["territoires"]["Lorraine"]:
            if t["nom"] == "MARTIN":
                t["confirmation"] = "oui"

        # Re-importer
        suivi.initialiser_depuis_excel(xlsx, "Lorraine", "Lorraine")

        for t in suivi._db[cle]["territoires"]["Lorraine"]:
            if t["nom"] == "MARTIN":
                assert t["confirmation"] == "oui"
                break
        else:
            pytest.fail("Tireur MARTIN non retrouvé après re-import")

    def test_excel_invalide_leve_erreur(self):
        import suivi
        with pytest.raises(suivi.ExcelParseError):
            suivi.initialiser_depuis_excel(excel_invalide(), "Lorraine", "Lorraine")


# =============================================================================
# Marqueur de version du format Excel (B6)
# =============================================================================

class TestVersionFormat:

    def _remarquer(self, contenu, marque):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(contenu))
        wb.properties.keywords = marque
        buf = io.BytesIO(); wb.save(buf)
        return buf.getvalue()

    def test_version_absente_acceptee(self):
        from suivi import lire_excel_selecmaster
        xlsx = excel_selecmaster(selectionnes_h=[{"nom": "A", "prenom": "B", "club": "C"}],
                                 remplacants_h=[], selectionnes_d=[], remplacants_d=[])
        assert lire_excel_selecmaster(xlsx, "Alsace", "Alsace")

    def test_version_differente_rejetee(self):
        from suivi import lire_excel_selecmaster, ExcelParseError
        xlsx = excel_selecmaster(selectionnes_h=[{"nom": "A", "prenom": "B", "club": "C"}],
                                 remplacants_h=[], selectionnes_d=[], remplacants_d=[])
        with pytest.raises(ExcelParseError):
            lire_excel_selecmaster(self._remarquer(xlsx, "AUTRE_V9"), "Alsace", "Alsace")

    def test_version_correcte_acceptee(self):
        from suivi import lire_excel_selecmaster, EXCEL_FORMAT_VERSION
        xlsx = excel_selecmaster(selectionnes_h=[{"nom": "A", "prenom": "B", "club": "C"}],
                                 remplacants_h=[], selectionnes_d=[], remplacants_d=[])
        assert lire_excel_selecmaster(self._remarquer(xlsx, EXCEL_FORMAT_VERSION), "Alsace", "Alsace")


# =============================================================================
# Versionnage pickle arbitres (B7)
# =============================================================================

class TestVersionArbitres:

    def test_migration_v1_sans_version(self, tmp_path, monkeypatch):
        """Un pickle v1 (sans __version__) est migré sans perte."""
        import suivi
        f = tmp_path / ".arbitres_master.pkl"
        v1 = {"Épée": [{"id": "abc", "nom": "N", "prenom": "P", "niveau": "Régionale",
                        "club": "C", "territoire": "Alsace", "statut": "retenu"}]}
        with open(f, "wb") as fh:
            pickle.dump(v1, fh)
        monkeypatch.setattr(suivi, "_ARB_FILE", str(f))
        suivi._charger_arb()
        assert suivi._arbitres.get("__version__") == suivi.ARB_VERSION
        assert suivi._arbitres["Épée"][0]["nom"] == "N"
        assert suivi._arbitres["Épée"][0]["note"] == ""  # champ complété

    def test_version_exclue_des_lectures(self, tmp_path, monkeypatch):
        import suivi
        monkeypatch.setattr(suivi, "_ARB_FILE", str(tmp_path / "a.pkl"))
        suivi._arbitres = {"__version__": suivi.ARB_VERSION, "Épée": []}
        assert "__version__" not in suivi.get_arbitres()
        assert "__version__" not in suivi.get_arbitres_serialisable()
