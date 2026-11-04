"""Page « Créer / modifier un test » : gestion des profils de test."""
import tkinter as tk
from tkinter import messagebox, ttk

import theme as T
from theme import BG, BORD, GRIS, ROUGE, TEXTE, VERT, ListeLignes

from . import chemins, profils


class PageProfils(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app = app
        self.mod = mod
        f = app.f
        self.index = None  # profil en cours d'édition (None = nouveau)
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))

        # colonne gauche : bouton Nouveau + liste
        gauche = tk.Frame(corps, bg=BG, width=320)
        gauche.pack(side="left", fill="y", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Profils existants", f)
        ttk.Button(gauche, text="+  Nouveau profil", style="Start.TButton", command=self._nouveau).pack(fill="x")
        self.liste = ListeLignes(gauche, f, hauteur=300, radio=False, on_select=self._selectionner,
                                 vide="Aucun profil pour l'instant.\nRemplissez le formulaire à droite.")
        self.liste.pack(fill="both", expand=True, pady=(12, 0))

        # colonne droite : boutons d'abord (toujours visibles), puis formulaire
        droite = tk.Frame(corps, bg=BG)
        droite.pack(side="left", fill="both", expand=True)
        boutons = tk.Frame(droite, bg=BG)
        boutons.pack(side="bottom", fill="x", pady=(14, 0))
        ttk.Button(boutons, text="Enregistrer", style="Start.TButton", command=self._enregistrer).pack(side="left")
        self.btn_suppr = ttk.Button(boutons, text="Supprimer ce profil", style="Tool.TButton", command=self._supprimer)
        self.btn_suppr.pack(side="left", padx=12)

        self.lbl_titre = tk.Label(droite, text="", bg=BG, fg=TEXTE, font=f(14, True), anchor="w")
        self.lbl_titre.pack(fill="x")
        tk.Frame(droite, bg=BORD, height=1).pack(fill="x", pady=(4, 6))
        self.vars = {c: tk.StringVar() for c in ("nom", "tension_coupure", "courant", "puissance", "notes")}

        def champ(parent_, cle, texte):
            bloc = tk.Frame(parent_, bg=BG)
            tk.Label(bloc, text=texte, bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x", pady=(8, 2))
            e = ttk.Entry(bloc, textvariable=self.vars[cle], font=f(13))
            e.pack(fill="x")
            e.bind("<Return>", lambda ev: self._enregistrer())
            return bloc, e

        bloc, self.e_nom = champ(droite, "nom", "Nom du profil (ex. LFP 48 V)")
        bloc.pack(fill="x")
        nombres = tk.Frame(droite, bg=BG)
        nombres.pack(fill="x")
        for col, (cle, texte) in enumerate([("tension_coupure", "Tension de coupure (V)"),
                                            ("courant", "Courant (A)"), ("puissance", "Puissance (W)")]):
            nombres.columnconfigure(col, weight=1, uniform="n")
            b_, _ = champ(nombres, cle, texte)
            b_.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        tk.Label(droite, text="Indiquez le courant, la puissance, ou les deux. Le test s'arrête dès que la "
                              "tension passe sous la coupure.", bg=BG, fg=GRIS, font=f(10), anchor="w",
                 justify="left", wraplength=480).pack(fill="x", pady=(6, 0))
        bloc, _ = champ(droite, "notes", "Notes (facultatif)")
        bloc.pack(fill="x")
        self.lbl_msg = tk.Label(droite, text="", bg=BG, fg=ROUGE, font=f(12, True), anchor="w",
                                justify="left", wraplength=480)
        self.lbl_msg.pack(fill="x", pady=(10, 0))

    # ---------- cycle de vie ----------
    def on_show(self):
        noms = [p["nom"] for p in self.mod.profils]
        i = noms.index(self.mod.dernier) if self.mod.dernier in noms else -1
        self._rafraichir(i)
        self._selectionner(i) if i >= 0 else self._nouveau()

    def _rafraichir(self, index=-1):
        self.liste.remplir([(p["nom"], T.resume_profil(p)) for p in self.mod.profils], index)

    def _afficher(self, p):
        for cle, var in self.vars.items():
            v = p.get(cle) if p else ""
            var.set("" if v is None else (f"{v:g}" if isinstance(v, float) else v))
        self.lbl_msg.config(text="")

    def _nouveau(self):
        self.index = None
        self.liste.choisir(-1, notifier=False)
        self._afficher(None)
        self.lbl_titre.config(text="Nouveau profil")
        self.btn_suppr.config(state="disabled")
        self.e_nom.focus_set()

    def _selectionner(self, i):
        if not 0 <= i < len(self.mod.profils):
            return self._nouveau()
        self.index = i
        self.liste.choisir(i, notifier=False)
        self._afficher(self.mod.profils[i])
        self.lbl_titre.config(text="Modifier le profil")
        self.btn_suppr.config(state="normal")

    def _enregistrer(self):
        try:
            p = profils.valider({cle: var.get() for cle, var in self.vars.items()})
        except ValueError as e:
            return self.lbl_msg.config(text=str(e), fg=ROUGE)
        autres = [q["nom"].lower() for k, q in enumerate(self.mod.profils) if k != self.index]
        if p["nom"].lower() in autres:
            return self.lbl_msg.config(text="Un profil porte déjà ce nom.", fg=ROUGE)
        if self.index is None:
            self.mod.profils.append(p)
            self.index = len(self.mod.profils) - 1
        else:
            self.mod.profils[self.index] = p
        self.mod.dernier = p["nom"]
        profils.sauver(chemins.fichier_profils(), self.mod.profils, p["nom"])
        self._rafraichir(self.index)
        self._selectionner(self.index)
        self.lbl_msg.config(text="✔ Profil enregistré.", fg=VERT)

    def _supprimer(self):
        if self.index is None:
            return
        nom = self.mod.profils[self.index]["nom"]
        if not messagebox.askyesno("Supprimer", f"Supprimer le profil « {nom} » ?"):
            return
        del self.mod.profils[self.index]
        self.mod.dernier = None
        profils.sauver(chemins.fichier_profils(), self.mod.profils, None)
        self._rafraichir()
        self._nouveau()
