"""
app.py — Bootstrap Flask pour SelecGE.
Lance avec : python app.py  |  http://localhost:5001
"""
import os
import tempfile

from flask import Flask

import services.cache as cache

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'sorties')
UPLOAD_FOLDER = tempfile.mkdtemp()
CONFIG_PATH   = os.path.join(BASE_DIR, 'config_selection.json')

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialisation du cache (avec persistance disque)
cache.init(UPLOAD_FOLDER)

# Application Flask
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['OUTPUT_FOLDER']      = OUTPUT_FOLDER
app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['CONFIG_PATH']        = CONFIG_PATH

# Enregistrement des blueprints
from routes.misc        import bp as bp_misc
from routes.classements import bp as bp_classements
from routes.generation  import bp as bp_generation
from routes.sabre_laser import bp as bp_sl

app.register_blueprint(bp_misc)
app.register_blueprint(bp_classements)
app.register_blueprint(bp_generation)
app.register_blueprint(bp_sl)

if __name__ == '__main__':
    from services.construction import get_saison
    saison = get_saison()
    print("\n" + "=" * 55)
    print(f"  SelecGE v34 -- Selections CDF Grand Est")
    print(f"  Saison {saison}")
    print("=" * 55 + "\n  http://localhost:5001\n  Ctrl+C pour quitter\n")
    app.run(debug=False, port=5001)
