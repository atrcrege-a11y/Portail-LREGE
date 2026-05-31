"""Fixtures HTML BellePoule synthétiques pour les tests SelecMaster."""


def html_cumulatif(arme="E", genre="H", categorie="M13", territoire="Lorraine",
                   tireurs=None, nb_competitions=3):
    """
    Génère un HTML BellePoule format cumulatif minimal.
    tireurs = [{"nom", "prenom", "club", "annee", "pts_total", "participations"}]
    """
    tireurs = tireurs or [
        {"nom": "MARTIN", "prenom": "Jean", "club": "NANCY CE", "annee": "2013",
         "pts_total": 30000, "participations": 3},
        {"nom": "DUPONT", "prenom": "Paul", "club": "METZ ESC", "annee": "2012",
         "pts_total": 20000, "participations": 2},
    ]

    # Dates
    date_cells = "".join(f"<td>01/0{i+1}/2026</td>" for i in range(nb_competitions))
    scores_header = "".join("<td>Rang</td><td>Points</td>" for _ in range(nb_competitions))

    # Lignes tireurs
    lignes = ""
    for i, t in enumerate(tireurs):
        scores = ""
        for j in range(nb_competitions):
            if j < t["participations"]:
                scores += f"<td>{j+1}</td><td>10000</td>"
            else:
                scores += "<td></td><td></td>"
        lignes += (
            f"<tr><td>{i+1}</td><td>{t['nom']}</td><td>{t['prenom']}</td>"
            f"<td>{t['club']}</td><td>{t['annee']}</td>"
            f"<td>{t['pts_total']}</td>{scores}</tr>\n"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<title>{arme}{genre}{categorie}, Origine du tireur {territoire}</title>
<meta charset="utf-8">
</head>
<body>
<table id="TableClsst">
<tr><td>Date</td>{date_cells}</tr>
<tr><td>Place</td><td>Nom</td><td>Prénom</td><td>Club</td>
    <td>Année Nais.</td><td>Points</td>{scores_header}</tr>
{lignes}
</table>
</body>
</html>""".encode("utf-8")


def html_competition(arme="Sabre", genre="Dames", categorie="M13",
                     cid="Alsace", tireurs=None):
    """
    Génère un HTML BellePoule format compétition minimal.
    """
    tireurs = tireurs or [
        {"nom": "KLEIN",  "prenom": "Anna",  "club": "STRAS ESC"},
        {"nom": "WEBER",  "prenom": "Marie", "club": "MULH ESC"},
    ]

    lignes = ""
    for i, t in enumerate(tireurs):
        lignes += (
            f"<tr><td>{i+1}</td><td>{t['nom']}</td><td>{t['prenom']}</td>"
            f"<td>{t['club']}</td><td>{cid}</td><td>FRA</td></tr>\n"
        )

    return f"""<!DOCTYPE html>
<html>
<head><title>Compétition BellePoule</title></head>
<body>
<div class="Round">
  <h1>Classement général</h1>
  <h1>{arme} - {genre} - {categorie}</h1>
  <table class="List">
    <tr><th>Place</th><th>Nom</th><th>Prénom</th><th>Club</th>
        <th>CID</th><th>Nation</th></tr>
    {lignes}
  </table>
</div>
</body>
</html>""".encode("utf-8")


def html_invalide():
    """HTML qui ne ressemble pas à un export BellePoule."""
    return b"<html><body><p>Bonjour monde</p></body></html>"


def html_vide():
    """HTML vide."""
    return b"<html><body></body></html>"
