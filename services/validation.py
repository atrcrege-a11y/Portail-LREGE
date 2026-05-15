"""
services/validation.py — Validation des fichiers et DataFrames importés.

Retourne des messages d'erreur lisibles au lieu de tracebacks bruts.
"""
import os
import pandas as pd

EXTENSIONS_CLASSEMENT = ('.xlsx', '.xls', '.csv')
EXTENSIONS_PDF        = ('.pdf',)
EXTENSIONS_PDF_FFE    = ('.pdf',)
EXTENSIONS_EQUIPES    = ('.pdf', '.fff', '.xml')
TAILLE_MAX_MB         = 16


class ValidationError(Exception):
    """Erreur de validation avec message utilisateur lisible."""
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail  = detail


def valider_fichier(filename: str, contenu_bytes: int, extensions_ok: tuple) -> None:
    """Vérifie l'extension et la taille d'un fichier uploadé."""
    if not filename:
        raise ValidationError("Aucun fichier reçu.")
    ext = os.path.splitext(filename.lower())[1]
    if ext not in extensions_ok:
        formats = ", ".join(e.lstrip('.').upper() for e in extensions_ok)
        raise ValidationError(
            f"Format non supporté : '{ext or 'inconnu'}'",
            f"Formats acceptés : {formats}"
        )
    taille_mb = contenu_bytes / (1024 * 1024)
    if taille_mb > TAILLE_MAX_MB:
        raise ValidationError(
            f"Fichier trop lourd : {taille_mb:.1f} Mo (max {TAILLE_MAX_MB} Mo)"
        )


def valider_dataframe_classement(df: pd.DataFrame, filename: str = "") -> None:
    """Vérifie qu'un DataFrame classement est utilisable."""
    if df is None or df.empty:
        raise ValidationError(
            f"Aucun tireur trouvé dans ce fichier.",
            f"Vérifiez que '{filename}' est un classement FFE valide (colonnes Nom, Prénom, Région attendues)."
        )
    cols_attendues = {'Nom', 'Prenom'}
    cols_presentes = set(df.columns)
    manquantes = cols_attendues - cols_presentes
    if manquantes:
        raise ValidationError(
            f"Colonnes manquantes dans le fichier : {', '.join(sorted(manquantes))}",
            f"Colonnes trouvées : {', '.join(sorted(cols_presentes))}"
        )
    if len(df) < 2:
        raise ValidationError(
            f"Seulement {len(df)} ligne(s) trouvée(s) — fichier probablement mal formaté."
        )


def valider_dataframe_pdf(sections: dict, filename: str = "") -> None:
    """Vérifie qu'un PDF BellePoule contient au moins une section."""
    if not sections:
        raise ValidationError(
            "Aucune section trouvée dans ce PDF.",
            f"Vérifiez que '{filename}' est un classement BellePoule valide (N1/N2/N3 attendus)."
        )
    vides = [niv for niv, df in sections.items() if df.empty]
    if len(vides) == len(sections):
        raise ValidationError(
            "Toutes les sections du PDF sont vides.",
            f"Sections trouvées : {', '.join(sections.keys())}"
        )


def valider_dataframe_ffe(df: pd.DataFrame, filename: str = "") -> None:
    """Vérifie qu'un PDF FFE liste qualifiés est utilisable."""
    if df is None or df.empty:
        raise ValidationError(
            "Aucun tireur trouvé dans ce PDF FFE.",
            f"Vérifiez que '{filename}' est une liste FFE qualifiés CDF valide."
        )
    if 'Niveau' not in df.columns:
        raise ValidationError(
            "Colonne 'Niveau' absente — PDF FFE non reconnu.",
            "Le PDF doit contenir les sections Nationale 1 / Nationale 2."
        )
    if len(df) < 5:
        raise ValidationError(
            f"Seulement {len(df)} tireur(s) trouvé(s) — liste incomplète ou mal parsée."
        )


def valider_equipes(equipes: list, filename: str = "") -> None:
    """Vérifie qu'un fichier équipes a été parsé."""
    if not equipes:
        raise ValidationError(
            "Aucune équipe trouvée dans ce fichier.",
            f"Vérifiez que '{filename}' est un PDF BellePoule ou Engarde équipes valide."
        )


def erreur_json(e: ValidationError) -> dict:
    """Formate une ValidationError en dict JSON."""
    d = {"error": e.message}
    if e.detail:
        d["detail"] = e.detail
    return d
