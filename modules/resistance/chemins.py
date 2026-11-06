"""Emplacements des données du module Résistance interne (profils et mesures), sous le dossier de données de l'application."""
import os

import theme as T

ID = "resistance"


def dossier():
    chemin = os.path.join(T.BASE, ID)
    os.makedirs(chemin, exist_ok=True)
    return chemin


def dossier_csv():
    chemin = os.path.join(dossier(), "mesures")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def fichier_profils():
    return os.path.join(dossier(), "profils.json")
