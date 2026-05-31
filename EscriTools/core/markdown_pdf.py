"""
core/markdown_pdf.py — Conversion Markdown → PDF soigné via reportlab.

Gère : titres H1/H2/H3, listes, tableaux, code, gras/italique,
       séparateurs horizontaux. Option fusion de plusieurs fichiers.
"""
import re
import os
import uuid
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, ListFlowable, ListItem,
    Table, TableStyle, Preformatted,
)

# ── Palette de couleurs ───────────────────────────────────────────────────────
BLEU       = colors.HexColor("#1F3864")
BLEU_CLAIR = colors.HexColor("#2e5da8")
GRIS       = colors.HexColor("#555555")
GRIS_CLAIR = colors.HexColor("#f4f4f4")
NOIR       = colors.HexColor("#1a1a1a")


def _mkstyle(name: str, **kw) -> ParagraphStyle:
    """Crée un style reportlab avec un nom unique (évite les collisions)."""
    return ParagraphStyle(name + "_" + uuid.uuid4().hex[:6], **kw)


# ── Styles typographiques ──────────────────────────────────────────────────────
sH1    = _mkstyle("h1",   fontSize=22, textColor=BLEU,       spaceAfter=6,  spaceBefore=18,
                           fontName="Helvetica-Bold",         leading=26)
sH2    = _mkstyle("h2",   fontSize=16, textColor=BLEU_CLAIR, spaceAfter=4,  spaceBefore=14,
                           fontName="Helvetica-Bold",         leading=20)
sH3    = _mkstyle("h3",   fontSize=13, textColor=BLEU,       spaceAfter=3,  spaceBefore=10,
                           fontName="Helvetica-BoldOblique",  leading=16)
sPara  = _mkstyle("para", fontSize=10, textColor=NOIR,        spaceAfter=4,  spaceBefore=2,
                           fontName="Helvetica",              leading=14)
sCode  = _mkstyle("code", fontSize=9,  fontName="Courier",   spaceAfter=6,  leading=13,
                           backColor=GRIS_CLAIR, leftIndent=10, rightIndent=10)
sListe = _mkstyle("lst",  fontSize=10, textColor=NOIR,        fontName="Helvetica", leading=14)


def echapper(txt: str) -> str:
    """
    Échappe le HTML et convertit la syntaxe Markdown inline
    (**gras**, *italique*, `code`) en balises reportlab.
    """
    txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    txt = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', txt)
    txt = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', txt)
    txt = re.sub(r'`(.+?)`',       r'<font name="Courier">\1</font>', txt)
    return txt


def convertir(md_path: str, output_path: str, log=print) -> tuple[bool, str]:
    """
    Convertit un fichier Markdown en PDF soigné.
    Retourne (succès, chemin_sortie_ou_message_erreur).
    """
    if not os.path.isfile(md_path):
        return False, f"Fichier introuvable : {md_path}"

    try:
        contenu = Path(md_path).read_text(encoding="utf-8")
        lignes  = contenu.splitlines()
        log(f"   -> {len(lignes)} lignes")

        story          = []
        liste_en_cours = []
        i              = 0

        def vider_liste():
            if liste_en_cours:
                items = [
                    ListItem(Paragraph(t, sListe), leftIndent=20, bulletColor=BLEU)
                    for t in liste_en_cours
                ]
                story.append(ListFlowable(items, bulletType="bullet",
                                          leftIndent=10, bulletFontSize=8))
                story.append(Spacer(1, 4))
                liste_en_cours.clear()

        while i < len(lignes):
            ligne = lignes[i]

            if ligne.startswith("# ") and not ligne.startswith("## "):
                vider_liste()
                story.append(Spacer(1, 6))
                story.append(Paragraph(echapper(ligne[2:].strip()), sH1))
                story.append(HRFlowable(width="100%", thickness=2,
                                        color=BLEU, spaceAfter=6))

            elif ligne.startswith("## ") and not ligne.startswith("### "):
                vider_liste()
                story.append(Paragraph(echapper(ligne[3:].strip()), sH2))
                story.append(HRFlowable(width="100%", thickness=0.5,
                                        color=BLEU_CLAIR, spaceAfter=4))

            elif ligne.startswith("### "):
                vider_liste()
                story.append(Paragraph(echapper(ligne[4:].strip()), sH3))

            elif re.match(r'^-{3,}$', ligne.strip()):
                vider_liste()
                story.append(Spacer(1, 8))
                story.append(HRFlowable(width="100%", thickness=1,
                                        color=GRIS, spaceAfter=8))

            elif ligne.strip().startswith("```"):
                vider_liste()
                bloc = []
                i += 1
                while i < len(lignes) and not lignes[i].strip().startswith("```"):
                    bloc.append(lignes[i])
                    i += 1
                if bloc:
                    story.append(Preformatted("\n".join(bloc), sCode))

            elif ligne.strip().startswith("|") and "|" in ligne[1:]:
                vider_liste()
                rows_raw = []
                while i < len(lignes) and lignes[i].strip().startswith("|"):
                    cells = [c.strip() for c in lignes[i].strip().strip("|").split("|")]
                    rows_raw.append(cells)
                    i += 1
                rows = [r for r in rows_raw
                        if not all(re.match(r'^-+$', c) for c in r if c)]
                if rows:
                    nb_cols = max(len(r) for r in rows)
                    data    = [r + [""] * (nb_cols - len(r)) for r in rows]
                    col_w   = (A4[0] - 4 * cm) / nb_cols
                    t = Table(data, colWidths=[col_w] * nb_cols)
                    t.setStyle(TableStyle([
                        ("BACKGROUND",    (0, 0), (-1, 0),  BLEU),
                        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                        ("FONTSIZE",      (0, 0), (-1, -1), 9),
                        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
                        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, GRIS_CLAIR]),
                        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING",    (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 8))
                continue

            elif re.match(r'^\s*[\-\*] ', ligne):
                m = re.match(r'^\s*[\-\*] (.+)$', ligne)
                if m:
                    liste_en_cours.append(echapper(m.group(1).strip()))

            elif not ligne.strip():
                vider_liste()
                if story and not isinstance(story[-1], Spacer):
                    story.append(Spacer(1, 4))

            else:
                vider_liste()
                texte = echapper(ligne.strip())
                if texte:
                    story.append(Paragraph(texte, sPara))

            i += 1

        vider_liste()
        log(f"   -> {len(story)} éléments")

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.5 * cm,  bottomMargin=2.5 * cm,
            title=Path(md_path).stem,
        )
        doc.build(story)
        return True, output_path

    except Exception as e:
        return False, f"Erreur inattendue : {e}"


def convertir_lot(md_paths: list, output_dir: str, fusion: bool,
                  log=print) -> tuple[list, list]:
    """
    Convertit un lot de fichiers Markdown en PDF.
    Si fusion=True, fusionne tous les fichiers en un seul PDF.
    Retourne (succes, erreurs).
    """
    succes, erreurs = [], []
    if fusion:
        textes = []
        for p in md_paths:
            try:
                t = Path(p).read_text(encoding="utf-8")
                textes.append(f"---\n\n# {Path(p).stem}\n\n{t}")
            except Exception as e:
                erreurs.append((p, str(e)))
        if textes:
            tmp = os.path.join(output_dir, "_fusion_tmp.md")
            Path(tmp).write_text("\n\n".join(textes), encoding="utf-8")
            nom = os.path.join(output_dir, "fusion.pdf")
            log(f"Fusion de {len(textes)} fichiers...")
            ok, res = convertir(tmp, nom, log)
            os.remove(tmp)
            if ok:
                succes.append(res)
            else:
                erreurs.append(("fusion", res))
    else:
        for p in md_paths:
            log(f"\n--- {os.path.basename(p)} ---")
            nom = os.path.join(output_dir, Path(p).stem + ".pdf")
            ok, res = convertir(p, nom, log)
            if ok:
                succes.append(res)
            else:
                erreurs.append((p, res))
    return succes, erreurs
