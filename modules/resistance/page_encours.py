"""Page « Test en cours » : phase et compte à rebours, mesures en direct, résistances calculées au fil des pulses."""
import queue
import time
import tkinter as tk
from tkinter import messagebox, ttk

import envoi
import identite
import theme as T
from theme import BG, BLEU, BORD, GRIS, ORANGE, ROUGE, TEAL, TEXTE, VERT, GraphesTemps

from . import calcul, profils
from .mesure import Mesure
from .widgets import BarresResistance, texte_mohm

DEFS_GRAPHE = [("V", "Tension pack", "V", TEAL), ("A", "Courant", "A", "#8a9a00")]
NOMS_PHASES = {"attente": "Attente avant le pulse suivant", "repos": "Repos (tension de référence)", "pulse": "Pulse de courant"}


class PageEnCours(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        f = app.f
        self.file = queue.Queue()
        self.mesure = None
        self.series = {"V": [], "A": []}
        self.essais = []
        self.dernier_csv = None
        self.profil = None
        self.phase = None    # (essai, nom, fin monotonic)

        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        haut = tk.Frame(corps, bg=BG)
        haut.pack(fill="x")
        self.zone_btn = tk.Frame(haut, bg=BG)
        self.zone_btn.pack(side="right", padx=(20, 0))
        self.btn_stop = ttk.Button(self.zone_btn, text="Arrêter le test", style="Stop.TButton", command=self._arreter)
        self.btn_nouveau = ttk.Button(self.zone_btn, text="Nouveau test", style="Start.TButton",
                                      command=lambda: app.aller("resistance.lancer"))
        self.btn_analyse = ttk.Button(self.zone_btn, text="Voir dans l'analyse", style="Tool.TButton", command=self._voir_analyse)
        textes = tk.Frame(haut, bg=BG)
        textes.pack(side="left", fill="x", expand=True)
        self.lbl_profil = tk.Label(textes, text="", bg=BG, fg=TEXTE, font=f(22, True), anchor="w")
        self.lbl_profil.pack(fill="x")
        self.lbl_detail = tk.Label(textes, text="", bg=BG, fg=GRIS, font=f(12), anchor="w")
        self.lbl_detail.pack(fill="x")
        self.lbl_etat = tk.Label(textes, text="", bg=BG, fg=GRIS, font=f(14, True), anchor="w", justify="left", wraplength=900)
        self.lbl_etat.pack(fill="x", pady=(6, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(12, 12))

        grille = tk.Frame(corps, bg=BG)
        grille.pack(fill="x")
        self.vals = {}
        for col, (cle, titre) in enumerate([("V", "Tension pack"), ("A", "Courant"), ("essai", "Pulse"),
                                            ("r", "R pack (dernier pulse)"), ("rm", "R pack (moyenne)")]):
            grille.columnconfigure(col, weight=1, uniform="m")
            bloc = tk.Frame(grille, bg=BG)
            bloc.grid(row=0, column=col, sticky="w")
            tk.Label(bloc, text=titre, bg=BG, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=BG, fg=TEXTE, font=f(26 if cle in ("V", "r", "rm") else 22, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl

        tk.Label(corps, text="Résistance interne de chaque cellule (moyenne des pulses terminés)", bg=BG, fg=TEXTE,
                 font=f(14, True), anchor="w").pack(fill="x", pady=(14, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(4, 8))
        self.barres = BarresResistance(corps, f)
        self.barres.pack(fill="x")
        self.graphes = GraphesTemps(corps, f, vide="Les courbes apparaissent dès les premières mesures", defs=DEFS_GRAPHE)
        self.graphes.pack(fill="both", expand=True, pady=(10, 0))
        self.graphes.definir(self.series)
        self.after(200, self._traiter_file)

    def on_show(self):
        pass

    def en_test(self):
        return self.mesure is not None and self.mesure.vivant()

    def occupe(self):
        return self.en_test()

    def _etat(self, texte, couleur=GRIS):
        self.lbl_etat.config(text=texte, fg=couleur)

    def _boutons(self, mode):
        for w in self.zone_btn.winfo_children():
            w.pack_forget()
        if mode == "test":
            self.btn_stop.config(state="normal")
            self.btn_stop.pack()
        else:
            self.btn_nouveau.pack(side="left")
            self.btn_analyse.pack(side="left", padx=(10, 0))
        self.app.btn_menu.config(state="disabled" if mode == "test" else "normal")

    # ---------- test ----------
    def demarrer(self, p, serie, port_charge, port_daly, chemin, technicien=""):
        if self.en_test():
            return
        for s in self.series.values():
            s.clear()
        self.essais, self.phase, self.profil, self.dernier_csv = [], None, p, chemin
        for lbl in self.vals.values():
            lbl.config(text="--")
        self.barres.definir([])
        self.lbl_profil.config(text=p["nom"])
        morceaux = ([f"N° de série : {serie}"] if serie else []) + [profils.resume(p)] + ([f"Technicien : {technicien}"] if technicien else [])
        self.lbl_detail.config(text="   ·   ".join(morceaux))
        self.graphes.definir(self.series)
        self._boutons("test")
        self._etat("Test en cours… ne débranchez pas la batterie.", BLEU)
        self.mesure = Mesure(p, port_charge, port_daly, self.file, chemin, identite.lignes_signature(technicien))
        self.mesure.demarrer()

    def _arreter(self):
        if self.mesure:
            self.mesure.arreter()
        self.btn_stop.config(state="disabled")
        self._etat("Arrêt en cours…", ORANGE)

    def arreter_et_attendre(self):
        if self.mesure:
            self.mesure.arreter()
            self.mesure.attendre(8)

    # ---------- messages du thread ----------
    def _traiter_file(self):
        try:
            while True:
                msg = self.file.get_nowait()
                if msg[0] == "phase":
                    self.phase = (msg[1], msg[2], msg[3])
                    self.vals["essai"].config(text=f"{msg[1]} / {self.profil['repetitions']}")
                elif msg[0] == "echantillon":
                    _, t, essai, phase, v, i, cellules = msg
                    self.vals["V"].config(text=f"{v:.2f} V")
                    self.vals["A"].config(text=f"{i:.2f} A")
                    self.series["V"].append((t, v))
                    self.series["A"].append((t, i))
                    self.graphes.tracer()
                elif msg[0] == "essai":
                    self._essai_termine(msg[1])
                elif msg[0] == "fin":
                    self._fin_test(msg[1], msg[2])
        except queue.Empty:
            pass
        if self.phase and self.en_test() and self.btn_stop["state"] != "disabled":
            essai, nom, fin = self.phase
            self._etat(f"{NOMS_PHASES[nom]}  ·  {max(0, int(fin - time.monotonic()) + 1)} s", BLEU)
        self.after(200, self._traiter_file)

    def _essai_termine(self, resultat):
        self.essais.append(resultat)
        s = calcul.synthese(self.essais)
        self.vals["r"].config(text=texte_mohm(resultat["r_pack"]))
        self.vals["rm"].config(text=texte_mohm(s["pack"]["moyenne"]))
        self.barres.definir(s["cellules"])

    def _fin_test(self, motif, detail):
        self.phase = None
        self._boutons("fin")
        envoi.envoyer("resistance", self.dernier_csv, motif)
        if motif == "erreur":
            self._etat("Test interrompu sur erreur - vérifiez la charge et l'équilibreur.", ROUGE)
            return messagebox.showerror("Erreur", f"{detail}\n\nL'entrée de la charge a été coupée (vérifiez-le sur la charge).")
        n = detail["n_essais"]
        mesures = f"{n} pulse{'s' if n > 1 else ''} mesuré{'s' if n > 1 else ''}"
        if motif == "coupure":
            self._etat(f"Tension mini d'une cellule atteinte : test arrêté ({mesures}). La charge est coupée.", ROUGE)
        elif motif == "stop":
            self._etat(f"Test arrêté ({mesures}).", ORANGE)
        else:
            self._etat(f"✔ Test terminé · R pack = {texte_mohm(detail['pack']['moyenne'])} ({mesures}) · enregistré", VERT)
        self.barres.definir(detail["cellules"])

    def _voir_analyse(self):
        self.app.page("resistance.resultats").a_selectionner = self.dernier_csv
        self.app.aller("resistance.resultats")
