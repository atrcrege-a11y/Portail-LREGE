"""
parser_pdf.py — Import du calendrier FFE depuis PDF (format grille annuelle).

Structure exacte :
  Tableau 0 d'une page :
    Ligne 0 : ["Septembre 2026 Octobre 2026...", "", "", ...]
    Ligne 2 : ["", "", "5-6", "12-13", "19-20", "26-27", "3-4", "10-11", ...]
              ↑ col 0 = arme (rotatif), col 1 = catégorie, col 2+ = dates
    Lignes suivantes : ["", "Seniors", "", "", "", "", "", "", "Hénin-B.", ...]
                        ↑ col 1 = catégorie, col N = lieu pour date col N

  9 tableaux par page (3 armes × H+D + variations)
  Les tableaux 1-8 partagent les mêmes colonnes-dates que le tableau 0.
"""
import re
import uuid
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

# ── Constantes ────────────────────────────────────────────────────────────────

CATS_NATIONALES = {"Seniors", "M20", "M17", "M13/M15", "Vétérans"}

MOIS_NUM = {
    "janvier":"01","février":"02","mars":"03","avril":"04",
    "mai":"05","juin":"06","juillet":"07","août":"08",
    "septembre":"09","octobre":"10","novembre":"11","décembre":"12",
}

NIVEAUX_MOTS = {
    "FRA":"national","EN1":"national","EN2":"national","EN3":"national",
    "EN4":"national","FDJ":"national","ELITE":"national","CF":"national",
    "CDF":"national","1/2":"national","FRA":"national",
}

# Fragments bruit PDF à ignorer (artefacts de mise en page)
_BRUIT = re.compile(r'^[\d/NIS]$|^[A-Z]$|^(20|N°|N°IS|\d{4})$')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extraire_mois_annees(header: str) -> list[tuple[str,str]]:
    """[("09","2026"), ("10","2026"), ...] depuis l'en-tête de page."""
    res = []
    for m in re.finditer(r'(\w+)\s+(20\d{2})', header, re.IGNORECASE):
        num = MOIS_NUM.get(m.group(1).lower())
        if num:
            res.append((num, m.group(2)))
    return res


def _resoudre_dates(col_dates: list, mois_annees: list) -> dict:
    """
    Construit un dict {col_idx: (date_debut_iso, date_fin_iso)}.
    Détecte le changement de mois quand le jour remet à zéro.
    """
    if not mois_annees:
        return {}

    mois_idx = 0
    prev_j1 = 0
    result = {}

    for col_idx, jours in col_dates:
        # Gérer "17-18-19" (3 jours) → prendre premier et dernier
        parts = jours.split("-")
        try:
            j1, j2 = int(parts[0]), int(parts[-1])
        except (ValueError, IndexError):
            continue

        # Changer de mois si le jour remet à zéro
        if j1 < prev_j1 - 5 and mois_idx + 1 < len(mois_annees):
            mois_idx += 1
        prev_j1 = j1

        m_debut, a_debut = mois_annees[mois_idx]

        # Passage de mois pour j2 (ex: "31-1")
        if j2 < j1:
            if mois_idx + 1 < len(mois_annees):
                m_fin, a_fin = mois_annees[mois_idx + 1]
            else:
                m_fin, a_fin = m_debut, a_debut
        else:
            m_fin, a_fin = m_debut, a_debut

        try:
            d1 = datetime(int(a_debut), int(m_debut), j1).strftime("%Y-%m-%d")
            d2 = datetime(int(a_fin),   int(m_fin),   j2).strftime("%Y-%m-%d")
            result[col_idx] = (d1, d2)
        except ValueError:
            pass

    return result


def _est_bruit(val: str) -> bool:
    if not val or not val.strip():
        return True
    v = val.strip()
    if len(v) <= 1:
        return True
    if _BRUIT.match(v):
        return True
    return False


def _detecter_niveau(lieu: str) -> str:
    l = lieu.upper()
    for mot, niv in NIVEAUX_MOTS.items():
        if mot in l:
            return niv
    return "national"


def _nettoyer_lieu(val: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'\n', ' ', str(val))).strip()


# ── Parser principal ──────────────────────────────────────────────────────────

def parse_pdf_ffe(pdf_path: str) -> list[dict]:
    """
    Parse le PDF calendrier FFE et retourne une liste d'événements
    compatibles avec le schéma CalendrierLREGE.
    """
    bruts = []  # [(date_debut, date_fin, categorie, lieu)]

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables:
                continue

            # En-tête mois (ligne 0 du tableau 0)
            header = str(tables[0][0][0] or "") if tables else ""
            mois_annees = _extraire_mois_annees(header)

            # Extraire les colonnes-dates depuis la ligne 2 du tableau 0
            # Structure : col 0 = arme rotatif, col 1 = catégorie, col 2+ = dates
            col_dates = []  # [(col_idx, "5-6"), ...]
            if len(tables[0]) > 2:
                for col_idx, cell in enumerate(tables[0][2]):
                    val = str(cell or "").strip()
                    # Format : "5-6", "12-13", "17-18-19", "31-1"
                    if re.match(r'^\d{1,2}(-\d{1,2})+$', val):
                        col_dates.append((col_idx, val))

            if not col_dates or not mois_annees:
                continue

            # Résoudre les dates réelles de chaque colonne
            dates_map = _resoudre_dates(col_dates, mois_annees)

            # Parser tous les tableaux de la page
            for t in tables:
                for row in t:
                    if not row or len(row) < 2 or row[1] is None:
                        continue
                    cat = str(row[1] or "").strip()
                    if cat not in CATS_NATIONALES:
                        continue

                    # Parcourir chaque colonne-date
                    for col_idx, _ in col_dates:
                        if col_idx >= len(row):
                            continue
                        cell_val = row[col_idx]
                        if not cell_val:
                            continue
                        lieu = _nettoyer_lieu(str(cell_val))
                        if _est_bruit(lieu):
                            continue
                        if col_idx not in dates_map:
                            continue
                        d1, d2 = dates_map[col_idx]
                        bruts.append((d1, d2, cat, lieu))

    # Déduplication (même date + catégorie + lieu)
    dedup = {}
    for d1, d2, cat, lieu in bruts:
        key = (d1, cat, lieu.lower()[:30])
        if key not in dedup:
            dedup[key] = (d1, d2, cat, lieu)

    # Construction des événements finaux
    resultats = []
    for d1, d2, cat, lieu in sorted(dedup.values(), key=lambda x: x[0]):
        resultats.append({
            "id":               str(uuid.uuid4()),
            "source":           "pdf_ffe",
            "manuel":           False,
            "type_evenement":   "competition",
            "statut":           "",
            "date_debut":       d1,
            "date_fin":         d2 if d2 != d1 else d1,
            "type_competition": "",
            "niveau":           _detecter_niveau(lieu),
            "niveau_raw":       "National(e)",
            "numero":           "",
            "intitule":         f"{cat} — {lieu}",
            "lieu":             lieu,
            "perimetre":        "National(e)",
            "armes":            [],   # non extractible depuis ce format PDF
            "arme":             "",
            "sexe":             "",
            "categories":       [cat],
            "type_epreuve":     "",
            "url":              "",
            "grand_est":        False,
            "notes":            "Import PDF calendrier FFE",
            "__version__":      1,
        })

    return resultats


# ── Test autonome ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "calendrier.pdf"
    evs = parse_pdf_ffe(path)
    print(f"\nÉvénements extraits : {len(evs)}")
    cats = {}
    for e in evs:
        for c in e["categories"]:
            cats[c] = cats.get(c, 0) + 1
    print("Par catégorie :", cats)
    print("\nDétail :")
    for e in evs:
        print(f"  {e['date_debut']} → {e['date_fin']} | {e['categories'][0]:10} | {e['lieu']}")
