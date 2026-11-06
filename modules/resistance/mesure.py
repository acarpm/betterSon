"""Séquence de mesure de la résistance interne, dans un thread : pulses de courant sur la charge EA, tensions lues en continu.

Pour chaque pulse : [attente] -> repos (charge coupée) -> pulse (charge active) -> la charge est coupée.
Tout est échantillonné en continu (tension et courant de la charge, tension de chaque cellule par le Daly) et écrit au
fil de l'eau dans un CSV : les résistances sont calculées à partir de ces échantillons (voir calcul.py), donc le fichier
suffit à refaire le calcul plus tard.

Messages poussés dans `sortie` :
    ("phase", essai, nom, fin)            début d'une phase (nom : attente | repos | pulse) ; fin = horloge monotonic prévue
    ("echantillon", t, essai, phase, v, i, cellules)
    ("essai", resultat)                   résultat d'un pulse terminé (calcul.resistance_essai)
    ("fin", motif, resume)                motif : termine | stop | coupure | erreur ; resume : synthèse ou message d'erreur
"""
import csv
import os
import threading
import time

import serial

from instruments import ea as charge
from instruments.daly import BAUD as BAUD_DALY, DELAI_SERIE, Daly

from . import calcul

PAUSE_MIN_S = 0.05    # une boucle qui répondrait instantanément ne doit pas saturer le port


class Mesure:
    def __init__(self, profil, port_charge, port_daly, sortie, chemin_csv, signature=""):
        self.p, self.port_charge, self.port_daly = profil, port_charge, port_daly
        self.sortie, self.chemin_csv, self.signature = sortie, chemin_csv, signature
        self.stop = threading.Event()
        self.thread = None
        self.echantillons = []

    def demarrer(self):
        self.stop.clear()
        self.thread = threading.Thread(target=self._boucle, daemon=True)
        self.thread.start()

    def arreter(self):
        self.stop.set()

    def vivant(self):
        return self.thread is not None and self.thread.is_alive()

    def attendre(self, delai=5.0):
        if self.thread:
            self.thread.join(timeout=delai)

    # ---------- thread ----------
    def _boucle(self):
        q = self.sortie
        try:
            with serial.Serial(self.port_charge, charge.BAUD, timeout=1) as s, \
                    serial.Serial(self.port_daly, BAUD_DALY, timeout=DELAI_SERIE) as ser:
                daly = Daly(ser)
                for _ in range(3):
                    daly.n_cellules = daly.lire_nombre_cellules()
                    if daly.n_cellules:
                        break
                if not daly.n_cellules:
                    q.put(("fin", "erreur", "L'équilibreur Daly ne répond pas (nombre de cellules illisible)."))
                    return
                if not charge.verrou(s, True):
                    q.put(("fin", "erreur", "La charge n'est pas passée en mode distant."))
                    return
                try:
                    charge.regler_charge(s, None, self.p["courant"], None)
                    motif = self._sequence(s, daly)
                finally:
                    charge.entree(s, False)   # toujours couper l'entrée de la charge
                    charge.verrou(s, False)   # rend la main à la face avant
            q.put(("fin", motif, calcul.synthese(calcul.resistances(self.echantillons))))
        except (serial.SerialException, OSError, ValueError) as e:
            q.put(("fin", "erreur", f"Communication perdue : {e}"))

    def _sequence(self, s, daly):
        p, q = self.p, self.sortie
        with open(self.chemin_csv, "w", newline="", encoding="utf-8") as fichier:
            fichier.write(self.signature)
            ecr = csv.writer(fichier)
            ecr.writerow(["temps_s", "essai", "phase", "v_pack", "courant"] + [f"c{k + 1}" for k in range(daly.n_cellules)])
            t0 = time.monotonic()

            def phase(nom, duree, essai):
                """Échantillonne pendant `duree` secondes. None si la phase va à son terme, sinon 'stop' ou 'coupure'."""
                debut = time.monotonic()
                q.put(("phase", essai, nom, debut + duree))
                while not self.stop.is_set():
                    t = time.monotonic()
                    ecoule = t - debut
                    if ecoule >= duree:
                        return None
                    etiquette = "mesure" if nom == "pulse" and ecoule >= p["mesure_apres_s"] else nom
                    v, i, _ = charge.lire_valeurs(s, 1, 1, None)
                    cellules = daly.lire_cellules(tenir=False) or []
                    cellules = (cellules + [None] * daly.n_cellules)[:daly.n_cellules]
                    self.echantillons.append({"essai": essai, "phase": etiquette, "v": v, "i": i, "cellules": cellules})
                    ecr.writerow([f"{t - t0:.2f}", essai, etiquette, v, i] + ["" if c is None else c for c in cellules])
                    fichier.flush()   # rien n'est perdu si le programme est coupé
                    q.put(("echantillon", t - t0, essai, etiquette, v, i, cellules))
                    mini = p["tension_min_cellule"]
                    if nom == "pulse" and mini and any(c is not None and c < mini for c in cellules):
                        return "coupure"
                    self.stop.wait(PAUSE_MIN_S)
                return "stop"

            for essai in range(1, p["repetitions"] + 1):
                if essai > 1:
                    fin = phase("attente", p["attente_s"], essai)
                    if fin:
                        return fin
                fin = phase("repos", p["repos_s"], essai)
                if fin:
                    return fin
                if not charge.entree(s, True):
                    raise ValueError("La charge n'a pas activé son entrée.")
                try:
                    fin = phase("pulse", p["pulse_s"], essai)
                finally:
                    charge.entree(s, False)
                if fin:
                    return fin
                resultat = calcul.resistance_essai(self.echantillons, essai)
                if resultat:
                    q.put(("essai", resultat))
        return "termine"
