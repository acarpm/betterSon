"""Page « Connexion » : choix du port série de l'équilibreur Daly et test de la liaison."""
import tkinter as tk
from tkinter import ttk

import serial

import theme as T
from theme import BG, GRIS, ORANGE, ROUGE, VERT, ListeLignes

from . import daly


class PageConnexion(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        f = app.f
        self.ports = []
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        gauche = tk.Frame(corps, bg=BG, width=470)
        gauche.pack(side="left", fill="y", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Port série de l'équilibreur", f)
        tk.Label(gauche, text="Branchez l'adaptateur USB-série de l'équilibreur Daly (9600 bauds), puis choisissez son port.",
                 bg=BG, fg=GRIS, font=f(11), anchor="w", justify="left", wraplength=450).pack(fill="x", pady=(0, 10))
        self.liste = ListeLignes(gauche, f, hauteur=240, on_select=self._choisi,
                                 vide="Aucun port série détecté.\nBranchez l'adaptateur USB puis « Actualiser ».")
        self.liste.pack(fill="both", expand=True)
        ttk.Button(gauche, text="Actualiser la liste", style="Tool.TButton", command=self._actualiser).pack(anchor="w", pady=(6, 0))

        droite = tk.Frame(corps, bg=BG)
        droite.pack(side="left", fill="both", expand=True)
        T.titre(droite, "Tester la liaison", f)
        self.lbl_port = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(13), anchor="w")
        self.lbl_port.pack(fill="x")
        self.btn_test = ttk.Button(droite, text="Tester la connexion", style="Start.TButton", command=self._tester)
        self.btn_test.pack(anchor="w", pady=(14, 0))
        self.lbl_res = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(12, True), anchor="w", justify="left", wraplength=520)
        self.lbl_res.pack(fill="x", pady=(14, 0))

    def on_show(self):
        self.lbl_res.config(text="")
        self._actualiser()

    def _actualiser(self):
        self.ports = self.mod.ports_candidats()
        courant = self.mod.port()
        noms = [p[0] for p in self.ports]
        self.liste.remplir([(p[0], p[1]) for p in self.ports], noms.index(courant) if courant in noms else -1)
        self._maj()

    def _choisi(self, i):
        self.mod.definir_port(self.ports[i][0])
        self.lbl_res.config(text="")
        self._maj()

    def _maj(self):
        p = self.mod.port()
        self.lbl_port.config(text=f"Port choisi : {p}" if p else "Aucun port choisi.", fg=GRIS if p else ORANGE)
        self.btn_test.config(state="normal" if p else "disabled")

    def _tester(self):
        port = self.mod.port()
        self.lbl_res.config(text="Test en cours…", fg=GRIS)
        self.update_idletasks()
        try:
            with serial.Serial(port, daly.BAUD, timeout=0.4) as ser:
                d = daly.Daly(ser).lire_tout()
        except (serial.SerialException, OSError) as e:
            return self.lbl_res.config(text=f"Port inaccessible : {e}\nIl est peut-être utilisé par un autre logiciel.", fg=ROUGE)
        if d is None:
            return self.lbl_res.config(
                text="Aucune réponse de l'appareil. Vérifiez le câblage (TX/RX), l'alimentation, le port choisi,\n"
                     "et que l'équilibreur n'est pas en veille.", fg=ROUGE)
        morceaux = [f"{len(d['cellules'])} cellules"]
        if d["v_pack"] is not None:
            morceaux.append(f"pack {d['v_pack']:.1f} V")
        if d.get("ecart_mv") is not None:
            morceaux.append(f"écart {d['ecart_mv']:.0f} mV")
        self.lbl_res.config(text="✔ Appareil détecté : " + ", ".join(morceaux), fg=VERT)
