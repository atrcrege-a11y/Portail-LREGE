"""
core/config.py
Constantes partagées entre toutes les compétitions.
"""

APP_NAME         = "SYNESC"
APP_VERSION      = "2.4.3"
APP_RELEASE_DATE = "2026-04-05"

CHANGELOG = [
    {
        "version": "2.4.3",
        "date": "2026-04-05",
        "label": "Bilan financier Alsace par arme",
        "notes": [
            "Bilan Financier Alsace : recettes équipes groupées par arme (Fleuret / Épée / Sabre) puis par catégorie",
            "Colonnes Eq.H / Eq.D / Eq.MX / P.U. / Rec.H / Rec.D / Total avec formules dynamiques",
            "Équipes mixtes (M9) : colonne Eq.MX dédiée dans le bilan",
            "Dépenses arbitres : résumé (nb + coût total barème LREGE) sans détail nominatif",
            "Solde par jour et solde global avec mise en forme conditionnelle vert/rouge",
        ],
    },
    {
        "version": "2.4.2",
        "date": "2026-04-05",
        "label": "Alsace par arme + colonne Arme arbitres",
        "notes": [
            "Alsace : feuilles Excel séparées par arme (Indiv Fleuret / Épée / Sabre, Équipe Fleuret / Épée / Sabre)",
            "Seules les armes présentes dans les fichiers chargés génèrent une feuille",
            "Feuille Arbitres : nouvelle colonne 'Arme' avec code couleur (bleu=Fleuret, vert=Épée, orange=Sabre)",
            "Colonne Arme disponible pour tous les types de compétition (Grand Est, Alsace, Lorraine)",
            "Équipes mixtes (M9 Alsace) : colonne Eq.MX / Tir.MX avec fond violet dans la feuille Équipe",
            "Aperçu : compteur clubs corrigé pour les fichiers mixtes et les catégories Alsace (M9/M11)",
        ],
    },
    {
        "version": "2.4.1",
        "date": "2026-04-05",
        "label": "PDF Lorraine arme + compteur clubs",
        "notes": [
            "PDF Coupe de Lorraine : parsing des libellés avec arme ('M11 Fleuret H/D') → clé M11|F",
            "Détection correcte de la date par position y dans la page (multi-tableaux multi-jours)",
            "Regex arme corrigé pour les accents (Épée, Epée) via lookaround",
            "Compteur CLUBS affiché correctement dans l'interface (appel dynamique /api/preview)",
            "Rappel DT reformulé : 'le DT reste libre de modifier les formules en fonction des effectifs'",
            "Rappel DT affiché une seule fois par jour (après les épreuves individuelles)",
        ],
    },
    {
        "version": "2.4.0",
        "date": "2026-04-05",
        "label": "Formules compétition + PDF multi-formats + améliorations",
        "notes": [
            "Formule proposée dans le corps du mail pour chaque épreuve (poules + TED)",
            "Algorithme de décomposition en poules de 5 à 8 tireurs (préférence 7), adapté à l'effectif réel",
            "Extraction PDF horaires : 4 formats reconnus (tableau colonnes, tableau structuré, texte libre, texte condensé)",
            "Normalisation V1/V2/V3/V4/Hommes/Dames → Vétérans dans les PDF et dans le mail",
            "Coupe de Lorraine activée dans l'interface (bouton cliquable)",
            "Nouveau logo Escrime Grand Est dans l'interface web",
            "Logo supprimé des fichiers Excel générés",
            "Suppression de la clé API Claude (extraction PDF 100% locale via pdfplumber, sans coût)",
            "Correction : routes /api/generate_mail et /api/mail_body restaurées (décorateurs perdus)",
        ],
    },
    {
        "version": "2.3.1",
        "date": "2026-04-04",
        "label": "Correctifs interface",
        "notes": [
            "Onglets (Aperçu / Changelog / À propos) repositionnés en haut du panneau principal",
            "Layout fixe : header, sidebar et panneau principal ne scrollent plus ensemble",
            "Import PDF programme : bouton 'Choisir un fichier' en plus du glisser-déposer",
            "Messages d'erreur PDF précis et affichés dans la zone (plus de message générique)",
        ],
    },
    {
        "version": "2.3.0",
        "date": "2026-04-04",
        "label": "Extraction horaires PDF + génération mail Gmail",
        "notes": [
            "Zone de dépôt PDF programme dans la sidebar",
            "Extraction automatique des horaires par catégorie (pdfplumber, sans API externe)",
            "Horaires indiv dans le corps du mail : Appel · Scratch · Début",
            "Équipes : horaires propres si disponibles, sinon 'à l'issue des épreuves individuelles'",
            "Bouton Gmail : ouvre Gmail avec sujet pré-rempli + modale copier-coller du corps",
            "Bouton Mail (.eml) : fichier prêt pour Outlook/Thunderbird avec Excel en PJ",
        ],
    },
    {
        "version": "2.2.0",
        "date": "2026-04-04",
        "label": "Contrôle des quotas arbitrage par club",
        "notes": [
            "Colonnes Besoin arb. / Fournis / Statut après Total Club dans Épreuve Indiv et Équipe",
            "Statut coloré : ✓ OK (vert) ou ▲ Manque N (rouge) par club et par jour",
            "Même logique dans les 3 feuilles arme de la Coupe de Lorraine",
            "Fournis = nb d'arbitres du même club ce jour-là (dédoublonné par licence)",
        ],
    },
    {
        "version": "2.1.0",
        "date": "2026-04-04",
        "label": "Arbitrage, bilan financier et arbitres-tireurs",
        "notes": [
            "Quota arbitrage commun H+D : indiv <4=0 / 4-8=1 / >8=2 ; équipe 1-2=1 / 3-4=2 / 5+=3",
            "Détection arbitres-tireurs par croisement de licences dans la feuille Arbitres",
            "Bilan Financier : recettes indiv + équipes par jour, dépenses arbitres, solde coloré",
            "Alsace : ajout M9/M11/M13 en équipe (tarif 30 €)",
            "Coupe de Lorraine : implémentation complète (M9-M15, 3 armes, indiv uniquement)",
        ],
    },
    {
        "version": "2.0.0",
        "date": "2026-04-03",
        "label": "Refactorisation modulaire — architecture plugin/strategy",
        "notes": [
            "Séparation core/ (config, parser, styles) et competitions/ (Grand Est, Alsace, Lorraine)",
            "Classe abstraite CompetitionBase : pipeline commun, surcharges par compétition",
            "Sélecteur type compétition dans l'interface (Grand Est / Alsace / Coupe de Lorraine)",
            "Vétérans équipe : V1+V2 → 'Vétérans', V3+V4 → 'Gds Vétérans'",
        ],
    },
    {
        "version": "1.0.0",
        "date": "2026-04-02",
        "label": "Première version",
        "notes": [
            "Lecture et parsing des fichiers XML Engarde (individuel et équipes)",
            "Génération du fichier Excel EGESC au format LREGE standard",
            "Interface web avec glisser-déposer des fichiers XML et ZIP",
            "Lanceur Windows automatique",
        ],
    },
]

# ── Règles d'arbitrage
def besoin_arbitre_indiv(nb_tireurs):
    """< 4 tireurs = 0, 4-8 = 1, > 8 = 2."""
    if nb_tireurs < 4:
        return 0
    elif nb_tireurs <= 8:
        return 1
    else:
        return 2

def besoin_arbitre_equipe(nb_equipes):
    """1-2 équipes = 1, 3-4 = 2, 5+ = 3. 0 équipe = 0."""
    if nb_equipes == 0:
        return 0
    elif nb_equipes <= 2:
        return 1
    elif nb_equipes <= 4:
        return 2
    else:
        return 3

FORMULE_ARBITRE_INDIV = (
    '=IF({col}{row}<4,0,IF({col}{row}<=8,1,2))'
)
FORMULE_ARBITRE_EQUIPE = (
    '=IF({col}{row}=0,0,IF({col}{row}<=2,1,IF({col}{row}<=4,2,3)))'
)

BAREME_ARBITRES = [
    # Source : règlement FFE 2024–2025 (en attente des informations 2025–2026)
    # Codes Engarde : FD = Formation Territoriale, D = Territorial
    ("FT", 25),   # Formation Territoriale
    ("FD", 25),   # Formation Territoriale (alias Engarde)
    ("T",  30),   # Territorial
    ("D",  30),   # Territorial (alias Engarde)
    ("FR", 35),   # Formation Régionale
    ("R",  45),   # Régional
    ("FN", 50),   # Formation Nationale
    ("N",  70),   # National
    ("I",  100),  # International
]

# ── Jours de la semaine (lundi=0)
JOURS_SEMAINE = ["lundi", "mardi", "mercredi", "jeudi",
                 "vendredi", "samedi", "dimanche"]

# ── Couleurs communes Excel
COLORS = {
    "navy":      "1F4E79",
    "blue":      "2E6099",
    "accent":    "C8941A",
    "grey":      "D9D9D9",
    "ice_blue":  "BDD7EE",
    "light_blue":"DDEEFF",
    "light_pink":"FFE0E0",
    "light_h":   "EAF4FF",
    "light_d":   "FFF0F5",
    "green_bg":  "EBF3E8",
    "gold":      "C8941A",
    "white":     "FFFFFF",
    # Financier
    "fin_indiv":  "DDEEFF",
    "fin_equipe": "D9F0D3",
    "fin_depense":"FFE5D0",
    "solde_pos":  "C6EFCE",
    "solde_neg":  "FFC7CE",
}

# ── Responsables arbitrage
# À compléter dès réception des listes officielles
# Format : liste de chaînes "Prénom NOM"

# Responsable CRA (Grand Est et Alsace) — 1 seul par compétition
NOMS_CRA = [
    # "Prénom NOM",   ← à ajouter
]

# Superviseur Grand Est — 1 par compétition (en plus du CRA)
NOMS_SUPERVISEURS_GRAND_EST = [
    # "Prénom NOM",   ← à ajouter
]

# Superviseurs Lorraine — 1 par arme
NOMS_SUPERVISEURS_LORRAINE = [
    # "Prénom NOM",   ← à ajouter
]
