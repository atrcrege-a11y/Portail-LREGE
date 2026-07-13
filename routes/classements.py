"""
routes/classements.py — Routes d'import des classements et PDFs.
"""
import os
import tempfile
import traceback

from flask import Blueprint, request, jsonify

from crege_app.core.utils import est_grand_est
from importer_classements_ffe import lire_classement_ffe
from importer_classements_pdf import (
    lire_classement_pdf, lire_classement_ffe_pdf, detecter_wildcards_ffe_pdf,
    lire_classement_ffe_equipes_pdf, lire_classement_engarde_equipes,
)
from crege_app.core.parser_pdf_equipes    import parser_pdf_equipes
from crege_app.core.parser_engarde_equipes import parser_engarde_equipes
import services.cache as cache
from services.validation import (
    ValidationError, valider_fichier, valider_dataframe_classement,
    valider_dataframe_pdf, valider_dataframe_ffe, valider_equipes,
    erreur_json,
    EXTENSIONS_CLASSEMENT, EXTENSIONS_PDF, EXTENSIONS_EQUIPES,
)

bp = Blueprint('classements', __name__)
UPLOAD_FOLDER = tempfile.mkdtemp()


def _apercu_ge(df, cols_voulues):
    """Retourne l'aperçu des tireurs GES + stats."""
    if 'Region' not in df.columns:
        return [], 0, []
    mask    = df['Region'].apply(est_grand_est)
    nb_ge   = int(mask.sum())
    ge_df   = df[mask]
    cols    = [c for c in cols_voulues if c in ge_df.columns]
    apercu  = ge_df[cols].head(10).fillna('').to_dict('records')
    all_ge  = ge_df[cols].fillna('').to_dict('records')
    return apercu, nb_ge, all_ge


@bp.route('/api/upload_classement', methods=['POST'])
def upload_classement():
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400
    f   = request.files['file']
    cle = request.form.get('cle', f"upload_{request.form.get('type','')}_{request.form.get('genre','')}")
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_CLASSEMENT)
        path = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(path)
        df = lire_classement_ffe(path)
        valider_dataframe_classement(df, f.filename)
        cache.set(cle, {"path": path, "df": df})
        apercu, nb_ge, all_ge = _apercu_ge(df, ['Rang', 'Nom', 'Prenom', 'Nom club'])
        return jsonify({
            "status": "ok", "cle": cle, "nb_total": len(df),
            "nb_tireurs": len(df), "nb_grand_est": nb_ge,
            "apercu": apercu, "tireurs_ge": all_ge,
            "filename": f.filename,
        })
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    f   = request.files['fichier']
    cle = request.form.get('cle', f'pdf_{id(f)}')
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_PDF)
        tmp = os.path.join(UPLOAD_FOLDER, f'upload_{cle}.pdf')
        f.save(tmp)
        sections = lire_classement_pdf(tmp)
        valider_dataframe_pdf(sections, f.filename)
        niveaux = {}
        tireurs_ge = {}
        for niv, df in sections.items():
            cle_niv = f'{cle}_{niv}'
            cache.set(cle_niv, {'path': tmp, 'df': df, 'source': 'pdf', 'niveau': niv})
            niveaux[niv] = len(df)
            _, nb_ge, all_ge = _apercu_ge(df, ['Rang', 'Nom', 'Prenom', 'Nom club'])
            tireurs_ge[niv] = {'nb': nb_ge, 'tireurs': all_ge}
        if 'N1' in sections:
            cache.set(cle, {'path': tmp, 'df': sections['N1'], 'source': 'pdf', 'niveau': 'N1'})
        return jsonify({
            'ok': True, 'cle': cle, 'niveaux': niveaux,
            'tireurs_ge': tireurs_ge, 'filename': f.filename,
        })
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        return jsonify({'error': f'Erreur parsing PDF : {e}', 'detail': traceback.format_exc()}), 500


@bp.route('/api/upload_pdf_ffe', methods=['POST'])
def upload_pdf_ffe():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    f   = request.files['fichier']
    cle = request.form.get('cle', f'pdf_ffe_{id(f)}')
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_PDF)
        tmp = os.path.join(UPLOAD_FOLDER, f'upload_{cle}.pdf')
        f.save(tmp)
        df = lire_classement_ffe_pdf(tmp)
        valider_dataframe_ffe(df, f.filename)
        cache.set(cle, {'path': tmp, 'df': df})
        apercu, nb_ge, all_ge = _apercu_ge(df, ['Rang', 'Nom', 'Prenom', 'Nom club', 'Niveau'])
        niveaux = {}
        tireurs_ge_par_niv = {}
        if 'Niveau' in df.columns:
            for niv, grp in df.groupby('Niveau'):
                nb = int(grp['Region'].apply(est_grand_est).sum()) if 'Region' in grp.columns else 0
                ge_grp = grp[grp['Region'].apply(est_grand_est)] if 'Region' in grp.columns else grp
                cols   = [c for c in ['Rang', 'Nom', 'Prenom', 'Nom club'] if c in ge_grp.columns]
                niveaux[niv] = {'total': len(grp), 'grand_est': nb}
                tireurs_ge_par_niv[niv] = ge_grp[cols].fillna('').to_dict('records')
        return jsonify({
            'status': 'ok', 'cle': cle, 'nb_total': len(df),
            'nb_grand_est': nb_ge, 'filename': f.filename,
            'niveaux': niveaux, 'apercu': apercu,
            'tireurs_ge': tireurs_ge_par_niv,
        })
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        return jsonify({'error': str(e), 'detail': traceback.format_exc()}), 500


@bp.route('/api/upload_pdf_ffe_equipes', methods=['POST'])
def upload_pdf_ffe_equipes():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    f   = request.files['fichier']
    cle = request.form.get('cle', f'pdf_eq_{id(f)}')
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_PDF)
        tmp = os.path.join(UPLOAD_FOLDER, f'upload_{cle}.pdf')
        f.save(tmp)
        equipes = lire_classement_ffe_equipes_pdf(tmp)
        valider_equipes(equipes, f.filename)
        cache.set(cle, {'path': tmp, 'equipes': equipes})
        ge = [e for e in equipes if e.get('grand_est')]
        return jsonify({
            'status': 'ok', 'cle': cle, 'nb_total': len(equipes),
            'nb_grand_est': len(ge), 'filename': f.filename,
            'equipes_ge': ge,
        })
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        return jsonify({'error': str(e), 'detail': traceback.format_exc()}), 500


@bp.route('/api/upload_pdf_engarde_eq', methods=['POST'])
def upload_pdf_engarde_eq():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    f   = request.files['fichier']
    cle = request.form.get('cle', f'pdf_reg_{id(f)}')
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_PDF)
        tmp = os.path.join(UPLOAD_FOLDER, f'upload_{cle}.pdf')
        f.save(tmp)
        equipes = lire_classement_engarde_equipes(tmp)
        valider_equipes(equipes, f.filename)
        cache.set(cle, {'path': tmp, 'equipes': equipes, 'source': 'engarde_eq'})
        return jsonify({'ok': True, 'cle': cle, 'equipes': equipes, 'filename': f.filename})
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        return jsonify({'error': f'Erreur parsing Engarde : {e}', 'detail': traceback.format_exc()}), 500


@bp.route('/api/upload_pdf_equipes', methods=['POST'])
def api_upload_pdf_equipes():
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    f     = request.files['fichier']
    fname = f.filename.lower()
    ext   = fname.rsplit('.', 1)[-1] if '.' in fname else ''
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_EQUIPES)
        suffix = f'.{ext}'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        result = parser_pdf_equipes(tmp_path) if ext == 'pdf' else parser_engarde_equipes(tmp_path)
        os.unlink(tmp_path)
        return jsonify(result)
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/upload_pdf_equipes_pages', methods=['POST'])
def api_upload_pdf_equipes_pages():
    """Parse un PDF équipes multi-pages (vétérans) et retourne les résultats par page."""
    from crege_app.core.parser_pdf_equipes import parser_pdf_equipes_pages
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    f = request.files['fichier']
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_EQUIPES)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        pages = parser_pdf_equipes_pages(tmp_path)
        os.unlink(tmp_path)
        return jsonify({'ok': True, 'pages': pages, 'nb_pages': len(pages)})
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/upload_pdf_indiv_veterans', methods=['POST'])
def api_upload_pdf_indiv_veterans():
    """Parse un PDF individuel vétérans multi-pages et retourne les GES par catégorie."""
    from crege_app.core.parser_pdf_equipes import parser_pdf_indiv_veterans
    from crege_app.core.utils import COL_NOM, COL_PRENOM, COL_CLUB, COL_RANG
    if 'fichier' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    f = request.files['fichier']
    try:
        valider_fichier(f.filename, f.content_length or 0, EXTENSIONS_PDF)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        pages = parser_pdf_indiv_veterans(tmp_path)
        os.unlink(tmp_path)

        result = {}
        for cat_id, p in pages.items():
            ge = p["tireurs_ge"]
            ge_list = []
            for _, r in ge.iterrows():
                ge_list.append({
                    "rang":   int(r.get(COL_RANG, 0)),
                    "nom":    str(r.get(COL_NOM, "")),
                    "prenom": str(r.get(COL_PRENOM, r.get("Prenom",""))),
                    "club":   str(r.get(COL_CLUB, r.get("Nom club",""))),
                })
            result[cat_id] = {
                "ge": ge_list,
                "nb_ge": len(ge_list),
                "nb_total": p["nb_total"],
                "cat_label": p["cat_label"],
            }

        return jsonify({"ok": True, "categories": result})
    except ValidationError as e:
        return jsonify(erreur_json(e)), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
