"""MODÈLE de module : à copier pour créer un nouveau module (résistance interne…).

Ce paquet n'est PAS enregistré dans modules.TOUS : il n'apparaît pas dans le logiciel.

Pour créer le module « resistance » :
  1. copier ce dossier en modules/resistance/ et renommer la classe, `id`, `nom`, `description` ;
  2. remplacer la page d'exemple par les vraies pages (une classe tk.Frame par page, voir modules/decharge/) ;
  3. dans modules/__init__.py :  from .resistance import Resistance   puis   TOUS = [Decharge(), Equilibrage(), Resistance()]

Ce que le logiciel fournit déjà à un module :
  - activation / désactivation par l'opérateur (« Gérer les modules »), tuile sur l'accueil, menu du module ;
  - navigation (bouton Retour), verrouillage automatique pendant une opération (méthode occupe() d'une page) ;
  - thème et composants (theme.py : ListeLignes, GraphesTemps, Interrupteur, couleurs, polices app.f) ;
  - dossier de données propre : self.dossier() (créé à la demande, sous le dossier de données de l'application) ;
  - mises à jour automatiques (le module fait partie de l'application, rien à faire).
"""
import tkinter as tk

from theme import BG, GRIS, TEXTE

from ..base import Action, Module


class PageExemple(tk.Frame):
    """Une page = un tk.Frame avec on_show() (appelée à chaque affichage). Ajouter occupe() pour verrouiller la navigation."""

    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        self.titre = tk.Label(self, text="", bg=BG, fg=TEXTE, font=app.f(22, True))
        self.titre.pack(pady=(60, 8))
        tk.Label(self, text="Page d'exemple : remplacez-la par la vôtre.", bg=BG, fg=GRIS, font=app.f(13)).pack()

    def on_show(self):
        self.titre.config(text=self.mod.nom)

    # def occupe(self):  # décommenter si la page peut lancer une opération longue (test, mesure…)
    #     return self.opération_en_cours


class Modele(Module):
    id = "modele"                      # stable : sert aux réglages (config.json) et aux noms de pages
    nom = "Module modèle"
    description = "Squelette à copier pour créer un nouveau module."
    icone = "module"                   # "test", "profils", "resultats" ou générique ; en ajouter dans theme.icone()
    actif_par_defaut = True

    def actions(self):
        return [Action("accueil", "Page d'exemple", "Ouvre la page d'exemple du modèle.", info=lambda app: "prêt")]

    def creer_page(self, nom, parent, app):
        if nom == "accueil":
            return PageExemple(parent, app, self)
        return super().creer_page(nom, parent, app)

    def statut(self, app):
        return None                    # ex. ("● Équilibreur connecté", theme.VERT) pour afficher le matériel du module
