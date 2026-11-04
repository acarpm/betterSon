"""Lecture périodique de l'équilibreur dans un thread, avec enregistrement CSV et critère d'arrêt facultatifs."""
import csv
import os
import threading
import time

import serial

from instruments.daly import BAUD, DELAI_SERIE, Daly


class CritereFin:
    """Fin de session : écart max-min sous la cible pendant `stable_s` secondes, ou durée maximale atteinte."""

    def __init__(self, cible_mv, stable_s=60, duree_max_s=3 * 3600):
        self.cible_mv, self.stable_s, self.duree_max_s = cible_mv, stable_s, duree_max_s
        self._depuis = None

    def verifier(self, t, ecart_mv):
        """Motif d'arrêt ('cible' ou 'duree'), sinon None. ecart_mv vaut None quand la lecture a échoué."""
        if ecart_mv is not None:
            if ecart_mv <= self.cible_mv:
                self._depuis = t if self._depuis is None else self._depuis
            else:
                self._depuis = None
            if self._depuis is not None and t - self._depuis >= self.stable_s:
                return "cible"
        if t >= self.duree_max_s:
            return "duree"
        return None


class Acquisition:
    """Messages poussés dans `sortie` :
        ("donnees", t, d)   une lecture (d : dict de Daly.lire_tout() + ecart_mv...)
        ("silence", n)      n lectures de suite sans réponse
        ("fin", motif, resume)   motif : stop | cible | duree | silence | erreur ; resume : dict ou message d'erreur
    """

    def __init__(self, port, sortie, intervalle=1.0, chemin_csv=None, critere=None, silence_max_s=None, baud=BAUD):
        self.port, self.sortie, self.intervalle = port, sortie, intervalle
        self.chemin_csv, self.critere, self.silence_max_s, self.baud = chemin_csv, critere, silence_max_s, baud
        self.stop = threading.Event()
        self.thread = None

    def demarrer(self):
        self.stop.clear()
        self.thread = threading.Thread(target=self._boucle, daemon=True)
        self.thread.start()

    def arreter(self):
        self.stop.set()

    def vivant(self):
        return self.thread is not None and self.thread.is_alive()

    def attendre(self, delai=3.0):
        if self.thread:
            self.thread.join(timeout=delai)

    def _boucle(self):
        q = self.sortie
        fichier = ecrivain = None
        premier = dernier = None
        n_lectures = silence = 0
        entete_ecrit = False
        motif = "stop"
        silence_depuis = None
        try:
            with serial.Serial(self.port, self.baud, timeout=DELAI_SERIE) as ser:
                daly = Daly(ser)
                t0 = time.monotonic()
                if self.chemin_csv:
                    os.makedirs(os.path.dirname(self.chemin_csv), exist_ok=True)
                    fichier = open(self.chemin_csv, "w", newline="", encoding="utf-8")
                    ecrivain = csv.writer(fichier)
                try:
                    while not self.stop.is_set():
                        debut = time.monotonic()
                        d = daly.lire_tout()
                        t = debut - t0
                        ecart = None
                        if d is None:
                            silence += 1
                            silence_depuis = debut if silence_depuis is None else silence_depuis
                            q.put(("silence", silence))
                            if self.silence_max_s and debut - silence_depuis >= self.silence_max_s:
                                motif = "silence"
                                break
                        else:
                            silence, silence_depuis = 0, None
                            ecart = d.get("ecart_mv")
                            n_lectures += 1
                            if ecart is not None:
                                premier = premier or d
                                dernier = d
                            if ecrivain and d["cellules"]:  # pas de ligne (ni d'en-tête) tant qu'on n'a pas les cellules
                                if not entete_ecrit:
                                    ecrivain.writerow(["temps_s", "v_pack", "courant", "soc", "ecart_mv"]
                                                      + [f"c{i + 1}" for i in range(len(d["cellules"]))])
                                    entete_ecrit = True
                                ecrivain.writerow([f"{t:.1f}", d["v_pack"], d["courant"], d["soc"],
                                                   "" if ecart is None else f"{ecart:.1f}"]
                                                  + ["" if v is None else v for v in d["cellules"]])
                                fichier.flush()  # rien n'est perdu si le programme est coupé
                            q.put(("donnees", t, d))
                        if self.critere:
                            fin = self.critere.verifier(t, ecart)
                            if fin:
                                motif = fin
                                break
                        self.stop.wait(max(0.05, self.intervalle - (time.monotonic() - debut)))
                finally:
                    if fichier:
                        fichier.close()
            q.put(("fin", motif, {
                "duree_s": time.monotonic() - t0, "lectures": n_lectures, "chemin": self.chemin_csv,
                "ecart_initial": premier.get("ecart_mv") if premier else None,
                "ecart_final": dernier.get("ecart_mv") if dernier else None}))
        except (serial.SerialException, OSError) as e:
            q.put(("fin", "erreur", f"Port série inaccessible ou perdu : {e}"))
