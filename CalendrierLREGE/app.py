from flask import Flask, render_template, request, jsonify, send_file
import json, os, uuid, io
from datetime import datetime
from parser_ffe import parse_xlsx
from exports import build_ical, build_excel, build_pdf

app = Flask(__name__)
PORT = 5003
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'calendrier.json')

def load_events():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, encoding='utf-8') as f: return json.load(f)

def save_events(events):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(events, f, ensure_ascii=False, indent=2)

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

@app.route('/api/import', methods=['POST'])
def import_xlsx():
    if 'file' not in request.files: return jsonify({'error':'Aucun fichier'}),400
    f = request.files['file']
    if not f.filename.endswith('.xlsx'): return jsonify({'error':'Format .xlsx attendu'}),400
    tmp = '/tmp/import_cal.xlsx'; f.save(tmp)
    try:
        new_events = parse_xlsx(tmp)
        manuels = [e for e in load_events() if e.get('manuel')]
        merged = new_events + manuels
        merged.sort(key=lambda e: e.get('date_debut',''))
        save_events(merged)
        return jsonify({'success':True,'total':len(merged),'ffe':len(new_events),'manuels':len(manuels)})
    except Exception as ex:
        return jsonify({'error':str(ex)}),500

@app.route('/api/events', methods=['POST'])
def add_event():
    data = request.json
    events = load_events()
    e = {
        'id': str(uuid.uuid4()), 'source':'manuel', 'manuel':True,
        'type_evenement': data.get('type_evenement','competition'),
        'statut': data.get('statut','À venir'),
        'date_debut': data.get('date_debut',''), 'date_fin': data.get('date_fin',''),
        'type_competition': '', 'niveau': data.get('niveau','regional'),
        'niveau_raw': data.get('niveau','regional'), 'numero':'',
        'intitule': data.get('intitule',''), 'lieu': data.get('lieu',''),
        'perimetre': data.get('perimetre','Régional'),
        'armes': [data.get('arme','')] if data.get('arme') else [],
        'arme': data.get('arme',''), 'sexe': data.get('sexe',''),
        'categories': data.get('categories',[]),
        'type_epreuve': data.get('type_epreuve',''),
        'url': data.get('url',''),
        'grand_est': data.get('grand_est', True),
        'notes': data.get('notes',''),
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
