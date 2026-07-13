"""
arbitrage.py — Règle métier arbitrage (Specs 10.1).

Modèle de données : SelecGE n'a pas de BD. Les champs arbitres vivent dans le
dict `arbitrage_config` (JSON config + propagé dans le cache de génération).

Champs (Specs 10.1, étendant l'existant {source, seuil1, seuil2}) :
    - arbitres_requis (bool)        : un arbitrage est-il demandé
    - type_arbitrage  (TypeArbitrage): none | standard | master
    - arbitres_nombre (int, calculé) : dérivé du nombre de tireurs, jamais stocké

Décision métier confirmée (cf. REGLES.md §5) :
    - STANDARD : seuils 4 / 9, plafonné à 2 arbitres
        0..3 tireurs -> 0 ; 4..8 -> 1 ; 9 et + -> 2
        (= seuils historiques seuil1=4 / seuil2=9 déjà présents dans SelecGE)
    - MASTER   : 1 arbitre dès 1 tireur, sans contrainte au-delà (toujours 1)
        0 -> 0 ; 1 et + -> 1
    - NONE     : 0
"""
from enum import Enum


class TypeArbitrage(str, Enum):
    NONE = "none"
    STANDARD = "standard"
    MASTER = "master"


# Valeurs de seuils par défaut (modèle STANDARD historique SelecGE)
SEUIL1_DEFAUT = 4   # 1er arbitre à partir de ce nombre de tireurs
SEUIL2_DEFAUT = 9   # 2e arbitre à partir de ce nombre de tireurs
STANDARD_PLAFOND = 2


def calculer_arbitres_requis(nombre_tireurs, type_arbitrage,
                             seuil1=SEUIL1_DEFAUT, seuil2=SEUIL2_DEFAUT):
    """Nombre d'arbitres requis selon le type et le nombre de tireurs confirmés.

    STANDARD respecte les seuils configurables (défaut 4/9), plafonné à 2.
    MASTER : 1 arbitre dès 1 tireur, sans contrainte au-delà.
    """
    n = int(nombre_tireurs or 0)
    t = type_arbitrage.value if isinstance(type_arbitrage, TypeArbitrage) else (type_arbitrage or "none")

    if t == TypeArbitrage.NONE.value or n <= 0:
        return 0

    if t == TypeArbitrage.STANDARD.value:
        if n < seuil1:
            return 0
        if n < seuil2:
            return 1
        return STANDARD_PLAFOND

    if t == TypeArbitrage.MASTER.value:
        return 1  # 1 arbitre dès 1 tireur, sans contrainte au-delà (n>0 garanti ici)

    return 0


def normaliser_arbitrage_config(cfg):
    """Étend un arbitrage_config existant avec les champs Specs 10.1, en
    rétrocompatibilité avec l'ancien format {source, seuil1, seuil2}.

    Un config sans `type_arbitrage` mais avec une source != 'aucun' est traité
    comme STANDARD (modèle seuils historique).
    """
    cfg = dict(cfg or {})
    source = cfg.get("source", "aucun")

    # type_arbitrage : explicite, sinon dérivé de l'ancien `source`
    type_arb = cfg.get("type_arbitrage")
    if not type_arb:
        type_arb = (TypeArbitrage.NONE.value if source == "aucun"
                    else TypeArbitrage.STANDARD.value)
    cfg["type_arbitrage"] = type_arb

    # arbitres_requis : explicite, sinon dérivé
    if "arbitres_requis" not in cfg:
        cfg["arbitres_requis"] = type_arb != TypeArbitrage.NONE.value

    # seuils par défaut conservés pour rétrocompat
    cfg.setdefault("seuil1", SEUIL1_DEFAUT)
    cfg.setdefault("seuil2", SEUIL2_DEFAUT)
    return cfg


def arbitres_nombre(arbitrage_config, nombre_tireurs):
    """Champ calculé `arbitres_nombre` à partir d'un arbitrage_config normalisé."""
    cfg = normaliser_arbitrage_config(arbitrage_config)
    if not cfg.get("arbitres_requis"):
        return 0
    return calculer_arbitres_requis(
        nombre_tireurs, cfg["type_arbitrage"],
        cfg.get("seuil1", SEUIL1_DEFAUT), cfg.get("seuil2", SEUIL2_DEFAUT),
    )


def regle_texte(arbitrage_config):
    """Phrase lisible décrivant la règle d'arbitrage (pour export / affichage)."""
    cfg = normaliser_arbitrage_config(arbitrage_config)
    if not cfg.get("arbitres_requis"):
        return "Pas d'arbitre requis"
    if cfg["type_arbitrage"] == TypeArbitrage.MASTER.value:
        return "1 arbitre dès le 1er tireur engagé"
    s1, s2 = cfg.get("seuil1", SEUIL1_DEFAUT), cfg.get("seuil2", SEUIL2_DEFAUT)
    return (f"1 arbitre à partir de {s1} tireurs engagés, "
            f"2 arbitres à partir de {s2} (max {STANDARD_PLAFOND})")


def export_arbitrage_json(arbitrage_config, nombre_tireurs=None):
    """Bloc arbitrage au format contrat plateforme de confirmation (Specs 10.2).

    `arbitres_nombre` n'est calculé que si `nombre_tireurs` est fourni ; sinon
    None (l'engagement réel n'est pas figé côté SelecGE).
    """
    cfg = normaliser_arbitrage_config(arbitrage_config)
    return {
        "arbitres_requis": cfg["arbitres_requis"],
        "type_arbitrage":  cfg["type_arbitrage"],
        "source":          cfg.get("source", "aucun"),
        "seuils":          {"seuil1": cfg.get("seuil1", SEUIL1_DEFAUT),
                            "seuil2": cfg.get("seuil2", SEUIL2_DEFAUT)},
        "arbitres_nombre": (arbitres_nombre(cfg, nombre_tireurs)
                            if nombre_tireurs is not None else None),
        "regle":           regle_texte(cfg),
    }
