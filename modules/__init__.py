"""Registre des modules du logiciel.

Pour ajouter un module :
  1. créer le paquet modules/<id>/ avec une sous-classe de modules.base.Module (voir modules/decharge/) ;
  2. l'importer ici et l'ajouter à TOUS.
Chaque module peut ensuite être activé / désactivé depuis l'écran « Gérer les modules ».
"""
from .decharge import Decharge
from .equilibrage import Equilibrage
from .resistance import Resistance

TOUS = [Decharge(), Equilibrage(), Resistance()]
