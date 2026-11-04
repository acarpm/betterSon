"""Réglages de l'application (modules activés), dans config.json du dossier de données."""
import json
import os
import threading

import theme as T

_VERROU = threading.RLock()  # lecture-modification-écriture : la détection d'instruments écrit en tâche de fond


def charger():
    try:
        with open(T.FICHIER_CONFIG, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def sauver(data):
    os.makedirs(os.path.dirname(T.FICHIER_CONFIG), exist_ok=True)
    tmp = T.FICHIER_CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, T.FICHIER_CONFIG)  # écriture atomique


def module_actif(module_id, defaut=True):
    return bool(charger().get("modules", {}).get(module_id, defaut))


def definir_module(module_id, actif):
    with _VERROU:
        data = charger()
        data.setdefault("modules", {})[module_id] = bool(actif)
        sauver(data)


def reglage(module_id, cle, defaut=None):
    """Réglage propre à un module (ex. le port série de l'équilibreur)."""
    return charger().get("reglages", {}).get(module_id, {}).get(cle, defaut)


def definir_reglage(module_id, cle, valeur):
    with _VERROU:
        data = charger()
        data.setdefault("reglages", {}).setdefault(module_id, {})[cle] = valeur
        sauver(data)
