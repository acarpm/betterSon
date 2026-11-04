"""Identités : le poste de test (ce PC) et les techniciens qui commandent les tests.

- Le poste a un identifiant (ex. « banc-1 »), saisi une fois au premier lancement.
- Les techniciens sont une liste (« Prénom Nom ») ; chaque test est rattaché à celui qui l'a commandé.
Tout est dans config.json : "poste", "techniciens", "dernier_technicien".
Le serveur BatConnect est la référence pour la liste des techniciens (voir synchro.py) ; config.json en garde une copie
qui sert tant que le serveur ne répond pas. Les ajouts et suppressions faits hors-ligne attendent dans
"techniciens_a_ajouter" / "techniciens_a_supprimer" et sont transmis dès que le serveur répond.
Chaque CSV commence par deux lignes de commentaire (« # technicien: … », « # poste: … »), relues par l'analyse.
"""
import re

import config

LONGUEUR_MAX = 60
PREFIXES = {"technicien": "# technicien:", "poste": "# poste:"}
_POSTE_VALIDE = re.compile(r"^[\w .\-]+$")  # le serveur refuse les autres caractères (pas de chemin, pas de contrôle)


def nettoyer(texte):
    """Espaces et caractères de contrôle normalisés ; chaîne vide si rien d'exploitable."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", str(texte or ""))).strip()[:LONGUEUR_MAX]


# ---------- poste ----------
def poste():
    p = nettoyer(config.charger().get("poste"))
    return p if p and _POSTE_VALIDE.match(p) else None


def definir_poste(identifiant):
    p = nettoyer(identifiant)
    if not p:
        raise ValueError("L'identifiant du poste est obligatoire.")
    if not _POSTE_VALIDE.match(p):
        raise ValueError("Utilisez uniquement lettres, chiffres, espaces, tirets et points.")
    with config._VERROU:
        data = config.charger()
        data["poste"] = p
        config.sauver(data)


# ---------- techniciens ----------
def techniciens():
    brut = config.charger().get("techniciens")
    vus, liste = set(), []
    for t in brut if isinstance(brut, list) else []:
        t = nettoyer(t)
        if t and t.casefold() not in vus:
            vus.add(t.casefold())
            liste.append(t)
    return liste


def ajouter_technicien(prenom, nom):
    """Ajoute « Prénom Nom » (sans doublon) et renvoie ce nom complet ; ValueError si prénom ou nom vide."""
    prenom, nom = nettoyer(prenom), nettoyer(nom)
    if not prenom or not nom:
        raise ValueError("Le prénom et le nom sont obligatoires.")
    maj = lambda t: t[:1].upper() + t[1:]  # première lettre en majuscule, le reste tel que saisi (d'Artagnan, Jean-Pierre)
    complet = f"{maj(prenom)} {maj(nom)}"
    with config._VERROU:
        existants = techniciens()
        deja = next((t for t in existants if t.casefold() == complet.casefold()), None)
        if deja:
            return deja
        data = config.charger()
        data["techniciens"] = existants + [complet]
        data["techniciens_a_ajouter"] = _en_attente(data, "techniciens_a_ajouter") + [complet]
        data["techniciens_a_supprimer"] = [t for t in _en_attente(data, "techniciens_a_supprimer")
                                           if t.casefold() != complet.casefold()]
        config.sauver(data)
    return complet


def supprimer_technicien(complet):
    with config._VERROU:
        data = config.charger()
        cle = nettoyer(complet).casefold()
        data["techniciens"] = [t for t in techniciens() if t.casefold() != cle]
        data["techniciens_a_ajouter"] = [t for t in _en_attente(data, "techniciens_a_ajouter") if t.casefold() != cle]
        data["techniciens_a_supprimer"] = _en_attente(data, "techniciens_a_supprimer") + [nettoyer(complet)]
        if nettoyer(data.get("dernier_technicien")).casefold() == nettoyer(complet).casefold():
            data.pop("dernier_technicien", None)
        config.sauver(data)


def _en_attente(data, cle):
    brut = data.get(cle)
    return [t for t in (nettoyer(x) for x in (brut if isinstance(brut, list) else [])) if t]


def operations_en_attente():
    """(ajouts, suppressions) pas encore transmis au serveur."""
    data = config.charger()
    return _en_attente(data, "techniciens_a_ajouter"), _en_attente(data, "techniciens_a_supprimer")


def operation_transmise(cle, nom):
    """Retire `nom` de la liste d'attente `cle` ('techniciens_a_ajouter' ou 'techniciens_a_supprimer')."""
    with config._VERROU:
        data = config.charger()
        data[cle] = [t for t in _en_attente(data, cle) if t.casefold() != nettoyer(nom).casefold()]
        config.sauver(data)


def remplacer_techniciens(liste):
    """Copie locale = liste du serveur (opérations en attente comprises, qui sont rejouées si le serveur les a ratées)."""
    with config._VERROU:
        data = config.charger()
        ajouts, suppr = _en_attente(data, "techniciens_a_ajouter"), _en_attente(data, "techniciens_a_supprimer")
        data["techniciens"] = [t for t in liste if nettoyer(t)]
        known = {t.casefold() for t in data["techniciens"]}
        data["techniciens"] += [t for t in ajouts if t.casefold() not in known]
        data["techniciens"] = [t for t in data["techniciens"] if t.casefold() not in {x.casefold() for x in suppr}]
        config.sauver(data)


def dernier_technicien():
    d = nettoyer(config.charger().get("dernier_technicien"))
    return d if d in techniciens() else None


def retenir_technicien(complet):
    with config._VERROU:
        data = config.charger()
        data["dernier_technicien"] = nettoyer(complet)
        config.sauver(data)


# ---------- signature des CSV ----------
def lignes_signature(technicien):
    """En-tête de commentaires à écrire en tête d'un CSV (fins de ligne comprises)."""
    lignes = [f"{PREFIXES['technicien']} {nettoyer(technicien)}\n"] if nettoyer(technicien) else []
    if poste():
        lignes.append(f"{PREFIXES['poste']} {poste()}\n")
    return "".join(lignes)


def lire_entete(f):
    """Lit les lignes de commentaire en tête d'un fichier texte ouvert ; renvoie {'technicien', 'poste'} (None si absent).
    Le curseur est laissé sur la première ligne qui n'est pas une signature (l'en-tête du CSV)."""
    infos = {"technicien": None, "poste": None}
    while True:
        debut = f.tell()
        ligne = f.readline()
        cle = next((k for k, p in PREFIXES.items() if ligne.startswith(p)), None)
        if cle is None:
            f.seek(debut)
            return infos
        infos[cle] = nettoyer(ligne[len(PREFIXES[cle]):]) or None
