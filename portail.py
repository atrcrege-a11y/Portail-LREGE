"""
Portail LREGE — Lanceur unifié des outils CREGE Grand Est
"""

import os, sys, subprocess, threading, webbrowser, time, json, tempfile
from flask import Flask, render_template_string, jsonify
try:
    import urllib.request as urlreq
except ImportError:
    urlreq = None

VERSION_LOCALE = "1.1.0"
VERSION_JSON_URL = "https://drive.google.com/uc?export=download&id=19uHR_WR3V1z7eqEFODsafLr_YCcef1Wo"

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTILS = {
    "selecge": {
        "nom": "SelecGE",
        "description": "Sélections Championnat de France",
        "detail": "Armes olympiques · Sabre Laser · Individuel & Équipes",
        "script": os.path.join(BASE_DIR, "SelecGE", "app.py"),
        "port": 5001,
        "icone": "🏆",
        "couleur": "#1F3864",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "SelecGE"),
    },
    "synesc": {
        "nom": "SYNESC",
        "description": "Gestion des compétitions",
        "detail": "Grand Est · Alsace · Lorraine · Arbitres · Mails",
        "script": os.path.join(BASE_DIR, "SYNESC", "app.py"),
        "port": 5002,
        "icone": "⚔️",
        "couleur": "#1F6391",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "SYNESC"),
    },
    "escritools": {
        "nom": "EscriTools",
        "description": "Outils de conversion",
        "detail": "BellePoule → FFF · PDF → Markdown",
        "script": os.path.join(BASE_DIR, "EscriTools", "escritools.py"),
        "port": None,
        "icone": "🔄",
        "couleur": "#2E75B6",
        "type": "tkinter",
        "cwd": os.path.join(BASE_DIR, "EscriTools"),
    },
}

_processus = {}

# Venvs par outil (None = python système)
VENVS = {
    "selecge":    os.path.join(BASE_DIR, "SelecGE",  ".venv", "Scripts", "python.exe"),
    "synesc":     os.path.join(BASE_DIR, "SYNESC",   ".venv", "Scripts", "python.exe"),
    "escritools": None,
}


def python_pour(oid):
    venv = VENVS.get(oid)
    if venv and os.path.isfile(venv):
        return venv
    return sys.executable


def verifier_maj():
    """Vérifie si une MAJ est disponible sur Drive au démarrage."""
    try:
        with urlreq.urlopen(VERSION_JSON_URL, timeout=5) as r:
            data = json.loads(r.read().decode())
        version_distante = data.get("version", "0.0.0")
        url_exe = data.get("url", "")

        def _comparer(v):
            return tuple(int(x) for x in v.split("."))

        if _comparer(version_distante) > _comparer(VERSION_LOCALE) and url_exe:
            # Télécharger et lancer l'installeur dans un thread
            threading.Thread(target=_telecharger_et_installer, args=(url_exe, version_distante), daemon=True).start()
            return {"maj_disponible": True, "version": version_distante}
    except Exception:
        pass
    return {"maj_disponible": False, "version": VERSION_LOCALE}


def _telecharger_et_installer(url, version):
    try:
        tmp = tempfile.mktemp(suffix=".exe", prefix=f"PortailLREGE_Setup_v{version}_")
        urlreq.urlretrieve(url, tmp)
        subprocess.Popen([tmp], shell=True)
        time.sleep(2)
        os.kill(os.getpid(), 9)  # Ferme le portail après lancement installeur
    except Exception:
        pass


@app.route("/api/maj")
def api_maj():
    return jsonify(verifier_maj())



    return os.path.isfile(OUTILS[oid]["script"])


def outil_en_cours(oid):
    proc = _processus.get(oid)
    return proc is not None and proc.poll() is None


@app.route("/")
def index():
    return render_template_string(HTML_PORTAIL, outils=OUTILS)


@app.route("/api/statut")
def statut():
    return jsonify({
        oid: {"en_cours": outil_en_cours(oid), "disponible": outil_disponible(oid)}
        for oid in OUTILS
    })


@app.route("/api/lancer/<outil_id>", methods=["POST"])
def lancer(outil_id):
    if outil_id not in OUTILS:
        return jsonify({"ok": False, "message": "Outil inconnu"}), 404
    if not outil_disponible(outil_id):
        return jsonify({"ok": False, "message": "Fichier introuvable"}), 404

    cfg = OUTILS[outil_id]

    if outil_en_cours(outil_id):
        if cfg["type"] == "web" and cfg["port"]:
            webbrowser.open(f"http://localhost:{cfg['port']}")
        return jsonify({"ok": True, "message": "Déjà en cours"})

    try:
        proc = subprocess.Popen(
            [python_pour(outil_id), cfg["script"]],
            cwd=cfg.get('cwd', BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        _processus[outil_id] = proc

        if cfg["type"] == "web" and cfg["port"]:
            port = cfg["port"]
            def ouvrir():
                time.sleep(2.5)
                if proc.poll() is None:
                    webbrowser.open(f"http://localhost:{port}")
            threading.Thread(target=ouvrir, daemon=True).start()

        return jsonify({"ok": True, "message": f"{cfg['nom']} lancé"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/arreter/<outil_id>", methods=["POST"])
def arreter(outil_id):
    proc = _processus.get(outil_id)
    if proc and proc.poll() is None:
        proc.terminate()
    return jsonify({"ok": True})


HTML_PORTAIL = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portail LREGE</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');
  :root {
    --bleu-nuit: #0f1e35; --bleu-fonce: #1F3864; --bleu-moyen: #1F6391;
    --bleu-clair: #2E75B6; --blanc: #f4f7fb; --gris: #8fa3bc;
    --ok: #4caf7d; --ko: #c0392b;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', sans-serif; background: var(--bleu-nuit); color: var(--blanc); min-height: 100vh; display: flex; flex-direction: column; }
  header { padding: 32px 48px 24px; border-bottom: 1px solid rgba(255,255,255,.08); display: flex; align-items: center; gap: 20px; }
  .logo-badge { width: 48px; height: 48px; background: linear-gradient(135deg, var(--bleu-clair), var(--bleu-moyen)); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 16px rgba(46,117,182,.4); }
  .header-text h1 { font-size: 1.25rem; font-weight: 600; }
  .header-text p { font-size: .8rem; color: var(--gris); font-family: 'DM Mono', monospace; margin-top: 2px; }
  main { flex: 1; padding: 40px 48px; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; align-content: start; }
  .card { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 16px; padding: 28px; display: flex; flex-direction: column; gap: 16px; transition: border-color .2s, transform .2s, box-shadow .2s; position: relative; overflow: hidden; }
  .card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); border-radius: 16px 16px 0 0; }
  .card:hover { border-color: rgba(255,255,255,.18); transform: translateY(-2px); box-shadow: 0 12px 32px rgba(0,0,0,.3); }
  .card.indisponible { opacity: .4; pointer-events: none; }
  .card-header { display: flex; align-items: flex-start; gap: 14px; }
  .card-icone { font-size: 26px; width: 50px; height: 50px; background: rgba(255,255,255,.06); border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .card-titre { flex: 1; }
  .card-titre h2 { font-size: 1.05rem; font-weight: 600; margin-bottom: 4px; }
  .card-titre .desc { font-size: .82rem; color: var(--gris); }
  .card-titre .detail { font-size: .72rem; font-family: 'DM Mono', monospace; color: rgba(143,163,188,.7); margin-top: 4px; }
  .statut-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--gris); flex-shrink: 0; margin-top: 6px; transition: background .3s; }
  .statut-dot.actif { background: var(--ok); box-shadow: 0 0 8px var(--ok); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { box-shadow: 0 0 6px var(--ok); } 50% { box-shadow: 0 0 14px var(--ok); } }
  .card-actions { display: flex; gap: 10px; margin-top: auto; }
  .btn { flex: 1; padding: 10px 16px; border-radius: 10px; border: none; font-family: 'DM Sans', sans-serif; font-size: .85rem; font-weight: 500; cursor: pointer; transition: opacity .15s, transform .1s; }
  .btn:active { transform: scale(.97); }
  .btn:disabled { opacity: .35; cursor: not-allowed; }
  .btn-lancer { background: var(--accent); color: #fff; }
  .btn-lancer:hover:not(:disabled) { opacity: .85; }
  .btn-ouvrir { background: rgba(255,255,255,.08); color: var(--blanc); border: 1px solid rgba(255,255,255,.12); }
  .btn-ouvrir:hover:not(:disabled) { background: rgba(255,255,255,.14); }
  .btn-arreter { background: rgba(192,57,43,.18); color: #e8877f; border: 1px solid rgba(192,57,43,.3); flex: 0 0 auto; padding: 10px 14px; }
  .btn-arreter:hover:not(:disabled) { background: rgba(192,57,43,.3); }
  .badge-indispo { font-size: .72rem; font-family: 'DM Mono', monospace; color: var(--gris); background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.08); padding: 6px 12px; border-radius: 8px; text-align: center; width: 100%; }
  .bandeau-maj { display: none; background: linear-gradient(90deg, #e67e22, #d35400); color: #fff; padding: 12px 48px; font-size: .82rem; font-family: 'DM Mono', monospace; align-items: center; gap: 12px; }
  .bandeau-maj.visible { display: flex; }
  .bandeau-maj a { color: #fff; font-weight: 600; text-decoration: underline; cursor: pointer; }
  footer { padding: 16px 48px; border-top: 1px solid rgba(255,255,255,.06); display: flex; align-items: center; justify-content: space-between; font-size: .72rem; color: var(--gris); font-family: 'DM Mono', monospace; }
  .dot-live { width: 6px; height: 6px; border-radius: 50%; background: var(--ok); display: inline-block; margin-right: 6px; animation: pulse 2s infinite; }
</style>
</head>
<body>
<header>
  <div class="logo-badge">🤺</div>
  <div class="header-text">
    <h1>Portail LREGE</h1>
    <p>CREGE Grand Est — Outils de gestion</p>
  </div>
</header>
<div class="bandeau-maj" id="bandeau-maj">
  ⬆️ Une nouvelle version est disponible — <a onclick="installerMaj()">Installer maintenant</a>
  <span id="maj-version"></span>
</div>
<main>
  {% for oid, cfg in outils.items() %}
  <div class="card" id="card-{{ oid }}" style="--accent: {{ cfg.couleur }}">
    <div class="card-header">
      <div class="card-icone">{{ cfg.icone }}</div>
      <div class="card-titre">
        <h2>{{ cfg.nom }}</h2>
        <div class="desc">{{ cfg.description }}</div>
        <div class="detail">{{ cfg.detail }}</div>
      </div>
      <div class="statut-dot" id="dot-{{ oid }}"></div>
    </div>
    <div class="card-actions" id="actions-{{ oid }}">
      <span class="badge-indispo">Chargement…</span>
    </div>
  </div>
  {% endfor %}
</main>
<footer>
  <span>Portail LREGE v1.0</span>
  <span><span class="dot-live"></span><span id="ts">—</span></span>
</footer>
<script>
const TYPES = { selecge: "web", synesc: "web", escritools: "tkinter" };
const PORTS = { selecge: 5001, synesc: 5002 };

function renderActions(oid, { en_cours, disponible }) {
  const div = document.getElementById(`actions-${oid}`);
  const card = document.getElementById(`card-${oid}`);
  const dot = document.getElementById(`dot-${oid}`);
  card.classList.toggle('indisponible', !disponible);
  dot.classList.toggle('actif', en_cours);
  if (!disponible) { div.innerHTML = `<span class="badge-indispo">Fichier introuvable</span>`; return; }
  const isWeb = TYPES[oid] === "web";
  if (en_cours) {
    const ouvrirBtn = isWeb ? `<button class="btn btn-ouvrir" onclick="ouvrir('${oid}')">Ouvrir</button>` : `<span class="badge-indispo" style="flex:1">En cours</span>`;
    div.innerHTML = ouvrirBtn + `<button class="btn btn-arreter" onclick="arreter('${oid}')" title="Arrêter">■</button>`;
  } else {
    div.innerHTML = `<button class="btn btn-lancer" onclick="lancer('${oid}')">Lancer</button>`;
  }
}

async function fetchStatut() {
  try {
    const data = await (await fetch('/api/statut')).json();
    for (const [oid, s] of Object.entries(data)) renderActions(oid, s);
    document.getElementById('ts').textContent = 'Actualisé ' + new Date().toLocaleTimeString('fr-FR');
  } catch(e) {}
}

async function lancer(oid) {
  const btn = document.querySelector(`#actions-${oid} .btn-lancer`);
  if (btn) { btn.disabled = true; btn.textContent = 'Lancement…'; }
  await fetch(`/api/lancer/${oid}`, { method: 'POST' });
  setTimeout(fetchStatut, TYPES[oid] === 'tkinter' ? 1000 : 3500);
}

function ouvrir(oid) { window.open(`http://localhost:${PORTS[oid]}`, '_blank'); }

async function arreter(oid) {
  if (!confirm(`Arrêter cet outil ?`)) return;
  await fetch(`/api/arreter/${oid}`, { method: 'POST' });
  setTimeout(fetchStatut, 500);
}

fetchStatut();
setInterval(fetchStatut, 4000);

// Vérification MAJ au démarrage
async function verifierMaj() {
  try {
    const data = await (await fetch('/api/maj')).json();
    if (data.maj_disponible) {
      document.getElementById('bandeau-maj').classList.add('visible');
      document.getElementById('maj-version').textContent = `(v${data.version})`;
    }
  } catch(e) {}
}

async function installerMaj() {
  if (!confirm('Installer la mise à jour ? Le portail va se fermer.')) return;
  await fetch('/api/maj');  // Relance le téléchargement
}

setTimeout(verifierMaj, 4000);
</script>
</body>
</html>"""

def ouvrir_portail():
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")

def verifier_maj_demarrage():
    time.sleep(3)  # Laisser le portail démarrer
    verifier_maj()

if __name__ == "__main__":
    threading.Thread(target=ouvrir_portail, daemon=True).start()
    threading.Thread(target=verifier_maj_demarrage, daemon=True).start()
    app.run(port=5000, debug=False)
