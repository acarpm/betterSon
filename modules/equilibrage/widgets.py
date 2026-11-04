"""Composants graphiques du module Équilibrage."""
import tkinter as tk

from theme import BG, BORD, CARTE, GRIS, LIME, ORANGE, ROUGE, TEAL, TEXTE


class Mesures(tk.Frame):
    """Rangée de grandes valeurs étiquetées. regler(cle, texte) change une valeur."""

    def __init__(self, parent, f, champs, taille=22, fond=BG):
        super().__init__(parent, bg=fond)
        self.vals = {}
        for col, (cle, titre) in enumerate(champs):
            self.columnconfigure(col, weight=1, uniform="m")
            bloc = tk.Frame(self, bg=fond)
            bloc.grid(row=0, column=col, sticky="w")
            tk.Label(bloc, text=titre, bg=fond, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=fond, fg=TEXTE, font=f(taille, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl

    def regler(self, cle, texte):
        self.vals[cle].config(text=texte)

    def effacer(self):
        for lbl in self.vals.values():
            lbl.config(text="--")


class BarresCellules(tk.Canvas):
    """Une barre par cellule. L'échelle est zoomée autour des valeurs pour rendre les écarts visibles :
    la plus haute en rouge, la plus basse en bleu-gris, un point orange sous une cellule en cours d'équilibrage."""

    def __init__(self, parent, f, vide="En attente des mesures…", hauteur=200):
        super().__init__(parent, height=hauteur, bg=CARTE, highlightbackground=BORD, highlightthickness=1)
        self.f, self.vide = f, vide
        self.cellules, self.equilibrage = [], None
        self.bind("<Configure>", lambda e: self.tracer())

    def definir(self, cellules, equilibrage=None):
        self.cellules, self.equilibrage = list(cellules or []), equilibrage
        self.tracer()

    def tracer(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        f = self.f
        if w < 100 or h < 80:
            return
        mesurees = [v for v in self.cellules if v is not None]
        if not mesurees:
            self.create_text(w / 2, h / 2, text=self.vide, fill=GRIS, font=f(12))
            return
        lo, hi = min(mesurees), max(mesurees)
        marge = max(0.02, (hi - lo) * 0.6)
        bas_v, haut_v = lo - marge, hi + marge
        haut, bas = 34, 40
        n = len(self.cellules)
        place = (w - 24) / n
        largeur = min(54, place * 0.62)
        taille = 11 if place > 56 else 9
        self.create_text(12, 8, anchor="nw", fill=GRIS, font=f(9),
                         text=f"Échelle zoomée : le bas des barres correspond à {bas_v:.3f} V")
        for i, v in enumerate(self.cellules):
            cx = 12 + place * (i + 0.5)
            self.create_text(cx, h - bas + 8, text=f"C{i + 1}", fill=GRIS, font=f(taille, True), anchor="n")
            if v is None:
                self.create_text(cx, h - bas - 8, text="—", fill=GRIS, font=f(taille))
                continue
            hauteur = (v - bas_v) / (haut_v - bas_v) * (h - bas - haut)
            couleur = LIME
            if hi - lo > 0.0005:
                couleur = ROUGE if v == hi else TEAL if v == lo else LIME
            self.create_rectangle(cx - largeur / 2, h - bas - hauteur, cx + largeur / 2, h - bas, fill=couleur, outline="")
            self.create_text(cx, h - bas - hauteur - 4, text=f"{v:.3f}", fill=TEXTE, font=f(taille, True), anchor="s")
            if self.equilibrage and i < len(self.equilibrage) and self.equilibrage[i]:
                self.create_oval(cx - 5, h - 14, cx + 5, h - 4, fill=ORANGE, outline="")
