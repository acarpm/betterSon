"""Page « Analyser les résultats » : parcourt les CSV de tests et affiche synthèse + courbes."""
import os
import tkinter as tk
from tkinter import ttk

import theme as T
from theme import BG, BORD, GRIS, TEXTE, GraphesTemps, ListeLignes

from . import chemins, resultats

VIDE = {"V": [], "A": [], "W": []}


class PageResultats(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app = app
        self.mod = mod
        f = app.f
        self.tous, self.affiches = [], []
        self.a_selectionner = None
        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))

        # ---- gauche : recherche + liste ----
        gauche = tk.Frame(corps, bg=BG, width=340)
        gauche.pack(side="left", fill="y", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Tests réalisés", f)
        self.var_filtre = tk.StringVar()
        e = ttk.Entry(gauche, textvariable=self.var_filtre, font=f(12))
        e.pack(fill="x")
        tk.Label(gauche, text="Filtrer par profil ou n° de série", bg=BG, fg=GRIS, font=f(10),
                 anchor="w").pack(fill="x", pady=(2, 8))
        self.var_filtre.trace_add("write", lambda *a: self._filtrer())
        self.liste = ListeLignes(gauche, f, hauteur=300, radio=False, on_select=self._afficher,
                                 vide="Aucun résultat.\nLancez un test depuis le menu.")
        self.liste.pack(fill="both", expand=True)
        ttk.Button(gauche, text="Ouvrir le dossier des résultats", style="Tool.TButton",
                   command=lambda: T.ouvrir(self._dossier())).pack(anchor="w", pady=(8, 0))

        # ---- droite : synthèse + courbe ----
        droite = tk.Frame(corps, bg=BG)
        droite.pack(side="left", fill="both", expand=True)
        self.lbl_nom = tk.Label(droite, text="", bg=BG, fg=TEXTE, font=f(18, True), anchor="w")
        self.lbl_nom.pack(fill="x")
        self.lbl_date = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(12), anchor="w")
        self.lbl_date.pack(fill="x")
        tk.Frame(droite, bg=BORD, height=1).pack(fill="x", pady=(8, 10))

        grille = tk.Frame(droite, bg=BG)
        grille.pack(fill="x")
        self.vals = {}
        cases = [("ah", "Capacité"), ("wh", "Énergie"), ("duree", "Durée"), ("points", "Mesures"),
                 ("v_debut", "Tension départ"), ("v_fin", "Tension fin"), ("i_moy", "Courant moyen"),
                 ("p_moy", "Puissance moyenne")]
        for k, (cle, titre) in enumerate(cases):
            r, col = divmod(k, 4)
            grille.columnconfigure(col, weight=1, uniform="m")
            bloc = tk.Frame(grille, bg=BG)
            bloc.grid(row=r, column=col, sticky="w", pady=(0, 10))
            tk.Label(bloc, text=titre, bg=BG, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=BG, fg=TEXTE, font=f(20 if r == 0 else 16, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl

        self.graphes = GraphesTemps(droite, f, vide="Sélectionnez un test dans la liste")
        self.graphes.pack(fill="both", expand=True, pady=(4, 0))

        actions = tk.Frame(droite, bg=BG)
        actions.pack(fill="x", pady=(8, 0))
        self.btn_csv = ttk.Button(actions, text="Ouvrir le fichier CSV", style="Tool.TButton", command=self._ouvrir_csv)
        self.btn_csv.pack(side="left")
        self.btn_voir = ttk.Button(actions, text="Afficher dans le dossier", style="Tool.TButton",
                                   command=lambda: self._ouvrir_csv(True))
        self.btn_voir.pack(side="left")

    @staticmethod
    def _dossier():
        os.makedirs(chemins.dossier_csv(), exist_ok=True)
        return chemins.dossier_csv()

    # ---------- cycle de vie ----------
    def on_show(self):
        self.tous = resultats.analyser_dossier(self._dossier())
        self.var_filtre.set("")
        self._filtrer()
        cible, self.a_selectionner = self.a_selectionner, None  # ex. : « Voir dans l'analyse » après un test
        if cible:
            for i, res in enumerate(self.affiches):
                if os.path.abspath(res["chemin"]) == os.path.abspath(cible):
                    self.liste.choisir(i, notifier=False)
                    self._afficher(i)
                    break

    def _filtrer(self):
        mots = self.var_filtre.get().lower().split()
        self.affiches = [r for r in self.tous if all(m in r["nom"].lower() for m in mots)]
        items = [(r["nom"], f"{r['date']:%d/%m/%Y %H:%M}  ·  {r['ah']:.2f} Ah  ·  {r['wh']:.0f} Wh")
                 for r in self.affiches]
        self.liste.remplir(items, 0 if items else -1)
        self._afficher(0) if items else self._afficher(None)

    # ---------- affichage ----------
    def _courant(self):
        i = self.liste.index
        return self.affiches[i] if 0 <= i < len(self.affiches) else None

    def _afficher(self, i):
        r = self.affiches[i] if i is not None and 0 <= i < len(self.affiches) else None
        etat = "normal" if r else "disabled"
        self.btn_csv.config(state=etat)
        self.btn_voir.config(state=etat)
        if r is None:
            self.lbl_nom.config(text="")
            self.lbl_date.config(text="")
            for lbl in self.vals.values():
                lbl.config(text="--")
            self.graphes.definir({k: [] for k in VIDE})
            return
        self.lbl_nom.config(text=r["nom"])
        self.lbl_date.config(text=f"{r['date']:%d/%m/%Y à %H:%M}")
        v = self.vals
        v["ah"].config(text=f"{r['ah']:.3f} Ah")
        v["wh"].config(text=f"{r['wh']:.1f} Wh")
        v["duree"].config(text=T.duree(r["duree_s"]))
        v["points"].config(text=str(r["points"]))
        v["v_debut"].config(text=f"{r['v_debut']:.2f} V")
        v["v_fin"].config(text=f"{r['v_fin']:.2f} V")
        v["i_moy"].config(text=f"{r['i_moy']:.2f} A")
        v["p_moy"].config(text=f"{r['p_moy']:.1f} W")
        self._tracer()

    def _tracer(self):
        r = self._courant()
        self.graphes.definir(r["series"] if r else {k: [] for k in VIDE})

    def _ouvrir_csv(self, reveler=False):
        r = self._courant()
        if r:
            T.ouvrir(r["chemin"], reveler)
