"""crege_app/sabre_laser — Module Sabre Laser SelecGE."""
from .config    import (DISCIPLINES, DISC_MAP, PALETTES, get_discipline,
                        get_quota_ge, get_calendrier, get_palette, get_niveau, detecter_format)
from .parseurs  import lire_classement, lire_et, lire_chore
from .selection import construire_selection_sl, construire_selection_et, construire_selection_chore
from .generateur import generer_docs_separes, generer_doc_multi
