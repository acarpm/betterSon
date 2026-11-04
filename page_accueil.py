"""Écrans du noyau : accueil (un module = une tuile) et menu d'un module (ses actions = des tuiles)."""
import tkinter as tk
from tkinter import ttk

import theme as T
from theme import BG, GRIS, ORANGE, TEXTE


def _disposer(parent, tuiles, par_ligne=3):
    """Range des tuiles par rangées de `par_ligne`, centrées."""
    for debut in range(0, len(tuiles), par_ligne):
        rangee = tk.Frame(parent, bg=BG)
        rangee.pack(pady=(0, 18))
        for t in tuiles[debut:debut + par_ligne]:
            t.pack(in_=rangee, side="left", padx=10)


class Accueil(tk.Frame):
    """Menu principal : une tuile par module activé."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.centre = tk.Frame(self, bg=BG)
        self.centre.place(relx=0.5, rely=0.46, anchor="center")
        ttk.Button(self, text="Gérer les modules", style="Tool.TButton",
                   command=lambda: app.aller("modules")).place(relx=1, rely=1, x=-28, y=-16, anchor="se")

    def on_show(self):
        a, f = self.app, self.app.f
        for w in self.centre.winfo_children():
            w.destroy()
        actifs = a.modules_actifs()
        tk.Label(self.centre, text="Que souhaitez-vous faire ?" if actifs else "Aucun module activé",
                 bg=BG, fg=TEXTE, font=f(24, True)).pack(pady=(0, 26))
        if not actifs:
            tk.Label(self.centre, text="Activez au moins un module avec « Gérer les modules » (en bas à droite).",
                     bg=BG, fg=ORANGE, font=f(13)).pack()
            return
        tuiles = []
        for m in actifs:
            info = T.tuile(self.centre, f, m.nom, m.description, m.icone, m.couleur, m.teinte,
                           lambda m=m: a.aller(f"module:{m.id}"))
            info.config(text=m.info(a))
            tuiles.append(info.tuile)
        _disposer(self.centre, tuiles)


class PageModule(tk.Frame):
    """Menu d'un module : une tuile par action."""

    def __init__(self, parent, app, module):
        super().__init__(parent, bg=BG)
        self.app, self.module = app, module
        self.centre = tk.Frame(self, bg=BG)
        self.centre.place(relx=0.5, rely=0.46, anchor="center")

    def on_show(self):
        a, f, m = self.app, self.app.f, self.module
        for w in self.centre.winfo_children():
            w.destroy()
        tk.Label(self.centre, text=m.nom, bg=BG, fg=TEXTE, font=f(24, True)).pack()
        tk.Label(self.centre, text=m.description, bg=BG, fg=GRIS, font=f(12), wraplength=760).pack(pady=(4, 26))
        tuiles = []
        for act in m.actions():
            info = T.tuile(self.centre, f, act.titre, act.description, act.icone, act.couleur, act.teinte,
                           lambda act=act: a.aller(f"{m.id}.{act.page}"))
            if act.info:
                info.config(text=act.info(a))
            tuiles.append(info.tuile)
        _disposer(self.centre, tuiles)
