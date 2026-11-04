"""Module « Équilibrage » : lecture des tensions de chaque cellule via l'équilibreur actif Daly (UART)
et sessions d'équilibrage supervisées (suivi de l'écart, enregistrement CSV, arrêt automatique).

Le logiciel ne commande pas l'équilibreur : il lit l'état de l'appareil (commandes Daly en lecture seule).
"""
import glob
import os

import serial.tools.list_ports as lp

import config
from theme import ANTHRACITE, LIME, ORANGE, ROUGE, TEAL, VERT

from ..base import Action, Module

VID_EA = 0x232E  # la charge EA du module Décharge : jamais proposée comme port d'équilibreur


class Equilibrage(Module):
    id = "equilibrage"
    nom = "Équilibrage de batteries"
    description = "Lit la tension de chaque cellule avec l'équilibreur actif Daly et suit une session d'équilibrage."
    icone = "equilibrage"
    couleur = TEAL
    teinte = "#dcebf1"

    # ---------- réglages ----------
    def port(self):
        return config.reglage(self.id, "port")

    def definir_port(self, port):
        config.definir_reglage(self.id, "port", port)

    @staticmethod
    def ports_candidats():
        """[(périphérique, description)] des ports série disponibles, hors charge EA."""
        return [(p.device, p.description or p.hwid or "") for p in sorted(lp.comports(), key=lambda p: p.device)
                if p.vid != VID_EA]

    def dossier_sessions(self):
        chemin = os.path.join(self.dossier(), "sessions")
        os.makedirs(chemin, exist_ok=True)
        return chemin

    # ---------- interface ----------
    def statut(self, app):
        p = self.port()
        if not p:
            return "● Port de l'équilibreur non choisi", ORANGE
        if p in [c[0] for c in self.ports_candidats()]:
            return f"● {p} disponible", VERT
        return f"● {p} introuvable - vérifiez le câble USB", ROUGE

    def actions(self):
        def info_lire(app):
            return f"Port : {self.port()}" if self.port() else "Choisissez d'abord le port"

        def info_session(app):
            k = len(glob.glob(os.path.join(self.dossier(), "sessions", "*.csv")))
            return f"{k} session{'s' if k > 1 else ''} enregistrée{'s' if k > 1 else ''}"

        return [
            Action("cellules", "Lire les tensions", "Tension de chaque cellule en direct, écart entre la plus haute et la plus basse.",
                   "cellules", TEAL, "#dcebf1", info_lire),
            Action("session", "Session d'équilibrage", "Suivre l'écart jusqu'à la cible, avec enregistrement CSV.",
                   "equilibrage", LIME, "#eef3c0", info_session),
            Action("connexion", "Connexion", "Choisir le port série de l'équilibreur et tester la liaison.",
                   "connexion", ANTHRACITE, "#e8e8e5", lambda app: f"Port : {self.port() or 'non choisi'}"),
        ]

    def info(self, app):
        return f"Port : {self.port()}" if self.port() else "Port à choisir"

    def creer_page(self, nom, parent, app):
        from .page_cellules import PageCellules
        from .page_connexion import PageConnexion
        from .page_session import PageSession
        pages = {"cellules": PageCellules, "session": PageSession, "connexion": PageConnexion}
        if nom not in pages:
            return super().creer_page(nom, parent, app)
        return pages[nom](parent, app, self)
