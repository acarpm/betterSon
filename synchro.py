"""Synchronisation des identités avec le serveur BatConnect (annuaire des techniciens, déclaration du poste).

Le serveur est la référence ; config.json en garde une copie. Hors-ligne (ou serveur non configuré), tout continue à
fonctionner en local et les modifications attendent d'être transmises. Jamais bloquant : tout se passe en tâche de fond.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote

import envoi
import identite

TIMEOUT_S = 5
INTERVALLE_MIN_S = 30   # pas de nouvelle synchronisation avant ce délai (sauf force=True)

_verrou = threading.Lock()
_etat = "inconnu"       # "serveur" : copie à jour avec le serveur · "local" : serveur injoignable · "non_configure" · "inconnu"
_dernier = None


def etat():
    return _etat


def _appeler(reglages, methode, chemin, corps=None):
    url, cle, _ = reglages
    donnees = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(url + chemin, data=donnees, method=methode,
                                 headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read() or b"null")


def synchroniser():
    """Un passage complet (bloquant : à lancer via lancer()). Renvoie l'état : 'serveur', 'local' ou 'non_configure'."""
    global _etat, _dernier
    with _verrou:
        reglages = envoi._reglages()
        if not reglages:
            _etat = "non_configure"
            return _etat
        try:
            ajouts, suppressions = identite.operations_en_attente()
            for nom in suppressions:
                _appeler(reglages, "DELETE", "/api/techniciens/" + quote(nom, safe=""))
                identite.operation_transmise("techniciens_a_supprimer", nom)
            for nom in ajouts:
                _appeler(reglages, "POST", "/api/techniciens", {"nom": nom})
                identite.operation_transmise("techniciens_a_ajouter", nom)
            liste = _appeler(reglages, "GET", "/api/techniciens")
            if isinstance(liste, list):
                identite.remplacer_techniciens([str(t) for t in liste])
            poste = identite.poste()
            if poste:
                _appeler(reglages, "PUT", "/api/postes/" + quote(poste, safe=""))
            _etat = "serveur"
        except (urllib.error.URLError, OSError, ValueError):
            _etat = "local"  # serveur injoignable, clé refusée ou réponse invalide : on garde la copie locale
        _dernier = time.monotonic()
        return _etat


def lancer(force=False):
    """Synchronise en arrière-plan ; renvoie le thread, ou None si une synchronisation récente suffit."""
    if not force and _dernier is not None and time.monotonic() - _dernier < INTERVALLE_MIN_S:
        return None
    t = threading.Thread(target=synchroniser, daemon=True)
    t.start()
    return t
