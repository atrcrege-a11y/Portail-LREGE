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


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    print("\n" + "=" * 50)
    print("  SuiviMaster — Confirmations Master Grand Est")
    print("=" * 50)
    print("  http://localhost:5005\n")
    app.run(port=5005, debug=False)
