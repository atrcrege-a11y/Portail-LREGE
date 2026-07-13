"""Tests CalendrierLREGE — parser FFE, routes CRUD, écriture atomique, exports."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

import app as appmod
import parser_ffe as pf


# ─────────────────────────────────────────────────────────────────────────────
# parser_ffe — fonctions pures
# ─────────────────────────────────────────────────────────────────────────────

class TestParserFFE:

    def test_parse_date_ok(self):
        assert pf.parse_date("25/12/2026") == "2026-12-25"

    def test_parse_date_invalide(self):
        assert pf.parse_date("pas une date") is None
        assert pf.parse_date("") is None

    def test_parse_arme_codes(self):
        assert pf.parse_arme("EPEM") == ("épée", "H")
        assert pf.parse_arme("SABF") == ("sabre", "D")
        assert pf.parse_arme("FLEMF") == ("fleuret", "H+D")
        assert pf.parse_arme("LASM") == ("sabre laser", "H")

    def test_parse_arme_inconnu(self):
        arme, sexe = pf.parse_arme("XYZ")
        assert arme == "xyz" and sexe == ""

    def test_detect_type(self):
        assert pf.detect_type("Stage arbitrage JNA") == "formation_arbitrage"
        assert pf.detect_type("Formation animateur") == "formation_animateur"
        assert pf.detect_type("Stage de ligue") == "stage"
        assert pf.detect_type("Circuit national M17") == "competition"

    def test_is_grand_est_par_perimetre(self):
        assert pf.is_grand_est({pf.COL_PERIMETRE: "Régional", pf.COL_INTITULE: "X"})

    def test_is_grand_est_par_intitule(self):
        assert pf.is_grand_est({pf.COL_PERIMETRE: "National",
                                pf.COL_INTITULE: "Open Grand Est de sabre"})

    def test_pas_grand_est(self):
        assert not pf.is_grand_est({pf.COL_PERIMETRE: "National",
                                    pf.COL_INTITULE: "Circuit de Bretagne"})


# ─────────────────────────────────────────────────────────────────────────────
# Routes Flask — CRUD + écriture atomique
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "DATA_FILE", str(tmp_path / "calendrier.json"))
    appmod.app.config["TESTING"] = True
    with appmod.app.test_client() as c:
        yield c


def _event_min(**kw):
    e = {"date_debut": "2026-11-15", "intitule": "Test compet", "lieu": "Metz"}
    e.update(kw)
    return e


class TestRoutes:

    def test_liste_vide(self, client):
        assert client.get("/api/events").get_json() == []

    def test_ajout_et_lecture(self, client):
        r = client.post("/api/events", json=_event_min())
        assert r.status_code == 200 and r.get_json()["success"]
        events = client.get("/api/events").get_json()
        assert len(events) == 1
        assert events[0]["intitule"] == "Test compet"
        assert events[0]["manuel"] is True

    def test_ajout_sans_date_refuse(self, client):
        r = client.post("/api/events", json={"intitule": "Sans date"})
        assert r.status_code == 400

    def test_ajout_date_invalide_refuse(self, client):
        r = client.post("/api/events", json=_event_min(date_debut="15/11/2026"))
        assert r.status_code == 400

    def test_ajout_sans_intitule_refuse(self, client):
        r = client.post("/api/events", json={"date_debut": "2026-11-15"})
        assert r.status_code == 400

    def test_modification(self, client):
        eid = client.post("/api/events", json=_event_min()).get_json()["event"]["id"]
        r = client.put(f"/api/events/{eid}", json={"lieu": "Nancy"})
        assert r.get_json()["success"]
        assert client.get("/api/events").get_json()[0]["lieu"] == "Nancy"

    def test_modification_introuvable(self, client):
        assert client.put("/api/events/inexistant", json={}).status_code == 404

    def test_suppression(self, client):
        eid = client.post("/api/events", json=_event_min()).get_json()["event"]["id"]
        client.delete(f"/api/events/{eid}")
        assert client.get("/api/events").get_json() == []

    def test_filtre_niveau(self, client):
        client.post("/api/events", json=_event_min(niveau="regional"))
        client.post("/api/events", json=_event_min(intitule="Nat", niveau="national"))
        assert len(client.get("/api/events?niveau=national").get_json()) == 1

    def test_stats(self, client):
        client.post("/api/events", json=_event_min())
        s = client.get("/api/stats").get_json()
        assert s["total"] == 1 and s["manuel"] == 1


class TestEcritureAtomique:

    def test_pas_de_fichier_tmp_residuel(self, client, tmp_path):
        client.post("/api/events", json=_event_min())
        assert not os.path.exists(str(tmp_path / "calendrier.json.tmp"))
        assert os.path.exists(str(tmp_path / "calendrier.json"))

    def test_json_valide_apres_ecriture(self, client, tmp_path):
        client.post("/api/events", json=_event_min())
        with open(str(tmp_path / "calendrier.json"), encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Exports — smoke tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExports:

    def test_export_ical(self, client):
        client.post("/api/events", json=_event_min())
        r = client.get("/api/export/ical")
        assert r.status_code == 200
        assert b"BEGIN:VCALENDAR" in r.data

    def test_export_excel(self, client):
        client.post("/api/events", json=_event_min())
        r = client.get("/api/export/excel")
        assert r.status_code == 200 and r.data[:2] == b"PK"  # zip xlsx

    def test_export_pdf(self, client):
        client.post("/api/events", json=_event_min())
        r = client.get("/api/export/pdf")
        assert r.status_code == 200 and r.data[:4] == b"%PDF"
