"""Composants graphiques du module Résistance interne."""
import tkinter as tk

from theme import BORD, CARTE, GRIS, ORANGE, TEAL, TEXTE


class BarresResistance(tk.Canvas):
    """Résistance interne de chaque cellule (mΩ), une barre par cellule, depuis zéro. Une cellule dont R s'écarte
    nettement de la médiane (calcul.ECART_ANORMAL) est en orange."""

    def __init__(self, parent, f, vide="Les résistances apparaissent après le premier pulse", hauteur=190):
        super().__init__(parent, height=hauteur, bg=CARTE, highlightbackground=BORD, highlightthickness=1)
        self.f, self.vide, self.cellules = f, vide, []
        self.bind("<Configure>", lambda e: self.tracer())

    def definir(self, cellules):
        """cellules : liste de dicts de calcul.synthese()['cellules'] (clés moyenne, anormale)."""
        self.cellules = list(cellules or [])
        self.tracer()

    def tracer(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        valeurs = [c["moyenne"] for c in self.cellules if c["moyenne"] is not None]
        if w < 100 or h < 80:
            return
        if not valeurs:
            self.create_text(w / 2, h / 2, text=self.vide, fill=GRIS, font=self.f(12))
            return
        n, haut, bas = len(self.cellules), 30, 34
        place = (w - 24) / n
        largeur = min(54, place * 0.62)
        maxi = max(max(valeurs), 1e-9)
        taille = 11 if place > 56 else 9
        for i, c in enumerate(self.cellules):
            cx = 12 + place * (i + 0.5)
            self.create_text(cx, h - bas + 8, text=f"C{i + 1}", fill=GRIS, font=self.f(taille, True), anchor="n")
            if c["moyenne"] is None:
                self.create_text(cx, h - bas - 6, text="—", fill=GRIS, font=self.f(taille, True), anchor="s")
                continue
            hauteur = max(c["moyenne"], 0) / maxi * (h - bas - haut)
            self.create_rectangle(cx - largeur / 2, h - bas - hauteur, cx + largeur / 2, h - bas,
                                  fill=ORANGE if c.get("anormale") else TEAL, outline="")
            self.create_text(cx, h - bas - hauteur - 4, text=f"{c['moyenne']:.1f}", fill=TEXTE,
                             font=self.f(taille, True), anchor="s")
        self.create_text(12, 8, anchor="nw", fill=GRIS, font=self.f(9),
                         text="mΩ  ·  orange : s'écarte de plus de 30 % de la médiane des cellules")


def texte_mohm(valeur, decimales=1):
    return "--" if valeur is None else f"{valeur:.{decimales}f} mΩ"
