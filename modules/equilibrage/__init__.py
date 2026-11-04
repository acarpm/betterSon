"""Module « Équilibrage » : lecture des tensions de chaque cellule via l'équilibreur actif Daly (UART)
et sessions d'équilibrage supervisées (suivi de l'écart, enregistrement CSV, arrêt automatique).

Le logiciel ne commande pas l'équilibreur : il lit l'état de l'appareil (commandes Daly en lecture seule).
La détection du port et la connexion sont gérées par l'application (app.instruments, page « Instruments »).
"""
import glob
import os

from theme import ANTHRACITE, LIME, TEAL

from ..base import Action, Module


class Equilibrage(Module):
    id = "equilibrage"
    nom = "Équilibrage de batteries"
    description = "Lit la tension de chaque cellule avec l'équilibreur actif Daly et suit une session d'équilibrage."
    icone = "equilibrage"
    couleur = TEAL
    teinte = "#dcebf1"
    instruments = ("equilibreur_daly",)   # détection, port et statut : gérés par l'application

    def dossier_sessions(self):
        chemin = os.path.join(self.dossier(), "sessions")
        os.makedirs(chemin, exist_ok=True)
        return chemin

    def _nb_sessions(self):
        return len(glob.glob(os.path.join(self.dossier(), "sessions", "*.csv")))

    def actions(self):
        def info_session(app):
            k = self._nb_sessions()
            return f"{k} session{'s' if k > 1 else ''} enregistrée{'s' if k > 1 else ''}"

        return [
            Action("cellules", "Lire les tensions", "Tension de chaque cellule en direct, écart entre la plus haute et la plus basse.",
                   "cellules", TEAL, "#dcebf1"),
            Action("session", "Session d'équilibrage", "Suivre l'écart jusqu'à la cible, avec enregistrement CSV.",
                   "equilibrage", LIME, "#eef3c0", info_session),
        ]

    def info(self, app):
        k = self._nb_sessions()
        return f"{k} session{'s' if k > 1 else ''}"

    def creer_page(self, nom, parent, app):
        from .page_cellules import PageCellules
        from .page_session import PageSession
        pages = {"cellules": PageCellules, "session": PageSession}
        if nom not in pages:
            return super().creer_page(nom, parent, app)
        return pages[nom](parent, app, self)
