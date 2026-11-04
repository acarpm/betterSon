"""Contrat d'un module : ce qu'il faut fournir pour qu'il apparaisse dans le logiciel."""
import os
from dataclasses import dataclass
from typing import Callable, Optional

import theme as T
from theme import LIME


@dataclass
class Action:
    """Une entrée du menu d'un module (une grande tuile) qui ouvre une de ses pages."""
    page: str                      # nom court de la page, passé à Module.creer_page()
    titre: str
    description: str
    icone: str = "module"          # pictogramme de theme.icone() ("test", "profils", "resultats", sinon générique)
    couleur: str = LIME
    teinte: str = "#eef3c0"
    info: Optional[Callable] = None  # info(app) -> texte court affiché sur la tuile


class Module:
    """Classe de base. Pour créer un module : sous-classer, renseigner les champs, puis l'ajouter à modules.TOUS."""

    id = ""                        # identifiant stable (minuscules, sans espace) : sert aux réglages et aux pages
    nom = ""                       # nom affiché
    description = ""               # une phrase, affichée sur l'accueil et dans la gestion des modules
    icone = "module"
    couleur = LIME
    teinte = "#eef3c0"
    actif_par_defaut = True
    instruments = ()               # identifiants des instruments utilisés (ex. ("charge_ea",)) : statut en en-tête, port via app.instruments

    def actions(self):
        """Liste d'Action : le menu du module."""
        return []

    def creer_page(self, nom, parent, app):
        """Construit la page `nom` (un tk.Frame avec on_show(), et occupe() s'il peut verrouiller la navigation)."""
        raise NotImplementedError(f"{self.id}: page inconnue {nom!r}")

    def info(self, app):
        """Texte court affiché sous la description sur l'accueil."""
        return ""

    def dossier(self):
        """Dossier de données propre au module (sous le dossier de données de l'application), créé à la demande."""
        chemin = os.path.join(T.BASE, self.id)
        os.makedirs(chemin, exist_ok=True)
        return chemin

