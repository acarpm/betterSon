"""Page « Lancer un test » : choix du profil + préparation, puis bascule sur la page « test en cours »."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import serial

import main as charge  # communication avec la charge EA
import theme as T
from theme import BG, BORD, CARTE, GRIS, TEXTE, ListeLignes

from . import chemins, profils


def _propre(texte):
    """Nettoie un texte pour un nom de fichier."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in texte.strip())


class PageLancer(tk.Frame):
    """Sélection du profil + préparation du test (puis bascule sur la page « test en cours »)."""

    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app = app
        self.mod = mod
        f = app.f
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        corps.columnconfigure(1, weight=1)
        corps.rowconfigure(0, weight=1)

        # ---- gauche : choix du profil ----
        gauche = tk.Frame(corps, bg=BG, width=380)
        gauche.grid(row=0, column=0, sticky="nsw", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Choisir le test", f)
        self.liste = ListeLignes(gauche, f, hauteur=200, on_select=self._profil_choisi,
                                 vide="Aucun profil pour l'instant.")
        self.liste.pack(fill="both", expand=True)
        self.btn_creer = ttk.Button(gauche, text="Créer ou modifier un profil", style="Tool.TButton",
                                    command=lambda: app.aller("decharge.profils"))
        self.btn_creer.pack(anchor="w", pady=(6, 0))

        # ---- droite : récapitulatif + lancement ----
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
        for col, (cle, titre) in enumerate([("v", "Tension de coupure"), ("a", "Courant de décharge"),
                                            ("w", "Puissance de décharge")]):
            grille.columnconfigure(col, weight=1, uniform="p")
            bloc = tk.Frame(grille, bg=CARTE)
            bloc.grid(row=0, column=col, sticky="w")
            tk.Label(bloc, text=titre, bg=CARTE, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=CARTE, fg=TEXTE, font=f(26, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl
        self.lbl_notes = tk.Label(interne, text="", bg=CARTE, fg=GRIS, font=f(12), anchor="w",
                                  justify="left", wraplength=560)
        self.lbl_notes.pack(fill="x", pady=(12, 0))

        tk.Label(droite, text="N° de série de la batterie (facultatif)", bg=BG, fg=GRIS, font=f(11),
                 anchor="w").pack(fill="x", pady=(20, 2))
        self.var_serie = tk.StringVar()
        self.e_serie = ttk.Entry(droite, textvariable=self.var_serie, font=f(14))
        self.e_serie.pack(fill="x")
        self.e_serie.bind("<Return>", lambda ev: self._demarrer())

        self.btn_start = ttk.Button(droite, text="Lancer le test", style="Start.TButton", command=self._demarrer)
        self.btn_start.pack(fill="x", pady=(20, 0))
        tk.Label(droite, text="Vérifiez que la batterie est bien branchée sur la charge avant de lancer.",
                 bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x", pady=(8, 0))
        self.lbl_etat = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(12, True), anchor="w",
                                 justify="left", wraplength=560)
        self.lbl_etat.pack(fill="x", pady=(10, 0))

        outils = tk.Frame(droite, bg=BG)
        outils.pack(side="bottom", fill="x")
        tk.Frame(outils, bg=BORD, height=1).pack(fill="x", pady=(0, 6))
        ttk.Button(outils, text="Identité de la charge", style="Tool.TButton", command=self._identite).pack(side="left")
        ttk.Button(outils, text="Mesure instantanée", style="Tool.TButton", command=self._mesure).pack(side="left")

    def on_show(self):
        self.lbl_etat.config(text="")
        noms = [p["nom"] for p in self.mod.profils]
        i = noms.index(self.mod.dernier) if self.mod.dernier in noms else (0 if noms else -1)
        self.liste.remplir([(p["nom"], T.resume_profil(p)) for p in self.mod.profils], i)
        self._resume()

    # ---------- profils ----------
    def _profil_courant(self):
        i = self.liste.index
        return self.mod.profils[i] if 0 <= i < len(self.mod.profils) else None

    def _profil_choisi(self, i):
        self.mod.dernier = self.mod.profils[i]["nom"]
        profils.sauver(chemins.fichier_profils(), self.mod.profils, self.mod.dernier)  # retient le dernier profil
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
        self.vals["v"].config(text=f"{p['tension_coupure']:g} V")
        self.vals["a"].config(text="--" if p["courant"] is None else f"{p['courant']:g} A")
        self.vals["w"].config(text="--" if p["puissance"] is None else f"{p['puissance']:g} W")
        self.lbl_notes.config(text=p["notes"])

    # ---------- diagnostic ----------
    def _commande_simple(self, fonction):
        port = self.mod.port_ou_erreur()
        if not port:
            return
        try:
            with serial.Serial(port, 115200, timeout=1) as s:
                return fonction(s)
        except (serial.SerialException, OSError, ValueError) as e:
            messagebox.showerror("Erreur de communication", str(e))

    def _identite(self):
        rep = self._commande_simple(charge.identifier)
        if rep is not None:
            self.lbl_etat.config(text=f"Identité : {rep or '(pas de réponse)'}", fg=GRIS)

    def _mesure(self):
        rep = self._commande_simple(lambda s: charge.lire_valeurs(s, 1, 1, 1))
        if rep:
            v, i, p = rep
            self.lbl_etat.config(text=f"Mesure : {v:.2f} V   {i:.2f} A   {p:.1f} W", fg=GRIS)

    # ---------- lancement ----------
    def _demarrer(self):
        p = self._profil_courant()
        if p is None:
            return messagebox.showwarning("Aucun profil", "Créez ou choisissez un profil de test.")
        port = self.mod.port_ou_erreur()
        if not port:
            return
        serie = self.var_serie.get().strip()
        nom = "_".join(x for x in (_propre(p["nom"]), _propre(serie)) if x) or "batterie"
        os.makedirs(chemins.dossier_csv(), exist_ok=True)
        chemin = os.path.join(chemins.dossier_csv(), f"{nom}_{datetime.now():%Y%m%d_%H%M%S}.csv")
        self.app.page("decharge.encours").demarrer(p, serie, port, chemin)
        self.var_serie.set("")  # prêt pour la batterie suivante
        self.app.aller("decharge.encours")
