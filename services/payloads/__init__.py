"""
services/payloads/ — Bibliothèque de construction des payloads plateforme
pour les familles non couvertes par les 3 exports historiques
(indiv générique, équipes M15, équipes séniors — INCHANGÉS, cf.
services/export_plateforme.py).

Principe (décision 2026-07-03) : pour les vétérans, le classeur Excel est
généré EN MÉMOIRE par le générateur existant puis PARSÉ pour produire le
payload — source unique = l'Excel que voient les clubs. Pour le sabre
laser, les `construire_selection_*` retournent déjà {"meta","sections"}
et sont sérialisés directement (pas de parsing).

Chaque payload passe par `regles.valider_payload` avant envoi
(garde-fou anti-sélection-erronée).
"""
from .parse_workbook import parse_workbook
from .regles import valider_payload, ValidationPayloadError
from .veterans import (
    construire_payload_indiv_veterans,
    construire_payload_indiv_veterans_fs,
    construire_payload_equipes_veterans,
)
from .sabre_laser import construire_payload_sabre_laser
