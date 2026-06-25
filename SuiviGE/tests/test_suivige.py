"""Tests unitaires SuiviGE — fixtures synthétiques."""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from tests.fixtures import excel_indiv, excel_equipes, excel_invalide


# =============================================================================
# Constantes
# =============================================================================
class TestConstantes:
    def test_prefix_indiv(self):
        from suivi import EXCEL_PREFIX_INDIV
        import re
        assert re.match(EXCEL_PREFIX_INDIV, "CL NAT 1")
        assert re.match(EXCEL_PREFIX_INDIV, "CL GE 5")
        assert not re.match(EXCEL_PREFIX_INDIV, "M 1")

    def test_prefix_equipe(self):
        from suivi import EXCEL_PREFIX_EQUIPE
        import re
        assert re.match(EXCEL_PREFIX_EQUIPE, "N° 1")
        assert re.match(EXCEL_PREFIX_EQUIPE, "N°2")
        assert not re.match(EXCEL_PREFIX_EQUIPE, "CL NAT 1")

    def test_armes_map_complete(self):
        from suivi import EXCEL_ARMES_MAP
        assert "Épée" in EXCEL_ARMES_MAP.values()
        assert "Fleuret" in EXCEL_ARMES_MAP.values()
        assert "Sabre" in EXCEL_ARMES_MAP.values()

    def test_db_version_definie(self):
        from suivi import DB_VERSION
        assert isinstance(DB_VERSION, int) and DB_VERSION >= 2


# =============================================================================
# lire_excel_indiv()
# =============================================================================
class TestLireExcelIndiv:

    def test_tireurs_qualifies_extraits(self):
        from suivi import lire_excel_indiv
        qual = [{"nom":"MARTIN","prenom":"Jean","club":"C"}]
        xlsx = excel_indiv(qualifies=qual, remplacants=[])
        r = lire_excel_indiv(xlsx)
        h = next((f for f in r if f["genre"] == "H"), None)
        assert h is not None
        assert any(t["nom"] == "MARTIN" for t in h["tireurs"])

    def test_statut_qualifie(self):
        from suivi import lire_excel_indiv
        xlsx = excel_indiv()
        h = next(f for f in lire_excel_indiv(xlsx) if f["genre"] == "H")
        qual = [t for t in h["tireurs"] if t["statut"] == "qualifie"]
        assert len(qual) >= 1

    def test_statut_remplacant(self):
        from suivi import lire_excel_indiv
        rem = [{"nom":"REM","prenom":"X","club":"C"}]
        xlsx = excel_indiv(remplacants=rem)
        h = next(f for f in lire_excel_indiv(xlsx) if f["genre"] == "H")
        r = [t for t in h["tireurs"] if t["statut"] == "remplacant"]
        assert len(r) >= 1

    def test_arme_detectee(self):
        from suivi import lire_excel_indiv
        xlsx = excel_indiv(arme="Fleuret")
        h = next(f for f in lire_excel_indiv(xlsx) if f["genre"] == "H")
        assert h["arme"] == "Fleuret"

    def test_categorie_detectee(self):
        from suivi import lire_excel_indiv
        xlsx = excel_indiv(categorie="M13")
        h = next(f for f in lire_excel_indiv(xlsx) if f["genre"] == "H")
        assert h["categorie"] == "M13"

    def test_confirmation_initiale_attente(self):
        from suivi import lire_excel_indiv
        xlsx = excel_indiv()
        for f in lire_excel_indiv(xlsx):
            for t in f["tireurs"]:
                assert t["confirmation"] == "attente"


# =============================================================================
# lire_excel_equipes()
# =============================================================================
class TestLireExcelEquipes:

    def test_equipes_extraites(self):
        from suivi import lire_excel_equipes
        eqs = [{"rang":"N° 1","nom":"STRAS","club":"C","composition":[]}]
        xlsx = excel_equipes(equipes=eqs)
        h = next((f for f in lire_excel_equipes(xlsx) if f["genre"] == "H"), None)
        assert h is not None
        assert len(h["equipes"]) == 1
        assert h["equipes"][0]["nom"] == "STRAS"

    def test_composition_extraite(self):
        from suivi import lire_excel_equipes
        eqs = [{"rang":"N° 1","nom":"STRAS","club":"C",
                "composition":[{"nom":"A","prenom":"X"}]}]
        xlsx = excel_equipes(equipes=eqs)
        h = next(f for f in lire_excel_equipes(xlsx) if f["genre"] == "H")
        assert len(h["equipes"][0]["composition"]) >= 1

    def test_arme_equipes_detectee(self):
        from suivi import lire_excel_equipes
        xlsx = excel_equipes(arme="Sabre")
        h = next(f for f in lire_excel_equipes(xlsx) if f["genre"] == "H")
        assert h["arme"] == "Sabre"


# =============================================================================
# Versioning pickle
# =============================================================================
class TestVersioningPickle:

    def test_sauvegarder_inclut_version(self, tmp_path, monkeypatch):
        import suivi
        pkl = tmp_path / ".suivi_ge_test.pkl"
        monkeypatch.setattr(suivi, "_SUIVI_FILE", str(pkl))
        monkeypatch.setattr(suivi, "_db", {})
        suivi._sauvegarder()
        with open(str(pkl), "rb") as f:
            d = pickle.load(f)
        assert d.get("__version__") == suivi.DB_VERSION

    def test_chargement_ancien_format_migre(self, tmp_path, monkeypatch):
        import suivi
        pkl = tmp_path / ".suivi_ge_test.pkl"
        ancien = {
            "indiv|Épée|M17|H": {
                "type": "indiv", "arme": "Épée", "categorie": "M17", "genre": "H",
                "competition": "", "date_lieu": "", "arbitres": [],
                "created_at": None, "updated_at": None, "audit": [],
                "tireurs": [{"rang":"CL GE 1","nom":"A","prenom":"B","club":"C",
                             "statut":"qualifie","confirmation":"attente"}],
            }
        }
        with open(str(pkl), "wb") as f:
            pickle.dump(ancien, f)
        monkeypatch.setattr(suivi, "_SUIVI_FILE", str(pkl))
        monkeypatch.setattr(suivi, "_db", {})
        suivi._charger()
        t = suivi._db["indiv|Épée|M17|H"]["tireurs"][0]
        assert "note" in t
        assert "confirmation_at" in t

    def test_get_tous_suivis_ignore_version(self, tmp_path, monkeypatch):
        import suivi
        monkeypatch.setattr(suivi, "_db", {
            "__version__": 2,
            "indiv|Épée|M17|H": {
                "type":"indiv","arme":"Épée","categorie":"M17","genre":"H",
                "competition":"","updated_at": __import__("datetime").datetime.now(),
            }
        })
        res = suivi.get_tous_suivis()
        assert "__version__" not in res
        assert "indiv|Épée|M17|H" in res


# =============================================================================
# initialiser_indiv() + initialiser_equipes()
# =============================================================================
class TestInitialiser:

    def setup_method(self):
        import suivi
        suivi._db = {"__version__": suivi.DB_VERSION}

    def test_init_indiv_basique(self):
        import suivi
        xlsx = excel_indiv(arme="Épée", categorie="M17", genre="H")
        cles = suivi.initialiser_indiv(xlsx)
        assert len(cles) >= 1
        assert any("indiv" in c for c in cles)

    def test_init_indiv_preserve_confirmation(self):
        import suivi
        qual = [{"nom":"MARTIN","prenom":"Jean","club":"C"}]
        xlsx = excel_indiv(qualifies=qual, remplacants=[])
        suivi.initialiser_indiv(xlsx)
        cle = "indiv|Épée|M17|H"
        for t in suivi._db[cle]["tireurs"]:
            if t["nom"] == "MARTIN":
                t["confirmation"] = "oui"
        suivi.initialiser_indiv(xlsx)
        for t in suivi._db[cle]["tireurs"]:
            if t["nom"] == "MARTIN":
                assert t["confirmation"] == "oui"

    def test_init_equipes_basique(self):
        import suivi
        xlsx = excel_equipes(arme="Épée", categorie="M17", genre="H")
        cles = suivi.initialiser_equipes(xlsx)
        assert len(cles) >= 1
        assert any("equipe" in c for c in cles)


# ── Pont plateforme (mapper pur) ───────────────────────────────────────────────
import suivi as _sv


def _comp_pf(fmt="individuel"):
    return {
        "nom": "FÊTE DES JEUNES", "categorie": "V1", "arme": "epee",
        "format": fmt, "genre": "HD", "date": "2026-06-13", "lieu": "Paris",
        "clubs": [{"club": "CE Châlons", "attendus": [
            {"nom": "JANER", "prenom": "Léo", "section": "QUOTA FÉDÉRAL",
             "rang": 1, "saisi": True, "present": True},
            {"nom": "WILLEM", "prenom": "Jules", "section": "TIREURS REMPLACANTS",
             "rang": 5, "saisi": False, "present": None},
        ]}],
    }


def test_mapper_plateforme_indiv():
    e = _sv.mapper_plateforme([_comp_pf()])
    cle = "indiv|Épée|Vétérans|HD"
    assert cle in e
    ent = e[cle]
    assert ent["type"] == "indiv" and ent["genre"] == "HD"
    t = {x["nom"]: x for x in ent["tireurs"]}
    assert t["JANER"]["confirmation"] == "oui" and t["JANER"]["statut"] == "qualifie"
    assert t["WILLEM"]["confirmation"] == "attente" and t["WILLEM"]["statut"] == "remplacant"
    assert t["JANER"]["club"] == "CE Châlons"


def test_mapper_plateforme_ignore_equipes():
    assert _sv.mapper_plateforme([_comp_pf(fmt="equipe")]) == {}
