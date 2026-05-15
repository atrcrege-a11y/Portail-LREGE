"""
build.py — Repackage SelecGE.py depuis les fichiers sources.

Usage :
    python build.py                  # repackage uniquement
    python build.py --commit         # repackage + git commit automatique
    python build.py --version 35     # force le numéro de version
    python build.py --commit --version 35

Le script :
  1. Lit chaque fichier source
  2. Encode en base64/zlib
  3. Remplace le blob correspondant dans SelecGE.py
  4. Met à jour le numéro de version dans SelecGE.py
  5. (optionnel) Fait un git commit avec le message de version
"""

import os
import re
import sys
import base64
import zlib
import argparse
import subprocess
import datetime

# ── Répertoire racine ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP = os.path.join(ROOT, 'SelecGE.py')

# ── Mapping (chemin relatif → variable b64 dans SelecGE.py) ──────────
FICHIERS = [
    ('app.py',                                              'b64_app_py'),
    ('importer_classements_ffe.py',                         'b64_importer_classements_ffe_py'),
    ('importer_classements_pdf.py',                         'b64_importer_classements_pdf_py'),
    ('services/__init__.py',                                'b64_services___init___py'),
    ('services/cache.py',                                   'b64_services_cache_py'),
    ('services/construction.py',                            'b64_services_construction_py'),
    ('services/validation.py',                              'b64_services_validation_py'),
    ('routes/__init__.py',                                  'b64_routes___init___py'),
    ('routes/misc.py',                                      'b64_routes_misc_py'),
    ('routes/classements.py',                               'b64_routes_classements_py'),
    ('routes/generation.py',                                'b64_routes_generation_py'),
    ('routes/sabre_laser.py',                               'b64_routes_sabre_laser_py'),
    ('crege_app/__init__.py',                               'b64_crege_app___init___py'),
    ('crege_app/core/__init__.py',                          'b64_crege_app_core___init___py'),
    ('crege_app/core/styles.py',                            'b64_crege_app_core_styles_py'),
    ('crege_app/core/utils.py',                             'b64_crege_app_core_utils_py'),
    ('crege_app/core/feuille.py',                           'b64_crege_app_core_feuille_py'),
    ('crege_app/core/reglementation.py',                    'b64_crege_app_core_reglementation_py'),
    ('crege_app/core/quotas_lrege.py',                      'b64_crege_app_core_quotas_lrege_py'),
    ('crege_app/core/calendrier_cdf.py',                    'b64_crege_app_core_calendrier_cdf_py'),
    ('crege_app/core/parser_pdf_equipes.py',                'b64_crege_app_core_parser_pdf_equipes_py'),
    ('crege_app/core/parser_engarde_equipes.py',            'b64_crege_app_core_parser_engarde_equipes_py'),
    ('crege_app/categories/__init__.py',                    'b64_crege_app_categories___init___py'),
    ('crege_app/categories/base.py',                        'b64_crege_app_categories_base_py'),
    ('crege_app/categories/jeunes.py',                      'b64_crege_app_categories_jeunes_py'),
    ('crege_app/categories/seniors.py',                     'b64_crege_app_categories_seniors_py'),
    ('crege_app/categories/equipes_m15.py',                 'b64_crege_app_categories_equipes_m15_py'),
    ('crege_app/categories/equipes_seniors.py',             'b64_crege_app_categories_equipes_seniors_py'),
    ('crege_app/generateur/__init__.py',                    'b64_crege_app_generateur___init___py'),
    ('crege_app/generateur/sections.py',                    'b64_crege_app_generateur_sections_py'),
    ('crege_app/generateur/equipes.py',                     'b64_crege_app_generateur_equipes_py'),
    ('crege_app/generateur/equipes_seniors.py',             'b64_crege_app_generateur_equipes_seniors_py'),
    ('crege_app/generateur/excel.py',                       'b64_crege_app_generateur_excel_py'),
    ('crege_app/sabre_laser/__init__.py',                   'b64_crege_app_sabre_laser___init___py'),
    ('crege_app/sabre_laser/config.py',                     'b64_crege_app_sabre_laser_config_py'),
    ('crege_app/sabre_laser/parseurs.py',                   'b64_crege_app_sabre_laser_parseurs_py'),
    ('crege_app/sabre_laser/selection.py',                  'b64_crege_app_sabre_laser_selection_py'),
    ('crege_app/sabre_laser/generateur.py',                 'b64_crege_app_sabre_laser_generateur_py'),
    ('templates/index.html',                                'b64_templates_index_html'),
]


def encoder(chemin_abs: str) -> str:
    with open(chemin_abs, 'rb') as f:
        return base64.b64encode(zlib.compress(f.read(), 9)).decode()


def version_courante(contenu: str) -> int:
    """Extrait le numéro de version depuis 'SelecGE vXX'."""
    m = re.search(r'SelecGE v(\d+)', contenu)
    return int(m.group(1)) if m else 34


def build(version_forcee: int = None, commit: bool = False):
    print("=" * 55)
    print("  SelecGE — Build script")
    print("=" * 55)

    # Lire le bootstrap
    with open(BOOTSTRAP, 'r', encoding='utf-8') as f:
        contenu = f.read()

    v_actuelle = version_courante(contenu)
    v_nouvelle = version_forcee if version_forcee else v_actuelle
    print(f"  Version actuelle : v{v_actuelle}")
    if v_nouvelle != v_actuelle:
        print(f"  → Nouvelle version : v{v_nouvelle}")

    # Patcher chaque fichier
    erreurs = []
    maj = []
    for rel_path, varname in FICHIERS:
        abs_path = os.path.join(ROOT, rel_path)
        if not os.path.exists(abs_path):
            print(f"  ⚠️  Absent : {rel_path}")
            continue

        pattern = rf'{re.escape(varname)}\s*=\s*\([^)]+\)'
        if not re.search(pattern, contenu):
            erreurs.append(f"Variable introuvable dans bootstrap : {varname}")
            continue

        new_b64  = encoder(abs_path)
        new_bloc = f'{varname} = (\n    "{new_b64}"\n)'
        contenu  = re.sub(pattern, new_bloc, contenu)
        maj.append(rel_path)
        print(f"  ✅ {rel_path}")

    if erreurs:
        print("\n  ERREURS :")
        for e in erreurs:
            print(f"    ✗ {e}")
        sys.exit(1)

    # Mettre à jour la version
    contenu = re.sub(r'SelecGE v\d+', f'SelecGE v{v_nouvelle}', contenu)

    # Écrire le bootstrap
    with open(BOOTSTRAP, 'w', encoding='utf-8') as f:
        f.write(contenu)

    print(f"\n  ✅ SelecGE.py repackagé — {len(maj)} fichiers encodés")
    print(f"  Version : v{v_nouvelle}")

    # Smoke test : vérifier que l'import Flask fonctionne depuis le répertoire
    print("\n  🔍 Smoke test...")
    try:
        import subprocess, sys as _sys
        result = subprocess.run(
            [_sys.executable, '-c',
             'import sys; sys.path.insert(0, "."); from app import app; '
             'print("routes:", len(list(app.url_map.iter_rules())))'],
            capture_output=True, text=True, timeout=15, cwd=ROOT
        )
        if result.returncode == 0 and 'routes:' in result.stdout:
            nb = result.stdout.strip().split('routes:')[-1].strip()
            print(f"  ✅ Smoke test OK — {nb} routes")
        else:
            err = (result.stderr or result.stdout)[:400]
            print(f"  ⚠️  Smoke test : {err}")
    except Exception as e:
        print(f"  ⚠️  Smoke test non exécuté : {e}")

    # Git commit optionnel
    if commit:
        date = datetime.date.today().strftime('%d/%m/%Y')
        msg  = f"v{v_nouvelle} — build {date}"
        try:
            subprocess.run(['git', 'add', 'SelecGE.py'], cwd=ROOT, check=True)
            subprocess.run(['git', 'commit', '-m', msg], cwd=ROOT, check=True)
            print(f"  ✅ Git commit : {msg}")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Git commit échoué : {e}")

    print("=" * 55)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repackage SelecGE.py')
    parser.add_argument('--commit',  action='store_true', help='Git commit après build')
    parser.add_argument('--version', type=int, default=None, help='Forcer le numéro de version')
    args = parser.parse_args()
    build(version_forcee=args.version, commit=args.commit)
