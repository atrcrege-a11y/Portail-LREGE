"""
Registre des catégories.
"""
from .jeunes  import M13, M15, M17, M20
from .seniors import Seniors, V1, V2, V3, V4

# Registre : cat_id -> classe
REGISTRY = {
    cls.CAT_ID: cls
    for cls in [M13, M15, M17, M20, Seniors, V1, V2, V3, V4]
}
