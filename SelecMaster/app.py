"""
app.py — SelecMaster : sélection Master Grand Est M11/M13 — Port 5004
"""
import os
from flask import Flask, request, jsonify, render_template, send_file
from parser import parser_html, ParseurError
from selection import calculer_selection, enrichir_alertes_m11
from generateur import generer_excel
import suivi as suivi_module

app = Flask(__name__)
app.secret_key = "selecmaster-lrege-2025"

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options(path):
    return "", 204

import pickle, pathlib

_cache = {}  # clés : "H_M11", "H_M13", "D_M11", "D_M13"
_params = {}
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_selecmaster.pkl")


def _sauvegarder_cache():
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump(_cache, f)
    except Exception:
        pass


def _charger_cache():
    global _cache
    try:
        if os.path.isfile(_CACHE_FILE):
            with open(_CACHE_FILE, "rb") as f:
                _cache.update(pickle.load(f))
    except Exception:
        pass


_charger_cache()


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
    except ParseurError as e:
        msg = str(e.args[0]) if e.args else str(e)
        return jsonify({"erreur": msg, "hint": e.hint}), 400
    except Exception as e:
        return jsonify({"erreur": f"Erreur inattendue : {str(e)}"}), 400

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
    print(f"[UPLOAD] cle={cle} | cache keys={list(_cache.keys())}")
    _params[cle] = {"territoire_orga": territoire_orga, "bonus": bonus_organisateur}

    _tenter_croisement_m11(genre)
    _sauvegarder_cache()

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

    print(f"[GENERER] categorie={categorie} | cache keys={list(_cache.keys())} | sel_h={sel_h is not None} | sel_d={sel_d is not None}")

    if not sel_h and not sel_d:
        return jsonify({"erreur": f"Aucun fichier {categorie} importé. Cache: {list(_cache.keys())}"}), 400

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
    chemin = os.path.join(sorties_dir, nom)
    with open(chemin, "wb") as f:
        f.write(buf.read())

    return jsonify({"ok": True, "fichier": nom})


@app.route("/api/telecharger/<nom>")
def telecharger(nom):
    sorties_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
    chemin = os.path.join(sorties_dir, nom)
    if not os.path.isfile(chemin):
        return jsonify({"erreur": "Fichier introuvable"}), 404
    return send_file(chemin, as_attachment=True, download_name=nom,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── Routes suivi ─────────────────────────────────────────────────────────────

@app.route("/api/suivi/init", methods=["POST"])
def suivi_init():
    """Initialise le suivi depuis le cache courant."""
    data = request.get_json() or {}
    arme     = data.get("arme")
    categorie = data.get("categorie")
    territoire = data.get("territoire")
    if not all([arme, categorie, territoire]):
        return jsonify({"erreur": "arme, categorie, territoire requis"}), 400
    sel_h = _cache.get(f"H_{categorie}")
    sel_d = _cache.get(f"D_{categorie}")
    if not sel_h and not sel_d:
        return jsonify({"erreur": f"Aucune sélection {categorie} en cache"}), 400
    tireurs_h = sel_h.get("tireurs", []) if sel_h else []
    tireurs_d = sel_d.get("tireurs", []) if sel_d else []
    orga = data.get("territoire_organisateur", "")
    suivi_module.initialiser_suivi(arme, categorie, territoire, tireurs_h, tireurs_d)
    # Stocker l'organisateur dans le suivi
    cle = f"{arme}_{categorie}"
    if cle in suivi_module._suivi and orga:
        suivi_module._suivi[cle]["territoire_organisateur"] = orga
        suivi_module._sauvegarder()
    return jsonify({"ok": True})


@app.route("/api/suivi/liste")
def suivi_liste():
    return jsonify(suivi_module.get_tous_suivis())


@app.route("/api/suivi/<arme>/<categorie>")
def suivi_get(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    s = suivi_module.get_stats(arme, categorie)
    if not s:
        return jsonify({"erreur": "Aucun suivi trouvé"}), 404
    return jsonify(s)


@app.route("/api/suivi/<arme>/<categorie>/detail")
def suivi_detail(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    s = suivi_module.get_suivi(arme, categorie)
    if not s:
        return jsonify({"erreur": "Aucun suivi trouvé"}), 404
    # Sérialiser les datetimes
    import copy
    s2 = copy.deepcopy(s)
    for t_data in s2["territoires"].values():
        for t in t_data["tireurs"]:
            if t.get("confirmation_at"):
                t["confirmation_at"] = t["confirmation_at"].strftime("%d/%m/%Y %H:%M")
    s2["created_at"] = s2["created_at"].strftime("%d/%m/%Y %H:%M")
    s2["updated_at"] = s2["updated_at"].strftime("%d/%m/%Y %H:%M")
    s2["audit"] = suivi_module.get_audit(arme, categorie)
    return jsonify(s2)


@app.route("/api/suivi/<arme>/<categorie>/confirmation", methods=["POST"])
def suivi_confirmation(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    data = request.get_json() or {}
    try:
        suivi_module.mettre_a_jour_confirmation(
            arme, categorie,
            data["territoire"], data["nom"], data["prenom"],
            data["genre"], data["confirmation"],
            data.get("note", "")
        )
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<arme>/<categorie>/appel", methods=["POST"])
def suivi_appel(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    data = request.get_json() or {}
    try:
        suivi_module.marquer_appele(
            arme, categorie,
            data["territoire"], data["nom"], data["prenom"],
            data["genre"], data.get("appele", True)
        )
        return jsonify({"ok": True})
    except KeyError as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<arme>/<categorie>/arbitre", methods=["POST"])
def suivi_arbitre(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    data = request.get_json() or {}
    try:
        suivi_module.mettre_a_jour_arbitre(
            arme, categorie,
            data["territoire"], data.get("nom",""), data.get("prenom",""),
            data.get("niveau",""), data.get("club",""),
            data.get("valide", False), data.get("note","")
        )
        return jsonify({"ok": True})
    except (KeyError, ValueError) as e:
        return jsonify({"erreur": str(e)}), 400


@app.route("/api/suivi/<arme>/<categorie>/import_excel", methods=["POST"])
def suivi_import_excel(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    territoire = request.form.get("territoire")
    fichier    = request.files.get("fichier")
    if not fichier or not territoire:
        return jsonify({"erreur": "fichier et territoire requis"}), 400
    try:
        modifs = suivi_module.importer_excel_retour(arme, categorie, territoire, fichier.read())
        return jsonify({"ok": True, "modifications": modifs})
    except Exception as e:
        import traceback
        return jsonify({"erreur": str(e), "detail": traceback.format_exc()}), 500


@app.route("/api/suivi/<arme>/<categorie>/remplacants")
def suivi_remplacants(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    orga = request.args.get("organisateur", "")
    return jsonify(suivi_module.get_remplacants_a_appeler(arme, categorie, orga or None))


@app.route("/api/suivi/<arme>/<categorie>/audit")
def suivi_audit(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    return jsonify(suivi_module.get_audit(arme, categorie))


@app.route("/api/suivi/<arme>/<categorie>/supprimer", methods=["POST"])
def suivi_supprimer(arme, categorie):
    arme = arme.replace("_", " ").replace("Epee", "Épée")
    suivi_module.supprimer_suivi(arme, categorie)
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
def reset():
    _cache.clear()
    _params.clear()
    try:
        if os.path.isfile(_CACHE_FILE):
            os.remove(_CACHE_FILE)
    except Exception:
        pass
    return jsonify({"ok": True})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app.run(port=5004, debug=False)
