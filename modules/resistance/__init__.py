"""Module « Résistance interne » : pulse de courant sur la charge EA et mesure de la chute de tension.

Pour chaque pulse, R = (V repos - V pulse) / I, pour le pack entier (tension lue par la charge) et pour chaque cellule
(tensions lues par l'équilibreur Daly). Tous les réglages (courant, durées, nombre de pulses, attente) sont dans un
profil choisi par l'opérateur ; les mesures brutes sont enregistrées en CSV et les résistances en sont déduites (calcul.py).
"""
import glob
import os

from theme import ANTHRACITE, LIME, TEAL

from ..base import Action, Module
from . import chemins, profils


class Resistance(Module):
    id = "resistance"
    nom = "Résistance interne"
    description = "Mesure la résistance interne du pack et de chaque cellule avec un pulse de courant de la charge EA."
    icone = "resistance"
    couleur = TEAL
    teinte = "#dcebf1"
    instruments = ("charge_ea", "equilibreur_daly")   # détection, port et statut : gérés par l'application

    def __init__(self):
        self._profils = None
        self._dernier = None

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

    @staticmethod
    def _nb_tests():
        return len(glob.glob(os.path.join(chemins.dossier_csv(), "*.csv")))

    @staticmethod
    def _pluriel(n, mot):
        return f"{n} {mot}{'s' if n > 1 else ''}"

    def actions(self):
        return [
            Action("lancer", "Lancer un test", "Choisir un profil et mesurer la résistance interne du pack et des cellules.",
                   "test", LIME, "#eef3c0",
                   lambda app: f"Profil : {self.dernier}" if self.dernier else ("Choisissez un profil" if self.profils else "Créez d'abord un profil")),
            Action("profils", "Créer / modifier un profil", "Courant du pulse, durées, nombre de pulses, attente entre pulses.",
                   "profils", TEAL, "#dcebf1", lambda app: self._pluriel(len(self.profils), "profil") + " enregistré" + ("s" if len(self.profils) > 1 else "")),
            Action("resultats", "Analyser les résultats", "Résistance du pack et de chaque cellule, tests passés.",
                   "resultats", ANTHRACITE, "#e8e8e5", lambda app: self._pluriel(self._nb_tests(), "test") + " enregistré" + ("s" if self._nb_tests() > 1 else "")),
        ]

    def info(self, app):
        return f"{self._pluriel(len(self.profils), 'profil')}  ·  {self._pluriel(self._nb_tests(), 'test')}"

    def creer_page(self, nom, parent, app):
        from .page_encours import PageEnCours
        from .page_lancer import PageLancer
        from .page_profils import PageProfils
        from .page_resultats import PageResultats
        pages = {"lancer": PageLancer, "encours": PageEnCours, "profils": PageProfils, "resultats": PageResultats}
        if nom not in pages:
            return super().creer_page(nom, parent, app)
        return pages[nom](parent, app, self)
