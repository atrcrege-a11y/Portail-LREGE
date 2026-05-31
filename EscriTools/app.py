"""
app.py — EscriTools v2.0 Flask
Lance : python app.py  |  http://localhost:5002
"""
import os
import tempfile
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR  = tempfile.mkdtemp(prefix="escritools_")
OUTPUT_DIR  = os.path.join(BASE_DIR, "sorties")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _save_upload(file, ext: str) -> str:
    """Sauvegarde un fichier uploadé et retourne son chemin."""
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    file.save(path)
    return path


def _output_path(nom: str) -> str:
    return os.path.join(OUTPUT_DIR, nom)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── BellePoule → FFF ─────────────────────────────────────────────────────────

@app.route("/api/bellepoule/convertir", methods=["POST"])
def api_bellepoule_convertir():
    """
    Reçoit : pdf (fichier), csv (fichier optionnel)
    Retourne : fichier .fff en téléchargement
    """
    from core.bellepoule_fff import convertir

    if "pdf" not in request.files:
        return jsonify({"error": "Fichier PDF manquant"}), 400

    pdf_file = request.files["pdf"]
    csv_file = request.files.get("csv")

    pdf_path = _save_upload(pdf_file, ".pdf")
    csv_path = _save_upload(csv_file, ".csv") if csv_file and csv_file.filename else None
    out_name = Path(pdf_file.filename).stem + ".fff"
    out_path = _output_path(out_name)

    logs = []
    ok, res = convertir(pdf_path, out_path, log=logs.append, csv_path=csv_path)

    if ok:
        return jsonify({"ok": True, "filename": out_name, "logs": logs})
    else:
        return jsonify({"error": res, "logs": logs}), 422


@app.route("/api/bellepoule/telecharger/<filename>")
def api_bellepoule_telecharger(filename):
    path = _output_path(filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── PDF → Markdown ───────────────────────────────────────────────────────────

@app.route("/api/pdf2md/convertir", methods=["POST"])
def api_pdf2md_convertir():
    """
    Reçoit : pdf[] (un ou plusieurs fichiers), fusion (bool)
    Retourne : JSON avec liste de fichiers générés
    """
    from core.pdf_markdown import convertir as convertir_md

    files = request.files.getlist("pdf")
    if not files or not files[0].filename:
        return jsonify({"error": "Aucun fichier PDF fourni"}), 400

    fusion = request.form.get("fusion", "false").lower() == "true"
    resultats = []
    erreurs = []

    if fusion:
        blocs = []
        for f in files:
            pdf_path = _save_upload(f, ".pdf")
            logs = []
            try:
                contenu = convertir_md(pdf_path, log=logs.append)
                if contenu.strip():
                    blocs.append(f"---\n\n# {Path(f.filename).stem}\n\n{contenu}")
                else:
                    erreurs.append({"fichier": f.filename, "erreur": "Aucun texte extrait"})
            except Exception as e:
                erreurs.append({"fichier": f.filename, "erreur": str(e)})
        if blocs:
            nom = "fusion.md"
            out_path = _output_path(nom)
            Path(out_path).write_text("\n\n".join(blocs), encoding="utf-8")
            resultats.append({"fichier": nom, "url": f"/api/pdf2md/telecharger/{nom}"})
    else:
        for f in files:
            pdf_path = _save_upload(f, ".pdf")
            logs = []
            try:
                contenu = convertir_md(pdf_path, log=logs.append)
                if contenu.strip():
                    nom = Path(f.filename).stem + ".md"
                    out_path = _output_path(nom)
                    Path(out_path).write_text(contenu, encoding="utf-8")
                    resultats.append({"fichier": nom, "url": f"/api/pdf2md/telecharger/{nom}", "logs": logs})
                else:
                    erreurs.append({"fichier": f.filename, "erreur": "Aucun texte extrait (PDF scanné ?)"})
            except Exception as e:
                erreurs.append({"fichier": f.filename, "erreur": str(e)})

    return jsonify({"ok": bool(resultats), "resultats": resultats, "erreurs": erreurs})


@app.route("/api/pdf2md/telecharger/<filename>")
def api_pdf2md_telecharger(filename):
    path = _output_path(filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── Markdown → PDF ───────────────────────────────────────────────────────────

@app.route("/api/md2pdf/convertir", methods=["POST"])
def api_md2pdf_convertir():
    """
    Reçoit : md[] (un ou plusieurs fichiers), fusion (bool)
    Retourne : JSON avec liste de fichiers générés
    """
    from core.markdown_pdf import convertir as convertir_pdf, convertir_lot

    files = request.files.getlist("md")
    if not files or not files[0].filename:
        return jsonify({"error": "Aucun fichier Markdown fourni"}), 400

    fusion = request.form.get("fusion", "false").lower() == "true"
    md_paths = [(_save_upload(f, ".md"), f.filename) for f in files]

    if len(md_paths) == 1 and not fusion:
        path, orig = md_paths[0]
        nom = Path(orig).stem + ".pdf"
        out_path = _output_path(nom)
        logs = []
        ok, res = convertir_pdf(path, out_path, log=logs.append)
        if ok:
            return jsonify({"ok": True, "resultats": [{"fichier": nom, "url": f"/api/md2pdf/telecharger/{nom}"}], "erreurs": [], "logs": logs})
        else:
            return jsonify({"error": res, "logs": logs}), 422
    else:
        succes, erreurs = convertir_lot([p for p, _ in md_paths], OUTPUT_DIR, fusion)
        resultats = [{"fichier": os.path.basename(p), "url": f"/api/md2pdf/telecharger/{os.path.basename(p)}"} for p in succes]
        errs = [{"fichier": os.path.basename(p), "erreur": e} for p, e in erreurs]
        return jsonify({"ok": bool(resultats), "resultats": resultats, "erreurs": errs})


@app.route("/api/md2pdf/telecharger/<filename>")
def api_md2pdf_telecharger(filename):
    path = _output_path(filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── Renommage XML ↔ cotcot ────────────────────────────────────────────────────

@app.route("/api/renommage/renommer", methods=["POST"])
def api_renommage_renommer():
    """
    Reçoit : files[] + sens ("xml2cot" ou "cot2xml")
    Renomme les fichiers sur le serveur et retourne les résultats.
    Note : fonctionne sur les fichiers déposés temporairement.
    """
    from core.renommage import xml_vers_cotcot, cotcot_vers_xml

    files = request.files.getlist("files")
    sens  = request.form.get("sens", "xml2cot")

    if not files or not files[0].filename:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    ext_src = ".xml" if sens == "xml2cot" else ".cotcot"
    ext_dst = ".cotcot" if sens == "xml2cot" else ".xml"

    chemins, resultats = [], []
    for f in files:
        if f.filename.lower().endswith(ext_src):
            path = _save_upload(f, ext_src)
            chemins.append((path, f.filename))

    if not chemins:
        return jsonify({"error": f"Aucun fichier {ext_src} dans la sélection"}), 400

    succes = []
    for path, orig in chemins:
        dst = path[:-len(ext_src)] + ext_dst
        try:
            os.rename(path, dst)
            nom_sortie = Path(orig).stem + ext_dst
            out_path = _output_path(nom_sortie)
            os.rename(dst, out_path)
            succes.append({"original": orig, "renomme": nom_sortie,
                           "url": f"/api/renommage/telecharger/{nom_sortie}"})
        except Exception as e:
            resultats.append({"original": orig, "erreur": str(e)})

    return jsonify({"ok": bool(succes), "succes": succes, "erreurs": resultats})


@app.route("/api/renommage/telecharger/<filename>")
def api_renommage_telecharger(filename):
    path = _output_path(filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── Équipe → Individuel ───────────────────────────────────────────────────────

@app.route("/api/equipe_indiv/convertir", methods=["POST"])
def api_equipe_indiv_convertir():
    """
    Reçoit : files[] (PDF ou .md), + params compétition en form-data
    Retourne : JSON avec liste de fichiers .fff générés
    """
    from core.equipe_individuel import traiter_fichier

    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    params = {
        "date_comp": request.form.get("date", ""),
        "arme":      request.form.get("arme", "Epee"),
        "sexe":      request.form.get("sexe", "M"),
        "categorie": request.form.get("categorie", "M13"),
        "nom_comp":  request.form.get("nom_comp", ""),
        "lieu":      request.form.get("lieu", ""),
    }

    manquants = [k for k, v in params.items() if not v.strip()]
    if manquants:
        return jsonify({"error": f"Champs manquants : {', '.join(manquants)}"}), 400

    resultats, erreurs = [], []
    for f in files:
        ext  = Path(f.filename).suffix.lower()
        path = _save_upload(f, ext)
        nom  = Path(f.filename).stem + "_indiv.fff"
        out  = _output_path(nom)
        logs = []
        ok, res = traiter_fichier(path, **params, output_path=out, log=logs.append)
        if ok:
            resultats.append({"fichier": nom, "url": f"/api/equipe_indiv/telecharger/{nom}", "logs": logs})
        else:
            erreurs.append({"fichier": f.filename, "erreur": res, "logs": logs})

    return jsonify({"ok": bool(resultats), "resultats": resultats, "erreurs": erreurs})


@app.route("/api/equipe_indiv/telecharger/<filename>")
def api_equipe_indiv_telecharger(filename):
    path = _output_path(filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  EscriTools v2.0")
    print("=" * 50)
    print("  http://localhost:5002")
    print("  Ctrl+C pour quitter\n")
    app.run(debug=False, port=5002, use_reloader=True, reloader_type="stat")
