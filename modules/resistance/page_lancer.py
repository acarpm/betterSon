"""Page « Lancer un test » : choix du profil, technicien, n° de série, puis bascule sur la page « en cours »."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import theme as T
from dialogue_identite import SelecteurTechnicien
from theme import BG, BORD, CARTE, GRIS, TEXTE, ListeLignes

from . import chemins, profils


def _propre(texte):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in texte.strip())


class PageLancer(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        f = app.f
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        corps.columnconfigure(1, weight=1)
        corps.rowconfigure(0, weight=1)

        gauche = tk.Frame(corps, bg=BG, width=380)
        gauche.grid(row=0, column=0, sticky="nsw", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Choisir le profil", f)
        self.liste = ListeLignes(gauche, f, hauteur=200, on_select=self._profil_choisi, vide="Aucun profil pour l'instant.")
        self.liste.pack(fill="both", expand=True)
        ttk.Button(gauche, text="Créer ou modifier un profil", style="Tool.TButton",
                   command=lambda: app.aller("resistance.profils")).pack(anchor="w", pady=(6, 0))

        droite = tk.Frame(corps, bg=BG)
        droite.grid(row=0, column=1, sticky="nsew")
        T.titre(droite, "Préparer le test", f)
        carte = tk.Frame(droite, bg=CARTE, highlightbackground=BORD, highlightthickness=2)
        carte.pack(fill="x")
        interne = tk.Frame(carte, bg=CARTE)
        interne.pack(fill="x", padx=24, pady=20)
        self.lbl_nom = tk.Label(interne, text="", bg=CARTE, fg=TEXTE, font=f(22, True), anchor="w")
        self.lbl_nom.pack(fill="x")
        grille = tk.Frame(interne, bg=CARTE)
        grille.pack(fill="x", pady=(14, 0))
        self.vals = {}
        cases = [("courant", "Courant du pulse"), ("pulse", "Pulse / mesure dès"), ("repet", "Pulses"),
                 ("attente", "Attente entre pulses"), ("duree", "Durée totale")]
        for k, (cle, titre) in enumerate(cases):
            grille.columnconfigure(k, weight=1, uniform="p")
            bloc = tk.Frame(grille, bg=CARTE)
            bloc.grid(row=0, column=k, sticky="w")
            tk.Label(bloc, text=titre, bg=CARTE, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=CARTE, fg=TEXTE, font=f(20, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl
        self.lbl_notes = tk.Label(interne, text="", bg=CARTE, fg=GRIS, font=f(12), anchor="w", justify="left", wraplength=560)
        self.lbl_notes.pack(fill="x", pady=(12, 0))

        self.sel_technicien = SelecteurTechnicien(droite, f)
        self.sel_technicien.pack(fill="x", pady=(20, 0))
        tk.Label(droite, text="N° de série de la batterie (facultatif)", bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x", pady=(12, 2))
        self.var_serie = tk.StringVar()
        e = ttk.Entry(droite, textvariable=self.var_serie, font=f(14))
        e.pack(fill="x")
        e.bind("<Return>", lambda ev: self._demarrer())
        self.btn_start = ttk.Button(droite, text="Lancer le test", style="Start.TButton", command=self._demarrer)
        self.btn_start.pack(fill="x", pady=(20, 0))
        tk.Label(droite, text="La charge EA doit être branchée sur les bornes du pack, et l'équilibreur Daly sur ses cellules.",
                 bg=BG, fg=GRIS, font=f(11), anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(8, 0))

    def on_show(self):
        self.sel_technicien.rafraichir()
        noms = [p["nom"] for p in self.mod.profils]
        i = noms.index(self.mod.dernier) if self.mod.dernier in noms else (0 if noms else -1)
        self.liste.remplir([(p["nom"], profils.resume(p)) for p in self.mod.profils], i)
        self._resume()

    def _profil_courant(self):
        i = self.liste.index
        return self.mod.profils[i] if 0 <= i < len(self.mod.profils) else None

    def _profil_choisi(self, i):
        self.mod.dernier = self.mod.profils[i]["nom"]
        profils.sauver(chemins.fichier_profils(), self.mod.profils, self.mod.dernier)
        self._resume()

    def _resume(self):
        p = self._profil_courant()
        self.btn_start.config(state="normal" if p else "disabled")
        if p is None:
            self.lbl_nom.config(text="Aucun profil sélectionné")
            for lbl in self.vals.values():
                lbl.config(text="--")
            self.lbl_notes.config(text="Créez un profil pour pouvoir lancer un test.")
            return
        self.lbl_nom.config(text=p["nom"])
        v = self.vals
        v["courant"].config(text=f"{p['courant']:g} A")
        v["pulse"].config(text=f"{p['pulse_s']:g} s / {p['mesure_apres_s']:g} s")
        v["repet"].config(text=str(p["repetitions"]))
        v["attente"].config(text=f"{p['attente_s']:g} s")
        v["duree"].config(text=T.duree(profils.duree_totale_s(p)))
        self.lbl_notes.config(text=p["notes"])

    def _demarrer(self):
        p = self._profil_courant()
        if p is None:
            return messagebox.showwarning("Aucun profil", "Créez ou choisissez un profil de test.")
        technicien = self.sel_technicien.valeur()
        if not technicien:
            return messagebox.showwarning("Technicien", "Choisissez le technicien qui commande ce test (bouton « Gérer » pour l'ajouter).")
        port_charge = self.app.instruments.port_ou_erreur("charge_ea")
        port_daly = port_charge and self.app.instruments.port_ou_erreur("equilibreur_daly")
        if not (port_charge and port_daly):
            return
        serie = self.var_serie.get().strip()
        nom = "_".join(x for x in (_propre(p["nom"]), _propre(serie)) if x) or "batterie"
        chemin = os.path.join(chemins.dossier_csv(), f"{nom}_{datetime.now():%Y%m%d_%H%M%S}.csv")
        self.app.page("resistance.encours").demarrer(p, serie, port_charge, port_daly, chemin, technicien)
        self.var_serie.set("")
        self.app.aller("resistance.encours")
