"""Envoi des CSV de mesures vers le serveur BatConnect, en plus de la sauvegarde locale.

Le CSV local reste la référence : l'envoi est en tâche de fond, ne bloque jamais l'interface et n'échoue jamais
bruyamment. Un envoi raté (réseau coupé, serveur arrêté) reste dans une file persistante (envoi_attente.json)
et est réessayé toutes les minutes, y compris après un redémarrage du logiciel (voir reprendre()).

Réglages dans config.json : "reglages": {"serveur": {"url": "http://192.168.2.3:8090", "cle": "...", "poste": "banc-1"}}
Sans url et cle, rien n'est envoyé.
"""
import glob
import json
import os
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

import config
import identite
import theme as T
import version

FICHIER_FILE = os.path.join(T.BASE, "envoi_attente.json")
FICHIER_ENVOYES = os.path.join(T.BASE, "envoi_envoyes.json")  # CSV déjà reçus par le serveur : jamais renvoyés au démarrage
DELAI_RETENTE_S = 60
TIMEOUT_S = 15

_verrou = threading.RLock()
_reveil = threading.Event()
_thread = None


def _reglages():
    r = config.charger().get("reglages", {}).get("serveur", {})
    url, cle = str(r.get("url", "")).rstrip("/"), str(r.get("cle", ""))
    poste = str(r.get("poste", "")) or identite.poste() or os.environ.get("COMPUTERNAME") or os.uname().nodename
    return (url, cle, poste) if url and cle else None


def _lire_file():
    try:
        with open(FICHIER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _ecrire_file(file):
    tmp = FICHIER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(file, f, ensure_ascii=False)
    os.replace(tmp, FICHIER_FILE)


def _poster(reglages, element):
    """True si accepté (ou fichier disparu / refus définitif) ; False si le réseau ne répond pas (inutile d'insister) ;
    None si ce fichier précis échoue (erreur serveur) : il reste en file mais les suivants sont tentés."""
    url, cle, poste = reglages
    try:
        with open(element["chemin"], "rb") as f:
            corps = f.read()
    except OSError:
        return True
    req = urllib.request.Request(url + "/api/tests", data=corps, method="POST", headers={
        "Authorization": f"Bearer {cle}", "Content-Type": "text/csv",
        "X-Poste": quote(poste), "X-Module": quote(element["module"]),
        "X-Fichier": quote(os.path.basename(element["chemin"])), "X-Motif": quote(element.get("motif", "")),
        "X-Version": quote(version.__version__)})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S):
            return True
    except urllib.error.HTTPError as e:
        if e.code in (401, 408, 429):
            return False
        return True if e.code < 500 else None  # 4xx : refus définitif, inutile de réessayer
    except (urllib.error.URLError, OSError):
        return False


def _noter_envoyes(elements):
    try:
        with open(FICHIER_ENVOYES, encoding="utf-8") as f:
            deja = json.load(f)
    except (OSError, ValueError):
        deja = []
    tmp = FICHIER_ENVOYES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(set(deja) | {el["chemin"] for el in elements}), f, ensure_ascii=False)
    os.replace(tmp, FICHIER_ENVOYES)


def _boucle():
    while True:
        reglages = _reglages()
        with _verrou:
            file = _lire_file()
        if not file or not reglages:
            return
        envoyes = []
        for el in file:
            ok = _poster(reglages, el)
            if ok is False:
                break  # serveur injoignable : on ne tente pas les suivants (chacun attendrait le délai maximal)
            if ok:
                envoyes.append(el)
        with _verrou:
            _ecrire_file([el for el in _lire_file() if el not in envoyes])  # les ajouts survenus pendant l'envoi restent
            _noter_envoyes(envoyes)
            if len(envoyes) == len(file) and not _lire_file():
                return
        if len(envoyes) < len(file):
            _reveil.wait(DELAI_RETENTE_S)
            _reveil.clear()


def _demarrer():
    global _thread
    with _verrou:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_boucle, daemon=True)
            _thread.start()


def envoyer(module, chemin, motif=""):
    """Met le CSV en file d'envoi (si le serveur est configuré) et lance l'envoi en arrière-plan."""
    if not chemin or not _reglages():
        return
    el = {"module": module, "chemin": os.path.abspath(chemin), "motif": motif}
    with _verrou:
        file = _lire_file()
        if el not in file:
            _ecrire_file(file + [el])
    _demarrer()


def rattraper(dossiers):
    """Met en file les CSV locaux jamais envoyés (tests faits avant la mise en place de l'envoi, ou sans serveur).
    dossiers : {identifiant du module: dossier de ses CSV}. À appeler au démarrage, quand aucun test n'est en cours."""
    if not _reglages():
        return
    try:
        with open(FICHIER_ENVOYES, encoding="utf-8") as f:
            deja = set(json.load(f))
    except (OSError, ValueError):
        deja = set()
    with _verrou:
        file = _lire_file()
        connus = deja | {el["chemin"] for el in file}
        nouveaux = [{"module": m, "chemin": os.path.abspath(p), "motif": "importe"}
                    for m, d in dossiers.items() for p in sorted(glob.glob(os.path.join(d, "*.csv")))
                    if os.path.abspath(p) not in connus]
        if nouveaux:
            _ecrire_file(file + nouveaux)
    if file or nouveaux:
        _demarrer()


def reprendre():
    """À appeler au démarrage du logiciel : renvoie ce qui était resté en attente."""
    if _reglages() and _lire_file():
        _demarrer()
