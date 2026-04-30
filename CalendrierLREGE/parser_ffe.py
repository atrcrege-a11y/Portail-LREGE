import pandas as pd
import json
from datetime import datetime
import uuid

ARME_DECODE = {
    'EPEM':('épée','H'),'EPEF':('épée','D'),'EPEMF':('épée','H+D'),
    'FLEM':('fleuret','H'),'FLEF':('fleuret','D'),'FLEMF':('fleuret','H+D'),
    'SABM':('sabre','H'),'SABF':('sabre','D'),'SABMF':('sabre','H+D'),
    'LASM':('sabre laser','H'),'LASF':('sabre laser','D'),'LASMF':('sabre laser','H+D'),
    'ARTM':('artistique','H'),'ARTF':('artistique','D'),'ARTMF':('artistique','H+D'),
}
NIVEAU_MAP = {
    'International(e)':'international','National(e)':'national',
    'De Zone':'zone','Régional(e)':'regional','Interrégional':'regional',
    'Départemental(e)':'departemental','Club':'club',
}
PERIMETRE_GE = {'Régional','Interrégional'}
MOTS_GE = ['grand est','lrege','crege']

def parse_date(s):
    if not s or pd.isna(s): return None
    try: return datetime.strptime(str(s).strip(),'%d/%m/%Y').strftime('%Y-%m-%d')
    except: return None

def is_grand_est(row):
    p = str(row.get('Périmètre','') or '').strip()
    t = str(row.get('Intitulé','') or '').lower()
    if p in PERIMETRE_GE: return True
    return any(m in t for m in MOTS_GE)

def detect_type(intitule):
    t = intitule.lower()
    if any(x in t for x in ['arbitr','jna','qcm']): return 'formation_arbitrage'
    if 'animateur' in t: return 'formation_animateur'
    if any(x in t for x in ['éducateur','educateur','cadre']): return 'formation_cadre'
    if 'stage' in t or 'formation' in t: return 'stage'
    return 'competition'

def parse_arme(code):
    code = str(code or '').strip()
    return ARME_DECODE.get(code, (code.lower() or 'multi', ''))

def parse_xlsx(filepath):
    df = pd.read_excel(filepath)
    dedup = {}
    for _, row in df.iterrows():
        d0 = parse_date(row.get('Date début compétition'))
        if not d0: continue
        intitule = str(row.get('Intitulé','') or '').strip()
        lieu = str(row.get('Lieu','') or '').strip()
        key = (d0, intitule.lower(), lieu.lower())
        arme, sexe = parse_arme(row.get('Arme/Sexe'))
        cats = [c.strip() for c in str(row.get('Catégorie','') or '').split(',') if c.strip()]
        if key in dedup:
            e = dedup[key]
            if arme and arme not in e['armes']: e['armes'].append(arme)
            for c in cats:
                if c not in e['categories']: e['categories'].append(c)
        else:
            niv_raw = str(row.get('Niveau','') or '')
            dedup[key] = {
                'id': str(uuid.uuid4()), 'source':'ffe', 'manuel':False,
                'type_evenement': detect_type(intitule),
                'statut': str(row.get('Statut','') or ''),
                'date_debut': d0,
                'date_fin': parse_date(row.get('Date fin compétition')),
                'type_competition': str(row.get('Type de compétition','') or ''),
                'niveau': NIVEAU_MAP.get(niv_raw,'autre'), 'niveau_raw': niv_raw,
                'numero': str(row.get('Numéro','') or ''),
                'intitule': intitule, 'lieu': lieu,
                'perimetre': str(row.get('Périmètre','') or ''),
                'armes': [arme] if arme else [], 'arme': arme, 'sexe': sexe,
                'categories': cats,
                'type_epreuve': str(row.get('Type','') or ''),
                'url': str(row.get('url','') or ''),
                'grand_est': is_grand_est(row), 'notes':'',
            }
    return sorted(dedup.values(), key=lambda e: e['date_debut'])

if __name__ == '__main__':
    import sys, os
    fp = sys.argv[1] if len(sys.argv)>1 else 'extraction.xlsx'
    ev = parse_xlsx(fp)
    print(f"Total dédupliqué: {len(ev)} | GE: {sum(1 for e in ev if e['grand_est'])} | Nat: {sum(1 for e in ev if e['niveau']=='national')} | Int: {sum(1 for e in ev if e['niveau']=='international')} | Stages: {sum(1 for e in ev if e['type_evenement']!='competition')}")
    os.makedirs('data',exist_ok=True)
    with open('data/calendrier.json','w',encoding='utf-8') as f: json.dump(ev,f,ensure_ascii=False,indent=2)
    print("OK → data/calendrier.json")
