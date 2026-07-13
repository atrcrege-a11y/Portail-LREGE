"""
core/sessions_store.py — Persistance des sessions de compétition.

Une session = les fichiers XML parsés (meta + tireurs + arbitres) + titre + date de sauvegarde.
Stockage : dossier sessions/ à la racine de SYNESC, un fichier JSON par session.
"""
import os
import json
import uuid
from datetime import datetime

SESSIONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "sessions")
)


def _ensure_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def sauvegarder(store: list, titre: str, comp_type: str) -> str:
    """
    Sauvegarde le store courant en JSON.
    Retourne l'id de la session créée.
    """
    _ensure_dir()
    session_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    data = {
        "id":        session_id,
        "titre":     titre,
        "comp_type": comp_type,
        "sauvegarde": now,
        "fichiers": []
    }

    for meta, tireurs, arbitres in store:
        data["fichiers"].append({
            "meta":     meta,
            "tireurs":  tireurs,
            "arbitres": arbitres,
        })

    filename = f"{session_id}_{_safe(titre)}.json"
    path = os.path.join(SESSIONS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return session_id


def lister() -> list[dict]:
    """Retourne la liste des sessions sauvegardées, triées par date desc."""
    _ensure_dir()
    sessions = []
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "id":         data.get("id", fname),
                "titre":      data.get("titre", "—"),
                "comp_type":  data.get("comp_type", "?"),
                "sauvegarde": data.get("sauvegarde", ""),
                "nb_fichiers":len(data.get("fichiers", [])),
                "filename":   fname,
            })
        except Exception:
            continue
    return sorted(sessions, key=lambda s: s["sauvegarde"], reverse=True)


def charger(session_id: str) -> tuple[list, str, str] | None:
    """
    Charge une session par id.
    Retourne (store, titre, comp_type) ou None si introuvable.
    store = liste de (meta, tireurs, arbitres)
    """
    _ensure_dir()
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        if not fname.startswith(session_id):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            store = [
                (f["meta"], f["tireurs"], f["arbitres"])
                for f in data.get("fichiers", [])
            ]
            return store, data.get("titre", ""), data.get("comp_type", "grand_est")
        except Exception:
            return None
    return None


def supprimer(session_id: str) -> bool:
    """Supprime une session. Retourne True si réussie."""
    _ensure_dir()
    for fname in os.listdir(SESSIONS_DIR):
        if fname.startswith(session_id) and fname.endswith(".json"):
            os.remove(os.path.join(SESSIONS_DIR, fname))
            return True
    return False


def _safe(titre: str) -> str:
    """Nettoie un titre pour en faire un nom de fichier."""
    import unicodedata, re
    s = unicodedata.normalize("NFD", titre)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:40]
