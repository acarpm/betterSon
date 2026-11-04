"""Page « Gérer les modules » : activer / désactiver chaque module du logiciel."""
import tkinter as tk

import config
import theme as T
from theme import BG, BORD, CARTE, GRIS, TEXTE, VERT, Interrupteur


class PageModules(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.colonne = tk.Frame(self, bg=BG)
        self.colonne.pack(fill="both", expand=True, padx=28, pady=(18, 16))

    def on_show(self):
        a, f = self.app, self.app.f
        for w in self.colonne.winfo_children():
            w.destroy()
        T.titre(self.colonne, "Gérer les modules", f)
        tk.Label(self.colonne, text="Un module désactivé disparaît de l'accueil. Ses données (profils, mesures…) "
                                    "sont conservées et retrouvées à la réactivation.",
                 bg=BG, fg=GRIS, font=f(12), anchor="w", justify="left", wraplength=900).pack(fill="x", pady=(0, 14))
        for m in a.modules.values():
            carte = tk.Frame(self.colonne, bg=CARTE, highlightbackground=BORD, highlightthickness=2)
            carte.pack(fill="x", pady=(0, 10))
            interne = tk.Frame(carte, bg=CARTE)
            interne.pack(fill="x", padx=20, pady=16)
            etat = tk.Label(interne, text="", bg=CARTE, font=f(11, True), width=9, anchor="e")
            texte = tk.Frame(interne, bg=CARTE)
            tk.Label(texte, text=m.nom, bg=CARTE, fg=TEXTE, font=f(15, True), anchor="w").pack(fill="x")
            tk.Label(texte, text=m.description, bg=CARTE, fg=GRIS, font=f(11), anchor="w", justify="left",
                     wraplength=640).pack(fill="x", pady=(2, 0))
            actif = a.module_actif(m.id)

            def maj(est_actif, etat=etat):
                etat.config(text="Activé" if est_actif else "Désactivé", fg=VERT if est_actif else GRIS)

            def changer(est_actif, m=m, maj=maj):
                config.definir_module(m.id, est_actif)
                maj(est_actif)

            maj(actif)
            Interrupteur(interne, actif, changer).pack(side="left", padx=(0, 18))
            texte.pack(side="left", fill="x", expand=True)
            etat.pack(side="right")
