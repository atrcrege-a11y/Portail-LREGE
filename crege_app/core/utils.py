"""
core/utils.py — Utilitaires partagés : filtrage, détection région, slugification.
"""
import re
import unicodedata

# ── Colonnes FFE ─────────────────────────────────────────────────────
COL_RANG    = "Rang"
COL_NOM     = "Nom"
COL_PRENOM  = "Prenom"
COL_CLUB    = "Nom club"
COL_REGION  = "Region"
COL_NATION  = "Nationalite"

REGIONS_GE = {"alsace", "lorraine", "champagne-ardenne", "champagne ardenne",
              "grand est", "grand-est", "ges - grand est", "ges"}

def est_grand_est(region) -> bool:
    """Retourne True si la région appartient au Grand Est."""
    if not region or not isinstance(region, str):
        return False
    r = region.strip().lower()
    # Format FFE : "GES - GRAND EST" ou "GRAND EST" ou "Alsace"...
    return r in REGIONS_GE or "grand est" in r or r.startswith("ges")


def est_francais(row) -> bool:
    """Retourne True si le tireur est de nationalité française."""
    # La colonne peut s'appeler "Nationalite" ou "Nationalité" selon la source
    nat = str(row.get(COL_NATION, "") or row.get("Nationalité", "") or row.get("Nationalite", "")).strip().upper()
    return nat in ("FRA", "FRANÇAISE", "FRANCAIS", "FR", "FRANCE", "")


def filtrer_df(df, nationalite_francaise: bool):
    """Filtre un DataFrame selon la nationalité si demandé.

    Gère le cas d'un DataFrame vide : pandas retourne une Series float64 au lieu
    de bool via apply() sur un DF vide, ce qui écrase les colonnes lors du masquage.
    """
    if not nationalite_francaise:
        return df
    if df is None or df.empty:
        return df
    return df[df.apply(est_francais, axis=1)].copy()


def slugify(text: str) -> str:
    """Convertit un texte en slug ASCII sans accents."""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    return text.strip("_")
