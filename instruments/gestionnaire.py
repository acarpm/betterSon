"""Détection et attribution des ports série aux instruments, pour toute l'application.

Ordre de résolution du port d'un instrument (aucune communication, instantané) :
  1. choix manuel de l'opérateur (page « Instruments »), jamais remplacé en silence ;
  2. port mémorisé après une détection réussie, tant qu'il est présent ;
  3. identification directe par l'USB (ex. la charge EA).
Sinon, `detecter()` interroge les ports candidats (en tâche de fond avec `lancer_detection()`) et mémorise celui qui répond.
"""
import threading
import time

import serial
import serial.tools.list_ports as lp

import config

ESPACE = "instruments"          # espace de noms dans config.json
IGNORES = ("bluetooth", "debug-console", "wlan-debug")   # pseudo-ports macOS / Windows : inutile de les sonder


class Gestionnaire:
    def __init__(self, registre, lister=None):
        self.registre = {i.id: i for i in registre}
        self._lister = lister or lp.comports
        self._cache = (0.0, [])
        self._recherches = {}
        self._verrou_ports = threading.Lock()   # un seul dialogue série à la fois (jamais deux ouvertures du même port)

    def instrument(self, id_):
        return self.registre[id_]

    # ---------- ports ----------
    @staticmethod
    def _utilisable(p):
        texte = f"{p.device} {p.description}".lower()
        return not any(m in texte for m in IGNORES) and p.hwid != "n/a"

    def ports(self, age_max=1.5):
        """Ports série présents (rafraîchis au plus toutes les `age_max` secondes)."""
        if time.monotonic() - self._cache[0] > age_max:
            self._cache = (time.monotonic(), [p for p in self._lister() if self._utilisable(p)])
        return list(self._cache[1])

    def _reclames(self):
        """Périphériques que l'USB identifie déjà comme appartenant à un instrument : à ne pas sonder pour un autre."""
        return {p.device for p in self.ports() for i in self.registre.values() if i.reconnu_par_vid(p)}

    def candidats(self, id_):
        inst = self.registre[id_]
        c = inst.candidats(self.ports())
        if not inst.identification_directe:
            reclames = self._reclames()
            c = [p for p in c if p.device not in reclames]
        return c

    # ---------- réglages ----------
    def _cle(self, id_, nom):
        return f"{id_}.{nom}"

    def manuel(self, id_):
        return config.reglage(ESPACE, self._cle(id_, "manuel")) or None

    def memorise(self, id_):
        return config.reglage(ESPACE, self._cle(id_, "memorise")) or None

    def choisir(self, id_, port):
        """Choix manuel d'un port ; None revient à la détection automatique."""
        config.definir_reglage(ESPACE, self._cle(id_, "manuel"), port or "")

    # ---------- résolution ----------
    def port(self, id_):
        """Port actuellement attribué à l'instrument, ou None. Instantané (aucune communication)."""
        presents = {p.device for p in self.ports()}
        manuel = self.manuel(id_)
        if manuel:
            return manuel if manuel in presents else None
        memo = self.memorise(id_)
        if memo and memo in presents and memo in {p.device for p in self.candidats(id_)}:
            return memo
        inst = self.registre[id_]
        if inst.identification_directe:
            c = self.candidats(id_)
            return c[0].device if c else None
        return None

    def origine(self, id_):
        """'manuel', 'memorise', 'auto' (identification directe) ou None."""
        if not self.port(id_):
            return None
        if self.manuel(id_):
            return "manuel"
        return "auto" if self.registre[id_].identification_directe and self.memorise(id_) != self.port(id_) else "memorise"

    def statut(self, id_):
        """(état, texte) pour la barre d'état. état : ok | info | attention | erreur."""
        inst = self.registre[id_]
        if self.en_recherche(id_):
            return "info", f"{inst.libelle} : recherche…"
        p = self.port(id_)
        if p:
            return "ok", f"{inst.libelle} : {p}"
        manuel = self.manuel(id_)
        if manuel:
            return "erreur", f"{inst.libelle} : port {manuel} introuvable"
        if inst.identification_directe:
            return "erreur", f"{inst.libelle} : aucun appareil détecté - vérifiez le câble USB"
        return "attention", f"{inst.libelle} : aucun appareil détecté"

    # ---------- dialogue ----------
    def tester(self, id_, port=None):
        """Interroge l'instrument. (True, infos) s'il répond, sinon (False, message lisible)."""
        inst = self.registre[id_]
        port = port or self.port(id_)
        if not port:
            return False, f"Aucun port pour {inst.libelle}."
        with self._verrou_ports:
            try:
                with serial.Serial(port, inst.baud, timeout=inst.delai_serie) as ser:
                    infos = inst.sonde(ser)
            except (serial.SerialException, OSError) as e:
                return False, f"Port {port} inaccessible : {e}\nIl est peut-être utilisé par un autre logiciel."
        if infos is None:
            return False, f"Aucune réponse de {inst.libelle} sur {port}."
        return True, infos

    def detecter(self, id_):
        """Sonde les ports candidats un à un ; mémorise et renvoie (port, infos) du premier qui répond, sinon (None, None)."""
        for p in self.candidats(id_):
            ok, infos = self.tester(id_, p.device)
            if ok:
                config.definir_reglage(ESPACE, self._cle(id_, "memorise"), p.device)
                return p.device, infos
        return None, None

    def lancer_detection(self, id_):
        """Détection en tâche de fond (sans effet si déjà en cours)."""
        if self.en_recherche(id_):
            return

        def tache():
            try:
                self.detecter(id_)
            finally:
                self._recherches.pop(id_, None)

        t = threading.Thread(target=tache, daemon=True)
        self._recherches[id_] = t
        t.start()

    def en_recherche(self, id_):
        t = self._recherches.get(id_)
        return t is not None and t.is_alive()

    def port_ou_erreur(self, id_):
        """Port de l'instrument, ou fenêtre d'erreur expliquant quoi faire."""
        p = self.port(id_)
        if not p:
            from tkinter import messagebox
            inst = self.registre[id_]
            messagebox.showerror(f"{inst.libelle} introuvable",
                                 f"{inst.nom} : aucun port détecté.\n{inst.aide}\n\n"
                                 "Le menu « Instruments » de l'accueil permet de le chercher ou de choisir le port.")
        return p
