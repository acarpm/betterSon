"""Lecture et analyse des CSV du test de résistance interne (sans interface graphique)."""
import csv
import glob
import os
import re
from datetime import datetime

import identite

from . import calcul

MOTIF = re.compile(r"^(?P<nom>.+)_(?P<d>\d{8})_(?P<h>\d{6})\.csv$")   # <profil>_<serie>_<AAAAMMJJ>_<HHMMSS>.csv


def lister(dossier):
    return glob.glob(os.path.join(dossier, "*.csv"))


def _nombre(texte):
    try:
        return float(texte)
    except (TypeError, ValueError):
        return None


def analyser(chemin):
    """Dict de résumé (essais, synthèse, courbes) ou None si le fichier est vide / illisible."""
    base = os.path.basename(chemin)
    m = MOTIF.match(base)
    try:
        date = datetime.strptime(m["d"] + m["h"], "%Y%m%d%H%M%S") if m else datetime.fromtimestamp(os.path.getmtime(chemin))
    except (ValueError, OSError):
        date = datetime.fromtimestamp(0)
    nom = (m["nom"] if m else os.path.splitext(base)[0]).replace("_", " ")
    echantillons, temps, entete = [], [], {"technicien": None, "poste": None}
    try:
        with open(chemin, newline="", encoding="utf-8") as f:
            entete = identite.lire_entete(f)
            lecteur = csv.reader(f)
            next(lecteur, None)
            for ligne in lecteur:
                if len(ligne) < 5 or _nombre(ligne[0]) is None or not ligne[1].isdigit():
                    continue   # ligne incomplète (test coupé net) : ignorée
                echantillons.append({"essai": int(ligne[1]), "phase": ligne[2], "v": _nombre(ligne[3]), "i": _nombre(ligne[4]),
                                     "cellules": [_nombre(x) for x in ligne[5:]]})
                temps.append(float(ligne[0]))
    except OSError:
        return None
    if not echantillons:
        return None
    essais = calcul.resistances(echantillons)
    return {
        "chemin": chemin, "nom": nom, "technicien": entete["technicien"], "poste": entete["poste"], "date": date,
        "duree_s": temps[-1], "essais": essais, "synthese": calcul.synthese(essais),
        "series": {"V": [(t, e["v"]) for t, e in zip(temps, echantillons) if e["v"] is not None],
                   "A": [(t, e["i"]) for t, e in zip(temps, echantillons) if e["i"] is not None]},
    }


def analyser_dossier(dossier):
    """Tous les résultats lisibles, du plus récent au plus ancien."""
    res = [r for r in (analyser(c) for c in lister(dossier)) if r]
    return sorted(res, key=lambda r: r["date"], reverse=True)
