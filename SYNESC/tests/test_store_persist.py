"""
Tests C13 — persistance du store de travail (core/store_persist.py).
"""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core import store_persist


@pytest.fixture
def store_file(tmp_path, monkeypatch):
    path = str(tmp_path / "_store.pkl")
    monkeypatch.setattr(store_persist, "_STORE_FILE", path)
    return path


class TestStorePersist:

    def test_roundtrip(self, store_file):
        store = {"sid1": [({"uid": "u1", "titre": "T"}, [{"nom": "A"}], [{"nom": "R"}])]}
        store_persist.sauvegarder(store)
        assert store_persist.charger() == store

    def test_fichier_absent(self, store_file):
        assert store_persist.charger() == {}

    def test_fichier_corrompu(self, store_file):
        with open(store_file, "wb") as f:
            f.write(b"pas un pickle")
        assert store_persist.charger() == {}

    def test_version_ecrite(self, store_file):
        store_persist.sauvegarder({})
        with open(store_file, "rb") as f:
            brut = pickle.load(f)
        assert brut["__version__"] == store_persist.DB_VERSION

    def test_migration_version_anterieure(self, store_file):
        with open(store_file, "wb") as f:
            pickle.dump({"__version__": 0, "stores": {"s": []}}, f)
        assert store_persist.charger() == {"s": []}

    def test_types_preserves(self, store_file):
        """Pickle préserve les tuples (contrairement au JSON des sessions)."""
        store = {"sid": [({"uid": "u"}, [], [])]}
        store_persist.sauvegarder(store)
        item = store_persist.charger()["sid"][0]
        assert isinstance(item, tuple)


class TestIntegrationApp:

    def test_store_survit_redemarrage(self, store_file):
        """Upload → save → rechargement simule un redémarrage serveur."""
        import app as app_module
        client = app_module.app.test_client()
        app_module._store.clear()

        from tests.fixtures import xml_individuel
        import io as _io
        r = client.post("/api/upload", data={
            "files": (_io.BytesIO(xml_individuel(tireurs=[{"nom": "MARTIN", "club": "TEST"}])), "test.xml"),
        }, content_type="multipart/form-data")
        assert r.status_code == 200
        assert r.get_json()["total"] == 1

        # « redémarrage » : on recharge depuis le disque
        recharge = store_persist.charger()
        sid = next(iter(recharge))
        assert len(recharge[sid]) == 1
        meta = recharge[sid][0][0]
        assert "uid" in meta

    def test_clear_persiste(self, store_file):
        import app as app_module
        client = app_module.app.test_client()
        app_module._store.clear()

        from tests.fixtures import xml_individuel
        import io as _io
        client.post("/api/upload", data={
            "files": (_io.BytesIO(xml_individuel(tireurs=[{"nom": "MARTIN", "club": "TEST"}])), "test.xml"),
        }, content_type="multipart/form-data")

        client.post("/api/clear")
        recharge = store_persist.charger()
        assert all(len(v) == 0 for v in recharge.values())
