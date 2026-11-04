"""Emplacements des données du module Décharge (profils et mesures), sous le dossier de données de l'application."""
import os

import theme as T


def dossier_csv():
    return os.path.join(T.BASE, "mesures")


def fichier_profils():
    return os.path.join(T.BASE, "profils.json")
