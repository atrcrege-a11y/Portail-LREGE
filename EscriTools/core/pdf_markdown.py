"""
core/pdf_markdown.py — Conversion PDF → Markdown structuré.

Détecte automatiquement : titres (par taille/graisse), listes, tableaux,
mise en page 2 colonnes. Filtre les éléments répétitifs (en-têtes/pieds de page).
"""
import re
from collections import Counter

try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

# Glyphes mal encodés dans certains PDFs (ligatures → flèches)
GLYPH_MAP = {"fi": "→", "fl": "→", "ﬁ": "→", "ﬂ": "→"}

# Regex de filtrage des lignes parasites (URLs, numéros de page, etc.)
FILTRES = re.compile(
    r'(bellepoule|betton\.escrime|http[s]?://|^page\s+\d+|^\d+\s*/\s*\d+$'
    r'|^(cda|cdl|ceg|cdf|cdr|petites|cat.gories)$)',
    re.IGNORECASE
)


def _corriger_glyphes(texte: str) -> str:
    """Remplace les glyphes mal encodés par leur équivalent textuel."""
    for glyph, remplacement in GLYPH_MAP.items():
        texte = texte.replace(glyph, remplacement)
    texte = re.sub(r'(→\s*){2,}', '→ ', texte)
    return texte


def _nettoyer(texte: str) -> str:
    """
    Normalise un bloc de texte : supprime les doublons de caractères
    (artefacts OCR) et réduit les espaces multiples.
    """
    lettres = [c for c in texte if c.isalpha()]
    if len(lettres) >= 6:
        paires = sum(1 for i in range(0, len(lettres) - 1, 2) if lettres[i] == lettres[i + 1])
        if paires >= max(2, len(lettres) // 3):
            texte = re.sub(r'(.)\1', r'\1', texte)
    return re.sub(r'\s{2,}', ' ', texte).strip()


def _detecter_frontiere_colonnes(words: list) -> float | None:
    """
    Détecte une mise en page 2 colonnes en cherchant le plus grand écart
    horizontal entre mots consécutifs. Retourne la position X de la
    frontière ou None si la page est sur 1 colonne.
    """
    lignes_y = {}
    for w in words:
        key = round(w["top"] / 2) * 2
        lignes_y.setdefault(key, []).append(w)

    meilleur_ecart = 0
    frontiere = None
    for mots in lignes_y.values():
        mots_tries = sorted(mots, key=lambda w: w["x0"])
        for i in range(len(mots_tries) - 1):
            ecart = mots_tries[i + 1]["x0"] - mots_tries[i]["x1"]
            if ecart > meilleur_ecart:
                meilleur_ecart = ecart
                frontiere = (mots_tries[i]["x1"] + mots_tries[i + 1]["x0"]) / 2

    return frontiere if meilleur_ecart > 60 else None


def extraire_blocs(page) -> list[dict]:
    """
    Extrait les blocs de texte d'une page pdfplumber.
    Chaque bloc contient : text, size, bold, x0, top, col (g/d/None), has_cols.
    """
    try:
        mots = page.extract_words(extra_attrs=["size", "fontname"])
    except Exception:
        return []
    if not mots:
        return []

    frontiere = _detecter_frontiere_colonnes(mots)
    groupes = {}
    for m in mots:
        key = round(m["top"] / 3) * 3
        groupes.setdefault(key, []).append(m)

    blocs = []
    for top in sorted(groupes):
        ligne = sorted(groupes[top], key=lambda w: w["x0"])

        if frontiere:
            col_g = [w for w in ligne if (w["x0"] + w["x1"]) / 2 < frontiere]
            col_d = [w for w in ligne if (w["x0"] + w["x1"]) / 2 >= frontiere]
            for mots_col, col_id in [(col_g, "g"), (col_d, "d")]:
                if not mots_col:
                    continue
                texte = _corriger_glyphes(" ".join(w["text"] for w in mots_col)).strip()
                if not texte:
                    continue
                try:
                    size = max(float(w.get("size", 0) or 0) for w in mots_col)
                except Exception:
                    size = 10.0
                fonts = " ".join(w.get("fontname", "") or "" for w in mots_col).lower()
                bold  = any(k in fonts for k in ("bold", "heavy", "black", "demi"))
                blocs.append({
                    "text": texte, "size": size, "bold": bold,
                    "x0": min(w["x0"] for w in mots_col), "top": top,
                    "col": col_id, "has_cols": True, "frontiere": frontiere,
                })
        else:
            texte = _corriger_glyphes(" ".join(w["text"] for w in ligne)).strip()
            if not texte:
                continue
            try:
                size = max(float(w.get("size", 0) or 0) for w in ligne)
            except Exception:
                size = 10.0
            fonts = " ".join(w.get("fontname", "") or "" for w in ligne).lower()
            bold  = any(k in fonts for k in ("bold", "heavy", "black", "demi"))
            blocs.append({
                "text": texte, "size": size, "bold": bold,
                "x0": min(w["x0"] for w in ligne), "top": top,
                "col": None, "has_cols": False,
            })
    return blocs


def calculer_seuils(tous_blocs: list) -> dict:
    """
    Calcule les seuils de taille pour H1/H2/H3/body
    en analysant la distribution de tailles dans le document.
    """
    tailles = [round(b["size"]) for b in tous_blocs if b["size"] > 6]
    if not tailles:
        return {"h1": 18, "h2": 14, "h3": 12, "body": 10}
    freq = Counter(tailles)
    body_size = freq.most_common(1)[0][0]
    titres = sorted(set(t for t in tailles if t > body_size + 1), reverse=True)
    s = {"body": body_size}
    if len(titres) >= 1: s["h1"] = titres[0]
    if len(titres) >= 2: s["h2"] = titres[1]
    if len(titres) >= 3: s["h3"] = titres[2]
    s.setdefault("h1", body_size + 6)
    s.setdefault("h2", body_size + 3)
    s.setdefault("h3", body_size + 1)
    return s


def detecter_repetitifs(tous_blocs: list, nb_pages: int, seuil: float = 0.4) -> set:
    """
    Détecte les éléments répétés sur de nombreuses pages (en-têtes, pieds de page).
    Retourne un set de textes à ignorer.
    """
    if nb_pages <= 2:
        return set()
    cpt = Counter(_nettoyer(b["text"]) for b in tous_blocs)
    return {t for t, n in cpt.items() if n >= max(2, nb_pages * seuil) and len(t) < 120}


def page_en_md(page, seuils: dict, repetitifs: set) -> str:
    """
    Convertit une page pdfplumber en texte Markdown.
    Gère : titres, listes, tableaux structurés, mise en page 2 colonnes.
    """
    blocs = extraire_blocs(page)
    if not blocs:
        return ""

    has_cols  = any(b.get("has_cols") for b in blocs)
    x0s       = [b["x0"] for b in blocs if round(b["size"]) <= seuils["body"] + 1 and b.get("col") != "d"]
    x0_b      = sorted(x0s)[len(x0s) // 4] if x0s else 50
    sortie, para = [], []

    def vider():
        if para:
            sortie.append(" ".join(para))
            para.clear()

    def est_titre(b):
        size, bold = round(b["size"]), b["bold"]
        if size >= seuils["h1"] or (bold and size > seuils["body"] + 3): return 1
        if size >= seuils["h2"] or (bold and size > seuils["body"] + 2): return 2
        if size >= seuils["h3"] or (bold and size > seuils["body"] + 0.5): return 3
        return 0

    if has_cols:
        # ── Mode 2 colonnes : reconstruit des tableaux Markdown ──
        blocs_tableau_g = {}
        blocs_tableau_d = {}
        tops_traites = set()

        for b in blocs:
            texte = _nettoyer(b["text"])
            if not texte or FILTRES.search(texte.lower()) or texte in repetitifs:
                continue
            niv = est_titre(b)
            col = b.get("col")
            top = b["top"]

            if niv and col != "d":
                vider()
                sortie.append(f"\n{'#' * niv} {texte}\n")
                tops_traites.add(top)
            elif col == "g":
                blocs_tableau_g[top] = blocs_tableau_g.get(top, "") + " " + texte
            elif col == "d":
                blocs_tableau_d[top] = blocs_tableau_d.get(top, "") + " " + texte

        tops_tableau = sorted(
            set(list(blocs_tableau_g.keys()) + list(blocs_tableau_d.keys()))
        )
        if tops_tableau:
            lignes_paires = [
                (blocs_tableau_g.get(t, "").strip(), blocs_tableau_d.get(t, "").strip())
                for t in tops_tableau if t not in tops_traites
            ]
            tableau_courant = []
            tableaux = []
            for g, d in lignes_paires:
                if g or d:
                    tableau_courant.append((g, d))
                else:
                    if tableau_courant:
                        tableaux.append(tableau_courant)
                        tableau_courant = []
            if tableau_courant:
                tableaux.append(tableau_courant)

            for tbl in tableaux:
                if len(tbl) < 2:
                    for g, d in tbl:
                        if g: sortie.append(g)
                        if d: sortie.append(d)
                    continue
                h1, h2 = tbl[0]
                if not h1: h1 = "Colonne 1"
                if not h2: h2 = "Colonne 2"
                sortie.append(f"\n| {h1} | {h2} |")
                sortie.append("| --- | --- |")
                buf_g, buf_d = "", ""
                for g, d in tbl[1:]:
                    if g and d:
                        if buf_g or buf_d:
                            sortie.append(f"| {buf_g.strip()} | {buf_d.strip()} |")
                        buf_g, buf_d = g, d
                    elif g and not d:
                        buf_g += " " + g
                    elif d and not g:
                        buf_d += " " + d
                if buf_g or buf_d:
                    sortie.append(f"| {buf_g.strip()} | {buf_d.strip()} |")
                sortie.append("")
    else:
        # ── Mode colonne unique ──
        try:
            tableaux_md = []
            for tbl in (page.extract_tables() or []):
                if not tbl or len(tbl) < 2:
                    continue
                tbl = [[c or "" for c in row] for row in tbl]
                n   = max(len(r) for r in tbl)
                ent = tbl[0] + [""] * (n - len(tbl[0]))
                lmd = ["| " + " | ".join(str(c).replace("\n", " ").strip() for c in ent) + " |"]
                lmd += ["| " + " | ".join(["---"] * n) + " |"]
                for row in tbl[1:]:
                    row = row + [""] * (n - len(row))
                    lmd.append("| " + " | ".join(str(c).replace("\n", " ").strip() for c in row) + " |")
                tableaux_md.append("\n".join(lmd))
        except Exception:
            tableaux_md = []

        for b in blocs:
            texte = _nettoyer(b["text"])
            if not texte:
                continue
            t = texte.strip()
            if FILTRES.search(t.lower()) or t in repetitifs:
                vider()
                continue
            niv = est_titre(b)
            if niv:
                vider()
                sortie.append(f"\n{'#' * niv} {texte}\n")
            else:
                m = re.match(
                    r'^[\-\*•–—▪▸►→·]\s+(.+)$', texte
                )
                if m:
                    vider()
                    indent = "  " if b["x0"] - x0_b > 30 else ""
                    sortie.append(f"{indent}- {m.group(1)}")
                elif re.match(r'^((?:Art(?:icle)?\.?\s*)?\d+[\.\)]|[IVXivx]+[\.\)]|[A-Za-z][\.\)])\s+', texte):
                    vider()
                    sortie.append(f"- {texte}")
                else:
                    para.append(texte)
        vider()
        for t in tableaux_md:
            sortie.append(f"\n{t}\n")

    return "\n".join(sortie)


def convertir(pdf_path: str, log=print) -> str:
    """
    Pipeline complet PDF → Markdown.
    Retourne le contenu Markdown sous forme de chaîne.
    """
    with pdfplumber.open(pdf_path) as pdf:
        nb = len(pdf.pages)
        log(f"   -> {nb} pages")
        log("   -> Analyse de la structure...")
        tous = []
        for p in pdf.pages:
            tous.extend(extraire_blocs(p))
        seuils = calculer_seuils(tous)
        reps   = detecter_repetitifs(tous, nb)
        log(f"   -> Seuils : H1>={seuils['h1']} H2>={seuils['h2']} "
            f"H3>={seuils['h3']} corps={seuils['body']}")
        if reps:
            log(f"   -> {len(reps)} lignes répétitives filtrées")
        sections = []
        for p in pdf.pages:
            md = page_en_md(p, seuils, reps)
            if md.strip():
                sections.append(md)

    contenu = "\n\n".join(sections)
    contenu = re.sub(r'([^#\|\-\n].{20,}[^.!?:])\n([a-z\(])', r'\1 \2', contenu)
    contenu = re.sub(r'\n{4,}', '\n\n\n', contenu)
    contenu = re.sub(r'\n{3,}(#{1,3} )', r'\n\n\1', contenu)
    for niveau in ['###', '##', '#']:
        pattern = re.escape(niveau) + r' (.+)\n\n' + re.escape(niveau) + r' (.+)'
        def fusionner(m, niv=niveau):
            a, b = m.group(1).strip(), m.group(2).strip()
            if a.endswith(('—', ':', ',', '/')) or len(a) < 20:
                return f'{niv} {a} {b}'
            return m.group(0)
        contenu = re.sub(pattern, fusionner, contenu)
    return contenu.strip()
