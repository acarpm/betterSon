"""Instruments (appareils reliés par port série) connus de l'application.

Pour en ajouter un : créer sa classe (sous-classe de base.Instrument) dans ce paquet, puis l'ajouter à TOUS.
Un module déclare ceux dont il a besoin (`instruments = ("charge_ea",)`) et obtient leur port via `app.instruments`.
"""
from .daly import EquilibreurDaly
from .ea import ChargeEA
from .gestionnaire import Gestionnaire

TOUS = [ChargeEA(), EquilibreurDaly()]
