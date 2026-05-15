"""
services/cache.py — Cache des classements importés.

Le cache est persisté sur disque (pickle) dans le dossier tmp Flask.
Il survit aux redémarrages de l'appli tant que le dossier tmp existe.
"""
import os
import pickle
import logging

logger = logging.getLogger(__name__)

# Cache en mémoire : {cle: {"path": str, "df": DataFrame, ...}}
_cache: dict = {}
_CACHE_FILE: str = ""


def init(cache_dir: str):
    """Initialise le cache. Recharge depuis le disque si disponible."""
    global _cache, _CACHE_FILE
    _CACHE_FILE = os.path.join(cache_dir, "selecge_cache.pkl")
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "rb") as f:
                _cache = pickle.load(f)
            logger.info(f"Cache rechargé : {len(_cache)} entrées")
        except Exception as e:
            logger.warning(f"Cache disque illisible, réinitialisé : {e}")
            _cache = {}


def _persist():
    """Écrit le cache sur disque."""
    if not _CACHE_FILE:
        return
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump(_cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        logger.warning(f"Impossible de persister le cache : {e}")


def set(cle: str, valeur: dict):
    """Stocke une entrée et persiste sur disque."""
    _cache[cle] = valeur
    _persist()


def get(cle: str) -> dict | None:
    """Retourne une entrée ou None."""
    return _cache.get(cle)


def has(cle: str) -> bool:
    return cle in _cache


def delete(cle: str):
    if cle in _cache:
        del _cache[cle]
        _persist()


def keys():
    return list(_cache.keys())


def raw() -> dict:
    """Accès direct au dict interne (pour compatibilité avec code existant)."""
    return _cache


# ── Cache Sabre Laser (séparé) ────────────────────────────────────────
_sl_cache: dict = {}


def sl_set(cle: str, valeur: dict):
    _sl_cache[cle] = valeur


def sl_get(cle: str) -> dict | None:
    return _sl_cache.get(cle)


def sl_has(cle: str) -> bool:
    return cle in _sl_cache


def sl_raw() -> dict:
    return _sl_cache
