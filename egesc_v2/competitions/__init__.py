"""
competitions/__init__.py
Registre central des compétitions disponibles.
Ajouter une nouvelle compétition ici suffit pour la rendre disponible dans l'app.
"""

from .grand_est import GrandEst
from .alsace    import Alsace
from .lorraine  import Lorraine

# Registre : comp_type → classe
COMPETITIONS = {
    "grand_est": GrandEst,
    "alsace":    Alsace,
    "lorraine":  Lorraine,
}

# Métadonnées affichées dans l'interface
COMPETITIONS_META = {
    "grand_est": {
        "label":  "Grand Est",
        "icon":   "🥇",
        "active": True,
    },
    "alsace": {
        "label":  "Alsace",
        "icon":   "🛡",
        "active": True,
    },
    "lorraine": {
        "label":  "Coupe de Lorraine",
        "icon":   "⚜",
        "active": True,
    },
}


def get_competition(comp_type: str):
    """Retourne une instance de la compétition demandée."""
    cls = COMPETITIONS.get(comp_type, GrandEst)
    return cls()
