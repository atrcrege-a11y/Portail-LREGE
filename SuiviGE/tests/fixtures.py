"""Fixtures Excel SelecGE synthétiques pour les tests SuiviGE."""
import io, openpyxl


def excel_indiv(arme="Épée", categorie="M17", genre="H",
                qualifies=None, remplacants=None):
    """Génère un Excel SelecGE individuel minimal."""
    qualifies   = qualifies   or [{"nom":"MARTIN","prenom":"Jean","club":"NANCY"}]
    remplacants = remplacants or [{"nom":"DUPONT","prenom":"Paul","club":"METZ"}]

    wb = openpyxl.Workbook()
    for genre_label, g in [("Hommes","H"), ("Dames","D")]:
        ws = wb.create_sheet(genre_label)
        ws.cell(1,1, f"CHAMPIONNAT DE FRANCE {categorie.upper()}")
        ws.cell(2,1, "07/06/2026  ·  ORLÉANS")
        ws.cell(3,1, f"{arme.upper()} {'HOMMES' if g=='H' else 'DAMES'}")
        row = 5

        # Section qualifiés
        ws.cell(row,1, "QUALIFIÉS")
        row += 1
        ws.cell(row,1, "Rang / Classement")
        row += 1
        if g == genre:
            for i, t in enumerate(qualifies, 1):
                ws.cell(row,1, f"CL GE {i}")
                ws.cell(row,2, t["nom"])
                ws.cell(row,3, t["prenom"])
                ws.cell(row,4, t["club"])
                row += 1

        row += 1
        ws.cell(row,1, "REMPLAÇANTS")
        row += 1
        ws.cell(row,1, "Rang / Classement")
        row += 1
        if g == genre:
            for i, t in enumerate(remplacants, 1):
                ws.cell(row,1, f"CL GE {i}")
                ws.cell(row,2, t["nom"])
                ws.cell(row,3, t["prenom"])
                ws.cell(row,4, t["club"])
                row += 1

    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_equipes(arme="Épée", categorie="M17", genre="H", equipes=None):
    """Génère un Excel SelecGE équipes minimal."""
    equipes = equipes or [
        {"rang":"N° 1","nom":"STRAS ESC","club":"STRAS",
         "composition":[{"nom":"A","prenom":"X"},{"nom":"B","prenom":"Y"}]},
        {"rang":"N° 2","nom":"NANCY CE","club":"NANCY","composition":[]},
    ]

    wb = openpyxl.Workbook()
    for genre_label, g in [("Hommes","H"), ("Dames","D")]:
        ws = wb.create_sheet(genre_label)
        ws.cell(1,1, f"CHAMPIONNAT DE FRANCE {categorie.upper()}")
        ws.cell(2,1, "07/06/2026  ·  ORLÉANS")
        ws.cell(3,1, f"{arme.upper()} {'HOMMES' if g=='H' else 'DAMES'} ÉQUIPES")
        row = 5

        ws.cell(row,1, "Rang / Classement")
        row += 1
        if g == genre:
            for eq in equipes:
                ws.cell(row,1, eq["rang"])
                ws.cell(row,2, eq["nom"])
                ws.cell(row,3, eq["club"])
                row += 1
                for m in eq.get("composition", []):
                    ws.cell(row,1, f"  {1}")
                    ws.cell(row,2, m["nom"])
                    ws.cell(row,3, m["prenom"])
                    row += 1

    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_invalide():
    wb = openpyxl.Workbook()
    wb.active["A1"] = "Rien ici"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
