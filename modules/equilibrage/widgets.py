"""Composants graphiques du module Équilibrage."""
import math
import tkinter as tk

from theme import BG, BORD, CARTE, GRIS, LIME, ORANGE, ROUGE, TEAL, TEXTE


ECART_ANORMAL_MV = 30   # au-delà, un équilibreur au repos mérite d'être signalé (le seuil réel de l'appareil est inconnu)


def equilibrage_actif(flags, courant):
    """Vrai si l'appareil signale une activité : cellule en cours d'équilibrage (0x97) ou courant d'équilibrage non nul."""
    return any(flags or []) or (courant is not None and abs(courant) >= 0.05)


def texte_courant(courant, flags=None):
    """Texte de la tuile « Courant d'équilibrage ».

    Mesuré sur l'appareil : le champ courant de la trame 0x90 reste à 0,0 A même pendant l'équilibrage (cellule signalée
    active par 0x97). Un 0,0 A pendant une activité signalée n'est donc pas une mesure : « non fourni ».
    """
    if courant is None:
        return "--"
    if abs(courant) >= 0.05:
        return f"{courant:+.1f} A"
    return "non fourni" if any(flags or []) else "0.0 A"


def resume_equilibrage(flags, courant=None, ecart_mv=None, seuils=None, v_max=None):
    """(texte, couleur) décrivant ce que fait l'appareil : états d'équilibrage par cellule (0x97), courant d'équilibrage
    et, quand l'appareil les fournit (0x5F), ses seuils de déclenchement."""
    actives = [f"C{i + 1}" for i, a in enumerate(flags or []) if a]
    if equilibrage_actif(flags, courant):
        detail = f" sur {', '.join(actives)}" if actives else ""
        amp = f" · courant {courant:+.1f} A" if courant is not None and abs(courant) >= 0.05 else ""
        return f"Équilibrage en cours{detail}{amp}", ORANGE
    mesure = ("courant 0,0 A" + (", aucune cellule active" if flags is not None else "")) if courant is not None else "aucune activité signalée"
    if seuils and ecart_mv is not None:
        s_ecart, s_tension = seuils["ecart_ouverture_mv"], seuils["tension_ouverture_mv"]
        regle = f"seuils de l'appareil : écart ≥ {s_ecart} mV et cellule ≥ {s_tension / 1000:.3f} V"
        if ecart_mv < s_ecart:
            return f"Équilibrage au repos ({mesure}) : écart de {ecart_mv:.0f} mV sous le seuil de déclenchement ({regle})", GRIS
        if v_max is not None and v_max * 1000 < s_tension:
            return (f"Équilibrage au repos ({mesure}) : l'écart ({ecart_mv:.0f} mV) dépasse le seuil mais aucune cellule n'atteint la "
                    f"tension d'ouverture ({regle})"), GRIS
        return (f"L'appareil devrait équilibrer ({regle}) mais n'équilibre pas ({mesure}) : "
                "équilibrage désactivé ou réservé à la charge ? Voir les réglages de l'appareil."), ROUGE
    if ecart_mv is not None and ecart_mv >= ECART_ANORMAL_MV:
        return (f"L'appareil n'équilibre pas alors que l'écart est de {ecart_mv:.0f} mV ({mesure}) : équilibrage désactivé, "
                "réservé à la charge, ou seuil de déclenchement plus élevé ? Voir les réglages de l'appareil."), ROUGE
    return f"Équilibrage au repos ({mesure}) : rien à équilibrer, ou l'écart n'a pas atteint le seuil de l'appareil", GRIS


class Mesures(tk.Frame):
    """Rangée de grandes valeurs étiquetées.

    regler(cle, texte, titre=None) change une valeur (et son intitulé) ; masquer(cle, True) retire une valeur sans objet.
    """

    def __init__(self, parent, f, champs, taille=22, fond=BG):
        super().__init__(parent, bg=fond)
        self.vals, self.titres, self.blocs, self._titres_defaut, self._colonnes = {}, {}, {}, {}, {}
        for col, (cle, titre) in enumerate(champs):
            self._colonnes[cle] = col
            self.columnconfigure(col, weight=1, uniform="m")
            bloc = tk.Frame(self, bg=fond)
            bloc.grid(row=0, column=col, sticky="w")
            lbl_t = tk.Label(bloc, text=titre, bg=fond, fg=GRIS, font=f(11))
            lbl_t.pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=fond, fg=TEXTE, font=f(taille, True))
            lbl.pack(anchor="w")
            self.vals[cle], self.titres[cle], self.blocs[cle], self._titres_defaut[cle] = lbl, lbl_t, bloc, titre

    def regler(self, cle, texte, titre=None):
        self.vals[cle].config(text=texte)
        if titre is not None:
            self.titres[cle].config(text=titre)

    def masquer(self, cle, cache=True):
        col = self._colonnes[cle]
        if cache:
            self.blocs[cle].grid_remove()
            self.columnconfigure(col, weight=0, uniform="")   # une valeur masquée ne prend plus de place
        else:
            self.blocs[cle].grid()
            self.columnconfigure(col, weight=1, uniform="m")

    def effacer(self):
        for cle, lbl in self.vals.items():
            lbl.config(text="--")
            self.titres[cle].config(text=self._titres_defaut[cle])


class BarresCellules(tk.Canvas):
    """Une barre par cellule : la plus haute en rouge, la plus basse en bleu-gris, un point orange sous une cellule
    en cours d'équilibrage.

    L'affichage est mis à jour SUR PLACE (les éléments graphiques sont créés une fois, puis seulement déplacés) : aucun
    effacement entre deux lectures, donc aucun clignotement. L'échelle est zoomée pour rendre les écarts visibles mais
    arrondie au centième de volt : elle ne bouge pas à chaque millivolt.
    """

    def __init__(self, parent, f, vide="En attente des mesures…", hauteur=200):
        super().__init__(parent, height=hauteur, bg=CARTE, highlightbackground=BORD, highlightthickness=1)
        self.f, self.vide = f, vide
        self.cellules, self.equilibrage = [], None
        self._n, self._taille = 0, None
        self._el = []          # par cellule : (barre, valeur, indice, point)
        self._note = None
        self.bind("<Configure>", lambda e: self.tracer())

    def definir(self, cellules, equilibrage=None):
        nouvelles = list(cellules or [])
        if not nouvelles and self.cellules:
            return  # une lecture vide ne doit jamais effacer l'affichage : on garde les dernières valeurs
        self.cellules, self.equilibrage = nouvelles, equilibrage
        self.tracer()

    def vider(self):
        """Remise à zéro volontaire (changement de session) : la seule façon d'effacer les barres."""
        self.cellules, self.equilibrage = [], None
        self.tracer()

    def tracer(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 80:
            return
        mesurees = [v for v in self.cellules if v is not None]
        if not mesurees:
            if self._n or self._taille != (w, h, 0):
                self.delete("all")
                self._n, self._el, self._taille = 0, [], (w, h, 0)
                self.create_text(w / 2, h / 2, text=self.vide, fill=GRIS, font=self.f(12))
            return
        if len(self.cellules) != self._n or self._taille != (w, h, len(self.cellules)):
            self._construire(w, h)
        self._positionner(w, h, mesurees)

    def _construire(self, w, h):
        """Crée les éléments (une seule fois par nombre de cellules / taille de fenêtre)."""
        f = self.f
        self.delete("all")
        n = len(self.cellules)
        self._n, self._taille, self._el = n, (w, h, n), []
        self._note = self.create_text(12, 8, anchor="nw", fill=GRIS, font=f(9), text="")
        taille = 11 if (w - 24) / n > 56 else 9
        for _ in range(n):
            barre = self.create_rectangle(0, 0, 0, 0, fill=LIME, outline="")
            valeur = self.create_text(0, 0, text="", fill=TEXTE, font=f(taille, True), anchor="s")
            indice = self.create_text(0, 0, text="", fill=GRIS, font=f(taille, True), anchor="n")
            point = self.create_oval(0, 0, 0, 0, fill=ORANGE, outline="", state="hidden")
            self._el.append((barre, valeur, indice, point))

    def _positionner(self, w, h, mesurees):
        lo, hi = min(mesurees), max(mesurees)
        marge = max(0.02, (hi - lo) * 0.6)
        bas_v = math.floor((lo - marge) * 100) / 100   # échelle arrondie : stable d'une lecture à l'autre
        haut_v = max(math.ceil((hi + marge) * 100) / 100, bas_v + 0.01)
        haut, bas = 34, 40
        n = len(self.cellules)
        place = (w - 24) / n
        largeur = min(54, place * 0.62)
        self.itemconfigure(self._note, text=f"Échelle zoomée : le bas des barres correspond à {bas_v:.2f} V")
        for i, v in enumerate(self.cellules):
            barre, valeur, indice, point = self._el[i]
            cx = 12 + place * (i + 0.5)
            self.coords(indice, cx, h - bas + 8)
            self.itemconfigure(indice, text=f"C{i + 1}")
            if v is None:
                self.coords(barre, cx, h - bas, cx, h - bas)
                self.coords(valeur, cx, h - bas - 6)
                self.itemconfigure(valeur, text="—", fill=GRIS)
                self.itemconfigure(point, state="hidden")
                continue
            hauteur = (v - bas_v) / (haut_v - bas_v) * (h - bas - haut)
            couleur = LIME
            if hi - lo > 0.0005:
                couleur = ROUGE if v == hi else TEAL if v == lo else LIME
            self.coords(barre, cx - largeur / 2, h - bas - hauteur, cx + largeur / 2, h - bas)
            self.itemconfigure(barre, fill=couleur)
            self.coords(valeur, cx, h - bas - hauteur - 4)
            self.itemconfigure(valeur, text=f"{v:.3f}", fill=TEXTE)
            actif = bool(self.equilibrage and i < len(self.equilibrage) and self.equilibrage[i])
            self.coords(point, cx - 5, h - 14, cx + 5, h - 4)
            self.itemconfigure(point, state="normal" if actif else "hidden")
