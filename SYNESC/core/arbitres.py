"""
core/arbitres.py — Lecture de la liste d'arbitres/responsables depuis un fichier Excel.

Format attendu : config_arbitres.xlsx dans le dossier SYNESC
Colonnes obligatoires : Prenom | Nom
Colonne optionnelle  : Role  (ex: "CRA", "Superviseur GE", "Superviseur Lorraine")

La liste est chargée à la demande (pas de cache — rechargée à chaque appel).
"""
import os
import openpyxl

ARBITRES_FILE = os.path.join(os.path.dirname(__file__), "..", "config_arbitres.xlsx")
ARBITRES_FILE = os.path.normpath(ARBITRES_FILE)


def _charger() -> list[dict]:
    """Lit config_arbitres.xlsx et retourne une liste de dicts {prenom, nom, role, label}."""
    if not os.path.exists(ARBITRES_FILE):
        return []
    try:
        wb = openpyxl.load_workbook(ARBITRES_FILE, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        # Détecter en-têtes (première ligne)
        header = [str(c).strip().lower() if c else "" for c in rows[0]]
        col_prenom = next((i for i, h in enumerate(header) if "prenom" in h or "prénom" in h), None)
        col_nom    = next((i for i, h in enumerate(header) if h == "nom"), None)
        col_role   = next((i for i, h in enumerate(header) if "role" in h or "rôle" in h), None)
        if col_nom is None:
            return []
        result = []
        for row in rows[1:]:
            nom    = str(row[col_nom]).strip()    if row[col_nom]    else ""
            prenom = str(row[col_prenom]).strip() if col_prenom is not None and row[col_prenom] else ""
            role   = str(row[col_role]).strip()   if col_role   is not None and row[col_role]   else ""
            if not nom:
                continue
            label = f"{prenom} {nom}".strip() if prenom else nom
            result.append({"prenom": prenom, "nom": nom, "role": role, "label": label})
        return result
    except Exception:
        return []


def get_liste_noms() -> list[str]:
    """Retourne la liste des labels 'Prénom NOM' triés alphabétiquement."""
    return sorted(set(p["label"] for p in _charger() if p["label"]))


def get_liste_par_role(role: str) -> list[str]:
    """Retourne les noms filtrés par rôle (insensible à la casse)."""
    all_items = _charger()
    role_lower = role.lower()
    filtered = [p["label"] for p in all_items if role_lower in p["role"].lower()]
    # Si aucun filtre possible, retourner tous
    return sorted(filtered) if filtered else sorted(p["label"] for p in all_items if p["label"])


def chemin_fichier() -> str:
    return ARBITRES_FILE


def fichier_existe() -> bool:
    return os.path.exists(ARBITRES_FILE)
