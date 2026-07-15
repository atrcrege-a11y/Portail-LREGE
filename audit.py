"""
audit.py — Script de référence pour valider les générations SelecGE.
À exécuter avant ET après toute modification.
Résultats doivent être identiques.

Étape 0 : scan intégrité (null bytes) — bloquant
Étape 1 : chargement des fichiers de classements
Étape 2 : tests de génération
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ─────────────────────────────────────────────────────────────
# ÉTAPE 0 — Scan intégrité : null bytes
# Doit passer avant tout import de module projet.
# Des null bytes = fichier tronqué par une écriture bash partielle.
# ─────────────────────────────────────────────────────────────
def _scan_null_bytes(base: str) -> list:
    """Retourne la liste des fichiers .py corrompus (null bytes détectés)."""
    corrompus = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv", "venv", "node_modules")]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            try:
                raw = open(path, "rb").read()
                nb_nulls = raw.count(b"\x00")
                if nb_nulls > 0:
                    last = len(raw)
                    while last > 0 and raw[last - 1] == 0:
                        last -= 1
                    corrompus.append({
                        "path":     path,
                        "rel":      os.path.relpath(path, base),
                        "total":    len(raw),
                        "utile":    last,
                        "nb_nulls": nb_nulls,
                    })
            except OSError:
                pass
    return corrompus

_BASE = os.path.dirname(os.path.abspath(__file__))
print("Étape 0 — Scan intégrité (null bytes)...")
_corrompus = _scan_null_bytes(_BASE)
if _corrompus:
    print(f"\n🔴 CORRUPTION DÉTECTÉE — {len(_corrompus)} fichier(s) avec null bytes :\n")
    for c in _corrompus:
        print(f"  ❌ {c['rel']}")
        print(f"     {c['nb_nulls']} null bytes | taille totale {c['total']} o | taille utile {c['utile']} o")
    print("\nCorrection : lancer le nettoyage ci-dessous pour chaque fichier :")
    print("  python3 -c \"")
    print("  import os; path='CHEMIN'; raw=open(path,'rb').read()")
    print("  last=len(raw)")
    print("  while last>0 and raw[last-1]==0: last-=1")
    print("  open(path,'wb').write(raw[:last])")
    print("  print(f'Nettoyé : {len(raw)} -> {last} bytes')\"")
    print("\n⛔  Audit interrompu — corriger les fichiers avant de continuer.")
    sys.exit(2)
else:
    print("  ✅ Aucun fichier corrompu (0 null bytes)\n")

from importer_classements_pdf import lire_classement_ffe_pdf
from importer_classements_ffe import lire_classement_ffe
from crege_app.core.utils import est_grand_est, COL_REGION
from services.construction import build_cfg

# Dossier des fixtures FFE : 1) env AUDIT_FIXTURES  2) ./uploads a cote de audit.py  3) chemin sandbox
_CANDIDATS = [os.environ.get("AUDIT_FIXTURES", ""),
              os.path.join(_BASE, "uploads"),
              "/mnt/user-data/uploads"]
U = next((c for c in _CANDIDATS if c and os.path.isdir(c)), _CANDIDATS[1])
U = U.rstrip("/\\") + os.sep
print(f"Fixtures : {U}")
if not os.path.isdir(U):
    print("⛔  Dossier fixtures introuvable. Options :")
    print("   - copier les fichiers FFE dans", os.path.join(_BASE, "uploads"))
    print("   - ou definir la variable :  set AUDIT_FIXTURES=C:\\chemin\\vers\\fixtures")
    sys.exit(2)
_FX_INDEX = None
def _fx(nom):
    """Résout un fichier fixture : U/nom direct, sinon recherche récursive
    dans U (sous-dossiers SOURCES/...) en tolérant espaces vs underscores."""
    global _FX_INDEX
    direct = os.path.join(U, nom)
    if os.path.exists(direct):
        return direct
    if _FX_INDEX is None:
        _FX_INDEX = {}
        for root, dirs, fs in os.walk(U):
            for f in fs:
                _FX_INDEX.setdefault(f.replace(" ", "_"), os.path.join(root, f))
    cle = nom.replace(" ", "_")
    if cle in _FX_INDEX:
        return _FX_INDEX[cle]
    print(f"⛔  Fixture introuvable : {nom} (cherchée dans {U})")
    sys.exit(2)

errors = []
ok = []

def _sans_accents(s):
    """Normalise pour comparaison : accents supprimes + tout sauf alphanumerique retire.
    Ainsi 'QUOTA LREGE N3' matche 'QUOTA LREGE -- N3' (legacy vs unifie)."""
    import unicodedata as _u, re as _r
    s = _u.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return _r.sub(r"[^a-z0-9]", "", s)

def flat_pairs(data):
    """[(nom, prenom, rang), ...] ordonnes -- toutes sections + sous-sections."""
    out = []
    for s in data["sections"]:
        tirs = s.get("tireurs", []) + [
            t for ss in s.get("sous_sections", [])
            for t in ss.get("tireurs", [])
        ]
        for t in tirs:
            if t.get("nom", "").strip():
                out.append((t.get("nom", ""), t.get("prenom", ""), t.get("rang", "")))
    return out

def compare_moteurs(label, data_legacy, data_unifie):
    """Equivalence stricte legacy/unifie : memes tireurs, meme ordre, memes rangs."""
    a, b = flat_pairs(data_legacy), flat_pairs(data_unifie)
    if a == b:
        ok.append(f"\u2705 {label} | equivalence legacy/unifie ({len(a)} tireurs)")
        return
    sa, sb = {(n, p) for n, p, _ in a}, {(n, p) for n, p, _ in b}
    if sa == sb:
        errors.append(f"\u274c {label} | memes tireurs mais ordre/rang differents:\n    legacy={a}\n    unifie={b}")
    else:
        errors.append(f"\u274c {label} | tireurs divergents:\n    legacy seul={sorted(sa - sb)}\n    unifie seul={sorted(sb - sa)}")

def flat_tireurs(sections):
    """Tous les tireurs (sections + sous-sections), hors lignes vides."""
    result = {}
    for s in sections:
        tirs = s.get("tireurs", []) + [
            t for ss in s.get("sous_sections", [])
            for t in ss.get("tireurs", [])
        ]
        nom_section = s["label"]
        result[nom_section] = [t for t in tirs if t.get("nom","").strip()]
    return result

def check(label, sections, specs):
    """
    specs = [(keyword, expected_count, comment), ...]
    keyword : sous-chaîne du label de section (insensible à la casse)
    expected_count : None = juste vérifier la présence, int = vérifier le count
    """
    flat = flat_tireurs(sections)
    for kw, exp, comment in specs:
        found = [(l, t) for l, t in flat.items() if _sans_accents(kw) in _sans_accents(l)]
        if exp == 0 and not found:
            ok.append(f"✅ {label} | '{kw}' absente (correct — 0 GES)")
            continue
        if not found:
            if exp is None or exp > 0:
                errors.append(f"❌ {label} | section '{kw}' ABSENTE")
            continue
        l, t = found[0]
        n = len(t)
        if exp is not None and n != exp:
            errors.append(f"❌ {label} | '{kw}': {n} ≠ attendu {exp} — {comment}")
        else:
            ok.append(f"✅ {label} | {kw}: {n} {comment}")

# ─────────────────────────────────────────────────────────────
# Chargement des fichiers (une seule fois)
# ─────────────────────────────────────────────────────────────
print("Chargement des fichiers...")

pdf_fh_m17  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FH_M17.pdf"))
pdf_fd_m17  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FD_M17.pdf"))
pdf_fh_m20  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FH_M20.pdf"))
pdf_fd_m20  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FD_M20.pdf"))
pdf_sh_m20  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_SH_M20.pdf"))
pdf_fh_sen  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FH_SEN.pdf"))
pdf_fd_sen  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_FD_SEN.pdf"))
pdf_sh_sen  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_SH_SEN.pdf"))
pdf_sd_sen  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_SD_SEN.pdf"))
pdf_ed_sen  = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_ED_SEN.pdf"))

nat_fh_m17  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-homme-m17-selection-cdf_20260429110047.xlsx"))
nat_fd_m17  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-dame-m17-selection-cdf_20260429110024.xlsx"))
nat_fh_m20  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-homme-m20-selection-cdf_20260507100307.xlsx"))
nat_fd_m20  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-dame-m20-selection-cdf_20260507100303.xlsx"))
nat_fh_sen  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-homme-senior-selection-cdf_20260513123929.xlsx"))
nat_fd_sen  = lire_classement_ffe(_fx("classement-national-individuel-fleuret-dame-senior-selection-cdf_20260513123924.xlsx"))
nat_ed_sen  = lire_classement_ffe(_fx("classement-national-individuel-epee-dame-senior-selection-cdf_20260513123919.xlsx"))

reg_fh_m17  = lire_classement_ffe(_fx("classement-regional-fleuret-hommes-m17-grand-est_20260430125304.xlsx"))
reg_fd_m17  = lire_classement_ffe(_fx("classement-regional-fleuret-dames-m17-grand-est_20260430125258.xlsx"))
reg_fh_m20  = lire_classement_ffe(_fx("classement-regional-fleuret-hommes-m20-grand-est_20260507125312.xlsx"))
reg_fd_m20  = lire_classement_ffe(_fx("classement-regional-fleuret-dames-m20-grand-est_20260507125309.xlsx"))
reg_fh_sen  = lire_classement_ffe(_fx("classement-regional-fleuret-hommes-seniors-grand-est_20260513123951.xlsx"))
reg_fd_sen  = lire_classement_ffe(_fx("classement-regional-fleuret-dames-seniors-grand-est_20260513123947.xlsx"))
reg_ed_sen  = lire_classement_ffe(_fx("classement-regional-epee-dames-seniors-grand-est_20260513123943.xlsx"))
reg_eh_m13  = lire_classement_ffe(_fx("classement-regional-classement-regional-epee-hommes-m13-grand-est_20260505090729.xlsx"))
reg_ed_m13  = lire_classement_ffe(_fx("classement-departemental-classement-regional-epee-dames-m13-grand-est_20260505090733.xlsx"))

print("OK. Lancement des tests...\n")

# ─────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────

def run_tests():
    from crege_app.categories.jeunes import (
        _construire_jeunes,
        _construire_jeunes_ffe_n1n2_n3quota,
        _construire_jeunes_n1_ffe_n2_quota,
    )
    from crege_app.categories.seniors import _construire_seniors
    from crege_app.categories.selection import construire_selection as _cs

    # ── M17 Fleuret H : N1(1) + N2(1) + N3 quota(2nat+3rég=5) ──
    n1 = pdf_fh_m17[pdf_fh_m17["Niveau"]=="N1"].copy()
    n2 = pdf_fh_m17[pdf_fh_m17["Niveau"]=="N2"].copy()
    cfg,_ = build_cfg({"cat_id":"M17","arme_id":"F"},"H")
    data = _construire_jeunes_ffe_n1n2_n3quota(n1, n2, nat_fh_m17, reg_fh_m17, cfg)
    check("M17 FH", data["sections"], [
        ("N1 (LISTE", 1, "POUSSEL"),
        ("N2 (LISTE", 1, "CREUSAT"),
        ("QUOTA LREGE", cfg["quota_crege_nat"]+cfg["quota_crege_reg"], f"{cfg['quota_crege_nat']}nat+{cfg['quota_crege_reg']}rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    u = _cs("M17","F","H",cfg, df_nat=nat_fh_m17, df_reg=reg_fh_m17, df_ffe=pdf_fh_m17)
    check("U-M17 FH", u["sections"], [
        ("N1 (LISTE", 1, "POUSSEL"),
        ("N2 (LISTE", 1, "CREUSAT"),
        ("QUOTA LREGE", cfg["quota_crege_nat"]+cfg["quota_crege_reg"], f"{cfg['quota_crege_nat']}nat+{cfg['quota_crege_reg']}rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    compare_moteurs("M17 FH", data, u)

    # ── M17 Fleuret D : N1(0) + N2 quota(1nat+2rég=3) ──────────
    n1d = pdf_fd_m17[pdf_fd_m17["Niveau"]=="N1"].copy()
    cfg_d,_ = build_cfg({"cat_id":"M17","arme_id":"F"},"D")
    data_d = _construire_jeunes_n1_ffe_n2_quota(n1d, nat_fd_m17, reg_fd_m17, cfg_d)
    ges_n1d = len(n1d[n1d[COL_REGION].apply(est_grand_est)])
    check("M17 FD", data_d["sections"], [
        ("N1 (LISTE", ges_n1d, f"{ges_n1d} GES N1"),
        ("QUOTA LREGE", cfg_d["quota_crege_nat"]+cfg_d["quota_crege_reg"],
         f"{cfg_d['quota_crege_nat']}nat+{cfg_d['quota_crege_reg']}rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    u = _cs("M17","F","D",cfg_d, df_nat=nat_fd_m17, df_reg=reg_fd_m17, df_ffe=pdf_fd_m17)
    check("U-M17 FD", u["sections"], [
        ("N1 (LISTE", ges_n1d, f"{ges_n1d} GES N1"),
        ("QUOTA LREGE", cfg_d["quota_crege_nat"]+cfg_d["quota_crege_reg"],
         f"{cfg_d['quota_crege_nat']}nat+{cfg_d['quota_crege_reg']}rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    compare_moteurs("M17 FD", data_d, u)

    # ── M20 Fleuret H : N2(1) + N3 quota(1nat+3rég=4) ──────────
    n1_20h = pdf_fh_m20[pdf_fh_m20["Niveau"]=="N1"].copy()
    n2_20h = pdf_fh_m20[pdf_fh_m20["Niveau"]=="N2"].copy()
    cfg20h,_ = build_cfg({"cat_id":"M20","arme_id":"F"},"H")
    data20h = _construire_jeunes_ffe_n1n2_n3quota(n1_20h, n2_20h, nat_fh_m20, reg_fh_m20, cfg20h)
    check("M20 FH", data20h["sections"], [
        ("N1 (LISTE", 0, "0 GES N1"),
        ("N2 (LISTE", 1, "MATSOUNGA LOUFOUMA"),
        ("QUOTA LREGE", cfg20h["quota_crege_nat"]+cfg20h["quota_crege_reg"],
         f"{cfg20h['quota_crege_nat']}nat+{cfg20h['quota_crege_reg']}rég"),
        ("REMPLAÇANT", None, "≤10 selon taille classement"),
    ])
    u = _cs("M20","F","H",cfg20h, df_nat=nat_fh_m20, df_reg=reg_fh_m20, df_ffe=pdf_fh_m20)
    check("U-M20 FH", u["sections"], [
        ("N1 (LISTE", 0, "0 GES N1"),
        ("N2 (LISTE", 1, "MATSOUNGA LOUFOUMA"),
        ("QUOTA LREGE", cfg20h["quota_crege_nat"]+cfg20h["quota_crege_reg"],
         f"{cfg20h['quota_crege_nat']}nat+{cfg20h['quota_crege_reg']}rég"),
        ("REMPLAÇANT", None, "≤10 selon taille classement"),
    ])
    compare_moteurs("M20 FH", data20h, u)

    # ── M20 Fleuret D : N1(0) + N2 quota ────────────────────────
    n1_20d = pdf_fd_m20[pdf_fd_m20["Niveau"]=="N1"].copy()
    cfg20d,_ = build_cfg({"cat_id":"M20","arme_id":"F"},"D")
    data20d = _construire_jeunes_n1_ffe_n2_quota(n1_20d, nat_fd_m20, reg_fd_m20, cfg20d)
    check("M20 FD", data20d["sections"], [
        ("N1 (LISTE", 0, "0 GES N1"),
        ("QUOTA LREGE", cfg20d["quota_crege_nat"]+cfg20d["quota_crege_reg"],
         f"{cfg20d['quota_crege_nat']}nat+{cfg20d['quota_crege_reg']}rég"),
    ])
    u = _cs("M20","F","D",cfg20d, df_nat=nat_fd_m20, df_reg=reg_fd_m20, df_ffe=pdf_fd_m20)
    check("U-M20 FD", u["sections"], [
        ("N1 (LISTE", 0, "0 GES N1"),
        ("QUOTA LREGE", cfg20d["quota_crege_nat"]+cfg20d["quota_crege_reg"],
         f"{cfg20d['quota_crege_nat']}nat+{cfg20d['quota_crege_reg']}rég"),
    ])
    compare_moteurs("M20 FD", data20d, u)

    # ── M20 Sabre H : open_circuit N1+N2 PDF ────────────────────
    from crege_app.categories.jeunes import _construire_jeunes_open_circuit
    n1_sh = pdf_sh_m20[pdf_sh_m20["Niveau"]=="N1"].copy()
    n2_sh = pdf_sh_m20[pdf_sh_m20["Niveau"]=="N2"].copy()
    cfg_sh,_ = build_cfg({"cat_id":"M20","arme_id":"S"},"H")
    ges_sh = len(pdf_sh_m20[(pdf_sh_m20["Niveau"]=="N1") & pdf_sh_m20[COL_REGION].apply(est_grand_est)])
    data_sh = _construire_jeunes_open_circuit(n1_sh, n2_sh, None, cfg_sh)
    check("M20 SH", data_sh["sections"], [
        ("LISTE NATIONALE", ges_sh, f"{ges_sh} GES N1+N2"),
    ])
    u = _cs("M20","S","H",cfg_sh, df_ffe=pdf_sh_m20)
    check("U-M20 SH", u["sections"], [
        ("N1 (LISTE", ges_sh, f"{ges_sh} GES N1"),
        ("N2 (LISTE", 10, "10 GES N2 — fichier mai"),
    ])
    compare_moteurs("M20 SH", data_sh, u)

    # ── M13 Épée H : 100% régional quota 10 ─────────────────────
    cfg13h,_ = build_cfg({"cat_id":"M13","arme_id":"E"},"H")
    data13h = _construire_jeunes(None, reg_eh_m13, cfg13h)
    check("M13 EH", data13h["sections"], [
        ("QUOTA LREGE", 10, "100% régional"),
        ("REMPLAÇANT", 10, ""),
    ])
    u = _cs("M13","E","H",cfg13h, df_reg=reg_eh_m13)
    check("U-M13 EH", u["sections"], [
        ("QUOTA LREGE", 10, "100% régional"),
        ("REMPLAÇANT", 10, ""),
    ])
    compare_moteurs("M13 EH", data13h, u)

    # ── M13 Épée D : 100% régional quota 10 ─────────────────────
    cfg13d,_ = build_cfg({"cat_id":"M13","arme_id":"E"},"D")
    data13d = _construire_jeunes(None, reg_ed_m13, cfg13d)
    check("M13 ED", data13d["sections"], [
        ("QUOTA LREGE", 10, "100% régional"),
        ("REMPLAÇANT", None, "≤10 selon taille"),
    ])
    u = _cs("M13","E","D",cfg13d, df_reg=reg_ed_m13)
    check("U-M13 ED", u["sections"], [
        ("QUOTA LREGE", 10, "100% régional"),
        ("REMPLAÇANT", None, "≤10 selon taille"),
    ])
    compare_moteurs("M13 ED", data13d, u)

    # ── Seniors FH : N3 FFE(1) + quota N3(1nat+3rég=4) ─────────
    cfg_fh_s,_ = build_cfg({"cat_id":"Seniors","arme_id":"F","quota_n2_reg_h":3},"H")
    data_fh_s = _construire_seniors(nat_fh_sen, reg_fh_sen, cfg_fh_s, df_ffe=pdf_fh_sen)
    check("Seniors FH", data_fh_s["sections"], [
        ("N3 (LISTE", 1, "BOHLY CL NAT 104"),
        ("QUOTA LREGE N3", 4, "1nat+3rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    u = _cs("Seniors","F","H",cfg_fh_s, df_nat=nat_fh_sen, df_reg=reg_fh_sen, df_ffe=pdf_fh_sen)
    check("U-Seniors FH", u["sections"], [
        ("N3 (LISTE", 1, "BOHLY CL NAT 104"),
        ("QUOTA LREGE N3", 4, "1nat+3rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    compare_moteurs("Seniors FH", data_fh_s, u)

    # ── Seniors FD : quota N2(1nat+3rég=4) ─────────────────────
    cfg_fd_s,_ = build_cfg({"cat_id":"Seniors","arme_id":"F","quota_n2_reg_d":3},"D")
    data_fd_s = _construire_seniors(nat_fd_sen, reg_fd_sen, cfg_fd_s, df_ffe=pdf_fd_sen)
    check("Seniors FD", data_fd_s["sections"], [
        ("QUOTA LREGE N2", 4, "1nat+3rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    u = _cs("Seniors","F","D",cfg_fd_s, df_nat=nat_fd_sen, df_reg=reg_fd_sen, df_ffe=pdf_fd_sen)
    check("U-Seniors FD", u["sections"], [
        ("QUOTA LREGE N2", 4, "1nat+3rég"),
        ("REMPLAÇANT", 10, ""),
    ])
    compare_moteurs("Seniors FD", data_fd_s, u)

    # ── Seniors SH : liste FFE N1 (8 GES) ───────────────────────
    n1_ssh = pdf_sh_sen[pdf_sh_sen["Niveau"]=="N1"].copy()
    cfg_ssh,_ = build_cfg({"cat_id":"Seniors","arme_id":"S"},"H")
    data_ssh = _construire_seniors(n1_ssh, None, cfg_ssh)
    check("Seniors SH", data_ssh["sections"], [
        ("LISTE NATIONALE FFE", 8, "8 GES N1"),
    ])
    u = _cs("Seniors","S","H",cfg_ssh, df_ffe=pdf_sh_sen)
    check("U-Seniors SH", u["sections"], [
        ("N1 (LISTE", 8, "8 GES N1 — fichier mai"),
        ("N2 (LISTE", 26, "26 GES N2 — fichier mai"),
    ])
    # pas de compare_moteurs : le legacy ci-dessus ne reçoit que N1 (fichier mai = N1+N2)

    # ── Seniors SD : liste FFE N1 (5 GES) ───────────────────────
    n1_ssd = pdf_sd_sen[pdf_sd_sen["Niveau"]=="N1"].copy()
    cfg_ssd,_ = build_cfg({"cat_id":"Seniors","arme_id":"S"},"D")
    data_ssd = _construire_seniors(n1_ssd, None, cfg_ssd)
    check("Seniors SD", data_ssd["sections"], [
        ("LISTE NATIONALE FFE", 5, "5 GES N1"),
    ])
    u = _cs("Seniors","S","D",cfg_ssd, df_ffe=pdf_sd_sen)
    check("U-Seniors SD", u["sections"], [
        ("N1 (LISTE", 5, "5 GES N1 — fichier mai"),
        ("N2 (LISTE", 12, "12 GES N2 — fichier mai"),
    ])
    # pas de compare_moteurs : le legacy ci-dessus ne reçoit que N1 (fichier mai = N1+N2)

    # ── Seniors EH : N1(4) + N2(4) + N3(2) liste FFE ───────────────
    from crege_app.categories.selection import construire_selection as _cs
    pdf_eh = lire_classement_ffe_pdf(_fx("LQ25-26_FRANCE_ind_-_EH_SEN.pdf"))
    cfg_eh,_ = build_cfg({"cat_id":"Seniors","arme_id":"E"},"H")
    data_eh = _cs("Seniors","E","H",cfg_eh,df_ffe=pdf_eh)
    check("Seniors EH", data_eh["sections"], [
        ("N1 (LISTE", 4, "BIABIANY/IMBERT/LE BERRE/LEGUBE"),
        ("N2 (LISTE", 4, "BRETON/LUCANI/AMBROSINI/LE BARS"),
        ("N3 (LISTE", 2, "NAEGELEN/ROBERT"),
    ])

    # ── Seniors ED : N1(7) + N2(3) + quota N3(1nat+3rég=4) ─────
    cfg_ed_s,_ = build_cfg({"cat_id":"Seniors","arme_id":"E"},"D")  # REGLES.md 1.6 : D = 1nat+3rég
    data_ed_s = _cs("Seniors","E","D",cfg_ed_s,df_nat=nat_ed_sen,df_reg=reg_ed_sen,df_ffe=pdf_ed_sen)
    check("Seniors ED", data_ed_s["sections"], [
        ("N1 (LISTE", 7, "7 GES N1"),
        ("N2 (LISTE", 3, "3 GES N2"),
        ("QUOTA LREGE", 4, "1nat+3rég — REGLES.md 1.6"),
        ("REMPLAÇANT", 10, ""),
    ])

run_tests()

print(f"\n{'='*50}")
print(f"✅ {len(ok)} OK   ❌ {len(errors)} ERREUR(S)")
if errors:
    for e in errors: print(e)
    sys.exit(1)
else:
    print("Tous les tests passent.")
