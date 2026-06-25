"""
app.py — SuiviGE : suivi des confirmations CDF individuel + équipes
Port 5006 — autonome de SelecGE
"""
import os, traceback
from flask import Flask, request, jsonify, render_template, send_file
import suivi as sv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "suivige-lrege-2025"
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024


@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r


@app.route("/")
def index():
    return render_template("index.html")


# ── Import ────────────────────────────────────────────────────────────────────

@app.route("/api/import/indiv", methods=["POST"])
def import_indiv():
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify({"erreur": "fichier requis"}), 400
    try:
        cles = sv.initialiser_indiv(fichier.read())
        return jsonify({"ok": True, "cles": cles, "nb": len(cles)})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/import/equipes", methods=["POST"])
def import_equipes():
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify({"erreur": "fichier requis"}), 400
    try:
        cles = sv.initialiser_equipes(fichier.read())
        return jsonify({"ok": True, "cles": cles, "nb": len(cles)})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/import/retour_indiv", methods=["POST"])
def import_retour_indiv():
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify({"erreur": "fichier requis"}), 400
    try:
        modifs = sv.importer_retour_indiv(fichier.read())
        return jsonify({"ok": True, "modifications": modifs})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/import/retour_equipes", methods=["POST"])
def import_retour_equipes():
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify({"erreur": "fichier requis"}), 400
    try:
        modifs = sv.importer_retour_equipes(fichier.read())
        return jsonify({"ok": True, "modifications": modifs})
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


# ── Lecture ───────────────────────────────────────────────────────────────────

@app.route("/api/suivis")
def liste_suivis():
    return jsonify(sv.get_tous_suivis())


@app.route("/api/suivi/<type_>/<path:params>/stats")
def stats(type_, params):
    arme, cat, genre = _parse_params(params)
    s = sv.get_stats(arme, cat, genre, type_)
    if not s:
        return jsonify({"erreur": "Suivi introuvable"}), 404
    return jsonify(s)


@app.route("/api/suivi/<type_>/<path:params>/detail")
def detail(type_, params):
    arme, cat, genre = _parse_params(params)
    d = sv.get_detail(arme, cat, genre, type_)
    if not d:
        return jsonify({"erreur": "Suivi introuvable"}), 404
    return jsonify(d)


@app.route("/api/suivi/indiv/<path:params>/remplacants")
def remplacants(params):
    arme, cat, genre = _parse_params(params)
    rems = sv.get_remplacants_a_appeler(arme, cat, genre)
    return jsonify(rems)


@app.route("/api/suivi/<type_>/<path:params>/audit")
def audit(type_, params):
    arme, cat, genre = _parse_params(params)
    return jsonify(sv.get_audit(arme, cat, genre, type_))


# ── Actions ───────────────────────────────────────────────────────────────────

@app.route("/api/suivi/indiv/<path:params>/confirmation", methods=["POST"])
def conf_tireur(params):
    arme, cat, genre = _parse_params(params)
    d = request.get_json() or {}
    try:
        sv.maj_confirmation_tireur(arme, cat, genre,
            d["nom"], d["prenom"], d["confirmation"], d.get("note", ""))
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/equipe/<path:params>/confirmation", methods=["POST"])
def conf_equipe(params):
    arme, cat, genre = _parse_params(params)
    d = request.get_json() or {}
    try:
        sv.maj_confirmation_equipe(arme, cat, genre,
            d["rang"], d["confirmation"], d.get("note", ""),
            d.get("composition"))
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/equipe/<path:params>/composition", methods=["POST"])
def composition_equipe(params):
    arme, cat, genre = _parse_params(params)
    d = request.get_json() or {}
    try:
        sv.maj_composition_equipe(arme, cat, genre, d["rang"], d["composition"])
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<type_>/<path:params>/supprimer", methods=["POST"])
def supprimer(type_, params):
    arme, cat, genre = _parse_params(params)
    sv.supprimer(arme, cat, genre, type_)
    return jsonify({"ok": True})


@app.route("/api/import/plateforme", methods=["POST"])
def import_plateforme():
    """Charge le suivi INDIVIDUEL depuis la plateforme de confirmation en ligne."""
    body = request.get_json(silent=True) or {}
    try:
        res = sv.importer_depuis_plateforme(
            base_url=body.get("url") or None,
            token=body.get("token") or None,
        )
        return jsonify(res)
    except ValueError as e:
        return jsonify({"erreur": str(e)}), 400
    except Exception as e:
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse_params(params):
    """Décode 'Épée/Seniors/H' ou 'Fleuret/M13/D' depuis l'URL."""
    parts = params.split("/")
    arme  = parts[0].replace("Epee", "Épée").replace("_", " ") if parts else ""
    cat   = parts[1] if len(parts) > 1 else ""
    genre = parts[2] if len(parts) > 2 else ""
    return arme, cat, genre


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    print("\n" + "=" * 50)
    print("  SuiviGE — Confirmations CDF Grand Est")
    print("=" * 50)
    print("  http://localhost:5006\n")
    app.run(port=5006, debug=False)
