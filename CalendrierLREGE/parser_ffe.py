import pandas as pd
import json
from datetime import datetime
import uuid

# ── Constantes colonnes FFE ───────────────────────────────────────────────────
# Si FFE renomme une colonne, modifier ici uniquement.
COL_DATE_DEBUT  = 'Date début compétition'
COL_DATE_FIN    = 'Date fin compétition'
COL_INTITULE    = 'Intitulé'
COL_LIEU        = 'Lieu'
COL_ARME_SEXE   = 'Arme/Sexe'
COL_CATEGORIE   = 'Catégorie'
COL_NIVEAU      = 'Niveau'
COL_STATUT      = 'Statut'
COL_TYPE_COMP   = 'Type de compétition'
COL_NUMERO      = 'Numéro'
COL_PERIMETRE   = 'Périmètre'
COL_TYPE        = 'Type'
COL_URL         = 'url'

COLONNES_OBLIGATOIRES = [COL_DATE_DEBUT, COL_INTITULE]
COLONNES_ATTENDUES    = [COL_DATE_DEBUT, COL_DATE_FIN, COL_INTITULE, COL_LIEU,
                         COL_ARME_SEXE, COL_CATEGORIE, COL_NIVEAU, COL_PERIMETRE]

JSON_VERSION = 1   # Incrémenter si le schéma d'un événement change


class ParseError(ValueError):
    """Erreur de parsing du fichier FFE — message utilisateur + hint technique.
    Attendue par app.py (/api/import) qui renvoie {'error': message, 'hint': hint}."""
    def __init__(self, message, hint=""):
        super().__init__(message)
        self.hint = hint

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
# Périmètres Grand Est — variantes FFE (avec/sans accents, parenthèses)
PERIMETRE_GE = {'Régional','Interrégional','Régional(e)','Interrégional(e)',
                'Regional','Interregional'}
MOTS_GE = ['grand est','lrege','crege']

def parse_date(s):
    if not s or pd.isna(s): return None
    try: return datetime.strptime(str(s).strip(),'%d/%m/%Y').strftime('%Y-%m-%d')
    except: return None

def is_grand_est(row):
    p = str(row.get(COL_PERIMETRE,'') or '').strip()
    t = str(row.get(COL_INTITULE,'') or '').lower()
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
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        raise ParseError("Fichier Excel illisible", hint=str(e))
    manquantes = [c for c in COLONNES_OBLIGATOIRES if c not in df.columns]
    if manquantes:
        raise ParseError(
            f"Colonnes obligatoires absentes : {', '.join(manquantes)}",
            hint=f"Colonnes trouvées : {', '.join(str(c) for c in df.columns[:10])}")
    dedup = {}
    for _, row in df.iterrows():
        d0 = parse_date(row.get(COL_DATE_DEBUT))
        if not d0: continue
        intitule_raw = str(row.get(COL_INTITULE,'') or '').strip()
        lieu = str(row.get(COL_LIEU,'') or '').strip()
        intitule = intitule_raw if intitule_raw.lower() not in ('nan','') else lieu or '—'
        key = (d0, intitule.lower(), lieu.lower())
        arme, sexe = parse_arme(row.get(COL_ARME_SEXE))
        cats = [c.strip() for c in str(row.get(COL_CATEGORIE,'') or '').split(',') if c.strip()]
        if key in dedup:
            e = dedup[key]
            if arme and arme not in e['armes']: e['armes'].append(arme)
            for c in cats:
                if c not in e['categories']: e['categories'].append(c)
        else:
            niv_raw = str(row.get(COL_NIVEAU,'') or '')
            dedup[key] = {
                'id': str(uuid.uuid4()), 'source':'ffe', 'manuel':False,
                'type_evenement': detect_type(intitule),
                'statut': str(row.get(COL_STATUT,'') or ''),
                'date_debut': d0,
                'date_fin': parse_date(row.get('Date fin compétition')),
                'type_competition': str(row.get(COL_TYPE_COMP,'') or ''),
                'niveau': NIVEAU_MAP.get(niv_raw,'autre'), 'niveau_raw': niv_raw,
                'numero': str(row.get(COL_NUMERO,'') or ''),
                'intitule': intitule, 'lieu': lieu,
                'perimetre': str(row.get(COL_PERIMETRE,'') or ''),
                'armes': [arme] if arme else [], 'arme': arme, 'sexe': sexe,
                'categories': cats,
                'type_epreuve': str(row.get(COL_TYPE,'') or ''),
                'url': str(row.get(COL_URL,'') or ''),
                'grand_est': is_grand_est(row), 'notes':'',
                '__version__': JSON_VERSION,
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
