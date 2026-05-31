"""
core/format_export.py — Abstraction du format de sortie .fff WIN/FFE.

Si FFE change le format, seul ce fichier est à modifier.
Les modules bellepoule_fff.py et equipe_individuel.py importent
ecrire_fff() depuis ici — ils ne connaissent pas le format concret.
"""
import os
from abc import ABC, abstractmethod


# ── Interface abstraite ────────────────────────────────────────────────────────

class FormatExport(ABC):
    """Interface commune pour tous les formats de sortie FFE."""

    @abstractmethod
    def entete(self, info: dict) -> list[str]:
        """Génère les lignes d'en-tête du fichier."""

    @abstractmethod
    def ligne_tireur(self, tireur: dict, info: dict) -> str:
        """Génère une ligne de données pour un tireur."""

    @abstractmethod
    def extension(self) -> str:
        """Extension du fichier de sortie (ex: '.fff')."""

    @abstractmethod
    def encodage(self) -> str:
        """Encodage du fichier (ex: 'latin-1')."""

    @abstractmethod
    def fin_de_ligne(self) -> str:
        """Séquence de fin de ligne (ex: '\\r\\n')."""

    def ecrire(self, tireurs: list, info: dict, output_path: str) -> None:
        """
        Écrit le fichier de sortie complet.
        Appelle entete() + ligne_tireur() pour chaque tireur.
        """
        lignes = self.entete(info)
        for t in tireurs:
            lignes.append(self.ligne_tireur(t, info))
        contenu = self.fin_de_ligne().join(lignes) + self.fin_de_ligne()
        with open(output_path, "w", encoding=self.encodage(), errors="replace") as f:
            f.write(contenu)


# ── Implémentation WIN/FFE actuelle ────────────────────────────────────────────

class FormatFFF(FormatExport):
    """
    Format .fff WIN/FFE — format actuel (2024-2025).

    Structure :
      Ligne 0 : FFF;WIN;competition;<lieu>;individuel
      Ligne 1 : DATE;ARME;SEXE;CATEGORIE;NOM;NOM
      Lignes  : NOM,PRENOM,DDN,SEXE,FRA,;,,;LICENCE,,CLUB,PLACE,,;PLACE,t
    """

    def extension(self) -> str:
        return ".fff"

    def encodage(self) -> str:
        return "latin-1"

    def fin_de_ligne(self) -> str:
        return "\r\n"

    def entete(self, info: dict) -> list[str]:
        lieu = info.get("lieu", "")
        return [
            f"FFF;WIN;competition;{lieu};individuel",
            f"{info['date']};{info['arme']};{info['sexe']};"
            f"{info['categorie']};{info['nom']};{info['nom']}",
        ]

    def ligne_tireur(self, tireur: dict, info: dict) -> str:
        nom     = tireur.get("nom",     "")
        prenom  = tireur.get("prenom",  "")
        ddn     = tireur.get("ddn",     "")
        sexe    = tireur.get("sexe",    "") or info.get("sexe", "")
        licence = tireur.get("licence", "")
        club    = tireur.get("club",    "")
        place   = tireur.get("place",   "")
        return (
            f"{nom},{prenom},{ddn},{sexe},FRA,;"
            f",,;{licence},,{club},{place},,;{place},t"
        )


# ── Registre des formats ───────────────────────────────────────────────────────

_FORMATS: dict[str, FormatExport] = {
    "fff": FormatFFF(),
}


def get_format(nom: str = "fff") -> FormatExport:
    """Retourne l'instance du format demandé. Lève ValueError si inconnu."""
    fmt = _FORMATS.get(nom.lower())
    if fmt is None:
        raise ValueError(f"Format inconnu : '{nom}'. Formats disponibles : {list(_FORMATS)}")
    return fmt


def ecrire_fff(tireurs: list, info: dict, output_path: str,
               format_nom: str = "fff") -> None:
    """
    Point d'entrée unique pour écrire un fichier de résultats.
    Remplace les appels directs à ecrire_fff() dans bellepoule_fff.py
    et equipe_individuel.py.
    """
    get_format(format_nom).ecrire(tireurs, info, output_path)
