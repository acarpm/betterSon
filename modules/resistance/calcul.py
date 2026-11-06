"""Calcul des résistances internes à partir des échantillons d'un test (sans interface, sans matériel).

Principe : R = (V_repos - V_pulse) / I_pulse, pour le pack (tension lue par la charge) et pour chaque cellule (Daly).
  - V_repos  : moyenne des tensions pendant la phase « repos » qui précède le pulse (charge coupée) ;
  - V_pulse  : moyenne des tensions pendant la phase « mesure » (du pulse, une fois passé le délai de stabilisation) ;
  - I_pulse  : moyenne du courant mesuré par la charge pendant la phase « mesure ».

Un échantillon est un dict : {"essai": n, "phase": "repos" | "pulse" | "mesure" | "attente", "v": V pack,
"i": A, "cellules": [V, ...]}. Une valeur absente est None. Les résistances sont en milliohms.
"""
import statistics

COURANT_MIN_A = 0.05      # en dessous, le pulse n'a pas eu lieu : aucune résistance n'est calculée
ECART_ANORMAL = 0.30      # une cellule dont R s'écarte de plus de 30 % de la médiane est signalée


def moyenne(valeurs):
    valeurs = [v for v in valeurs if v is not None]
    return sum(valeurs) / len(valeurs) if valeurs else None


def _r_mohm(v_repos, v_pulse, courant):
    if v_repos is None or v_pulse is None or courant is None or courant < COURANT_MIN_A:
        return None
    return (v_repos - v_pulse) / courant * 1000.0


def _moyenne_cellules(echantillons, nb):
    """Moyenne par cellule sur les échantillons ; une cellule jamais lue reste None."""
    return [moyenne([e["cellules"][k] for e in echantillons if k < len(e.get("cellules") or [])]) for k in range(nb)]


def resistance_essai(echantillons, essai):
    """Résultat d'un essai (un pulse) ou None s'il manque le repos ou la phase de mesure."""
    de_essai = [e for e in echantillons if e["essai"] == essai]
    repos = [e for e in de_essai if e["phase"] == "repos"]
    mesure = [e for e in de_essai if e["phase"] == "mesure"]
    if not repos or not mesure:
        return None
    nb = max((len(e.get("cellules") or []) for e in repos + mesure), default=0)
    courant = moyenne([e["i"] for e in mesure])
    v0, v1 = moyenne([e["v"] for e in repos]), moyenne([e["v"] for e in mesure])
    c0, c1 = _moyenne_cellules(repos, nb), _moyenne_cellules(mesure, nb)
    return {
        "essai": essai, "courant": courant, "v_repos": v0, "v_pulse": v1, "r_pack": _r_mohm(v0, v1, courant),
        "cellules": [{"v_repos": a, "v_pulse": b, "r": _r_mohm(a, b, courant)} for a, b in zip(c0, c1)],
    }


def resistances(echantillons):
    """Résultats de tous les essais présents (dans l'ordre), ceux qui sont incomplets étant ignorés."""
    numeros = sorted({e["essai"] for e in echantillons})
    return [r for r in (resistance_essai(echantillons, n) for n in numeros) if r]


def _stats(valeurs):
    valeurs = [v for v in valeurs if v is not None]
    if not valeurs:
        return {"moyenne": None, "ecart_type": None, "n": 0}
    return {"moyenne": statistics.fmean(valeurs), "ecart_type": statistics.stdev(valeurs) if len(valeurs) > 1 else 0.0,
            "n": len(valeurs)}


def synthese(essais):
    """Moyenne (et écart-type, qui renseigne sur la reproductibilité) des essais, pour le pack et chaque cellule.

    Renvoie {"n_essais", "pack": stats, "cellules": [stats + "ecart_mediane" (fraction) + "anormale"], "somme_cellules"}.
    """
    nb = max((len(r["cellules"]) for r in essais), default=0)
    cellules = [_stats([r["cellules"][k]["r"] for r in essais if k < len(r["cellules"])]) for k in range(nb)]
    connues = [c["moyenne"] for c in cellules if c["moyenne"] is not None]
    mediane = statistics.median(connues) if connues else None
    for c in cellules:
        ecart = None
        if c["moyenne"] is not None and mediane:
            ecart = (c["moyenne"] - mediane) / abs(mediane)
        c["ecart_mediane"] = ecart
        c["anormale"] = ecart is not None and abs(ecart) > ECART_ANORMAL
    return {"n_essais": len(essais), "pack": _stats([r["r_pack"] for r in essais]), "cellules": cellules,
            "somme_cellules": sum(connues) if connues and len(connues) == nb else None}
