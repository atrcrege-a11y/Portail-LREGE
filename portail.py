# -*- coding: utf-8 -*-
"""Portail LREGE - Lanceur unifie des outils CREGE Grand Est"""

import os, sys, subprocess, threading, webbrowser, time, json, tempfile
import urllib.request as urlreq
from flask import Flask, render_template_string, jsonify, request, make_response

VERSION_LOCALE = "7.6"
VERSION_JSON_URL = "https://raw.githubusercontent.com/atrcrege-a11y/Portail-LREGE/main/version.json"

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTILS = {
    "selecge": {
        "nom": "SelecGE",
        "description": "Selections Championnat de France",
        "detail": "Armes olympiques - Sabre Laser - Individuel & Equipes",
        "script": os.path.join(BASE_DIR, "SelecGE", "app.py"),
        "port": 5001,
        "icone": "\U0001F3C6",
        "couleur": "#1F3864",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "SelecGE"),
    },
    "synesc": {
        "nom": "SYNESC",
        "description": "Gestion des competitions",
        "detail": "Grand Est - Alsace - Lorraine - Arbitres - Mails",
        "script": os.path.join(BASE_DIR, "SYNESC", "app.py"),
        "port": 5002,
        "icone": "\u2694\uFE0F",
        "couleur": "#1F6391",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "SYNESC"),
    },
    "escritools": {
        "nom": "EscriTools",
        "description": "Outils de conversion",
        "detail": "BellePoule vers FFF - PDF vers Markdown",
        "script": os.path.join(BASE_DIR, "EscriTools", "escritools.py"),
        "port": None,
        "icone": "\U0001F504",
        "couleur": "#2E75B6",
        "type": "tkinter",
        "cwd": os.path.join(BASE_DIR, "EscriTools"),
    },
    "calendrier": {
        "nom": "Calendrier LREGE",
        "description": "Calendrier des competitions",
        "detail": "National - Regional - International - Stages - Formations",
        "script": os.path.join(BASE_DIR, "CalendrierLREGE", "app.py"),
        "port": 5003,
        "icone": "\U0001F4C5",
        "couleur": "#1F3864",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "CalendrierLREGE"),
    },
    "selecmaster": {
        "nom": "SelecMaster",
        "description": "Selection Master Grand Est",
        "detail": "M11 / M13 - Epee - Fleuret - Sabre - Territories",
        "script": os.path.join(BASE_DIR, "SelecMaster", "app.py"),
        "port": 5004,
        "icone": "\U0001F947",
        "couleur": "#1F6B38",
        "type": "web",
        "cwd": os.path.join(BASE_DIR, "SelecMaster"),
    },
}

_processus = {}
_derniere_activite = {}
VENVS = {
    "selecge":    os.path.join(BASE_DIR, "SelecGE", ".venv", "Scripts", "python.exe"),
    "synesc":     os.path.join(BASE_DIR, "SYNESC", ".venv", "Scripts", "python.exe"),
    "escritools": None,
    "calendrier": None,
    "selecmaster": None,
}


def python_pour(oid):
    venv = VENVS.get(oid)
    if venv and os.path.isfile(venv):
        return venv
    return sys.executable


def outil_disponible(oid):
    return os.path.isfile(OUTILS[oid]["script"])


def outil_en_cours(oid):
    proc = _processus.get(oid)
    return proc is not None and proc.poll() is None


def _comparer_versions(v):
    return tuple(int(x) for x in v.split("."))


def verifier_maj():
    try:
        with urlreq.urlopen(VERSION_JSON_URL, timeout=5) as r:
            data = json.loads(r.read().decode())
        version_distante = data.get("version", "0.0.0")
        url_exe = data.get("url", "")
        if _comparer_versions(version_distante) > _comparer_versions(VERSION_LOCALE) and url_exe:
            return {"maj_disponible": True, "version": version_distante, "url": url_exe}
    except Exception:
        pass
    return {"maj_disponible": False, "version": VERSION_LOCALE}


def _tuer_processus(oid):
    """Termine proprement un processus et ses enfants."""
    proc = _processus.get(oid)
    if not proc or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True)
        else:
            proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _telecharger_et_installer(url, version):
    try:
        tmp = os.path.join(tempfile.gettempdir(), "PortailLREGE_Setup_v{}.exe".format(version))
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                tmp = os.path.join(tempfile.gettempdir(), "PortailLREGE_Setup_v{}_new.exe".format(version))
        urlreq.urlretrieve(url, tmp)
        # Arrêter tous les outils proprement
        for oid in list(_processus.keys()):
            _tuer_processus(oid)
        time.sleep(1)
        # Lancer l'installeur puis quitter proprement
        subprocess.Popen([tmp], shell=True)
        time.sleep(2)
        os._exit(0)
    except Exception:
        pass


REQUIREMENTS = {
    "selecge":     os.path.join(BASE_DIR, "SelecGE",        "requirements.txt"),
    "synesc":      os.path.join(BASE_DIR, "SYNESC",         "requirements.txt"),
    "escritools":  os.path.join(BASE_DIR, "EscriTools",     "requirements.txt"),
    "calendrier":  os.path.join(BASE_DIR, "CalendrierLREGE","requirements.txt"),
    "selecmaster": os.path.join(BASE_DIR, "SelecMaster",    "requirements.txt"),
}


def installer_dependances():
    """Installe silencieusement les dépendances de chaque outil au démarrage."""
    time.sleep(2)
    for oid, req in REQUIREMENTS.items():
        if not os.path.isfile(req):
            continue
        py = python_pour(oid)
        try:
            subprocess.run(
                [py, "-m", "pip", "install", "-r", req, "--quiet", "--no-warn-script-location"],
                cwd=os.path.dirname(req),
                capture_output=True,
                timeout=120,
            )
            print(f"[DEPS] {oid} OK")
        except Exception as e:
            print(f"[DEPS] {oid} erreur : {e}")


def _watchdog():
    """Tue automatiquement un outil si son onglet est fermé (heartbeat absent > 10s)."""
    while True:
        time.sleep(10)
        maintenant = time.time()
        for oid in list(_processus.keys()):
            if not outil_en_cours(oid):
                continue
            derniere = _derniere_activite.get(oid)
            if derniere is not None and (maintenant - derniere) > 60:
                print(f"[WATCHDOG] {oid} inactif depuis >10s — arrêt automatique")
                _tuer_processus(oid)
                _derniere_activite.pop(oid, None)


def verifier_maj_demarrage():
    time.sleep(4)
    info = verifier_maj()
    if info["maj_disponible"]:
        threading.Thread(target=_telecharger_et_installer, args=(info["url"], info["version"]), daemon=True).start()


@app.route("/")
def index():
    return render_template_string(HTML_PORTAIL, outils=OUTILS, version=VERSION_LOCALE)


@app.route("/api/statut")
def statut():
    return jsonify({oid: {"en_cours": outil_en_cours(oid), "disponible": outil_disponible(oid)} for oid in OUTILS})


@app.route("/api/maj")
def api_maj():
    return jsonify(verifier_maj())


@app.route("/api/lancer/<outil_id>", methods=["POST"])
def lancer(outil_id):
    if outil_id not in OUTILS:
        return jsonify({"ok": False, "message": "Outil inconnu"}), 404
    if not outil_disponible(outil_id):
        return jsonify({"ok": False, "message": "Fichier introuvable"}), 404
    cfg = OUTILS[outil_id]
    if outil_en_cours(outil_id):
        if cfg["type"] == "web" and cfg["port"]:
            webbrowser.open("http://localhost:{}".format(cfg["port"]))
        return jsonify({"ok": True, "message": "Deja en cours"})
    try:
        proc = subprocess.Popen(
            [python_pour(outil_id), cfg["script"]],
            cwd=cfg.get("cwd", BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        _processus[outil_id] = proc
        if cfg["type"] == "web" and cfg["port"]:
            port = cfg["port"]
            def ouvrir():
                time.sleep(2.5)
                if proc.poll() is None:
                    webbrowser.open("http://localhost:{}".format(port))
            threading.Thread(target=ouvrir, daemon=True).start()
        return jsonify({"ok": True, "message": "{} lance".format(cfg["nom"])})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500



@app.route("/api/installer-maj", methods=["POST"])
def installer_maj():
    info = verifier_maj()
    if not info.get("maj_disponible"):
        return jsonify({"ok": False, "message": "Aucune mise a jour disponible"})
    threading.Thread(
        target=_telecharger_et_installer,
        args=(info["url"], info["version"]),
        daemon=True
    ).start()
    return jsonify({"ok": True, "message": "Telechargement lance"})


@app.route("/api/heartbeat/<outil_id>", methods=["POST", "OPTIONS"])
def heartbeat(outil_id):
    if request.method == "OPTIONS":
        r = make_response()
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Allow-Methods"] = "POST"
        return r
    if outil_id in OUTILS:
        _derniere_activite[outil_id] = time.time()
    resp = make_response(jsonify({"ok": True}))
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/api/arreter/<outil_id>", methods=["POST"])
def arreter(outil_id):
    _tuer_processus(outil_id)
    return jsonify({"ok": True})


@app.route("/api/arreter-tout", methods=["POST"])
def arreter_tout():
    """Appelé à la fermeture du navigateur — arrête tous les outils."""
    for oid in list(_processus.keys()):
        _tuer_processus(oid)
    return jsonify({"ok": True})


HTML_PORTAIL = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portail LREGE</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');
  :root { --bleu-nuit:#0f1e35;--bleu-moyen:#1F6391;--bleu-clair:#2E75B6;--blanc:#f4f7fb;--gris:#8fa3bc;--ok:#4caf7d; }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'DM Sans',sans-serif;background:var(--bleu-nuit);color:var(--blanc);min-height:100vh;display:flex;flex-direction:column}
  header{padding:32px 48px 24px;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:center;gap:20px}
  .logo-badge{width:48px;height:48px;background:linear-gradient(135deg,var(--bleu-clair),var(--bleu-moyen));border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px}
  .header-text h1{font-size:1.25rem;font-weight:600}
  .header-text p{font-size:.8rem;color:var(--gris);font-family:'DM Mono',monospace;margin-top:2px}
  .bandeau-maj{display:none;background:linear-gradient(90deg,#e67e22,#d35400);color:#fff;padding:12px 48px;font-size:.82rem;font-family:'DM Mono',monospace;align-items:center;gap:12px}
  .bandeau-maj.visible{display:flex}
  .bandeau-maj button{background:rgba(255,255,255,.25);border:none;color:#fff;font-weight:600;padding:4px 12px;border-radius:6px;cursor:pointer}
  main{flex:1;padding:40px 48px;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;align-content:start}
  .card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:28px;display:flex;flex-direction:column;gap:16px;transition:border-color .2s,transform .2s;position:relative;overflow:hidden}
  .card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent);border-radius:16px 16px 0 0}
  .card:hover{border-color:rgba(255,255,255,.18);transform:translateY(-2px)}
  .card.indisponible{opacity:.4;pointer-events:none}
  .card-header{display:flex;align-items:flex-start;gap:14px}
  .card-icone{font-size:26px;width:50px;height:50px;background:rgba(255,255,255,.06);border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .card-titre{flex:1}
  .card-titre h2{font-size:1.05rem;font-weight:600;margin-bottom:4px}
  .card-titre .desc{font-size:.82rem;color:var(--gris)}
  .card-titre .detail{font-size:.72rem;font-family:'DM Mono',monospace;color:rgba(143,163,188,.7);margin-top:4px}
  .statut-dot{width:8px;height:8px;border-radius:50%;background:var(--gris);flex-shrink:0;margin-top:6px;transition:background .3s}
  .statut-dot.actif{background:var(--ok);box-shadow:0 0 8px var(--ok);animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{box-shadow:0 0 6px var(--ok)}50%{box-shadow:0 0 14px var(--ok)}}
  .card-actions{display:flex;gap:10px;margin-top:auto}
  .btn{flex:1;padding:10px 16px;border-radius:10px;border:none;font-family:'DM Sans',sans-serif;font-size:.85rem;font-weight:500;cursor:pointer;transition:opacity .15s}
  .btn:disabled{opacity:.35;cursor:not-allowed}
  .btn-lancer{background:var(--accent);color:#fff}
  .btn-lancer:hover:not(:disabled){opacity:.85}
  .btn-ouvrir{background:rgba(255,255,255,.08);color:var(--blanc);border:1px solid rgba(255,255,255,.12)}
  .btn-arreter{background:rgba(192,57,43,.18);color:#e8877f;border:1px solid rgba(192,57,43,.3);flex:0 0 auto;padding:10px 14px}
  .badge-indispo{font-size:.72rem;font-family:'DM Mono',monospace;color:var(--gris);background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);padding:6px 12px;border-radius:8px;text-align:center;width:100%}
  footer{padding:16px 48px;border-top:1px solid rgba(255,255,255,.06);display:flex;align-items:center;justify-content:space-between;font-size:.72rem;color:var(--gris);font-family:'DM Mono',monospace}
  .dot-live{width:6px;height:6px;border-radius:50%;background:var(--ok);display:inline-block;margin-right:6px;animation:pulse 2s infinite}
</style>
</head>
<body>
<header>
  <div class="logo-badge">&#x1F93A;</div>
  <div class="header-text">
    <h1>Portail LREGE</h1>
    <p>CREGE Grand Est &mdash; Outils de gestion</p>
  </div>
</header>
<div class="bandeau-maj" id="bandeau-maj">
  Nouvelle version disponible &mdash; <span id="maj-version"></span>
  &nbsp;<button onclick="installerMaj()">Installer maintenant</button>
</div>
<main>
  {% for oid, cfg in outils.items() %}
  <div class="card" id="card-{{ oid }}" style="--accent:{{ cfg.couleur }}">
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
      <span class="badge-indispo">Chargement...</span>
    </div>
  </div>
  {% endfor %}
</main>
<footer>
  <span>Portail LREGE v{{ version }}</span>
  <span><span class="dot-live"></span><span id="ts">&mdash;</span></span>
</footer>
<script>
{% raw %}
const TYPES = {selecge:"web",synesc:"web",escritools:"tkinter",calendrier:"web",selecmaster:"web"};
const PORTS = {selecge:5001,synesc:5002,calendrier:5003,selecmaster:5004};

function btn(cls, oid, label, extra) {
  return `<button class="btn ${cls}" onclick="${extra||cls.replace('btn-','')}('${oid}')">${label}</button>`;
}

function renderActions(oid, s) {
  const div = document.getElementById("actions-" + oid);
  const card = document.getElementById("card-" + oid);
  const dot = document.getElementById("dot-" + oid);
  card.classList.toggle("indisponible", !s.disponible);
  dot.classList.toggle("actif", s.en_cours);
  if (!s.disponible) { div.innerHTML = "<span class='badge-indispo'>Fichier introuvable</span>"; return; }
  if (s.en_cours) {
    const ob = TYPES[oid]==="web" ? btn("btn-ouvrir", oid, "Ouvrir", "ouvrir") : "<span class='badge-indispo' style='flex:1'>En cours</span>";
    div.innerHTML = ob + btn("btn-arreter", oid, "&#x25A0;", "arreter");
  } else {
    div.innerHTML = btn("btn-lancer", oid, "Lancer", "lancer");
  }
}

async function fetchStatut() {
  try {
    const data = await (await fetch("/api/statut")).json();
    for (const [oid, s] of Object.entries(data)) renderActions(oid, s);
    document.getElementById("ts").textContent = "Actualise " + new Date().toLocaleTimeString("fr-FR");
  } catch(e) {}
}

async function lancer(oid) {
  const btn = document.querySelector("#actions-" + oid + " .btn-lancer");
  if (btn) { btn.disabled = true; btn.textContent = "Lancement..."; }
  await fetch("/api/lancer/" + oid, {method:"POST"});
  setTimeout(fetchStatut, TYPES[oid]==="tkinter" ? 1000 : 3500);
}

function ouvrir(oid) { window.open("http://localhost:" + PORTS[oid], "_blank"); }

async function arreter(oid) {
  if (!confirm("Arreter cet outil ?")) return;
  await fetch("/api/arreter/" + oid, {method:"POST"});
  setTimeout(fetchStatut, 500);
}

async function verifierMaj() {
  try {
    const data = await (await fetch("/api/maj")).json();
    if (data.maj_disponible) {
      document.getElementById("bandeau-maj").classList.add("visible");
      document.getElementById("maj-version").textContent = "v" + data.version;
    }
  } catch(e) {}
}

async function installerMaj() {
  if (!confirm("Installer la mise a jour ? L'installeur se lancera automatiquement. Le portail et les outils se fermeront automatiquement.")) return;
  const btn = document.querySelector("#bandeau-maj button");
  if (btn) { btn.disabled = true; btn.textContent = "Téléchargement..."; }
  try {
    const resp = await fetch("/api/installer-maj", {method: "POST"});
    const data = await resp.json();
    if (!data.ok) alert("Erreur : " + data.message);
  } catch(e) {
    alert("Erreur réseau : " + e.message);
  }
}

fetchStatut();
setInterval(fetchStatut, 4000);
setTimeout(verifierMaj, 4000);

// Fermeture navigateur → arrêt de tous les outils
window.addEventListener('beforeunload', function() {
  navigator.sendBeacon('/api/arreter-tout');
});
{% endraw %}
</script>
</body>
</html>"""


def ouvrir_portail():
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    threading.Thread(target=ouvrir_portail, daemon=True).start()
    threading.Thread(target=verifier_maj_demarrage, daemon=True).start()
    threading.Thread(target=installer_dependances, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    app.run(port=5000, debug=False)
