"""Page « Lire les tensions » : tension de chaque cellule en direct."""
import queue
import tkinter as tk
from tkinter import ttk

import theme as T
from theme import BG, BORD, GRIS, ORANGE, ROUGE, TEXTE, VERT

from .acquisition import Acquisition
from .widgets import BarresCellules, Mesures

ID = "equilibreur_daly"   # instrument utilisé (détecté par l'application)


class PageCellules(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        f = app.f
        self.file = queue.Queue()
        self.acq = None
        self._visible = False
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))

        haut = tk.Frame(corps, bg=BG)
        haut.pack(fill="x")
        self.btn = ttk.Button(haut, text="Arrêter la lecture", style="Start.TButton", command=self._basculer)
        self.btn.pack(side="right")
        textes = tk.Frame(haut, bg=BG)
        textes.pack(side="left", fill="x", expand=True)
        tk.Label(textes, text="Tensions des cellules", bg=BG, fg=TEXTE, font=f(22, True), anchor="w").pack(fill="x")
        self.lbl_etat = tk.Label(textes, text="", bg=BG, fg=GRIS, font=f(13, True), anchor="w")
        self.lbl_etat.pack(fill="x", pady=(2, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(12, 12))

        self.mesures = Mesures(corps, f, [("v_pack", "Tension pack"), ("courant", "Courant"), ("soc", "SoC"),
                                          ("ecart", "Écart max - min"), ("haute", "Plus haute"), ("basse", "Plus basse")])
        self.mesures.pack(fill="x")
        tk.Label(corps, text="Une barre par cellule (série)", bg=BG, fg=TEXTE, font=f(14, True), anchor="w").pack(fill="x", pady=(14, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(4, 8))
        self.barres = BarresCellules(corps, f)
        self.barres.pack(fill="both", expand=True)
        tk.Label(corps, text="● rouge : plus haute   ● bleu-gris : plus basse   ● orange sous la barre : cellule en cours d'équilibrage "
                             "(si l'appareil le signale)", bg=BG, fg=GRIS, font=f(10), anchor="w").pack(fill="x", pady=(6, 0))
        self.after(200, self._traiter)

    # ---------- cycle de vie ----------
    def on_show(self):
        self._visible = True
        self.mesures.effacer()
        self.barres.definir([])
        self._demarrer()

    def on_hide(self):
        """Libère le port série en quittant la page."""
        self._visible = False
        if self.acq:
            self.acq.arreter()
            self.acq.attendre(3)

    def _actif(self):
        return self.acq is not None and self.acq.vivant()

    def _basculer(self):
        if self._actif():
            self.acq.arreter()
            self.btn.config(state="disabled")
        else:
            self._demarrer()

    def _demarrer(self):
        inst = self.app.instruments
        port = inst.port(ID)
        if not port:  # port inconnu : recherche automatique en arrière-plan, puis démarrage dès que l'appareil est trouvé
            inst.lancer_detection(ID)
            self.btn.config(state="disabled")
            self._etat("Recherche de l'équilibreur sur les ports série…", GRIS)
            return self.after(500, self._attendre_detection)
        self.file = queue.Queue()
        self.acq = Acquisition(port, self.file, intervalle=1.0, baud=inst.instrument(ID).baud)
        self.acq.demarrer()
        self.btn.config(text="Arrêter la lecture", state="normal")
        self._etat(f"Lecture sur {port}…", T.BLEU)

    def _attendre_detection(self):
        if not self._visible:
            return
        inst = self.app.instruments
        if inst.en_recherche(ID):
            return self.after(500, self._attendre_detection)
        if inst.port(ID):
            return self._demarrer()
        self.btn.config(text="Rechercher à nouveau", state="normal")
        self._etat("Équilibreur introuvable : vérifiez l'adaptateur USB et l'alimentation, "
                   "ou ouvrez « Instruments » depuis l'accueil.", ORANGE)

    def _etat(self, texte, couleur=GRIS):
        self.lbl_etat.config(text=texte, fg=couleur)

    # ---------- affichage ----------
    def _traiter(self):
        try:
            while True:
                msg = self.file.get_nowait()
                if msg[0] == "donnees":
                    self._afficher(msg[2])
                elif msg[0] == "silence":
                    self._etat(f"Pas de réponse de l'appareil ({msg[1]} essais) : en veille, mauvais port ou câblage ?", ORANGE)
                elif msg[0] == "fin":
                    self.btn.config(text="Reprendre la lecture", state="normal")
                    if msg[1] == "erreur":
                        self._etat(msg[2], ROUGE)
                    else:
                        self._etat("Lecture arrêtée.", GRIS)
        except queue.Empty:
            pass
        self.after(200, self._traiter)

    def _afficher(self, d):
        m = self.mesures
        m.regler("v_pack", "--" if d["v_pack"] is None else f"{d['v_pack']:.1f} V")
        m.regler("courant", "--" if d["courant"] is None else f"{d['courant']:.1f} A")
        m.regler("soc", "--" if d["soc"] is None else f"{d['soc']:.1f} %")
        if d.get("ecart_mv") is not None:
            m.regler("ecart", f"{d['ecart_mv']:.0f} mV")
            m.regler("haute", f"C{d['i_max'] + 1}  {d['v_max']:.3f} V")
            m.regler("basse", f"C{d['i_min'] + 1}  {d['v_min']:.3f} V")
        self.barres.definir(d["cellules"], d["equilibrage"])
        self._etat(f"● Lecture en direct · {len(d['cellules'])} cellules", VERT)
