"""
routes/generation.py — Routes de génération des documents Excel.
"""
import os
import datetime
import traceback

from flask import Blueprint, request, jsonify, send_file

from crege_app.generateur.excel import generer_multi_genres, generer_equipes_m15
from crege_app.generateur.equipes_seniors import generer_equipes_seniors
from crege_app.categories.equipes_m15 import construire_equipes_m15
from crege_app.categories.equipes_seniors import construire_equipes_seniors
from crege_app.core.quotas_lrege import get_quotas_complets
from crege_app.core.calendrier_cdf import get_cdf_individuel, get_cdf_equipes, get_demi_finale_equipes
from crege_app.core.reglementation import N2_OPEN_CIRCUIT, N2_FFE_N3_QUOTA, N1_FFE_N2_QUOTA

import services.cache as cache
from services.construction import (
    build_cfg, construire_genre_seniors, construire_genre_jeunes,
    construire_genre_open_circuit, construire_genre_ffe_n1n2_n3quota,
    construire_genre_n1_ffe_n2_quota, nom_fichier_selection, slug, CATEGORIES,
)

bp = Blueprint('generation', __name__)


def _get_output_folder():
    from flask import current_app
    return current_app.config['OUTPUT_FOLDER']


@bp.route('/api/generer_multi', methods=['POST'])
def generer_multi():
    params    = request.json
    fmt       = params.get('format', 'seniors')
    cle_nat_h = params.get('cle_national_h')
    cle_reg_h = params.get('cle_regional_h')
    cle_nat_d = params.get('cle_national_d')
    cle_reg_d = params.get('cle_regional_d')

    try:
        def construire(cle_nat, cle_reg, genre):
            s          = genre.lower()
            cle_pdf    = params.get(f'cle_pdf_{s}')
            cle_pdf_n2 = params.get(f'cle_pdf_n2_{s}')
            n2_mode    = params.get('n2_mode', '')

            if n2_mode == 'open_circuit':
                def _df_niveau(cle, niv):
                    if not cle:
                        return None
                    entry = cache.get(f'{cle}_{niv}') or cache.get(cle)
                    if not entry:
                        return None
                    df_all = entry['df']
                    if f'{cle}_{niv}' in cache.raw():
                        return df_all
                    if 'Niveau' in df_all.columns:
                        sub = df_all[df_all['Niveau'] == niv].copy()
                        return sub if not sub.empty else None
                    return df_all

                df_n1 = _df_niveau(cle_pdf, 'N1')
                df_n2 = (_df_niveau(cle_pdf_n2, 'N2') or _df_niveau(cle_pdf_n2, 'N1')
                         or _df_niveau(cle_pdf, 'N2'))
                df_nat = cache.get(cle_nat)['df'] if cle_nat and cache.has(cle_nat) else None
                if df_n1 is None and df_n2 is None:
                    return None
                return construire_genre_open_circuit(params, genre, df_n1, df_n2, df_nat)

            # Mode FH M17/M20 Fleuret/Épée : N1+N2 PDF FFE, N3 quotas LREGE
            regle_n2_mode = build_cfg(params, genre)[0].get('n2_mode', '')
            if regle_n2_mode == N2_FFE_N3_QUOTA:
                def _df_niv(cle, niv):
                    if not cle:
                        return None
                    entry = cache.get(cle)
                    if not entry:
                        return None
                    df_all = entry['df']
                    if 'Niveau' in df_all.columns:
                        sub = df_all[df_all['Niveau'] == niv].copy()
                        return sub if not sub.empty else None
                    return df_all
                df_n1  = _df_niv(cle_pdf, 'N1')
                df_n2  = _df_niv(cle_pdf, 'N2')
                # df_nat : classement Excel national si disponible, sinon PDF FFE complet
                cle_nat_excel = params.get(f'cle_national_{s}')
                _entry_nat_xl = cache.get(cle_nat_excel) if cle_nat_excel and cache.has(cle_nat_excel) else None
                if _entry_nat_xl and 'Niveau' not in _entry_nat_xl['df'].columns:
                    df_nat = _entry_nat_xl['df']
                else:
                    _entry_nat = cache.get(cle_nat) if cle_nat and cache.has(cle_nat) else None
                    df_nat = _entry_nat['df'] if _entry_nat else None
                df_reg = cache.get(cle_reg)['df'] if cle_reg and cache.has(cle_reg) else None
                return construire_genre_ffe_n1n2_n3quota(params, genre, df_n1, df_n2, df_nat, df_reg)

            # Mode FD M17/M20 Fleuret/Épée : N1 PDF FFE, N2 quotas LREGE
            if regle_n2_mode == N1_FFE_N2_QUOTA:
                def _df_n1_only(cle, niv):
                    if not cle:
                        return None
                    entry = cache.get(cle)
                    if not entry:
                        return None
                    df_all = entry['df']
                    if 'Niveau' in df_all.columns:
                        sub = df_all[df_all['Niveau'] == niv].copy()
                        return sub if not sub.empty else None
                    return df_all
                df_n1  = _df_n1_only(cle_pdf, 'N1')
                # df_nat : classement Excel national si disponible
                cle_nat_excel = params.get(f'cle_national_{s}')
                _entry_nat_xl2 = cache.get(cle_nat_excel) if cle_nat_excel and cache.has(cle_nat_excel) else None
                if _entry_nat_xl2 and 'Niveau' not in _entry_nat_xl2['df'].columns:
                    df_nat = _entry_nat_xl2['df']
                else:
                    _entry_nat2 = cache.get(cle_nat) if cle_nat and cache.has(cle_nat) else None
                    df_nat = _entry_nat2['df'] if _entry_nat2 else None
                df_reg = cache.get(cle_reg)['df'] if cle_reg and cache.has(cle_reg) else None
                return construire_genre_n1_ffe_n2_quota(params, genre, df_n1, df_nat, df_reg)

            # Mode standard
            df_nat = None
            if cle_pdf and cache.has(f'{cle_pdf}_N1'):
                entry = cache.get(f'{cle_pdf}_N1')
                if entry: df_nat = entry['df']
            elif cle_pdf and cache.has(cle_pdf):
                entry = cache.get(cle_pdf)
                if entry: df_nat = entry['df']
            elif not cle_reg or not cache.has(cle_reg):
                return None

            df_reg = None
            if cle_reg and cache.has(cle_reg):
                entry = cache.get(cle_reg)
                if entry: df_reg = entry['df']
            if df_reg is None:
                df_reg = df_nat
            if df_nat is None and params.get('cat_id') != 'M23':
                if cle_nat and cache.has(cle_nat):
                    entry = cache.get(cle_nat)
                    if entry: df_nat = entry['df']

            fn = construire_genre_jeunes if fmt == 'jeunes' else construire_genre_seniors
            if fmt == 'seniors':
                # Passer le PDF FFE complet (N1/N2/N3) pour filtrer les qualifiés FFE
                df_ffe = None
                if cle_pdf and cache.has(cle_pdf):
                    entry_ffe = cache.get(cle_pdf)
                    if entry_ffe and 'Niveau' in entry_ffe['df'].columns:
                        df_ffe = entry_ffe['df']
                return construire_genre_seniors(params, genre, df_nat, df_reg, df_ffe=df_ffe)
            return fn(params, genre, df_nat, df_reg)

        data_h = construire(cle_nat_h, cle_reg_h, 'H')
        data_d = construire(cle_nat_d, cle_reg_d, 'D')

        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement chargé"}), 400

        wb  = generer_multi_genres(data_h, data_d)
        nom = nom_fichier_selection({**params, "genre": "HD",
                                     "cat": params.get("cat_id", ""),
                                     "arme": params.get("arme_id", "")})
        wb.save(os.path.join(_get_output_folder(), nom))
        feuilles = [f for f, d in [('Hommes', data_h), ('Dames', data_d)] if d]
        nb = sum(sum(len(s.get('tireurs', [])) for s in d.get('sections', []))
                 for d in [data_h, data_d] if d)
        return jsonify({"status": "ok", "fichier": nom, "feuilles": feuilles, "nb_tireurs": nb})

    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/generer_equipes_m15', methods=['POST'])
def generer_equipes_m15_route():
    params = request.json
    try:
        data_h = data_d = None
        for genre, cle_nat, cle_reg in [
            ('H', params.get('cle_national_h'), params.get('cle_regional_h')),
            ('D', params.get('cle_national_d'), params.get('cle_regional_d')),
        ]:
            if not cle_reg or not cache.has(cle_reg):
                continue
            df_nat = cache.get(cle_nat)['df'] if cle_nat and cache.has(cle_nat) else None
            df_reg = cache.get(cle_reg)['df']
            cfg, _ = build_cfg(params, genre)
            cfg['taille_equipe'] = params.get('taille_equipe', 4)
            date_ind = cfg.get('date', '')
            if date_ind:
                try:
                    from datetime import datetime as dt, timedelta
                    for fmt_d in ('%d/%m/%Y', '%Y-%m-%d'):
                        try:
                            d = dt.strptime(date_ind.strip(), fmt_d)
                            cfg['date'] = (d + timedelta(days=1)).strftime('%d/%m/%Y')
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            data = construire_equipes_m15(df_nat if df_nat is not None else df_reg, df_reg, cfg)
            if genre == 'H':
                data_h = data
            else:
                data_d = data
        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement régional chargé"}), 400
        wb  = generer_equipes_m15(data_h, data_d)
        nom = nom_fichier_selection({**params, "cat": "M15", "genre": "HD"}, mode="equipes")
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"status": "ok", "fichier": nom,
                        "nb_feuilles": sum(1 for d in [data_h, data_d] if d)})
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/generer_equipes_seniors', methods=['POST'])
def api_generer_equipes_seniors():
    try:
        params  = request.get_json(force=True)
        cat_id  = params.get('cat_id', 'Seniors')
        arme_id = params.get('arme_id', 'E')

        def parse_equipes(raw):
            if not raw:
                return []
            return [{"rang": e.get("rang", ""), "nom_equipe": e.get("nom_equipe", ""),
                     "club": e.get("club", "")} for e in raw if e.get("nom_equipe", "").strip()]

        eq_n1n2_h     = parse_equipes(params.get('equipes_n1n2_h',   []))
        eq_n1n2_d     = parse_equipes(params.get('equipes_n1n2_d',   []))
        eq_n3_ffe_h   = parse_equipes(params.get('equipes_n3_ffe_h', []))
        eq_n3_ffe_d   = parse_equipes(params.get('equipes_n3_ffe_d', []))
        eq_n3_h       = parse_equipes(params.get('equipes_n3_h',     []))
        eq_n3_d       = parse_equipes(params.get('equipes_n3_d',     []))
        remplacants_h = parse_equipes(params.get('remplacants_h',    []))
        remplacants_d = parse_equipes(params.get('remplacants_d',    []))

        cfg = {
            'cat_id':                   cat_id,
            'arme_id':                  arme_id,
            'competition':              params.get('competition', ''),
            'date':                     params.get('date', ''),
            'lieu':                     params.get('lieu', ''),
            'discipline':               params.get('discipline', ''),
            'mail_retour':              params.get('mail_retour', ''),
            'date_limite_retour':       params.get('date_limite_retour', ''),
            'date_engagement_extranet': params.get('date_engagement_extranet', ''),
            'arbitrage_config':         params.get('arbitrage_config', {}),
            'quota_n3_eq_h':            int(params.get('quota_n3_eq_h', 0)),
            'quota_n3_eq_d':            int(params.get('quota_n3_eq_d', 0)),
            'nb_open_n3':               int(params.get('nb_open_n3', 0)),
        }

        data = construire_equipes_seniors(
            eq_n1n2_h, eq_n1n2_d, eq_n3_ffe_h, eq_n3_ffe_d,
            eq_n3_h, eq_n3_d, cfg,
            remplacants_h=remplacants_h, remplacants_d=remplacants_d,
        )
        taille_defaut     = 5 if cat_id in ('V1', 'V2', 'V3', 'V4') else 4
        data['taille_equipe'] = int(params.get('taille_equipe', taille_defaut))
        data['nb_open_n3']    = int(params.get('nb_open_n3', 0))

        wb    = generer_equipes_seniors(data)
        arme  = {'E': 'Epee', 'F': 'Fleuret', 'S': 'Sabre'}.get(arme_id, arme_id)
        cat   = slug(cat_id)
        comp  = slug(params.get('competition', 'CDF'))
        fname = f"LREGE_GE_{cat}_EQ_{comp}_{arme}_HD_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
        wb.save(os.path.join(_get_output_folder(), fname))

        return jsonify({'fichier': fname, 'feuilles': ['Hommes', 'Dames'],
                        'mode_n3_h': data['mode_n3_h'], 'mode_n3_d': data['mode_n3_d']})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/telecharger/<nom_fichier>')
def telecharger(nom_fichier):
    chemin = os.path.join(_get_output_folder(), nom_fichier)
    if not os.path.exists(chemin):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(chemin, as_attachment=True)


@bp.route('/api/quotas_defaut', methods=['GET'])
def api_quotas_defaut():
    cat_id  = request.args.get('cat', '')
    arme_id = request.args.get('arme', '')
    mode    = request.args.get('mode', 'individuel')
    if not cat_id or not arme_id:
        return jsonify({'error': 'Paramètres cat et arme requis'}), 400
    quotas = get_quotas_complets(cat_id, arme_id)
    if mode == 'equipes':
        quotas['cdf']         = get_cdf_equipes(cat_id, arme_id)
        quotas['demi_finale'] = get_demi_finale_equipes(cat_id, arme_id)
    else:
        quotas['cdf'] = get_cdf_individuel(cat_id, arme_id)
    return jsonify(quotas)
