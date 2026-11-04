"""Envoi des CSV de mesures vers le serveur BatConnect, en plus de la sauvegarde locale.

Le CSV local reste la référence : l'envoi est en tâche de fond, ne bloque jamais l'interface et n'échoue jamais
bruyamment. Un envoi raté (réseau coupé, serveur arrêté) reste dans une file persistante (envoi_attente.json)
et est réessayé toutes les minutes, y compris après un redémarrage du logiciel (voir reprendre()).

Réglages dans config.json : "reglages": {"serveur": {"url": "http://192.168.2.3:8090", "cle": "...", "poste": "banc-1"}}
Sans url et cle, rien n'est envoyé.
"""
import json
import os
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

import config
import identite
import theme as T

FICHIER_FILE = os.path.join(T.BASE, "envoi_attente.json")
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
    """True si le serveur a accepté (ou si le fichier n'existe plus : rien à renvoyer)."""
    url, cle, poste = reglages
    try:
        with open(element["chemin"], "rb") as f:
            corps = f.read()
    except OSError:
        return True
    req = urllib.request.Request(url + "/api/tests", data=corps, method="POST", headers={
        "Authorization": f"Bearer {cle}", "Content-Type": "text/csv",
        "X-Poste": quote(poste), "X-Module": quote(element["module"]),
        "X-Fichier": quote(os.path.basename(element["chemin"])), "X-Motif": quote(element.get("motif", ""))})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S):
            return True
    except urllib.error.HTTPError as e:
        return 400 <= e.code < 500 and e.code not in (401, 408, 429)  # refus définitif : inutile de réessayer
    except (urllib.error.URLError, OSError):
        return False


def _boucle():
    while True:
        reglages = _reglages()
        with _verrou:
            file = _lire_file()
        if not file or not reglages:
            return
        restants = []
        for el in file:
            if not _poster(reglages, el):
                restants.append(el)
        with _verrou:
            # des éléments ont pu être ajoutés pendant l'envoi : on ne retire que ceux envoyés
            envoyes = [el for el in file if el not in restants]
            _ecrire_file([el for el in _lire_file() if el not in envoyes])
            if not restants and not _lire_file():
                return
        if restants:
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


def reprendre():
    """À appeler au démarrage du logiciel : renvoie ce qui était resté en attente."""
    if _reglages() and _lire_file():
        _demarrer()
