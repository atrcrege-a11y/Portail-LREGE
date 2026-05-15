"""
routes/misc.py — Routes utilitaires : index, config, favicon.
"""
import os
import json

from flask import Blueprint, request, jsonify, render_template, current_app

from services.construction import CATEGORIES, ARMES, GENRES, get_saison

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
