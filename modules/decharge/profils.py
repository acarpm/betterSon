"""Profils de test : un profil = tous les paramètres d'un type de batterie.

Stockés dans profils.json (à côté du programme), modifiable à la main ou via
la fenêtre « Gérer les profils » de l'interface.
"""
import json
import os

CHAMPS = ("nom", "tension_coupure", "courant", "puissance", "notes")


def _nombre(valeur, libelle, optionnel=False):
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
    return n


def valider(brut):
    """Renvoie un profil propre à partir de valeurs brutes (texte ou nombres), ou lève ValueError."""
    nom = str(brut.get("nom") or "").strip()
    if not nom:
        raise ValueError("Nom du profil : valeur obligatoire.")
    profil = {
        "nom": nom,
        "tension_coupure": _nombre(brut.get("tension_coupure"), "Tension de coupure"),
        "courant": _nombre(brut.get("courant"), "Courant de décharge", optionnel=True),
        "puissance": _nombre(brut.get("puissance"), "Puissance de décharge", optionnel=True),
        "notes": str(brut.get("notes") or "").strip(),
    }
    if profil["courant"] is None and profil["puissance"] is None:
        raise ValueError("Indiquez un courant ou une puissance de décharge (ou les deux).")
    return profil


def charger(chemin):
    """Renvoie (liste de profils valides, nom du dernier profil utilisé). Fichier absent ou illisible -> vide."""
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
    return profils, donnees.get("dernier")


def sauver(chemin, profils, dernier=None):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"profils": profils, "dernier": dernier}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, chemin)  # écriture atomique : pas de fichier à moitié écrit
