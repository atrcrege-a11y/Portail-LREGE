"""
routes/misc.py — Routes utilitaires : index, config, favicon.
"""
import os
import json

from flask import Blueprint, request, jsonify, render_template, current_app

from services.construction import CATEGORIES, ARMES, GENRES, get_saison
from crege_app.core.arbitrage import export_arbitrage_json

bp = Blueprint('misc', __name__)


@bp.route('/favicon.ico')
def favicon():
    return '', 204


@bp.route('/')
def index():
    return render_template('index.html', categories=CATEGORIES, armes=ARMES,
                            genres=GENRES, saison=get_saison())


@bp.route('/api/config', methods=['GET'])
def get_config():
    cfg_path = current_app.config['CONFIG_PATH']
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"dossier_sortie": "./sorties", "selections": []})


@bp.route('/api/config', methods=['POST'])
def save_config():
    cfg_path = current_app.config['CONFIG_PATH']
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(request.json, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "ok"})


@bp.route('/api/export/arbitrage', methods=['GET', 'POST'])
def export_arbitrage():
    """Export du bloc arbitrage (contrat plateforme de confirmation, Specs 10.2).

    Source de l'arbitrage_config :
      - POST JSON {arbitrage_config: {...}} : config fournie directement, ou
      - GET : lue depuis la config de sélection sauvegardée.
    Param optionnel `tireurs` (query ou body) : calcule arbitres_nombre.
    """
    arb_cfg = {}
    if request.method == 'POST' and request.is_json:
        arb_cfg = (request.json or {}).get('arbitrage_config', {})
    else:
        cfg_path = current_app.config['CONFIG_PATH']
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding='utf-8') as f:
                arb_cfg = json.load(f).get('arbitrage_config', {})

    tireurs = request.values.get('tireurs', type=int)
    if tireurs is None and request.is_json:
        tireurs = (request.json or {}).get('tireurs')
    return jsonify(export_arbitrage_json(arb_cfg, tireurs))
