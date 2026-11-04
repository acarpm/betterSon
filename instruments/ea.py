"""Charge électronique EA (USB, commandes SCPI) : détection du port et commandes.

Partagé par toute l'application (module Décharge, console main.py, page Instruments).
"""
import time

import serial.tools.list_ports as lp

from .base import Instrument

VID_EA = 0x232E          # identifiant USB du fabricant
SN_PREFERE = "2289160002"  # charge de l'atelier : choisie en premier si plusieurs charges EA sont branchées
BAUD = 115200
INTERVALLE_S = 1         # pause entre deux mesures (en secondes)


def trouver_ports(sn=None):
    """Ports des charges EA branchées (la charge préférée en premier). sn : ne garder que ce numéro de série."""
    ports = [p for p in lp.comports() if p.vid == VID_EA and (sn is None or p.serial_number == sn)]
    ports.sort(key=lambda p: p.serial_number != SN_PREFERE)
    return [p.device for p in ports]


def identifier(s):
    s.write(b"*IDN?\n")
    return s.readline().decode(errors="ignore").strip()


def mesurer(s, commande):
    s.write(commande)
    reponse = s.readline().decode(errors="ignore").strip()  # ex : "0.00 V"
    return float(reponse.split()[0])  # garde le nombre, enlève l'unité


def lire_valeurs(s, v, i, p):
    if (v != None):
        v = mesurer(s, b"MEAS:VOLT?\n")
    if (i != None):
        i = mesurer(s, b"MEAS:CURR?\n")
    if (p != None):
        p = mesurer(s, b"MEAS:POW?\n")
    return v, i, p


def regler_charge(s, v, i, p):
    if (v != None):
        s.write(f"VOLT {v}\n".encode())
    if (i != None):
        s.write(f"CURR {i}\n".encode())
    if (p != None):
        s.write(f"POW {p}\n".encode())


def verrou(s, actif):
    s.write(b"SYST:LOCK ON\n" if actif else b"SYST:LOCK OFF\n")
    time.sleep(0.5)  # la charge ignore les requêtes pendant qu'elle change de mode
    s.reset_input_buffer()
    s.write(b"SYST:LOCK:OWN?\n")
    return (s.readline().decode(errors="ignore").strip() == "REMOTE") == actif  # vérifie l'état réel


def entree(s, actif):
    s.write(b"INP ON\n" if actif else b"INP OFF\n")
    s.write(b"INP?\n")
    return (s.readline().decode(errors="ignore").strip() == "ON") == actif  # vérifie l'état réel


class ChargeEA(Instrument):
    id = "charge_ea"
    nom = "Charge électronique EA"
    libelle = "Charge EA"
    description = "Charge électronique EA reliée en USB (commandes SCPI, 115200 bauds). Reconnue automatiquement."
    aide = "Branchez le câble USB de la charge et allumez-la."
    baud = BAUD
    identification_directe = True

    def reconnu_par_vid(self, port):
        return port.vid == VID_EA

    def candidats(self, ports):
        c = [p for p in ports if self.reconnu_par_vid(p)]
        return sorted(c, key=lambda p: p.serial_number != SN_PREFERE)

    def sonde(self, ser):
        identite = identifier(ser)
        return {"identite": identite} if identite else None
