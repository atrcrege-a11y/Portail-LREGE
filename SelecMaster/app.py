"""
app.py — SelecMaster : sélection Master Grand Est M11/M13 — Port 5004
"""
import os
from flask import Flask, request, jsonify, render_template, send_file
from parser import parser_html
from selection import calculer_selection, enrichir_alertes_m11
from generateur import generer_excel

app = Flask(__name__)
app.secret_key = "selecmaster-lrege-2025"

_cache = {}  # clés : "H_M11", "H_M13", "D_M11", "D_M13"
_params = {}  # paramètres globaux : arme, territoire_organisateur, bonus_organisateur


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    genre     = request.form.get("genre")
    categorie = request.form.get("categorie")
    territoire_saisi    = request.form.get("territoire", "")
    territoire_orga     = request.form.get("territoire_organisateur", "")
    bonus_organisateur  = request.form.get("bonus_organisateur") == "true"
    fichier   = request.files.get("fichier")

    if not fichier or not genre or not categorie:
        return jsonify({"erreur": "Fichier, genre et catégorie requis."}), 400

    try:
        donnees = parser_html(fichier.read())
    except Exception as e:
        return jsonify({"erreur": f"Erreur de lecture : {str(e)}"}), 400

    # Vérification cohérence genre
    if donnees.get("genre") and donnees["genre"] != genre:
        return jsonify({
            "erreur": f"Fichier détecté comme {donnees['genre']} mais slot sélectionné : {genre}."
        }), 400

    # Vérification cohérence catégorie
    if donnees.get("categorie") and donnees["categorie"] != categorie:
        return jsonify({
            "erreur": f"Fichier détecté comme {donnees['categorie']} mais slot sélectionné : {categorie}."
        }), 400

    # Alerte incohérence territoire (parseur prime)
    territoire_detecte = donnees.get("territoire", "")
    alerte_territoire = None
    if territoire_saisi and territoire_detecte and \
       territoire_saisi.lower() != territoire_detecte.lower():
        alerte_territoire = (
            f"Territoire détecté dans le fichier : « {territoire_detecte} » "
            f"(vous aviez sélectionné « {territoire_saisi} »). "
            f"Le territoire du fichier est utilisé."
        )

    selection = calculer_selection(donnees, bonus_organisateur)
    cle = f"{genre}_{categorie}"
    _cache[cle] = selection
    _params[cle] = {"territoire_orga": territoire_orga, "bonus": bonus_organisateur}

    _tenter_croisement_m11(genre)

    return jsonify({**_resume(_cache[cle], genre, categorie),
                    "alerte_territoire": alerte_territoire})


def _tenter_croisement_m11(genre):
    cle_m13, cle_m11 = f"{genre}_M13", f"{genre}_M11"
    if cle_m13 in _cache and cle_m11 in _cache:
        enrichir_alertes_m11(_cache[cle_m13], _cache[cle_m11]["tireurs"])


def _resume(sel, genre, categorie):
    nb_sel  = sum(1 for t in sel["tireurs"] if t["statut"] == "selectionne")
    nb_rem  = sum(1 for t in sel["tireurs"] if t["statut"] == "remplacant")
    nb_non  = sum(1 for t in sel["tireurs"] if t["statut"] == "non_selectionnable")
    nb_dbl  = sum(1 for t in sel["tireurs"] if t.get("alerte_m11") == "double")
    nb_m13o = sum(1 for t in sel["tireurs"] if t.get("alerte_m11") == "m13only")
    return {
        "ok": True,
        "arme": sel.get("arme"),
        "categorie": sel.get("categorie"),
        "territoire": sel.get("territoire"),
        "genre": genre,
        "quota": sel.get("quota"),
        "bonus_organisateur": sel.get("bonus_organisateur"),
        "condition_participations": sel.get("condition_participations"),
        "nb_selectionnes": nb_sel,
        "nb_remplacants": nb_rem,
        "nb_non_selectionnables": nb_non,
        "nb_double_qualification": nb_dbl,
        "nb_m13_seulement": nb_m13o,
        "tireurs": sel["tireurs"],
    }


@app.route("/api/recalculer", methods=["POST"])
def recalculer():
    """Recalcule toutes les sélections après changement du bonus organisateur."""
    data = request.get_json() or {}
    bonus = data.get("bonus_organisateur", False)

    for cle, sel in list(_cache.items()):
        _cache[cle] = calculer_selection(sel, bonus)

    for genre in ['H', 'D']:
        _tenter_croisement_m11(genre)

    resultats = {}
    for cle, sel in _cache.items():
        genre, cat = cle.split("_")
        resultats[cle] = _resume(sel, genre, cat)

    return jsonify(resultats)


@app.route("/api/generer", methods=["POST"])
def generer():
    data = request.get_json() or {}
    categorie = data.get("categorie")
    date_confirmation = data.get("date_confirmation", "")
    date_extranet = data.get("date_extranet", "")

    sel_h = _cache.get(f"H_{categorie}")
    sel_d = _cache.get(f"D_{categorie}")

    if not sel_h and not sel_d:
        return jsonify({"erreur": f"Aucun fichier {categorie} importé."}), 400

    ref = sel_h or sel_d
    arme = ref.get("arme", "arme")
    territoire = ref.get("territoire", "")

    try:
        buf = generer_excel(sel_h or {}, sel_d or {}, date_confirmation=date_confirmation, date_extranet=date_extranet)
    except Exception as e:
        import traceback
        return jsonify({"erreur": f"Erreur génération : {str(e)}", "detail": traceback.format_exc()}), 500

    nom = f"Selection_Master_{arme}_{categorie}_{territoire}.xlsx".replace(" ", "_")
    sorties_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
    os.makedirs(sorties_dir, exist_ok=True)
    with open(os.path.join(sorties_dir, nom), "wb") as f:
        f.write(buf.read())
    buf.seek(0)

    return send_file(buf, as_attachment=True, download_name=nom,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/api/reset", methods=["POST"])
def reset():
    _cache.clear()
    _params.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app.run(port=5004, debug=False)
