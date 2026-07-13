"""Tests saison automatique SelecMaster (B8)."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from parser import saison_debut, annee_min_m11


def test_saison_avant_septembre():
    assert saison_debut(datetime.date(2026, 7, 10)) == 2025


def test_saison_apres_septembre():
    assert saison_debut(datetime.date(2026, 9, 1)) == 2026


def test_annee_m11_saison_2025_2026():
    """Référence connue : saison 2025-2026 → M11 nés >= 2015."""
    assert annee_min_m11(datetime.date(2026, 3, 1)) == 2015
    assert annee_min_m11(datetime.date(2025, 10, 1)) == 2015


def test_annee_m11_saison_suivante():
    assert annee_min_m11(datetime.date(2026, 9, 15)) == 2016
