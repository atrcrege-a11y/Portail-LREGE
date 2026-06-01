"""
app.py — SuiviMaster : suivi des confirmations Master Grand Est
Port 5005 — autonome de SelecMaster
"""
import os, sys, traceback
from flask import Flask, request, jsonify, render_template, send_file
import suivi as sv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "suivimaster-lrege-2025"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/")
def index():
    return render_template("index.html")


# ── Import Excel SelecMaster ──────────────────────────────────────────────────

@app.route("/api/import_selection", methods=["POST"])
def import_selection():
    """Import d'un Excel généré par SelecMaster pour initialiser le suivi."""
    territoire              = request.form.get("territoire", "")
    territoire_organisateur = request.form.get("territoire_organisateur", "")
    fichier                 = request.files.get("fichier")

    if not fichier or not territoire:
        return jsonify({"erreur": "fichier et territoire requis"}), 400
    if not territoire_organisateur:
        return jsonify({"erreur": "territoire organisateur requis"}), 400

    try:
        result = sv.initialiser_depuis_excel(
            fichier.read(), territoire, territoire_organisateur
        )
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/import_retour", methods=["POST"])
def import_retour():
    """Import d'un Excel retourné par un club avec confirmations remplies."""
    arme       = request.form.get("arme", "")
    categorie  = request.form.get("categorie", "")
    territoire = request.form.get("territoire", "")
    fichier    = request.files.get("fichier")

    if not all([arme, categorie, territoire, fichier]):
        return jsonify({"erreur": "arme, categorie, territoire, fichier requis"}), 400

    try:
        modifs = sv.importer_excel_retour(arme, categorie, territoire, fichier.read())
        return jsonify({"ok": True, "modifications": modifs})
    except KeyError as e:
        return jsonify({"erreur": str(e)}), 400
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


# ── Liste et stats ────────────────────────────────────────────────────────────

@app.route("/api/suivis")
def liste_suivis():
    return jsonify(sv.get_tous_suivis())


@app.route("/api/suivi/<arme>/<categorie>/stats")
def stats(arme, categorie):
    arme = _decode_arme(arme)
    s = sv.get_stats(arme, categorie)
    if not s:
        return jsonify({"erreur": "Suivi introuvable"}), 404
    return jsonify(s)


@app.route("/api/suivi/<arme>/<categorie>/detail")
def detail(arme, categorie):
    arme = _decode_arme(arme)
    d = sv.get_detail(arme, categorie)
    if not d:
        return jsonify({"erreur": "Suivi introuvable"}), 404
    return jsonify(d)


@app.route("/api/suivi/<arme>/<categorie>/remplacants")
def remplacants(arme, categorie):
    arme = _decode_arme(arme)
    return jsonify(sv.get_remplacants_a_appeler(arme, categorie))


@app.route("/api/suivi/<arme>/<categorie>/audit")
def audit(arme, categorie):
    arme = _decode_arme(arme)
    return jsonify(sv.get_audit(arme, categorie))


# ── Actions ───────────────────────────────────────────────────────────────────

@app.route("/api/suivi/<arme>/<categorie>/confirmation", methods=["POST"])
def confirmation(arme, categorie):
    arme = _decode_arme(arme)
    d = request.get_json() or {}
    try:
        sv.mettre_a_jour_confirmation(
            arme, categorie,
            d["territoire"], d["nom"], d["prenom"], d["genre"],
            d["confirmation"], d.get("note", "")
        )
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<arme>/<categorie>/appel", methods=["POST"])
def appel(arme, categorie):
    arme = _decode_arme(arme)
    d = request.get_json() or {}
    try:
        sv.marquer_appele(
            arme, categorie,
            d["territoire"], d["nom"], d["prenom"], d["genre"],
            d.get("appele", True)
        )
        return jsonify({"ok": True})
    except KeyError as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<arme>/<categorie>/supprimer", methods=["POST"])
def supprimer(arme, categorie):
    arme = _decode_arme(arme)
    sv.supprimer_suivi(arme, categorie)
    return jsonify({"ok": True})


# ── Helper ────────────────────────────────────────────────────────────────────

def _decode_arme(arme):
    """Convertit l'arme URL-encodée en nom complet."""
    return arme.replace("Epee", "Épée").replace("_", " ")


# ── Routes arbitres ──────────────────────────────────────────────────────────

@app.route("/api/arbitres")
def arbitres_all():
    return jsonify(sv.get_arbitres_serialisable())


@app.route("/api/arbitres/<arme>")
def arbitres_arme(arme):
    arme = _decode_arme(arme)
    try:
        return jsonify(sv.get_arbitres_serialisable(arme))
    except ValueError as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/arbitres/stats")
def arbitres_stats():
    return jsonify(sv.get_stats_arbitres())


@app.route("/api/arbitres/ajouter", methods=["POST"])
def arbitres_ajouter():
    d = request.get_json() or {}
    try:
        a = sv.ajouter_arbitre(
            _decode_arme(d.get("arme", "")),
            d.get("nom", ""), d.get("prenom", ""),
            d.get("niveau", ""), d.get("club", ""),
            d.get("territoire", ""), d.get("note", "")
        )
        return jsonify({"ok": True, "arbitre": {**a,
            "created_at": a["created_at"].strftime("%d/%m/%Y %H:%M"),
            "updated_at": a["updated_at"].strftime("%d/%m/%Y %H:%M")}})
    except (ValueError, KeyError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/arbitres/<arme>/<arb_id>/statut", methods=["POST"])
def arbitres_statut(arme, arb_id):
    arme = _decode_arme(arme)
    d = request.get_json() or {}
    try:
        sv.maj_statut_arbitre(arme, arb_id, d.get("statut", ""), d.get("note", ""))
        return jsonify({"ok": True})
    except (ValueError, KeyError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/arbitres/<arme>/<arb_id>/supprimer", methods=["POST"])
def arbitres_supprimer(arme, arb_id):
    arme = _decode_arme(arme)
    try:
        sv.supprimer_arbitre(arme, arb_id)
        return jsonify({"ok": True})
    except KeyError as e:
        return jsonify({"erreur": str(e)}), 404


@app.route("/api/arbitres/<arme>/supprimer_tous", methods=["POST"])
def arbitres_supprimer_tous(arme):
    arme = _decode_arme(arme)
    sv.supprimer_tous_arbitres(arme)
    return jsonify({"ok": True})


@app.route("/api/arbitres/import_excel", methods=["POST"])
def arbitres_import_excel():
    arme       = _decode_arme(request.form.get("arme", ""))
    territoire = request.form.get("territoire", "")
    fichier    = request.files.get("fichier")
    if not all([arme, territoire, fichier]):
        return jsonify({"erreur": "arme, territoire, fichier requis"}), 400
    try:
        result = sv.importer_arbitres_excel(arme, territoire, fichier.read())
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/arbitres/export_pdf")
def arbitres_export_pdf():
    """Génère un PDF avec retenus + libérés pour les 3 armes."""
    try:
        pdf_bytes = generer_pdf_arbitres()
        import io as _io
        buf = _io.BytesIO(pdf_bytes)
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name="Arbitres_Master_Grand_Est.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/recap")
def recap():
    """Récap des confirmés (sélectionnés oui + remplaçants appelés oui) par arme/catégorie/genre."""
    suivis = sv.get_tous_suivis()
    result = {}
    for cle in suivis:
        arme, categorie = cle.split("|", 1)
        detail = sv.get_detail(arme, categorie)
        if not detail:
            continue
        entry = {"arme": arme, "categorie": categorie, "H": [], "D": []}
        for tireurs in detail["territoires"].values():
            for t in tireurs:
                confirme = (
                    (t["statut"] == "selectionne" and t["confirmation"] == "oui") or
                    (t["statut"] == "remplacant"  and t["appele"]      and t["confirmation"] == "oui")
                )
                if confirme:
                    entry[t["genre"]].append({
                        "nom":        t["nom"],
                        "prenom":     t["prenom"],
                        "club":       t["club"],
                        "territoire": t["territoire"],
                        "remplacant": t["statut"] == "remplacant",
                    })
        result[cle] = entry
    return jsonify(result)


def generer_pdf_arbitres():
    """Génère le PDF arbitres avec reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io as _io

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles  = getSampleStyleSheet()
    story   = []

    COULEURS_ARME = {
        "Épée":    colors.HexColor("#1E6B3A"),
        "Fleuret": colors.HexColor("#1B3F7A"),
        "Sabre":   colors.HexColor("#7B0C0C"),
    }
    C_RETENU  = colors.HexColor("#E2EFDA")
    C_LIBERE  = colors.HexColor("#FFCCCC")
    C_PROPOSE = colors.HexColor("#FFF2CC")

    titre_style = ParagraphStyle("titre",
        parent=styles["Title"], fontSize=16, spaceAfter=4,
        textColor=colors.HexColor("#1F3864"))
    sous_titre_style = ParagraphStyle("sous",
        parent=styles["Normal"], fontSize=9, spaceAfter=12,
        textColor=colors.grey)
    arme_style = ParagraphStyle("arme",
        parent=styles["Heading1"], fontSize=13, spaceBefore=16, spaceAfter=6,
        textColor=colors.white)
    section_style = ParagraphStyle("section",
        parent=styles["Heading2"], fontSize=10, spaceBefore=8, spaceAfter=4,
        textColor=colors.HexColor("#1F3864"))

    import datetime as _dt
    story.append(Paragraph("LREGE Grand Est — Master M11/M13", titre_style))
    story.append(Paragraph(
        f"Liste des arbitres — Généré le {_dt.date.today().strftime('%d/%m/%Y')}",
        sous_titre_style))
    story.append(Spacer(1, 0.3*cm))

    for arme in ["Épée", "Fleuret", "Sabre"]:
        arbs  = sv.get_arbitres(arme)
        coul  = COULEURS_ARME[arme]
        stats = sv.get_stats_arbitres()[arme]

        # Titre arme (fond coloré)
        arme_data = [[Paragraph(
            f"  {arme}  —  {stats['retenu']}/{sv.MAX_RETENUS} retenus  |  "
            f"{stats['propose']} proposé(s)  |  {stats['libere']} libéré(s)",
            ParagraphStyle("ah", parent=styles["Normal"],
                           fontSize=12, textColor=colors.white, fontName="Helvetica-Bold"))]]
        arme_tbl = Table(arme_data, colWidths=[17*cm])
        arme_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), coul),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(arme_tbl)
        story.append(Spacer(1, 0.2*cm))

        # En-tête colonnes
        headers = ["Nom", "Prénom", "Niveau", "Club", "Territoire", "Statut"]
        col_w   = [3.5*cm, 3*cm, 3.5*cm, 3*cm, 2.5*cm, 2*cm]

        for statut_label, statut_cle, bg in [
            ("✓ RETENUS",  "retenu",  C_RETENU),
            ("✗ LIBÉRÉS",  "libere",  C_LIBERE),
            ("⏳ PROPOSÉS", "propose", C_PROPOSE),
        ]:
            groupe = [a for a in arbs if a["statut"] == statut_cle]
            if not groupe:
                continue

            story.append(Paragraph(f"{statut_label} ({len(groupe)})", section_style))

            rows = [headers] + [
                [a["nom"], a["prenom"], a["niveau"] or "—",
                 a["club"] or "—", a["territoire"] or "—",
                 a["note"] or ""]
                for a in groupe
            ]
            tbl = Table(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#DEEAF1")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("BACKGROUND",    (0, 1), (-1, -1), bg),
                ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.15*cm))

        story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    return buf.getvalue()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    print("\n" + "=" * 50)
    print("  SuiviMaster — Confirmations Master Grand Est")
    print("=" * 50)
    print("  http://localhost:5005\n")
    app.run(port=5005, debug=False)
