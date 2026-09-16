"""Fixtures XML Engarde synthetiques pour les tests SYNESC."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def xml_individuel(arme="E", categorie="SENIORS", sexe="M",
                   date="16.05.2026", titre="EGESC Test",
                   tireurs=None, arbitres=None, type_comp="I"):
    """Construit un XML Engarde minimal pour une epreuve individuelle."""
    tireurs = tireurs or []
    arbitres = arbitres or []
    t_xml = "\n".join(
        f'  <Tireur Nom="{t["nom"]}" Prenom="{t.get("prenom","X")}" '
        f'Licence="{t.get("licence","0")}" Club="{t.get("club","")}" '
        f'Equipe="{t.get("equipe","")}" Region="{t.get("region","Grand Est")}" '
        f'Ligue="{t.get("ligue","GES")}" Departement="{t.get("dept","88")}" '
        f'Sexe="{t.get("sexe","M")}" DateNaissance="1990-01-01" />'
        for t in tireurs
    )
    a_xml = "\n".join(
        f'  <Arbitre Nom="{a["nom"]}" Prenom="{a.get("prenom","X")}" '
        f'Licence="{a.get("licence","0")}" Club="{a.get("club","")}" '
        f'Region="{a.get("region","Grand Est")}" Ligue="{a.get("ligue","GES")}" '
        f'Departement="{a.get("dept","88")}" Categorie="{a.get("cat","R")}" />'
        for a in arbitres
    )
    xml_str = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        f'<Epreuve Arme="{arme}" Categorie="{categorie}" Sexe="{sexe}"\n'
        f'         TitreLong="{titre}" Date="{date}" DateDebut="{date}" DateFin="{date}"\n'
        f'         ID="001" Type="{type_comp}">\n'
        f'{t_xml}\n'
        f'{a_xml}\n'
        '</Epreuve>'
    )
    return xml_str.encode("iso-8859-1")
