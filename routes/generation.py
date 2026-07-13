"""
routes/generation.py — Routes de generation des documents Excel.
"""
import os
import datetime
import traceback

from flask import Blueprint, request, jsonify, send_file

from crege_app.generateur.excel import generer_multi_genres, generer_equipes_m15
from crege_app.generateur.equipes_seniors import generer_equipes_seniors
from crege_app.categories.equipes_m15 import construire_equipes_m15
from crege_app.categories.equipes_seniors import construire_equipes_seniors
from crege_app.categories.selection import construire_selection
from crege_app.core.quotas_lrege import get_quotas_complets
from crege_app.core.calendrier_cdf import get_cdf_individuel, get_cdf_equipes, get_demi_finale_equipes
from crege_app.core.reglementation import N2_OPEN_CIRCUIT, N2_FFE_N3_QUOTA, N1_FFE_N2_QUOTA

import services.cache as cache
from services.construction import (
    build_cfg, construire_genre, nom_fichier_selection, slug, CATEGORIES,
)
from services.export_plateforme import (
    construire_payload, construire_payload_equipes_m15,
    construire_payload_equipes_seniors, envoyer_payload,
)

bp = Blueprint('generation', __name__)


def _get_output_folder():
    from flask import current_app
    return current_app.config['OUTPUT_FOLDER']


def _df_cache(cle):
    """DataFrame depuis le cache, ou None."""
    if not cle or not cache.has(cle):
        return None
    entry = cache.get(cle)
    return entry['df'] if entry else None


def construire_data_multi(params):
    """Construit (data_h, data_d) pour la génération individuelle multi-genres.

    SOURCE UNIQUE partagée par /api/generer_multi (Excel) et
    /api/envoyer_plateforme (confirmation). Toute modif de la règle de
    construction se fait ici, pas en double.
    """
    def construire(cle_nat, cle_reg, genre):
        s             = genre.lower()
        cat_id        = params.get('cat_id', 'Seniors')
        arme_id       = params.get('arme_id', 'E')
        cfg, _        = build_cfg(params, genre)

        cle_pdf_raw   = params.get(f'cle_pdf_{s}')
        cle_nat_xl    = params.get(f'cle_national_{s}')

        df_ffe_raw = _df_cache(cle_pdf_raw)
        df_ffe = df_ffe_raw if (df_ffe_raw is not None and 'Niveau' in df_ffe_raw.columns) else None

        df_nat_xl = _df_cache(cle_nat_xl)
        if (df_nat_xl is not None
                and 'Niveau' not in df_nat_xl.columns
                and cle_nat_xl != cle_pdf_raw):
            df_nat = df_nat_xl
        elif df_ffe_raw is not None and 'Niveau' not in df_ffe_raw.columns:
            df_nat = df_ffe_raw
        else:
            df_nat = None

        df_reg = _df_cache(cle_reg)

        if df_ffe is None and df_nat is None and df_reg is None:
            return None

        return construire_selection(cat_id, arme_id, genre, cfg,
                                    df_nat=df_nat, df_reg=df_reg, df_ffe=df_ffe)

    data_h = construire(params.get('cle_national_h'), params.get('cle_regional_h'), 'H')
    data_d = construire(params.get('cle_national_d'), params.get('cle_regional_d'), 'D')
    return data_h, data_d


@bp.route('/api/generer_multi', methods=['POST'])
def generer_multi():
    params = request.json

    try:
        data_h, data_d = construire_data_multi(params)

        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement charge"}), 400

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


@bp.route('/api/envoyer_plateforme', methods=['POST'])
def envoyer_plateforme():
    """Envoie la sélection individuelle vers la plateforme de confirmation.

    Reçoit les MÊMES params que /api/generer_multi, reconstruit data_h/data_d
    (source unique construire_data_multi), sérialise au contrat plateforme et
    POST. N'altère pas la génération Excel (bouton séparé conservé).
    """
    params = request.json or {}
    try:
        data_h, data_d = construire_data_multi(params)
        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement charge"}), 400

        payload = construire_payload(params, data_h, data_d)
        ok, status, body = envoyer_payload(payload)
        if not ok:
            return jsonify({"error": "Envoi plateforme echoue",
                            "status": status, "detail": body}), 502
        return jsonify({
            "status": "ok",
            "competition": payload["competition"]["nom"],
            "nb_qualifies": len(payload["qualifies"]),
            "plateforme": body,
        })
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


def construire_data_equipes_m15(params):
    """(data_h, data_d) equipes M15 -- SOURCE UNIQUE Excel + plateforme."""
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
    return data_h, data_d


@bp.route('/api/generer_equipes_m15', methods=['POST'])
def generer_equipes_m15_route():
    params = request.json
    try:
        data_h, data_d = construire_data_equipes_m15(params)
        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement regional charge"}), 400
        wb  = generer_equipes_m15(data_h, data_d)
        nom = nom_fichier_selection({**params, "cat": "M15", "genre": "HD"}, mode="equipes")
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"status": "ok", "fichier": nom,
                        "nb_feuilles": sum(1 for d in [data_h, data_d] if d)})
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/envoyer_plateforme_equipes_m15', methods=['POST'])
def envoyer_plateforme_equipes_m15():
    """Envoie la selection EQUIPES M15 vers la plateforme (Excel conserve)."""
    params = request.json or {}
    try:
        data_h, data_d = construire_data_equipes_m15(params)
        if not data_h and not data_d:
            return jsonify({"error": "Aucun classement regional charge"}), 400
        payload = construire_payload_equipes_m15(params, data_h, data_d)
        ok, status, body = envoyer_payload(payload)
        if not ok:
            return jsonify({"error": "Envoi plateforme echoue",
                            "status": status, "detail": body}), 502
        return jsonify({"status": "ok",
                        "competition": payload["competition"]["nom"],
                        "nb_qualifies": len(payload["qualifies"]),
                        "plateforme": body})
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


def construire_data_equipes_seniors(params):
    """data équipes séniors (M17→Vétérans) -- SOURCE UNIQUE Excel + plateforme.

    Toute modif de la règle de construction doit passer ici pour rester
    cohérente entre /api/generer_equipes_seniors et /api/envoyer_plateforme_equipes_seniors.
    """
    cat_id  = params.get('cat_id', 'Seniors')
    arme_id = params.get('arme_id', 'E')

    def parse_equipes(raw):
        if not raw:
            return []
        return [{"rang": e.get("rang", ""), "nom_equipe": e.get("nom_equipe", ""),
                 "club": e.get("club", "")} for e in raw if e.get("nom_equipe", "").strip()]

    eq_n1n2_h     = parse_equipes(params.get('equipes_n1n2_h',   []))
    eq_n2_h       = parse_equipes(params.get('equipes_n2_h',     []))
    eq_n1n2_d     = parse_equipes(params.get('equipes_n1n2_d',   []))
    eq_n2_d       = parse_equipes(params.get('equipes_n2_d',     []))
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
    data['equipes_n2_H'] = eq_n2_h
    data['equipes_n2_D'] = eq_n2_d
    taille_defaut     = 5 if cat_id in ('V1', 'V2', 'V3', 'V4') else 4
    data['taille_equipe'] = int(params.get('taille_equipe', taille_defaut))
    data['nb_open_n3']    = int(params.get('nb_open_n3', 0))
    return data


@bp.route('/api/generer_equipes_seniors', methods=['POST'])
def api_generer_equipes_seniors():
    try:
        params = request.get_json(force=True)
        data   = construire_data_equipes_seniors(params)

        wb    = generer_equipes_seniors(data)
        arme_id = params.get('arme_id', 'E')
        arme  = {'E': 'Epee', 'F': 'Fleuret', 'S': 'Sabre'}.get(arme_id, arme_id)
        cat   = slug(params.get('cat_id', 'Seniors'))
        comp  = slug(params.get('competition', 'CDF'))
        fname = f"LREGE_GE_{cat}_EQ_{comp}_{arme}_HD_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
        wb.save(os.path.join(_get_output_folder(), fname))

        return jsonify({'fichier': fname, 'feuilles': ['Hommes', 'Dames'],
                        'mode_n3_h': data['mode_n3_h'], 'mode_n3_d': data['mode_n3_d']})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/envoyer_plateforme_equipes_seniors', methods=['POST'])
def envoyer_plateforme_equipes_seniors():
    """Envoie la sélection ÉQUIPES SÉNIORS vers la plateforme (Excel conservé)."""
    params = request.get_json(force=True) or {}
    try:
        data    = construire_data_equipes_seniors(params)
        payload = construire_payload_equipes_seniors(params, data)
        if not payload["qualifies"]:
            return jsonify({"error": "Aucune équipe à envoyer (listes vides)"}), 400
        ok, status, body = envoyer_payload(payload)
        if not ok:
            return jsonify({"error": "Envoi plateforme echoue",
                            "status": status, "detail": body}), 502
        return jsonify({"status": "ok",
                        "competition": payload["competition"]["nom"],
                        "nb_qualifies": len(payload["qualifies"]),
                        "plateforme": body})
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


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
        return jsonify({'error': 'Parametres cat et arme requis'}), 400
    quotas = get_quotas_complets(cat_id, arme_id)
    if mode == 'equipes':
        quotas['cdf']         = get_cdf_equipes(cat_id, arme_id)
        quotas['demi_finale'] = get_demi_finale_equipes(cat_id, arme_id)
    else:
        quotas['cdf'] = get_cdf_individuel(cat_id, arme_id)
    return jsonify(quotas)


def construire_data_equipes_veterans(params):
    """data équipes vétérans épée — SOURCE UNIQUE Excel + plateforme."""
    def _eq(key): return params.get(key, []) or []

    return {
            "meta": {
                "competition":              params.get("competition", "Championnat de France Veterans"),
                "date":                     params.get("date", ""),
                "lieu":                     params.get("lieu", ""),
                "mail_retour":              params.get("mail_retour", "administration@crege.fr"),
                "date_limite_retour":       params.get("date_limite_retour", ""),
                "date_engagement_extranet": params.get("date_engagement_extranet", ""),
                "arbitrage_config":         params.get("arbitrage_config", {}),
            },
            "equipes_n1n2_ehv":  _eq("equipes_n1n2_ehv"),
            "equipes_n1n2_ehgv": _eq("equipes_n1n2_ehgv"),
            "equipes_n1n2_edv":  _eq("equipes_n1n2_edv"),
            "equipes_n3_ehv":    _eq("equipes_n3_ehv"),
            "equipes_n3_ehgv":   _eq("equipes_n3_ehgv"),
            "equipes_n3_edv":    _eq("equipes_n3_edv"),
            "quota_n3_ehv":  int(params.get("quota_n3_ehv",  2)),
            "quota_n3_ehgv": int(params.get("quota_n3_ehgv", 2)),
            "quota_n3_edv":  int(params.get("quota_n3_edv",  1)),
            "texte_reg_ehv":  params.get("texte_reg_ehv",  ""),
            "texte_reg_ehgv": params.get("texte_reg_ehgv", ""),
            "texte_reg_edv":  params.get("texte_reg_edv",  ""),
        }


@bp.route('/api/generer_equipes_veterans', methods=['POST'])
def api_generer_equipes_veterans():
    from crege_app.generateur.equipes_veterans import generer_equipes_veterans

    params = request.json
    try:
        data = construire_data_equipes_veterans(params)
        wb  = generer_equipes_veterans(data)
        nom = nom_fichier_selection({**params, "cat": "Veterans", "genre": "HD"}, mode="equipes")
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"ok": True, "filename": nom, "url": f"/api/telecharger/{nom}"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Vétérans épée : les 32 premiers du classement national FFE sont qualifiés
# directement en N1 (REGLES.md §1.7 + texte réglementaire de l'Excel).
N1_FFE_CUTOFF_VETERANS = 32


def _ge_seulement(df):
    """Filtre Grand Est d'un classement (via colonne Region), ou df inchangé."""
    if df is None or "Region" not in getattr(df, "columns", []):
        return df
    from crege_app.core.utils import est_grand_est
    return df[df["Region"].apply(est_grand_est)].reset_index(drop=True)


def construire_data_indiv_veterans(params):
    """data indiv vétérans épée — SOURCE UNIQUE Excel + plateforme.

    L'UI n'envoie que les clés de cache des classements BRUTS :
    - ge_ffe (section N1) est DÉRIVÉ ici = tireurs GE parmi les
      N1_FFE_CUTOFF_VETERANS premiers du classement national
      (surchargable par params `ge_ffe_v1/v2/v3` si fourni non vide) ;
    - ge_nat / ge_reg sont filtrés Grand Est (le générateur prend les
      quotas dans l'ordre, hors tireurs déjà qualifiés N1).
    """
    data = {
        "meta": {
            "competition":              params.get("competition", "Championnat de France Veterans"),
            "date":                     params.get("date", ""),
            "lieu":                     params.get("lieu", ""),
            "mail_retour":              params.get("mail_retour", "administration@crege.fr"),
            "date_limite_retour":       params.get("date_limite_retour", ""),
            "date_engagement_extranet": params.get("date_engagement_extranet", ""),
            "arbitrage_config":         params.get("arbitrage_config", {}),
        }
    }
    for cat in ["V1", "V2", "V3"]:
        c = cat.lower()
        ge_nat = _ge_seulement(_df_cache(params.get(f"cle_nat_{c}")))
        ge_reg = _ge_seulement(_df_cache(params.get(f"cle_reg_{c}")))

        ge_ffe = params.get(f"ge_ffe_{c}") or []
        if not ge_ffe and ge_nat is not None and "Rang" in ge_nat.columns:
            ge_ffe = ge_nat[ge_nat["Rang"] <= N1_FFE_CUTOFF_VETERANS]

        data[cat] = {
            "ge_ffe":    ge_ffe,
            "ge_nat":    ge_nat,
            "ge_reg":    ge_reg,
            "quota_nat": int(params.get(f"quota_nat_{c}", 1)),
            "quota_reg": int(params.get(f"quota_reg_{c}", 3)),
        }
    return data


@bp.route('/api/generer_indiv_veterans', methods=['POST'])
def api_generer_indiv_veterans():
    from crege_app.generateur.indiv_veterans import generer_indiv_veterans

    params = request.json
    try:
        data = construire_data_indiv_veterans(params)
        wb  = generer_indiv_veterans(data)
        nom = nom_fichier_selection({**params, "cat": "Veterans_Indiv"}, mode="individuel")
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"ok": True, "filename": nom, "url": f"/api/telecharger/{nom}"})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route('/api/generer_equipes_veterans_fs', methods=['POST'])
def api_generer_equipes_veterans_fs():
    from crege_app.generateur.equipes_veterans_fs import generer_equipes_veterans_fs
    params = request.json
    try:
        arme_id = params.get("arme_id", "F")
        data = {
            "meta": {
                "competition":              params.get("competition", "Championnat de France Veterans"),
                "date":                     params.get("date", ""),
                "lieu":                     params.get("lieu", ""),
                "mail_retour":              params.get("mail_retour", "administration@crege.fr"),
                "date_limite_retour":       params.get("date_limite_retour", ""),
                "date_engagement_extranet": params.get("date_engagement_extranet", ""),
                "arbitrage_config":         params.get("arbitrage_config", {}),
            }
        }
        wb  = generer_equipes_veterans_fs(data, arme=arme_id)
        nom = nom_fichier_selection(
            {**params, "cat": "Veterans_EQ", "arme": arme_id, "genre": "HD"},
            mode="equipes"
        )
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"ok": True, "filename": nom, "url": f"/api/telecharger/{nom}"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def construire_data_indiv_veterans_fs(params):
    """data indiv vétérans F/S — SOURCE UNIQUE Excel + plateforme."""
    data = {
        "meta": {
            "competition":              params.get("competition", "Championnat de France Veterans"),
            "date":                     params.get("date", ""),
            "lieu":                     params.get("lieu", ""),
            "mail_retour":              params.get("mail_retour", "administration@crege.fr"),
            "date_limite_retour":       params.get("date_limite_retour", ""),
            "date_engagement_extranet": params.get("date_engagement_extranet", ""),
            "arbitrage_config":         params.get("arbitrage_config", {}),
        }
    }
    for cat in ["V1", "V2", "V3", "V4"]:
        c = cat.lower()
        data[cat] = {
            "ge_nat_h": _df_cache(params.get(f"cle_nat_{c}_h")),
            "ge_nat_d": _df_cache(params.get(f"cle_nat_{c}_d")),
        }
    return data


@bp.route('/api/generer_indiv_veterans_fs', methods=['POST'])
def api_generer_indiv_veterans_fs():
    from crege_app.generateur.indiv_veterans_fs import generer_indiv_veterans_fs
    params = request.json
    try:
        arme_id = params.get("arme_id", "F")
        data = construire_data_indiv_veterans_fs(params)
        wb  = generer_indiv_veterans_fs(data, arme=arme_id)
        nom = nom_fichier_selection(
            {**params, "cat": "Veterans_Indiv", "arme": arme_id, "genre": "HD"},
            mode="individuel"
        )
        wb.save(os.path.join(_get_output_folder(), nom))
        return jsonify({"ok": True, "filename": nom, "url": f"/api/telecharger/{nom}"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Envoi plateforme VÉTÉRANS (bibliothèque services/payloads/) ────────
# Mêmes params que les routes generer_* : le classeur est régénéré EN
# MÉMOIRE (source unique = l'Excel que voient les clubs) puis parsé.

def _envoyer_valide(payload, regle_id):
    """Validation regles.py + envoi. Retourne la réponse Flask."""
    from services.payloads import valider_payload, ValidationPayloadError
    try:
        valider_payload(payload, regle_id)
    except ValidationPayloadError as e:
        return jsonify({"error": f"Payload rejeté par la validation : {e}"}), 400
    ok, status, body = envoyer_payload(payload)
    if not ok:
        return jsonify({"error": "Envoi plateforme echoue",
                        "status": status, "detail": body}), 502
    return jsonify({"status": "ok",
                    "competition": payload["competition"]["nom"],
                    "nb_qualifies": len(payload["qualifies"]),
                    "plateforme": body})


@bp.route('/api/envoyer_plateforme_indiv_veterans', methods=['POST'])
def api_envoyer_plateforme_indiv_veterans():
    """Envoie l'INDIV VÉTÉRANS ÉPÉE vers la plateforme (Excel conservé)."""
    from crege_app.generateur.indiv_veterans import generer_indiv_veterans
    from services.payloads import construire_payload_indiv_veterans
    params = request.json or {}
    try:
        data = construire_data_indiv_veterans(params)
        wb   = generer_indiv_veterans(data)
        payload = construire_payload_indiv_veterans(params, wb, data["meta"])
        return _envoyer_valide(payload, "vet_indiv_epee")
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/envoyer_plateforme_indiv_veterans_fs', methods=['POST'])
def api_envoyer_plateforme_indiv_veterans_fs():
    """Envoie l'INDIV VÉTÉRANS FLEURET/SABRE (listes open de référence)."""
    from crege_app.generateur.indiv_veterans_fs import generer_indiv_veterans_fs
    from services.payloads import construire_payload_indiv_veterans_fs
    params = request.json or {}
    try:
        arme_id = params.get("arme_id", "F")
        data = construire_data_indiv_veterans_fs(params)
        wb   = generer_indiv_veterans_fs(data, arme=arme_id)
        payload = construire_payload_indiv_veterans_fs(params, wb, data["meta"], arme_id)
        return _envoyer_valide(payload, "vet_indiv_fs")
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


@bp.route('/api/envoyer_plateforme_equipes_veterans', methods=['POST'])
def api_envoyer_plateforme_equipes_veterans():
    """Envoie les ÉQUIPES VÉTÉRANS ÉPÉE. (Équipes F/S open : pas d'export,
    l'Excel ne contient que des placeholders vides.)"""
    from crege_app.generateur.equipes_veterans import generer_equipes_veterans
    from services.payloads import construire_payload_equipes_veterans
    params = request.json or {}
    try:
        data = construire_data_equipes_veterans(params)
        wb   = generer_equipes_veterans(data)
        payload = construire_payload_equipes_veterans(params, wb, data["meta"])
        return _envoyer_valide(payload, "vet_equipes_epee")
    except Exception as e:
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500
