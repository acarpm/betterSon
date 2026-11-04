"""Module « Décharge » : décharge d'une batterie sur la charge électronique EA, avec profils de test et analyse."""
from tkinter import messagebox

import main as charge  # communication avec la charge EA
from theme import ANTHRACITE, LIME, ROUGE, TEAL, VERT

from ..base import Action, Module
from . import chemins, profils, resultats


class Decharge(Module):
    id = "decharge"
    nom = "Décharge de batteries"
    description = "Décharge une batterie sur la charge EA avec un profil de test, enregistre et analyse les résultats."
    icone = "test"
    couleur = LIME
    teinte = "#eef3c0"

    def __init__(self):
        self._profils = None   # chargés à la première utilisation (et non à l'import)
        self._dernier = None
        self.port = None

    # ---------- état partagé par les pages du module ----------
    def _charger(self):
        if self._profils is None:
            self._profils, self._dernier = profils.charger(chemins.fichier_profils())

    @property
    def profils(self):
        self._charger()
        return self._profils

    @property
    def dernier(self):
        self._charger()
        return self._dernier

    @dernier.setter
    def dernier(self, nom):
        self._charger()
        self._dernier = nom

    # ---------- matériel ----------
    def port_ou_erreur(self):
        """Port série de la charge EA, ou message d'erreur pour l'opérateur."""
        self.port = (charge.trouver_ports() or [None])[0]
        if not self.port:
            messagebox.showerror("Charge introuvable",
                                 "Aucune charge EA détectée.\nBranchez le câble USB et allumez la charge.")
        return self.port

    def statut(self, app):
        if charge.trouver_ports():
            return "● Charge connectée", VERT
        return "● Charge non détectée - vérifiez le câble USB", ROUGE

    # ---------- interface ----------
    def actions(self):
        def info_lancer(app):
            n = len(self.profils)
            return f"Profil : {self.dernier}" if self.dernier else ("Choisissez un profil" if n else "Créez d'abord un profil")

        def info_profils(app):
            n = len(self.profils)
            return f"{n} profil{'s' if n > 1 else ''} enregistré{'s' if n > 1 else ''}"

        def info_resultats(app):
            k = len(resultats.lister(chemins.dossier_csv()))
            return f"{k} test{'s' if k > 1 else ''} enregistré{'s' if k > 1 else ''}"

        return [
            Action("lancer", "Lancer un test", "Choisir un profil et démarrer la décharge de la batterie.",
                   "test", LIME, "#eef3c0", info_lancer),
            Action("profils", "Créer / modifier un test", "Définir les paramètres d'un type de batterie.",
                   "profils", TEAL, "#dcebf1", info_profils),
            Action("resultats", "Analyser les résultats", "Consulter les tests passés : capacité, énergie, courbes.",
                   "resultats", ANTHRACITE, "#e8e8e5", info_resultats),
        ]

    def info(self, app):
        n, k = len(self.profils), len(resultats.lister(chemins.dossier_csv()))
        return f"{n} profil{'s' if n > 1 else ''}  ·  {k} test{'s' if k > 1 else ''}"

    def creer_page(self, nom, parent, app):
        # imports tardifs : un module désactivé ne coûte rien au démarrage
        from .page_encours import PageEnCours
        from .page_lancer import PageLancer
        from .page_profils import PageProfils
        from .page_resultats import PageResultats
        pages = {"lancer": PageLancer, "encours": PageEnCours, "profils": PageProfils, "resultats": PageResultats}
        if nom not in pages:
            return super().creer_page(nom, parent, app)
        return pages[nom](parent, app, self)
