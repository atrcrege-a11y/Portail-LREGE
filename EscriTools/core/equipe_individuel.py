"""
core/equipe_individuel.py — Conversion résultats équipes BellePoule → classement individuel .fff.

Supporte deux formats d'entrée :
  - PDF BellePoule (parsing direct des pages texte)
  - Markdown BellePoule (converti depuis PDF via core/pdf_markdown.py)

Flux : fichier → inscrits (équipes + membres) + classement général
       → classement individuel → .fff WIN/FFE
"""
import re
import os
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

# ── Patterns regex ──────────────────────────────────────────────────────────────

_REGION = (
    r'(?:CHAMPAGNE-ARDENNE|LORRAINE|ALSACE|GRAND[\s\-]EST|BOURGOGNE|'
    r'ILE[\s\-]DE[\s\-]FRANCE|NORMANDIE|BRETAGNE|OCCITANIE|PACA|AUVERGNE|'
    r'NOUVELLE[\s\-]AQUITAINE|CENTRE|HAUTS[\s\-]DE[\s\-]FRANCE|'
    r'PAYS[\s\-]DE[\s\-]LA[\s\-]LOIRE|FRANCHE[\s\-]COMTE)'
)
_REGION_PDF = _REGION.replace('(?:', '(?:').replace(r'[\s\-]', r'[\s\-]')

_PAT_DDN      = re.compile(r'\d{2}/\d{2}/\d{4}')
_PAT_ENTREE   = re.compile(r'(.+?)\s+' + _REGION + r'\s+FRA\s+(0|19998)\s*(\d{5,7})?', re.UNICODE)
_PAT_SPLIT    = re.compile(
    r'([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ ]+?\s+\d+)\s+'
    r'[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]+\s+([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ].+)$', re.UNICODE
)
_PAT_CG_FLAT  = re.compile(
    r'(\d+)\s+(.+?)\s+' + _REGION + r'\s+FRA\s*(?=\d|\Z)', re.UNICODE
)
_PAT_ENTREE_PDF = re.compile(
    r'^(.+?)\s+(?:CHAMPAGNE-ARDENNE|LORRAINE|ALSACE|GRAND[\s\-]EST|BOURGOGNE|'
    r'ILE[\s\-]DE[\s\-]FRANCE|NORMANDIE|BRETAGNE|OCCITANIE|PACA|AUVERGNE|'
    r'NOUVELLE[\s\-]AQUITAINE|CENTRE|HAUTS[\s\-]DE[\s\-]FRANCE|'
    r'PAYS[\s\-]DE[\s\-]LA[\s\-]LOIRE|FRANCHE[\s\-]COMTE)'
    r'\s+FRA\s+(0|19998)\s*(\d{5,7})?\s*$', re.UNICODE
)
_PAT_CG_PDF   = re.compile(
    r'^(\d+)\s+(.+?)\s+(?:CHAMPAGNE-ARDENNE|LORRAINE|ALSACE|GRAND[\s\-]EST|BOURGOGNE|'
    r'ILE[\s\-]DE[\s\-]FRANCE|NORMANDIE|BRETAGNE|OCCITANIE|PACA|AUVERGNE|'
    r'NOUVELLE[\s\-]AQUITAINE|CENTRE|HAUTS[\s\-]DE[\s\-]FRANCE|'
    r'PAYS[\s\-]DE[\s\-]LA[\s\-]LOIRE|FRANCHE[\s\-]COMTE)'
    r'\s+FRA\s*$', re.UNICODE
)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _nom_prenom(avant: str) -> tuple[str, str]:
    """Extrait NOM et Prénom (composés, tout-caps) depuis un champ avant."""
    avant = _PAT_DDN.sub('', avant).strip()
    tokens = avant.split()
    if not tokens:
        return "", ""

    last_mixed = None
    for i in range(len(tokens) - 1, -1, -1):
        if re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][a-zàâäéèêëîïôöùûü]', tokens[i]):
            last_mixed = i
            break
    if last_mixed is not None:
        tokens = tokens[:last_mixed + 1]
    else:
        while len(tokens) > 2 and re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]{2,}$', tokens[-1]):
            tokens = tokens[:-1]

    if not tokens:
        return "", ""

    last_mixed = None
    for i in range(len(tokens) - 1, -1, -1):
        if re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][a-zàâäéèêëîïôöùûü]', tokens[i]):
            last_mixed = i
            break

    if last_mixed is None:
        return (" ".join(tokens[:-1]) if len(tokens) > 1 else tokens[0],
                tokens[-1] if len(tokens) > 1 else "")

    prenom_start = last_mixed
    for i in range(last_mixed - 1, -1, -1):
        if re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][a-zàâäéèêëîïôöùûü]', tokens[i]):
            prenom_start = i
        else:
            break
    prenom = " ".join(tokens[prenom_start:last_mixed + 1])
    nom_tokens = [
        tokens[i] for i in range(prenom_start - 1, -1, -1)
        if re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ\-\']+$', tokens[i])
    ]
    nom_tokens.reverse()
    return " ".join(nom_tokens), prenom


def _nom_equipe(avant: str) -> str:
    """Extrait le nom d'équipe depuis un champ avant."""
    avant = avant.strip()
    matches = re.findall(
        r'([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ\s]+?\s+\d+)(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]|\s*$)',
        avant
    )
    if matches:
        return matches[-1].strip()
    return " ".join(avant.split()[-3:]).strip()


def _parse_nom_eq_cg(reste: str) -> str:
    """Extrait nom d'équipe depuis 'NOM_EQ CLUB' (répétition partielle)."""
    mots = reste.split()
    for l in range(len(mots) // 2 + 1, 0, -1):
        c = " ".join(mots[:l])
        s = " ".join(mots[l:])
        if s and (s in c or c.endswith(s.split()[0])):
            return c.strip()
    matches = re.findall(
        r'([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ\s]+?\s+\d+)(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]|\s*$)',
        reste
    )
    return matches[-1].strip() if matches else reste.strip()


def _trouver_membres(nom_eq: str, inscrits: dict) -> list:
    """Recherche tolérante du nom d'équipe dans le dict inscrits."""
    if nom_eq in inscrits:
        return inscrits[nom_eq]
    for k, v in inscrits.items():
        if nom_eq in k or k in nom_eq:
            return v
    return []


def _club_depuis_nom_eq(nom_eq: str) -> str:
    """Extrait le nom du club depuis le nom d'équipe. Ex: 'TROYES TG 1' → 'TROYES TG'."""
    m = re.match(r'^(.+?)\s+\d+\s*$', nom_eq.strip())
    return m.group(1).strip() if m else nom_eq.strip()


# ── Extraction depuis Markdown ───────────────────────────────────────────────────

def extraire_inscrits_md(texte: str) -> dict:
    """
    Extrait la composition des équipes depuis la section 'Liste des inscrits' (Markdown).
    Retourne {nom_equipe: [{nom, prenom, ddn, licence, sexe}]}.
    """
    m0 = re.search(r'Liste des inscrits', texte, re.IGNORECASE)
    if not m0:
        return {}
    bloc = texte[m0.start():]
    fin = re.search(r'\n#+ R[eé]partition', bloc)
    if fin:
        bloc = bloc[:fin.start()]
    flat = " ".join(bloc.splitlines())

    equipes = {}
    eq_courant = None

    for m in _PAT_ENTREE.finditer(flat):
        avant = m.group(1)
        cls   = m.group(2)
        lic   = m.group(3) or ""
        ddn   = _PAT_DDN.search(avant)
        ddn   = ddn.group(0) if ddn else ""

        if cls == "19998":
            eq_courant = _nom_equipe(avant)
            equipes.setdefault(eq_courant, [])
        else:
            ms = _PAT_SPLIT.search(avant.strip())
            if ms:
                g2 = ms.group(2).strip()
                is_eq_seule = (
                    all(re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]+$', t) for t in g2.split())
                    and len(g2.split()) <= 3
                )
                if is_eq_seule:
                    eq_courant = ms.group(1).strip()
                    equipes.setdefault(eq_courant, [])
                    continue
                eq_courant = ms.group(1).strip()
                equipes.setdefault(eq_courant, [])
                avant_tireur = g2
            else:
                avant_tireur = avant
            if eq_courant is None:
                continue
            nom, prenom = _nom_prenom(avant_tireur)
            if nom:
                equipes[eq_courant].append({
                    "nom": nom, "prenom": prenom,
                    "ddn": ddn, "licence": lic, "sexe": "",
                })

    return {k: v for k, v in equipes.items()
            if re.search(r'[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ]', k)
            and not k.startswith('|') and not k.startswith('*')}


def extraire_classement_general_md(texte: str) -> list[tuple]:
    """Extrait le classement général final (Markdown)."""
    blocs = list(re.finditer(r'Classement g[eé]n[eé]ral', texte, re.IGNORECASE))
    if not blocs:
        return []
    bloc = texte[blocs[-1].start():]
    result = []

    for ligne in bloc.splitlines():
        m = re.match(r'^\s*(\d+)\s+(.+)', ligne)
        if m:
            result.append((int(m.group(1)), _parse_nom_eq_cg(m.group(2))))

    if not result:
        flat = " ".join(bloc.splitlines())
        for m in _PAT_CG_FLAT.finditer(flat):
            result.append((int(m.group(1)), _parse_nom_eq_cg(m.group(2))))

    return result


def extraire_classement_poules_md(texte: str) -> dict:
    """Extrait le classement du dernier tour de poules (Markdown)."""
    occ = list(re.finditer(r'Classement Tour n', texte, re.IGNORECASE))
    if not occ:
        return {}
    debut = occ[-1].start()
    flat  = " ".join(texte[debut: debut + 2000].splitlines())
    cg    = extraire_classement_general_md(texte)
    noms  = [n for _, n in cg]
    result = {}
    for nom_eq in noms:
        m = re.search(r'(\d+)\s+' + re.escape(nom_eq) + r'\s', flat)
        if m:
            result[nom_eq] = int(m.group(1))
    return result


# ── Extraction depuis PDF ────────────────────────────────────────────────────────

def _pdf_pages(pdf_path: str) -> list[str]:
    """Extrait les textes de pages via pdfplumber."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                pages.append(t)
    return pages


def extraire_inscrits_pdf(pages: list[str]) -> dict:
    """Extrait inscrits depuis les pages PDF BellePoule équipes."""
    equipes = {}
    eq_courant = None
    in_inscrits = False

    for page_text in pages:
        for ligne in page_text.splitlines():
            ligne = ligne.strip()
            if not ligne:
                continue
            if 'liste des inscrits' in ligne.lower():
                in_inscrits = True
                continue
            if in_inscrits and re.match(
                r'^(r[eé]partition|poules?\s+tour|composition|page\s+\d)',
                ligne, re.I
            ):
                in_inscrits = False
                continue
            if not in_inscrits:
                continue

            m = _PAT_ENTREE_PDF.match(ligne)
            if not m:
                continue

            avant = m.group(1).strip()
            cls   = m.group(2)
            lic   = m.group(3) or ""
            ddn_m = _PAT_DDN.search(avant)
            ddn   = ddn_m.group(0) if ddn_m else ""

            tokens = avant.split()
            has_mixed = any(
                re.match(r'^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ][a-zàâäéèêëîïôöùûü]', t)
                for t in tokens
            )
            has_team_number = any(re.match(r'^\d+$', t) for t in tokens)

            if not has_mixed and not ddn and has_team_number:
                eq_courant = _nom_equipe(avant)
                equipes.setdefault(eq_courant, [])
            else:
                if eq_courant is None:
                    continue
                nom, prenom = _nom_prenom(avant)
                if nom:
                    equipes[eq_courant].append({
                        "nom": nom, "prenom": prenom,
                        "ddn": ddn, "licence": lic, "sexe": "",
                    })

    return equipes


def extraire_classement_general_pdf(pages: list[str]) -> list[tuple]:
    """Extrait le classement général depuis les pages PDF."""
    for page_text in reversed(pages):
        if not re.search(r'classement\s+g[eé]n[eé]ral', page_text, re.I):
            continue
        candidats = []
        for ligne in page_text.splitlines():
            m = _PAT_CG_PDF.match(ligne.strip())
            if m:
                candidats.append((int(m.group(1)), _parse_nom_eq_cg(m.group(2).strip())))
        if candidats:
            return candidats
    return []


def extraire_classement_poules_pdf(pages: list[str], noms_eq: list[str]) -> dict:
    """Extrait le classement du dernier tour de poules depuis les pages PDF."""
    PAT_CP = re.compile(r'^(\d+)\s+(.+?)\s+\d+\s+\d+\s+[+-]?\d+\s+\d+\s*$')
    cg_page_idx = len(pages)
    for i, pt in enumerate(pages):
        if re.search(r'classement\s+g[eé]n[eé]ral', pt, re.I) and \
           any(re.match(r'^\d+\s+[A-Z]', l.strip()) for l in pt.splitlines()):
            cg_page_idx = i
            break

    cp_page = None
    for pt in reversed(pages[:cg_page_idx]):
        lignes = [l.strip() for l in pt.splitlines() if l.strip()]
        if len([l for l in lignes if PAT_CP.match(l)]) >= 3:
            cp_page = pt
            break

    if not cp_page:
        return {}

    result = {}
    for nom_eq in noms_eq:
        m = re.search(r'(\d+)\s+' + re.escape(nom_eq) + r'\s', cp_page)
        if m:
            result[nom_eq] = int(m.group(1))
    return result


# ── Construction du classement individuel ────────────────────────────────────────

def construire_classement_individuel(inscrits: dict, classement_general: list,
                                     classement_poules: dict) -> list:
    """
    Construit le classement individuel depuis le classement d'équipes.
    Place individuelle = place de l'équipe. Ex æquo départagés par classement_poules.
    """
    if not classement_general:
        return []

    par_place = {}
    for place, nom_eq in classement_general:
        par_place.setdefault(place, []).append(nom_eq)

    tireurs = []
    for place in sorted(par_place):
        exaequo = par_place[place]
        ordre = sorted(exaequo, key=lambda e: classement_poules.get(e, 9999))
        rang = place
        for nom_eq in ordre:
            membres = _trouver_membres(nom_eq, inscrits)
            club = _club_depuis_nom_eq(nom_eq)
            for t in membres:
                tireurs.append({**t, "place": rang, "club": club})
            rang += 1
    return tireurs


# ── Génération .fff ──────────────────────────────────────────────────────────────

def generer_fff(tireurs: list, date_comp: str, arme: str, sexe: str,
                categorie: str, nom_comp: str, lieu: str, output_path: str) -> None:
    """Génère le fichier .fff individuel depuis le classement des équipes."""
    from core.format_export import ecrire_fff as _ecrire
    info = {"date": date_comp, "arme": arme, "sexe": sexe,
            "categorie": categorie, "nom": nom_comp, "lieu": lieu}
    _ecrire(tireurs, info, output_path)


# ── Pipeline complet ─────────────────────────────────────────────────────────────

def traiter_fichier(chemin: str, date_comp: str, arme: str, sexe: str,
                    categorie: str, nom_comp: str, lieu: str,
                    output_path: str, log=print) -> tuple[bool, str]:
    """
    Traite un fichier PDF ou .md BellePoule équipes → .fff individuel.
    Retourne (succès, chemin_sortie_ou_message_erreur).
    """
    ext = Path(chemin).suffix.lower()
    try:
        if ext == ".pdf":
            log("   -> Mode PDF")
            pages = _pdf_pages(chemin)
            log("   -> Extraction des inscrits...")
            inscrits = extraire_inscrits_pdf(pages)
            nb_eq = len(inscrits)
            nb_t  = sum(len(v) for v in inscrits.values())
            log(f"   -> {nb_eq} équipes, {nb_t} tireurs")
            if not inscrits:
                return False, "Aucune équipe extraite."
            log("   -> Extraction du classement général...")
            classement_general = extraire_classement_general_pdf(pages)
            if not classement_general:
                return False, "Classement général introuvable."
            log(f"   -> {len(classement_general)} équipes classées")
            log("   -> Extraction classement poules (départage ex æquo)...")
            noms_eq = [n for _, n in classement_general]
            classement_poules = extraire_classement_poules_pdf(pages, noms_eq)
        else:
            log("   -> Mode Markdown (.md)")
            texte = Path(chemin).read_text(encoding="utf-8")
            log("   -> Extraction des inscrits...")
            inscrits = extraire_inscrits_md(texte)
            nb_eq = len(inscrits)
            nb_t  = sum(len(v) for v in inscrits.values())
            log(f"   -> {nb_eq} équipes, {nb_t} tireurs")
            if not inscrits:
                return False, "Aucune équipe extraite."
            log("   -> Extraction du classement général...")
            classement_general = extraire_classement_general_md(texte)
            if not classement_general:
                return False, "Classement général introuvable."
            log(f"   -> {len(classement_general)} équipes classées")
            log("   -> Extraction classement poules...")
            classement_poules = extraire_classement_poules_md(texte)

        log(f"   -> {len(classement_poules)} entrées poules")
        log("   -> Construction classement individuel...")
        tireurs = construire_classement_individuel(inscrits, classement_general, classement_poules)
        log(f"   -> {len(tireurs)} tireurs classés")
        if not tireurs:
            return False, "Aucun tireur classé (vérifier la correspondance équipes/inscrits)."

        generer_fff(tireurs, date_comp, arme, sexe, categorie, nom_comp, lieu, output_path)
        return True, output_path

    except Exception as e:
        return False, f"Erreur inattendue : {e}"
