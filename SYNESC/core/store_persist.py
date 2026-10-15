"""
core/store_persist.py — Persistance du store de travail (_store) entre redémarrages.

Pickle versionné (pattern SuiviGE DB_VERSION) : sessions/_store.pkl.
Structure fichier : {"__version__": DB_VERSION, "stores": {sid: [(meta, tireurs, arbitres), ...]}}
"""
import os
import pickle

DB_VERSION = 2

_STORE_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "sessions", "_store.pkl")
)


def _migrer(brut: dict) -> dict:
    """Migre un fichier store d'une version antérieure vers DB_VERSION."""
    version = brut.get("__version__", 1)
    if version == DB_VERSION:
        return brut
    print(f"[SYNESC] Migration store v{version} -> v{DB_VERSION}")
    # v1 -> v2 : ajout de la liste des arbitres saisis à la main.
    brut.setdefault("manuels", {})
    brut["__version__"] = DB_VERSION
    return brut


def charger() -> dict:
    """Charge le store de travail. Dict vide si fichier absent ou illisible."""
    try:
        if os.path.isfile(_STORE_FILE):
            with open(_STORE_FILE, "rb") as f:
                brut = pickle.load(f)
            if not isinstance(brut, dict):
                raise ValueError("format inattendu")
            brut = _migrer(brut)
            stores = brut.get("stores", {})
            return stores if isinstance(stores, dict) else {}
    except Exception as e:
        print(f"[SYNESC] Erreur chargement store : {e}")
    return {}


def charger_manuels() -> dict:
    """Arbitres saisis à la main, par sid. Dict vide si absent ou illisible."""
    try:
        if os.path.isfile(_STORE_FILE):
            with open(_STORE_FILE, "rb") as f:
                brut = _migrer(pickle.load(f))
            manuels = brut.get("manuels", {})
            return manuels if isinstance(manuels, dict) else {}
    except Exception as e:
        print(f"[SYNESC] Erreur chargement arbitres manuels : {e}")
    return {}


def sauvegarder(store: dict, manuels: dict | None = None) -> None:
    """Sauvegarde le store de travail et les arbitres manuels (silencieux en cas d'erreur)."""
    try:
        os.makedirs(os.path.dirname(_STORE_FILE), exist_ok=True)
        with open(_STORE_FILE, "wb") as f:
            pickle.dump({"__version__": DB_VERSION, "stores": store,
                         "manuels": manuels or {}}, f)
    except Exception as e:
        print(f"[SYNESC] Erreur sauvegarde store : {e}")
