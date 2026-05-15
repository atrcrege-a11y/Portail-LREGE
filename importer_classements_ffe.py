"""
Lecture des exports Excel FFE (classements national et régional).

Structure des fichiers FFE :
    Ligne 0 : entêtes (Rang, Code adherent, Nom, Prenom, Ddn, Nationalité, Region,
               Code club, Nom club, Points, puis une colonne par épreuve EN...)
    Lignes 1+ : données tireurs
"""

import pandas as pd

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

CODE_REGION_GRAND_EST = "GES"
NATIONALITE_FRANCE    = "FRANCE"

COL_RANG        = "Rang"
COL_NOM         = "Nom"
COL_PRENOM      = "Prenom"
COL_CLUB        = "Nom club"
COL_REGION      = "Region"
COL_POINTS      = "Points"
COL_DDN         = "Ddn"
COL_NATIONALITE = "Nationalité"

def lire_classement_ffe(chemin_fichier):
    """
    Lit un export Excel FFE et retourne un DataFrame propre avec les colonnes :
    Rang, Nom, Prenom, Club, Region, Points, Ddn
    """
    # Tenter la feuille "Classement", fallback sur la première feuille
    try:
        df_raw = pd.read_excel(chemin_fichier, sheet_name="Classement", header=0)
    except Exception:
        df_raw = pd.read_excel(chemin_fichier, sheet_name=0, header=0)

    # Renommer pour homogénéiser (la ligne 0 du fichier sert déjà d'entête)
    df = df_raw.rename(columns={
        "Rang": COL_RANG,
        "Nom": COL_NOM,
        "Prenom": COL_PRENOM,
        "Nom club": COL_CLUB,
        "Region": COL_REGION,
        "Points": COL_POINTS,
        "Ddn": COL_DDN,
    })

    # Garder les colonnes utiles + colonnes épreuves nationales (EN) pour le critère de participation
    cols_utiles = [COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION, COL_POINTS, COL_DDN, COL_NATIONALITE]
    cols_epreuves_nat = [c for c in df_raw.columns if str(c).startswith('EN ')]
    toutes_cols = [c for c in cols_utiles + cols_epreuves_nat if c in df_raw.columns or c in df.columns]
    df = df[[c for c in toutes_cols if c in df.columns]].copy()

    # Nettoyage
    df[COL_RANG]   = pd.to_numeric(df[COL_RANG],   errors="coerce")
    df[COL_POINTS] = pd.to_numeric(df[COL_POINTS], errors="coerce")
    df = df.dropna(subset=[COL_RANG])
    df[COL_RANG]   = df[COL_RANG].astype(int)
    df[COL_NOM]    = df[COL_NOM].str.upper().str.strip()
    df[COL_PRENOM] = df[COL_PRENOM].str.strip()
    df[COL_CLUB]   = df[COL_CLUB].str.strip()
    if COL_NATIONALITE in df.columns:
        df[COL_NATIONALITE] = df[COL_NATIONALITE].str.upper().str.strip()

    return df.sort_values(COL_RANG).reset_index(drop=True)

def est_grand_est(region_str):
    """Détecte si un tireur appartient à la région Grand Est."""
    if not isinstance(region_str, str) or not region_str.strip():
        return False
    return CODE_REGION_GRAND_EST in region_str.upper()

def est_francais(nationalite_str):
    """Détecte si un tireur est de nationalité française."""
    if pd.isna(nationalite_str):
        return False
    return str(nationalite_str).upper().strip() == NATIONALITE_FRANCE

def filtrer_df(df, filtre_nationalite_fr=False):
    """Applique les filtres optionnels sur un DataFrame de classement."""
    if filtre_nationalite_fr and COL_NATIONALITE in df.columns:
        df = df[df[COL_NATIONALITE].apply(est_francais)]
    return df

