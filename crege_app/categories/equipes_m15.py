"""
categories/equipes_m15.py — Sélection équipes M15 : GE1 / GE2 / GE3.

Règles métier (protégées) :
  GE1 = Top N du classement NATIONAL Grand Est
  GE2 = N premiers du classement RÉGIONAL non déjà en GE1
  GE3 = N suivants du classement régional non sélectionnés
  Remplaçants = suite du classement régional
"""
import zlib as _z, base64 as _b
from ..core.utils import est_grand_est, COL_RANG, COL_NOM, COL_PRENOM, COL_CLUB, COL_REGION

# ── Logique GE protégée ─────────────────────────────────────────────
_SRC = (
    "def _build_equipes(df_nat_f, df_reg_f, taille_eq, config):\n"
    "    ge1_df = df_nat_f[df_nat_f[COL_REGION].apply(est_grand_est)].head(taille_eq)\n"
    "    noms_ge1 = set((r[COL_NOM], r[COL_PRENOM]) for _, r in ge1_df.iterrows())\n"
    "    df_reg_hors_ge1 = df_reg_f[~df_reg_f.apply(\n"
    "        lambda r: (r[COL_NOM], r[COL_PRENOM]) in noms_ge1, axis=1)]\n"
    "    ge2_df   = df_reg_hors_ge1.iloc[0:taille_eq]\n"
    "    ge3_df   = df_reg_hors_ge1.iloc[taille_eq:taille_eq*2]\n"
    "    rempl_df = df_reg_hors_ge1.iloc[taille_eq*2:]\n"
    "    top_reg_noms = set((r[COL_NOM], r[COL_PRENOM]) for _, r in df_reg_f.head(taille_eq).iterrows())\n"
    "    liberes = len(noms_ge1 & top_reg_noms)\n"
    "    comp = config.get('competition','FDJ')\n"
    "    return ge1_df, ge2_df, ge3_df, rempl_df, noms_ge1, liberes, comp\n"
)
_glb = {"est_grand_est": est_grand_est, "COL_REGION": COL_REGION,
        "COL_NOM": COL_NOM, "COL_PRENOM": COL_PRENOM, "COL_RANG": COL_RANG}
exec(compile(_SRC, "<equipes_m15>", "exec"), _glb)
_build_equipes = _glb["_build_equipes"]


def construire_equipes_m15(df_national, df_regional, config: dict) -> dict:
    """Construit les données équipes M15 pour H ou D."""
    from ..core.styles import COULEUR_GE1, COULEUR_GE2, COULEUR_GE3, COULEUR_REMPL_EQ

    taille_eq = config.get("taille_equipe", 4)
    ge1_df, ge2_df, ge3_df, rempl_df, noms_ge1, liberes, comp = \
        _build_equipes(df_national, df_regional, taille_eq, config)

    comp_labels = {
        "FDJ": "Fête des Jeunes",
        "Zone": "Épreuve de zone",
        "1/2": "1/2 Finale",
    }

    def _tireurs(df, rang_prefix):
        return [
            {"rang": f"{rang_prefix} {r[COL_RANG]}", "nom": r[COL_NOM],
             "prenom": r[COL_PRENOM], "club": r[COL_CLUB]}
            for _, r in df.iterrows()
        ]

    critere_ge2_n = taille_eq - liberes
    equipes = [
        {
            "numero": 1, "label": "Grand Est 1",
            "critere": f"Les {taille_eq} premiers du classement national Grand Est",
            "tireurs": _tireurs(ge1_df, "CL NAT"),
        },
        {
            "numero": 2, "label": "Grand Est 2",
            "critere": (f"Les {taille_eq} premiers du classement régional "
                        "non sélectionnés en GE1"),
            "tireurs": _tireurs(ge2_df, "CL GE"),
        },
        {
            "numero": 3, "label": "Grand Est 3",
            "critere": (f"Les {taille_eq} suivants du classement régional "
                        "non sélectionnés en GE1 ou GE2"),
            "tireurs": _tireurs(ge3_df, "CL GE"),
        },
    ]

    remplacants = _tireurs(rempl_df, "CL GE")

    return {
        "format": "equipes_m15",
        "meta": {
            "competition":              comp_labels.get(comp, comp),
            "cat_label":                config.get("cat_label", "M15"),
            "date":                     config.get("date", ""),
            "lieu":                     config.get("lieu", ""),
            "discipline":               config.get("discipline", ""),
            "mail_retour":              config.get("mail_retour", "administration@crege.fr"),
            "date_limite_retour":       config.get("date_limite_retour", ""),
            "date_engagement_extranet": config.get("date_engagement_extranet", ""),
            "arbitrage_config":         config.get("arbitrage_config", {}),
        },
        "equipes": equipes,
        "remplacants": remplacants,
    }
