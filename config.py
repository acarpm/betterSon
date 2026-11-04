"""Réglages de l'application (modules activés), dans config.json du dossier de données."""
import json
import os

import theme as T


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
    data = charger()
    data.setdefault("modules", {})[module_id] = bool(actif)
    sauver(data)
