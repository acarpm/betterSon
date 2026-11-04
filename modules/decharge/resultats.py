"""Lecture et analyse des fichiers CSV produits par les tests (sans interface graphique)."""
import csv
import glob
import os
import re
from datetime import datetime

import identite

# Nom de fichier : <profil>_<serie>_<AAAAMMJJ>_<HHMMSS>.csv
MOTIF = re.compile(r"^(?P<nom>.+)_(?P<d>\d{8})_(?P<h>\d{6})\.csv$")


def lister(dossier):
    return glob.glob(os.path.join(dossier, "*.csv"))


def analyser(chemin):
    """Renvoie un dict de résumé + séries, ou None si le fichier est vide / illisible."""
    base = os.path.basename(chemin)
    m = MOTIF.match(base)
    try:
        date = datetime.strptime(m["d"] + m["h"], "%Y%m%d%H%M%S") if m else datetime.fromtimestamp(os.path.getmtime(chemin))
    except (ValueError, OSError):
        date = datetime.fromtimestamp(0)
    nom = (m["nom"] if m else os.path.splitext(base)[0]).replace("_", " ")

    t, v, a, w = [], [], [], []
    ah = wh = 0.0
    entete = {"technicien": None, "poste": None}
    try:
        with open(chemin, newline="", encoding="utf-8") as f:
            entete = identite.lire_entete(f)  # absent sur les anciens tests : la première ligne est alors l'en-tête CSV
            lecteur = csv.reader(f)
            next(lecteur, None)  # en-tête
            for ligne in lecteur:
                try:
                    tt, vv, aa, ww, ahh, whh = (float(x) for x in ligne[:6])
                except ValueError:
                    continue  # ligne incomplète (test coupé net) : ignorée
                t.append(tt); v.append(vv); a.append(aa); w.append(ww)
                ah, wh = ahh, whh
    except OSError:
        return None
    if not t:
        return None
    n = len(t)
    return {
        "chemin": chemin, "nom": nom, "technicien": entete["technicien"], "poste": entete["poste"], "date": date, "points": n,
        "duree_s": t[-1], "ah": ah, "wh": wh,
        "v_debut": v[0], "v_fin": v[-1], "v_min": min(v),
        "i_moy": sum(a) / n, "p_moy": sum(w) / n,
        "series": {"V": list(zip(t, v)), "A": list(zip(t, a)), "W": list(zip(t, w))},
    }


def analyser_dossier(dossier):
    """Tous les résultats lisibles, du plus récent au plus ancien."""
    res = [r for r in (analyser(c) for c in lister(dossier)) if r]
    return sorted(res, key=lambda r: r["date"], reverse=True)
