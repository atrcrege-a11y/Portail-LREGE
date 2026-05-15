"""
core/styles.py — Palette, constantes visuelles et fonctions de style Excel.
"""
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side, Protection

# ── Palette bleu institutionnel ──────────────────────────────────────
COULEUR_TITRE        = "1B3F7A"
COULEUR_N1           = "1B3F7A"
COULEUR_N2           = "2563A8"
COULEUR_N3           = "4A86C8"
COULEUR_EQUIPE       = "1B3F7A"
COULEUR_REMPLACANT   = "3A5A8A"
COULEUR_ENTETE_COL   = "EBF2FA"
COULEUR_LIGNE_PAIRE  = "F5F9FF"
COULEUR_ALERTE       = "F0F5FF"
COULEUR_BLANC        = "FFFFFF"
COULEUR_GE1          = "1B3F7A"
COULEUR_GE2          = "2563A8"
COULEUR_GE3          = "4A86C8"
COULEUR_REMPL_EQ     = "5C5C5C"

_thin = Side(style="thin", color="CCCCCC")
BORDURE_FINE = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)

LABELS_ARB = {
    "regional":           "Régional",
    "regional_formation": "Régional en formation",
    "national":           "National",
    "national_formation": "National en formation",
    "international":      "International",
}


def style_cellule(ws, cell_ref, valeur=None, bold=False, italic=False,
                  font_size=10, font_color="000000", bg_color=None,
                  align_h="left", align_v="center", wrap=False, border=None):
    cell = ws[cell_ref] if isinstance(cell_ref, str) else cell_ref
    if valeur is not None:
        cell.value = valeur
    cell.font = Font(name="Calibri", size=font_size, bold=bold,
                     italic=italic, color=font_color)
    if bg_color:
        cell.fill = PatternFill("solid", fgColor=bg_color)
    cell.alignment = Alignment(horizontal=align_h, vertical=align_v, wrap_text=wrap)
    if border is not None:
        cell.border = border


def fusionner_style(ws, debut, fin, valeur, bold=False, font_size=11,
                    font_color="FFFFFF", bg_color=COULEUR_TITRE, align_h="center"):
    from openpyxl.utils import column_index_from_string, get_column_letter
    ws.merge_cells(f"{debut}:{fin}")
    cell = ws[debut]
    style_cellule(ws, cell, valeur, bold=bold, font_size=font_size,
                  font_color=font_color, bg_color=bg_color,
                  align_h=align_h, align_v="center", border=None)
    row_num   = int(''.join(filter(str.isdigit, debut)))
    col_start = column_index_from_string(''.join(filter(str.isalpha, debut)))
    col_end   = column_index_from_string(''.join(filter(str.isalpha, fin)))
    no_border = Border()
    fill      = PatternFill("solid", fgColor=bg_color)
    for col_i in range(col_start + 1, col_end + 1):
        ws.cell(row=row_num, column=col_i).border = no_border
        ws.cell(row=row_num, column=col_i).fill   = fill

# ── Palettes par catégorie ────────────────────────────────────────────
PALETTES = {
    "M13": {
        "titre":            "6A0DAD",
        "n1":            "7B1DC4",
        "n2":            "9B4DD4",
        "n3":            "C090E8",
        "wc":             "D97706",
        "alerte":            "F6EEFF",
        "entete_col":            "EDD9FA",
        "ligne_paire":            "FAF4FF",
    },
    "M15": {
        "titre":            "1A5C2A",
        "n1":            "2E7D45",
        "n2":            "4AAF68",
        "n3":            "80CC96",
        "wc":             "D97706",
        "alerte":            "EBF8EF",
        "entete_col":            "C8EDD5",
        "ligne_paire":            "F1FAF4",
    },
    "M17": {
        "titre":            "8B0000",
        "n1":            "B22222",
        "n2":            "D94040",
        "n3":            "E88080",
        "wc":             "D97706",
        "alerte":            "FFF0F0",
        "entete_col":            "FAD0D0",
        "ligne_paire":            "FFF5F5",
    },
    "M20": {
        "titre":            "7A6000",
        "n1":            "A08000",
        "n2":            "C4A010",
        "n3":            "DFC050",
        "wc":             "D97706",
        "alerte":            "FFFBEA",
        "entete_col":            "FFF0A0",
        "ligne_paire":            "FFFDF0",
    },
    "Seniors": {
        "titre":            "1B3F7A",
        "n1":            "1B3F7A",
        "n2":            "2563A8",
        "n3":            "4A86C8",
        "wc":             "D97706",
        "alerte":            "F0F5FF",
        "entete_col":            "EBF2FA",
        "ligne_paire":            "F5F9FF",
    },
    "V1": {
        "titre":            "3D1A5C",
        "n1":            "5A2A80",
        "n2":            "7A4A9E",
        "n3":            "A07ABE",
        "wc":             "D97706",
        "alerte":            "F2ECF9",
        "entete_col":            "DDD0EF",
        "ligne_paire":            "F7F3FC",
    },
    "V2": {
        "titre":            "3D1A5C",
        "n1":            "5A2A80",
        "n2":            "7A4A9E",
        "n3":            "A07ABE",
        "wc":             "D97706",
        "alerte":            "F2ECF9",
        "entete_col":            "DDD0EF",
        "ligne_paire":            "F7F3FC",
    },
    "V3": {
        "titre":            "3D1A5C",
        "n1":            "5A2A80",
        "n2":            "7A4A9E",
        "n3":            "A07ABE",
        "wc":             "D97706",
        "alerte":            "F2ECF9",
        "entete_col":            "DDD0EF",
        "ligne_paire":            "F7F3FC",
    },
    "V4": {
        "titre":            "3D1A5C",
        "n1":            "5A2A80",
        "n2":            "7A4A9E",
        "n3":            "A07ABE",
        "wc":             "D97706",
        "alerte":            "F2ECF9",
        "entete_col":            "DDD0EF",
        "ligne_paire":            "F7F3FC",
    },
}

PALETTE_DEFAUT = PALETTES["Seniors"]


def get_palette(cat_id: str) -> dict:
    """Retourne la palette de couleurs pour une catégorie donnée."""
    return PALETTES.get(cat_id, PALETTE_DEFAUT)
