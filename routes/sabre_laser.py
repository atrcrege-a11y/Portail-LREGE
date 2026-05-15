"""
routes/sabre_laser.py — Routes Sabre Laser.
"""
import os
import tempfile
import datetime
import traceback

from flask import Blueprint, request, jsonify

from crege_app.sabre_laser import (
    DISCIPLINES, lire_classement as sl_lire_classement,
    lire_et as sl_lire_et, lire_chore as sl_lire_chore,
    construire_selection_sl, construire_selection_et, construire_selection_chore,
    generer_docs_separes, generer_doc_multi,
    detecter_format as sl_detecter_format,
    get_discipline as sl_get_discipline,
)
import services.cache as cache
from services.validation import ValidationError, erreur_json

bp = Blueprint('sabre_laser', __name__)


def _get_output_folder():
    from flask import current_app
    return current_app.config['OUTPUT_FOLDER']


@bp.route('/api/sl/disciplines', methods=['GET'])
def sl_disciplines():
    return jsonify(DISCIPLINES)


@bp.route('/api/sl/upload', methods=['POST'])
def sl_upload():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    f       = request.files['fichier']
    disc_id = request.form.get('disc_id', '')
    niveau  = request.form.get('niveau_id', 'cdf')
    cle     = f"sl_{disc_id}_{niveau}_{int(__import__('time').time())}"

    fmt = sl_detecter_format(f.filename)
    if fmt == 'inconnu':
        return jsonify({'error': f'Format non supporté : {f.filename}'}), 400

    with tempfile.NamedTemporaryFile(suffix=f'.{fmt}', delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        parseur_hint = request.form.get('parseur_hint', '')
        if not parseur_hint and disc_id:
            parseur_hint = sl_get_discipline(disc_id).get('parseur', '')
        if parseur_hint == 'et':
            df = sl_lire_et(tmp_path)
        elif parseur_hint == 'chore':
            df = sl_lire_chore(tmp_path)
        else:
            df = sl_lire_classement(tmp_path, fmt)

        if df is None or df.empty:
            return jsonify({'error': 'Aucun tireur trouvé dans ce fichier'}), 400

        cache.sl_set(cle, {'path': tmp_path, 'df': df, 'format': fmt})

        nb_total = len(df)
        nb_ge    = int(df['Grand_Est'].sum()) if 'Grand_Est' in df.columns else 0
        ge_rows  = df[df['Grand_Est'] == True] if 'Grand_Est' in df.columns else df.head(10)
        cols     = ['Rang', 'Nom', 'Prenom', 'Club']
        apercu   = [{k: str(v) for k, v in r.items() if k in cols}
                    for r in ge_rows.head(10).fillna('').to_dict('records')]
        all_ge   = [{k: str(v) for k, v in r.items() if k in cols}
                    for r in ge_rows.fillna('').to_dict('records')]

        return jsonify({
            'status': 'ok', 'cle': cle, 'format': fmt,
            'nb_total': nb_total, 'nb_grand_est': nb_ge,
            'filename': f.filename,
            'apercu': apercu,
            'tireurs_ge': all_ge,
        })
    except Exception as e:
        os.unlink(tmp_path)
        return jsonify({'error': str(e), 'detail': traceback.format_exc()}), 500


@bp.route('/api/sl/generer', methods=['POST'])
def sl_generer():
    params            = request.get_json(force=True)
    mode              = params.get('mode', 'multi')
    selections_params = params.get('selections', [])

    if not selections_params:
        return jsonify({'error': 'Aucune sélection spécifiée'}), 400

    try:
        selections = []
        for sel in selections_params:
            disc_id = sel.get('disc_id', '')
            niveau  = sel.get('niveau_id', 'cdf')
            cle_nat = sel.get('cle_national')
            cle_reg = sel.get('cle_regional')

            df_nat = cache.sl_get(cle_nat)['df'] if cle_nat and cache.sl_has(cle_nat) else None
            df_reg = cache.sl_get(cle_reg)['df'] if cle_reg and cache.sl_has(cle_reg) else None
            df_df  = cache.sl_get(sel.get('cle_demifin', ''))['df'] \
                     if sel.get('cle_demifin') and cache.sl_has(sel.get('cle_demifin', '')) else None

            if cle_nat and df_nat is None:
                return jsonify({'error': f"Cache expiré pour {disc_id} (national). Ré-importez le fichier."}), 400
            if cle_reg and df_reg is None:
                return jsonify({'error': f"Cache expiré pour {disc_id} (régional). Ré-importez le fichier."}), 400

            parseur = sl_get_discipline(disc_id).get('parseur', '')

            if parseur == 'et':
                data = construire_selection_et(
                    disc_id=disc_id, niveau_id=niveau, df_regional=df_reg,
                    quota_ge=sel.get('quota_ge'),
                    nb_remplacants=int(sel.get('nb_remplacants', 5)),
                    date=sel.get('date', ''), lieu=sel.get('lieu', ''),
                    competition=sel.get('competition', ''),
                    mail_retour=sel.get('mail_retour', 'administration@crege.fr'),
                    date_limite=sel.get('date_limite', ''),
                    date_extranet=sel.get('date_extranet', ''),
                )
            elif parseur == 'chore':
                data = construire_selection_chore(
                    disc_id=disc_id, niveau_id=niveau, df_regional=df_reg,
                    quota_ge=sel.get('quota_ge'),
                    quota_duel=sel.get('quota_duel'),
                    quota_bataille=sel.get('quota_bataille'),
                    quota_ensemble=sel.get('quota_ensemble'),
                    nb_remplacants=int(sel.get('nb_remplacants', 3)),
                    date=sel.get('date', ''), lieu=sel.get('lieu', ''),
                    competition=sel.get('competition', ''),
                    mail_retour=sel.get('mail_retour', 'administration@crege.fr'),
                    date_limite=sel.get('date_limite', ''),
                    date_extranet=sel.get('date_extranet', ''),
                )
            else:
                data = construire_selection_sl(
                    disc_id=disc_id, niveau_id=niveau,
                    df_national=df_nat, df_regional=df_reg, df_demifin=df_df,
                    quota_ge=sel.get('quota_ge'),
                    nb_remplacants=int(sel.get('nb_remplacants', 5)),
                    date=sel.get('date', ''), lieu=sel.get('lieu', ''),
                    competition=sel.get('competition', ''),
                    mail_retour=sel.get('mail_retour', 'administration@crege.fr'),
                    date_limite=sel.get('date_limite', ''),
                    date_extranet=sel.get('date_extranet', ''),
                    arbitrage_config=sel.get('arbitrage_config', {}),
                )

            disc        = next((d for d in DISCIPLINES if d['id'] == disc_id), {})
            nom_feuille = disc.get('label_court', disc_id)[:31]
            selections.append({'nom_feuille': nom_feuille, 'data': data,
                                'niveau_id': niveau, 'disc_id': disc_id})

        date_str = datetime.datetime.now().strftime('%Y%m%d')
        sel_en   = [s for s in selections if s.get('niveau_id') == 'epreuve_nationale']
        sel_cdf  = [s for s in selections if s.get('niveau_id') != 'epreuve_nationale']
        fichiers = []

        for groupe, tag in [(sel_en, 'EN'), (sel_cdf, 'CDF')]:
            if not groupe:
                continue
            if mode == 'separes':
                for nom_f, wb in generer_docs_separes(groupe):
                    nom = f"SelecGE_SL_{tag}_{nom_f.replace('.xlsx','')}_{date_str}.xlsx"
                    wb.save(os.path.join(_get_output_folder(), nom))
                    fichiers.append(nom)
            else:
                wb  = generer_doc_multi(groupe)
                nom = f"SelecGE_SabreLaser_{tag}_{date_str}.xlsx"
                wb.save(os.path.join(_get_output_folder(), nom))
                fichiers.append(nom)

        if not fichiers:
            return jsonify({'error': 'Aucun fichier généré'}), 400

        return jsonify({'status': 'ok', 'fichiers': fichiers,
                        'feuilles': [s['nom_feuille'] for s in selections]})

    except Exception as e:
        return jsonify({'error': str(e), 'detail': traceback.format_exc()}), 500
