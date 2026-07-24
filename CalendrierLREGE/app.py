from flask import Flask, render_template, request, jsonify, send_file
import json, os, uuid, io
from datetime import datetime
from parser_ffe import parse_xlsx, ParseError, JSON_VERSION
from exports import build_ical, build_excel, build_pdf

app = Flask(__name__)
PORT = 5003
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'calendrier.json')

def load_events():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, encoding='utf-8') as f:
        events = json.load(f)
    # Migration : ajouter champs manquants pour compatibilité ascendante
    for e in events:
        e.setdefault('notes', '')
        e.setdefault('manuel', False)
        e.setdefault('source', 'ffe')
        e.setdefault('type_evenement', 'competition')
        e.setdefault('categories', [])
        e.setdefault('armes', [e.get('arme', '')] if e.get('arme') else [])
        e.setdefault('__version__', 0)
    return events

def save_events(events):
    """Écriture atomique : fichier temporaire puis os.replace (évite un
    calendrier.json corrompu si le processus est interrompu en cours d'écriture)."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp_file = DATA_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)

def season_of(date_str):
    """Saison sportive d'une date AAAA-MM-JJ. Sept→Août : mois>=9 → année, sinon année-1.
    Retourne l'année de début de saison (2025 = saison 2025-2026), ou None si date invalide."""
    if not date_str or len(date_str) < 7:
        return None
    try:
        y, m = int(date_str[:4]), int(date_str[5:7])
    except ValueError:
        return None
    return y if m >= 9 else y - 1

def season_bounds(saison):
    """Bornes AAAA-MM-JJ (incluses) d'une saison : (1er sept saison, 31 août saison+1)."""
    return f"{saison}-09-01", f"{saison + 1}-08-31"

def season_label(saison):
    return f"{saison}-{saison + 1}"

def current_season(today=None):
    today = today or datetime.now()
    return today.year if today.month >= 9 else today.year - 1

def apply_filters(events, args):
    niveau    = args.get('niveau')
    arme      = args.get('arme')
    categorie = args.get('categorie')
    type_ev   = args.get('type_evenement')
    grand_est = args.get('grand_est')
    mois      = args.get('mois')
    search    = args.get('search','').strip().lower()
    date_from = args.get('date_from')
    date_to   = args.get('date_to')

    if niveau    and niveau    != 'tous': events = [e for e in events if e.get('niveau')==niveau]
    if arme      and arme      != 'tous': events = [e for e in events if e.get('arme')==arme]
    if categorie and categorie != 'tous': events = [e for e in events if categorie in e.get('categories',[])]
    if type_ev   and type_ev   != 'tous': events = [e for e in events if e.get('type_evenement')==type_ev]
    if grand_est == '1': events = [e for e in events if e.get('grand_est')]
    if mois: events = [e for e in events if (e.get('date_debut') or '').startswith(mois)]
    if date_from: events = [e for e in events if (e.get('date_debut') or '') >= date_from]
    if date_to:   events = [e for e in events if (e.get('date_debut') or '') <= date_to]
    if search:
        events = [e for e in events if search in e.get('intitule','').lower() or search in e.get('lieu','').lower()]
    return events

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/events')
def get_events():
    events = apply_filters(load_events(), request.args)
    return jsonify(events)

@app.route('/api/stats')
def stats():
    events = load_events()
    by_niv = {}
    for e in events:
        n = e.get('niveau','autre')
        by_niv[n] = by_niv.get(n,0)+1
    return jsonify({
        'total': len(events),
        'grand_est': sum(1 for e in events if e.get('grand_est')),
        'international': by_niv.get('international',0),
        'national': by_niv.get('national',0),
        'regional': by_niv.get('regional',0),
        'stages': sum(1 for e in events if e.get('type_evenement','competition')!='competition'),
        'manuel': sum(1 for e in events if e.get('manuel')),
        'derniere_maj': datetime.now().strftime('%d/%m/%Y %H:%M'),
    })

def _backup_data():
    """Copie horodatée de calendrier.json avant toute opération destructive.
    Retourne le nom du fichier de sauvegarde, ou None si aucune donnée."""
    if not os.path.exists(DATA_FILE):
        return None
    backup_dir = os.path.join(os.path.dirname(DATA_FILE), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    name = 'calendrier_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'
    with open(DATA_FILE, encoding='utf-8') as src:
        content = src.read()
    with open(os.path.join(backup_dir, name), 'w', encoding='utf-8') as dst:
        dst.write(content)
    return name

@app.route('/api/seasons')
def seasons():
    """Saisons présentes dans les données (avec compteurs) + saison écoulée par défaut."""
    events = load_events()
    agg = {}
    for e in events:
        s = season_of(e.get('date_debut'))
        if s is None:
            continue
        d = agg.setdefault(s, {'saison': s, 'label': season_label(s), 'total': 0, 'manuel': 0})
        d['total'] += 1
        if e.get('manuel'):
            d['manuel'] += 1
    liste = [agg[k] for k in sorted(agg)]
    cur = current_season()
    return jsonify({
        'seasons': liste,
        'saison_courante': cur,
        'saison_ecoulee': cur - 1,   # saison précédant la saison en cours
    })

@app.route('/api/purge', methods=['POST'])
def purge_season():
    """Purge les événements d'une saison (1er sept → 31 août).
    Body JSON : saison (int, année de début, obligatoire), dry_run (bool),
    keep_manuel (bool, défaut True). Sauvegarde horodatée avant purge réelle."""
    data = request.json or {}
    saison = data.get('saison')
    try:
        saison = int(saison)
    except (TypeError, ValueError):
        return jsonify({'error': "Champ 'saison' obligatoire (année de début, ex. 2025)"}), 400

    dry_run = bool(data.get('dry_run', False))
    keep_manuel = bool(data.get('keep_manuel', True))
    d_from, d_to = season_bounds(saison)

    events = load_events()

    def in_season(e):
        d = e.get('date_debut') or ''
        if not (d_from <= d <= d_to):
            return False
        if keep_manuel and e.get('manuel'):
            return False
        return True

    to_purge = [e for e in events if in_season(e)]
    kept = [e for e in events if not in_season(e)]
    manuels_conserves = sum(
        1 for e in events
        if keep_manuel and e.get('manuel') and d_from <= (e.get('date_debut') or '') <= d_to
    )

    resp = {
        'saison': saison, 'label': season_label(saison),
        'date_from': d_from, 'date_to': d_to,
        'purged': len(to_purge), 'remaining': len(kept),
        'manuels_conserves': manuels_conserves, 'keep_manuel': keep_manuel,
        'dry_run': dry_run,
    }
    if dry_run:
        resp['success'] = True
        return jsonify(resp)

    backup = _backup_data()
    save_events(kept)
    resp['success'] = True
    resp['backup'] = backup
    return jsonify(resp)

@app.route('/api/import', methods=['POST'])
def import_xlsx():
    if 'file' not in request.files: return jsonify({'error':'Aucun fichier'}),400
    f = request.files['file']
    if not f.filename.endswith('.xlsx'): return jsonify({'error':'Format .xlsx attendu'}),400
    import tempfile, os as _os
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()
    f.save(tmp.name)
    try:
        new_events = parse_xlsx(tmp.name)
        manuels = [e for e in load_events() if e.get('manuel')]
        merged = new_events + manuels
        merged.sort(key=lambda e: e.get('date_debut',''))
        save_events(merged)
        return jsonify({'success':True,'total':len(merged),'ffe':len(new_events),'manuels':len(manuels)})
    except ParseError as ex:
        return jsonify({'error': str(ex.args[0]), 'hint': ex.hint}),400
    except Exception as ex:
        return jsonify({'error':str(ex)}),500
    finally:
        try: _os.unlink(tmp.name)
        except: pass

@app.route('/api/events', methods=['POST'])
def add_event():
    data = request.json or {}
    # Validation champs obligatoires
    date_debut = (data.get('date_debut') or '').strip()
    intitule   = (data.get('intitule')   or '').strip()
    if not date_debut:
        return jsonify({'error': "Le champ 'date_debut' est obligatoire (format AAAA-MM-JJ)"}), 400
    if not intitule:
        return jsonify({'error': "Le champ 'intitule' est obligatoire"}), 400
    # Validation format date
    try:
        datetime.strptime(date_debut, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': f"Format date invalide : '{date_debut}' — attendu AAAA-MM-JJ"}), 400

    events = load_events()
    e = {
        'id': str(uuid.uuid4()), 'source':'manuel', 'manuel':True,
        'type_evenement': data.get('type_evenement','competition'),
        'statut': data.get('statut','À venir'),
        'date_debut': date_debut, 'date_fin': (data.get('date_fin') or '').strip(),
        'type_competition': '', 'niveau': data.get('niveau','regional'),
        'niveau_raw': data.get('niveau','regional'), 'numero':'',
        'intitule': intitule, 'lieu': (data.get('lieu') or '').strip(),
        'perimetre': data.get('perimetre','Régional'),
        'armes': [data.get('arme','')] if data.get('arme') else [],
        'arme': data.get('arme',''), 'sexe': data.get('sexe',''),
        'categories': data.get('categories',[]),
        'type_epreuve': data.get('type_epreuve',''),
        'url': data.get('url',''),
        'grand_est': data.get('grand_est', True),
        'notes': data.get('notes',''),
        '__version__': JSON_VERSION,
    }
    events.append(e)
    events.sort(key=lambda x: x.get('date_debut',''))
    save_events(events)
    return jsonify({'success':True,'event':e})

@app.route('/api/events/<eid>', methods=['PUT'])
def update_event(eid):
    data = request.json; events = load_events()
    for i,e in enumerate(events):
        if e['id']==eid:
            events[i].update(data); events[i]['id']=eid
            events.sort(key=lambda x: x.get('date_debut',''))
            save_events(events)
            return jsonify({'success':True})
    return jsonify({'error':'Introuvable'}),404

@app.route('/api/events/<eid>', methods=['DELETE'])
def delete_event(eid):
    events = [e for e in load_events() if e['id']!=eid]
    save_events(events); return jsonify({'success':True})

# ── EXPORTS ───────────────────────────────────────────────────────────────────
@app.route('/api/export/ical')
def export_ical():
    events = apply_filters(load_events(), request.args)
    data = build_ical(events)
    return send_file(io.BytesIO(data), mimetype='text/calendar',
        as_attachment=True, download_name='calendrier_lrege.ics')

@app.route('/api/export/excel')
def export_excel():
    events = apply_filters(load_events(), request.args)
    data = build_excel(events)
    ts = datetime.now().strftime('%Y%m%d')
    return send_file(io.BytesIO(data),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'calendrier_lrege_{ts}.xlsx')

@app.route('/api/export/pdf')
def export_pdf():
    events = apply_filters(load_events(), request.args)
    data = build_pdf(events)
    ts = datetime.now().strftime('%Y%m%d')
    return send_file(io.BytesIO(data), mimetype='application/pdf',
        as_attachment=True, download_name=f'calendrier_lrege_{ts}.pdf')

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    print(f"Calendrier LREGE — http://localhost:{PORT}")
    app.run(port=PORT, debug=False)
