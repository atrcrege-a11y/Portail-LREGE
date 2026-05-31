"""
core/renommage.py — Renommage XML ↔ .cotcot pour masquage FFE WIN.

FFE WIN requiert parfois que les fichiers XML Engarde soient renommés
en .cotcot avant import. Ce module gère les deux sens de conversion.
"""
import os


def renommer_lot(chemins: list[str], ext_src: str, ext_dst: str,
                 log=print) -> tuple[list[str], list[tuple]]:
    """
    Renomme un lot de fichiers de ext_src vers ext_dst.
    Retourne (nouveaux_chemins, erreurs).
    Les fichiers dont l'extension ne correspond pas à ext_src sont ignorés.
    """
    cibles  = [p for p in chemins if p.lower().endswith(ext_src)]
    ignores = [p for p in chemins if not p.lower().endswith(ext_src)]

    for p in ignores:
        log(f"  IGNORÉ (extension incorrecte) : {os.path.basename(p)}")

    if not cibles:
        log(f"Aucun fichier {ext_src} dans la sélection.")
        return chemins[:], []

    nouveaux, erreurs = [], []
    for src in cibles:
        dst = src[:-len(ext_src)] + ext_dst
        try:
            os.rename(src, dst)
            log(f"  {os.path.basename(src)}  →  {os.path.basename(dst)}")
            nouveaux.append(dst)
        except Exception as e:
            log(f"  ERREUR {os.path.basename(src)} : {e}")
            erreurs.append((src, str(e)))
            nouveaux.append(src)  # garde l'ancien chemin en cas d'erreur

    # Reconstruire la liste complète (cibles renommées + non-cibles)
    idx_cibles = [i for i, p in enumerate(chemins) if p.lower().endswith(ext_src)]
    result = list(chemins)
    for i, nouveau in zip(idx_cibles, nouveaux):
        result[i] = nouveau

    return result, erreurs


def xml_vers_cotcot(chemins: list[str], log=print) -> tuple[list[str], list[tuple]]:
    """Renomme les fichiers .xml en .cotcot."""
    return renommer_lot(chemins, ".xml", ".cotcot", log)


def cotcot_vers_xml(chemins: list[str], log=print) -> tuple[list[str], list[tuple]]:
    """Restaure les fichiers .cotcot en .xml."""
    return renommer_lot(chemins, ".cotcot", ".xml", log)
