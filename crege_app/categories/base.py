"""
categories/base.py — Classe de base pour toutes les catégories.
Chaque catégorie hérite de BaseCategorie et implémente construire() et generer().
"""
from abc import ABC, abstractmethod


class BaseCategorie(ABC):
    """
    Interface commune à toutes les catégories.

    Attributs de classe à définir dans les sous-classes :
        CAT_ID      : str   — identifiant (ex: 'M13', 'Seniors')
        LABEL       : str   — libellé affiché
        FORMAT      : str   — 'jeunes' | 'seniors' | 'equipes_m15'
        ARMES       : list  — armes disponibles (ex: ['F','E','S'])
        COMPETITIONS: list  — compétitions disponibles
        NATIONALITE_FR : bool — filtrage nationalité par défaut
    """
    CAT_ID         = ""
    LABEL          = ""
    FORMAT         = ""
    ARMES          = ["F", "E", "S"]
    COMPETITIONS   = []
    NATIONALITE_FR = False

    @abstractmethod
    def construire(self, df_national, df_regional, config: dict) -> dict:
        """
        Construit le dictionnaire de données pour la génération Excel.
        Retourne un dict compatible avec le générateur.
        """

    @abstractmethod
    def generer(self, data: dict):
        """
        Génère un classeur openpyxl à partir des données construites.
        Retourne un Workbook.
        """

    @classmethod
    def get_config(cls) -> dict:
        """Retourne la config de la catégorie pour l'interface."""
        return {
            "id":           cls.CAT_ID,
            "label":        cls.LABEL,
            "format":       cls.FORMAT,
            "armes":        cls.ARMES,
            "competitions": cls.COMPETITIONS,
            "nationalite_fr": cls.NATIONALITE_FR,
        }
