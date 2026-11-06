"""Profils du test de résistance interne : un profil = tous les réglages de la séquence, fixés par l'opérateur."""
import json
import os

# (clé, libellé, unité, valeur par défaut, entier ?, obligatoire ?)
PARAMETRES = (
    ("courant", "Courant du pulse", "A", None, False, True),
    ("pulse_s", "Durée du pulse", "s", 20, False, True),
    ("mesure_apres_s", "Mesure à partir de", "s", 10, False, True),
    ("repos_s", "Repos avant chaque pulse", "s", 10, False, True),
    ("repetitions", "Nombre de pulses", "", 3, True, True),
    ("attente_s", "Attente entre deux pulses", "s", 60, False, True),
    ("tension_min_cellule", "Tension mini d'une cellule", "V", None, False, False),
)
CHAMPS = ("nom",) + tuple(p[0] for p in PARAMETRES) + ("notes",)


def defauts():
    return {c: d for c, _, _, d, _, _ in PARAMETRES if d is not None}


def _nombre(valeur, libelle, entier=False, optionnel=False):
    if valeur is None or str(valeur).strip() == "":
        if optionnel:
            return None
        raise ValueError(f"{libelle} : valeur obligatoire.")
    try:
        n = float(str(valeur).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"{libelle} : entrez un nombre.") from None
    if n <= 0:
        raise ValueError(f"{libelle} : doit être supérieur à 0.")
    if entier:
        if n != int(n):
            raise ValueError(f"{libelle} : entrez un nombre entier.")
        return int(n)
    return n


def valider(brut):
    """Profil propre à partir de valeurs brutes (texte ou nombres), ou ValueError avec un message lisible."""
    nom = str(brut.get("nom") or "").strip()
    if not nom:
        raise ValueError("Nom du profil : valeur obligatoire.")
    profil = {"nom": nom}
    for cle, libelle, _, _, entier, obligatoire in PARAMETRES:
        profil[cle] = _nombre(brut.get(cle), libelle, entier, optionnel=not obligatoire)
    if profil["mesure_apres_s"] >= profil["pulse_s"]:
        raise ValueError("« Mesure à partir de » doit être inférieure à la durée du pulse "
                         "(il faut une fenêtre de mesure avant la fin du pulse).")
    profil["notes"] = str(brut.get("notes") or "").strip()
    return profil


def duree_totale_s(p):
    """Durée approximative de la séquence complète."""
    n = p["repetitions"]
    return n * (p["repos_s"] + p["pulse_s"]) + (n - 1) * p["attente_s"]


def resume(p):
    texte = f"{p['courant']:g} A  ·  pulse {p['pulse_s']:g} s  ·  {p['repetitions']} pulse{'s' if p['repetitions'] > 1 else ''}"
    return texte


def charger(chemin):
    """(liste de profils valides, nom du dernier utilisé). Fichier absent ou illisible -> vide."""
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
    except (OSError, ValueError):
        return [], None
    profils = []
    for brut in donnees.get("profils", []) if isinstance(donnees, dict) else []:
        try:
            profils.append(valider(brut))
        except (ValueError, AttributeError):
            pass  # profil invalide ignoré plutôt que de bloquer le programme
    return profils, donnees.get("dernier") if isinstance(donnees, dict) else None


def sauver(chemin, profils, dernier=None):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"profils": profils, "dernier": dernier}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, chemin)  # écriture atomique
