"""Thème BatConnect et composants graphiques partagés par toutes les pages."""
import bisect
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

# Ressources (logo) : dans le bundle si packagé, sinon à côté du code.
RES = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _dossier_donnees():
    """Où vivent profils.json et mesures/ : jamais dans l'application (elle est remplacée à chaque mise à jour).

    - variable BATCONNECT_DATA si définie ;
    - version installée : Documents/BetterSon (facile à retrouver pour l'opérateur) ;
    - lancé depuis les sources : le dossier du projet.
    """
    perso = os.environ.get("BATCONNECT_DATA")
    if perso:
        return os.path.abspath(os.path.expanduser(perso))
    if getattr(sys, "frozen", False):
        documents = os.path.join(os.path.expanduser("~"), "Documents")
        nouveau, ancien = os.path.join(documents, "BetterSon"), os.path.join(documents, "BatConnect")
        if not os.path.exists(nouveau) and os.path.isdir(ancien):  # ancien nom (v0.1.0) : on reprend les données
            try:
                os.rename(ancien, nouveau)
            except OSError:
                return ancien  # migration impossible : on continue avec l'ancien dossier plutôt que de perdre les données
        return nouveau
    return os.path.dirname(os.path.abspath(__file__))


BASE = _dossier_donnees()
FICHIER_CONFIG = os.path.join(BASE, "config.json")

# Couleurs de la charte BatConnect (relevées sur le logo)
LIME = "#bcd00a"
TEAL = "#4d8ba5"
ANTHRACITE = "#3c3c3b"
BG = "#f7f7f5"
CARTE = "#ffffff"
BORD = "#d9d9d4"
TEXTE = ANTHRACITE
GRIS = "#74746f"
BLEU = TEAL
VERT = "#4a7c1f"
ROUGE = "#b42318"
ORANGE = "#b45309"
SELECTION = "#f1f5d3"  # teinte lime très claire


def init_styles(root):
    """Applique le thème ttk et renvoie la fonction de police f(taille, gras)."""
    base = tkfont.nametofont("TkDefaultFont").actual()["family"]
    f = lambda taille, gras=False: (base, taille, "bold" if gras else "normal")
    st = ttk.Style(root)
    st.theme_use("clam")  # seul thème qui respecte les couleurs sur les 3 systèmes
    st.configure("TEntry", fieldbackground="white", foreground=TEXTE, bordercolor=BORD,
                 lightcolor=BORD, darkcolor=BORD, padding=7)
    st.map("TEntry", bordercolor=[("focus", TEAL)], lightcolor=[("focus", TEAL)], darkcolor=[("focus", TEAL)],
           fieldbackground=[("disabled", "#ecece8")], foreground=[("disabled", GRIS)])
    for nom, fond, texte, actif in (("Start", LIME, ANTHRACITE, "#a9bc09"), ("Stop", ROUGE, "white", "#8f1c12")):
        st.configure(f"{nom}.TButton", background=fond, foreground=texte, font=f(13, True),
                     padding=(16, 11), borderwidth=0, focusthickness=0, focuscolor=fond)
        st.map(f"{nom}.TButton", background=[("disabled", "#dcdcd7"), ("active", actif)],
               foreground=[("disabled", "#a5a5a0")])
    st.configure("Maj.TButton", background=LIME, foreground=ANTHRACITE, font=f(11, True),
                 padding=(14, 6), borderwidth=0, focusthickness=0, focuscolor=LIME)
    st.map("Maj.TButton", background=[("disabled", "#dcdcd7"), ("active", "#a9bc09")],
           foreground=[("disabled", "#a5a5a0")])
    st.configure("Tool.TButton", background=BG, foreground=TEAL, font=f(11),
                 padding=(8, 5), borderwidth=0, focusthickness=0, focuscolor=BG)
    st.map("Tool.TButton", foreground=[("disabled", "#b5b5b0"), ("active", ANTHRACITE)],
           background=[("active", "#ecece8")])
    return f


def titre(parent, texte, f, fond=BG):
    tk.Label(parent, text=texte, bg=fond, fg=TEXTE, font=f(14, True), anchor="w").pack(fill="x")
    tk.Frame(parent, bg=BORD, height=1).pack(fill="x", pady=(4, 10))


def resume_profil(p):
    morceaux = [f"coupure {p['tension_coupure']:g} V"]
    if p["courant"] is not None:
        morceaux.append(f"{p['courant']:g} A")
    if p["puissance"] is not None:
        morceaux.append(f"{p['puissance']:g} W")
    return "  ·  ".join(morceaux)


def duree(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def ouvrir(chemin, reveler=False):
    """Ouvre un fichier/dossier avec l'application du système ; reveler=True l'affiche dans son dossier."""
    try:
        if sys.platform.startswith("win"):
            if reveler and os.path.isfile(chemin):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(chemin)])
            else:
                os.startfile(chemin)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", chemin] if reveler and os.path.isfile(chemin) else ["open", chemin])
        else:
            cible = os.path.dirname(chemin) if reveler and os.path.isfile(chemin) else chemin
            subprocess.Popen(["xdg-open", cible], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        messagebox.showerror("Ouverture impossible", str(e))


class ListeLignes(tk.Frame):
    """Liste de cartes cliquables (titre + détail), avec pastille de sélection et défilement si besoin."""

    def __init__(self, parent, f, hauteur, on_select, vide, radio=True):
        super().__init__(parent, bg=BG)
        self.f, self.on_select, self.texte_vide, self.radio = f, on_select, vide, radio
        self.index, self.actif, self.lignes = -1, True, []
        self.canvas = tk.Canvas(self, bg=BG, height=hauteur, highlightthickness=0)
        self.barre = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.barre.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.interieur = tk.Frame(self.canvas, bg=BG)
        self.fenetre = self.canvas.create_window((0, 0), window=self.interieur, anchor="nw")
        self.interieur.bind("<Configure>", lambda e: self._maj_defilement())
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfigure(self.fenetre, width=e.width),
                                                   self._maj_defilement()))
        self.bind("<Enter>", lambda e: self._molette(True))
        self.bind("<Leave>", lambda e: self._molette(False))

    # -- défilement --
    def _maj_defilement(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.interieur.winfo_reqheight() > self.canvas.winfo_height():
            self.barre.pack(side="right", fill="y", padx=(6, 0))
        else:
            self.barre.pack_forget()
            self.canvas.yview_moveto(0)

    def _molette(self, actif):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if actif:
                self.bind_all(ev, self._roue)
            else:
                self.unbind_all(ev)

    def _roue(self, e):
        if self.interieur.winfo_reqheight() <= self.canvas.winfo_height():
            return
        sens = -1 if (e.num == 4 or e.delta > 0) else 1
        self.canvas.yview_scroll(sens * (1 if sys.platform == "darwin" else 2), "units")

    # -- contenu --
    def remplir(self, items, index):
        """items : liste de (titre, détail)."""
        for w in self.interieur.winfo_children():
            w.destroy()
        self.lignes = []
        if not items:
            tk.Label(self.interieur, text=self.texte_vide, bg=BG, fg=ORANGE, font=self.f(12),
                     justify="left", wraplength=280).pack(padx=4, pady=12, anchor="w")
        for i, (nom, detail) in enumerate(items):
            self._ligne(i, nom, detail)
        self.choisir(index, notifier=False)

    def _ligne(self, i, nom, detail):
        carte = tk.Frame(self.interieur, bg=CARTE, highlightbackground=BORD, highlightcolor=BORD,
                         highlightthickness=2, cursor="hand2")
        carte.pack(fill="x", pady=(0, 8))
        interne = tk.Frame(carte, bg=CARTE)
        interne.pack(fill="x", padx=14, pady=10)
        pastille = None
        if self.radio:
            pastille = tk.Canvas(interne, width=24, height=24, bg=CARTE, highlightthickness=0)
            pastille.pack(side="left", padx=(0, 12))
        texte = tk.Frame(interne, bg=CARTE)
        texte.pack(side="left", fill="x", expand=True)
        lbl_nom = tk.Label(texte, text=nom, bg=CARTE, fg=TEXTE, font=self.f(14, True), anchor="w")
        lbl_nom.pack(fill="x")
        lbl_det = tk.Label(texte, text=detail, bg=CARTE, fg=GRIS, font=self.f(11), anchor="w")
        lbl_det.pack(fill="x")
        fond = [carte, interne, texte, lbl_nom, lbl_det] + ([pastille] if pastille else [])
        for w in fond:
            w.bind("<Button-1>", lambda e, k=i: self.choisir(k))
            w.bind("<Enter>", lambda e, k=i: self._survol(k, True))
            w.bind("<Leave>", lambda e, k=i: self._survol(k, False))
        self.lignes.append((carte, fond, pastille))

    def _survol(self, k, dedans):
        if k >= len(self.lignes) or k == self.index or not self.actif:
            return
        self.lignes[k][0].config(highlightbackground=TEAL if dedans else BORD)

    def choisir(self, i, notifier=True):
        if notifier and not self.actif:
            return
        self.index = i if 0 <= i < len(self.lignes) else -1
        for k, (carte, fond, pastille) in enumerate(self.lignes):
            sel = k == self.index
            couleur = SELECTION if sel else CARTE
            for w in fond:
                w.config(bg=couleur)
            carte.config(highlightbackground=LIME if sel else BORD)
            if pastille:
                pastille.delete("all")
                pastille.create_oval(3, 3, 21, 21, outline=ANTHRACITE if sel else "#b8b8b2", width=2)
                if sel:
                    pastille.create_oval(8, 8, 16, 16, fill=ANTHRACITE, outline=ANTHRACITE)
        if notifier and self.index >= 0:
            self.on_select(self.index)

    def activer(self, actif):
        self.actif = actif
        for carte, _, _ in self.lignes:
            carte.config(cursor="hand2" if actif else "arrow")


def icone(parent, genre, fond, teinte, taille=84):
    """Pictogramme dessiné (batterie / réglages / graphique) dans un disque teinté."""
    c = tk.Canvas(parent, width=taille, height=taille, bg=fond, highlightthickness=0)
    c.create_oval(2, 2, taille - 2, taille - 2, fill=teinte, outline="")
    if genre == "test":  # batterie + éclair
        c.create_rectangle(18, 29, 58, 55, outline=ANTHRACITE, width=3)
        c.create_rectangle(58, 37, 64, 47, fill=ANTHRACITE, outline=ANTHRACITE)
        c.create_polygon(41, 32, 31, 44, 38, 44, 34, 53, 47, 39, 40, 39, 44, 32, fill=ANTHRACITE, outline="")
    elif genre == "profils":  # curseurs de réglage
        for y, x in ((30, 34), (42, 52), (54, 38)):
            c.create_line(21, y, 63, y, fill=TEAL, width=3, capstyle="round")
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill="white", outline=TEAL, width=3)
    elif genre == "resultats":  # histogramme
        for x0, y0 in ((23, 46), (37, 37), (51, 27)):
            c.create_rectangle(x0, y0, x0 + 11, 58, fill=ANTHRACITE, outline="")
        c.create_line(19, 59, 66, 59, fill=ANTHRACITE, width=2)
    else:  # module générique : quatre pièces dont une « branchée »
        for x0, y0, col in ((22, 22, ANTHRACITE), (44, 22, ANTHRACITE), (22, 44, ANTHRACITE), (44, 44, LIME)):
            c.create_rectangle(x0, y0, x0 + 18, y0 + 18, fill=col, outline="")
    return c


def tuile(parent, f, titre_, desc, genre, couleur, teinte, commande, largeur=330, hauteur=330):
    """Grande tuile cliquable (icône, titre, description, ligne d'info, flèche). Renvoie le Label d'info."""
    t = tk.Frame(parent, bg=CARTE, highlightbackground=BORD, highlightcolor=couleur, highlightthickness=2,
                 cursor="hand2", width=largeur, height=hauteur)
    t.pack_propagate(False)
    corps = tk.Frame(t, bg=CARTE)
    corps.pack(fill="both", expand=True, padx=26, pady=24)
    ico = icone(corps, genre, CARTE, teinte)
    ico.pack(anchor="w")
    lbl_t = tk.Label(corps, text=titre_, bg=CARTE, fg=TEXTE, font=f(18, True), anchor="w", justify="left",
                     wraplength=largeur - 70)
    lbl_t.pack(fill="x", pady=(18, 0))
    lbl_d = tk.Label(corps, text=desc, bg=CARTE, fg=GRIS, font=f(12), anchor="w", justify="left",
                     wraplength=largeur - 70)
    lbl_d.pack(fill="x", pady=(8, 0))
    bas = tk.Frame(corps, bg=CARTE)
    bas.pack(side="bottom", fill="x")
    info = tk.Label(bas, text="", bg=CARTE, fg=TEAL, font=f(12, True), anchor="w")
    info.pack(side="left")
    fleche = tk.Label(bas, text="→", bg=CARTE, fg=GRIS, font=f(22, True))
    fleche.pack(side="right")

    def survol(dedans):
        t.config(highlightbackground=couleur if dedans else BORD)
        fleche.config(fg=TEXTE if dedans else GRIS)

    for w in (t, corps, ico, lbl_t, lbl_d, bas, info, fleche):
        w.bind("<Button-1>", lambda e: commande())
        w.bind("<Enter>", lambda e: survol(True))
        w.bind("<Leave>", lambda e: survol(False))
    info.tuile = t  # le conteneur à placer (pack/grid) par l'appelant
    return info


class Interrupteur(tk.Canvas):
    """Interrupteur à glissière (activé = lime). commande(nouvel_etat) est appelée à chaque clic."""

    def __init__(self, parent, actif, commande, fond=CARTE):
        super().__init__(parent, width=56, height=30, bg=fond, highlightthickness=0, cursor="hand2")
        self.actif, self.commande = actif, commande
        self.bind("<Button-1>", lambda e: self.basculer())
        self._dessiner()

    def regler(self, actif):
        self.actif = actif
        self._dessiner()

    def basculer(self):
        self.regler(not self.actif)
        self.commande(self.actif)

    def _dessiner(self):
        self.delete("all")
        couleur = LIME if self.actif else "#cfcfca"
        self.create_oval(2, 2, 30, 28, fill=couleur, outline=couleur)
        self.create_oval(26, 2, 54, 28, fill=couleur, outline=couleur)
        self.create_rectangle(16, 2, 40, 28, fill=couleur, outline=couleur)
        x = 41 if self.actif else 15
        self.create_oval(x - 11, 4, x + 11, 26, fill="white", outline="#b8b8b2" if not self.actif else "#9aab00")


class GraphesTemps(tk.Frame):
    """Un seul graphe pour tension, courant et puissance : un axe gradué (et colorié) par grandeur.

    Pastilles au-dessus pour afficher/masquer chaque courbe ; au survol, les trois valeurs à l'instant visé.
    """

    DEFS = [("V", "Tension", "V", TEAL), ("A", "Courant", "A", "#8a9a00"), ("W", "Puissance", "W", ANTHRACITE)]
    LARGEUR_AXE = 58

    def __init__(self, parent, f, vide="Aucune donnée"):
        super().__init__(parent, bg=BG)
        self.f, self.vide = f, vide
        self.series = {"V": [], "A": [], "W": []}
        self.seuil_v = None
        self.actifs = {k: True for k, *_ in self.DEFS}
        self._ctx = None

        barre = tk.Frame(self, bg=BG)
        barre.pack(fill="x", pady=(0, 6))
        self.pastilles = {}
        for cle, nom, unite, couleur in self.DEFS:
            lbl = tk.Label(barre, text=f"●  {nom} ({unite})", font=f(12, True), padx=14, pady=6, cursor="hand2")
            lbl.pack(side="left", padx=(0, 6))
            lbl.bind("<Button-1>", lambda e, c=cle: self.basculer(c))
            self.pastilles[cle] = lbl
        tk.Label(barre, text="cliquer pour masquer / afficher une courbe", bg=BG, fg=GRIS, font=f(10)).pack(side="left", padx=8)

        self.canvas = tk.Canvas(self, height=60, bg=CARTE, highlightbackground=BORD, highlightthickness=1)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.tracer())
        self.canvas.bind("<Motion>", self._survol)
        self.canvas.bind("<Leave>", lambda e: self.canvas.delete("curseur"))
        self._maj_pastilles()

    # ---------- API ----------
    def definir(self, series, seuil_v=None):
        """series : dict {'V','A','W'} -> liste de (temps_s, valeur) (listes éventuellement complétées ensuite)."""
        self.series, self.seuil_v = series, seuil_v
        self.tracer()

    def basculer(self, cle):
        if self.actifs[cle] and sum(self.actifs.values()) == 1:
            return  # au moins une courbe reste affichée
        self.actifs[cle] = not self.actifs[cle]
        self._maj_pastilles()
        self.tracer()

    def _maj_pastilles(self):
        for cle, nom, unite, couleur in self.DEFS:
            on = self.actifs[cle]
            self.pastilles[cle].config(bg="#eef0e2" if on else "#e4e4df", fg=couleur if on else "#a5a5a0")

    # ---------- tracé ----------
    def tracer(self):
        c = self.canvas
        c.delete("all")
        self._ctx = None
        w, h = c.winfo_width(), c.winfo_height()
        f = self.f
        actifs = [k for k, *_ in self.DEFS if self.actifs[k]]
        gauche = self.LARGEUR_AXE
        droite = 14 + self.LARGEUR_AXE * (len(actifs) - 1)
        haut, bas = 14, 26
        if w < 220 or h < 100:
            return
        v_pts = self.series["V"]
        if len(v_pts) < 2:
            c.create_text(w / 2, h / 2, text=self.vide, fill=GRIS, font=f(12))
            return
        n = len(v_pts)
        pas = n // 2000 + 1  # allège le tracé des très longs tests
        idx = list(range(0, n, pas)) + ([n - 1] if (n - 1) % pas else [])
        ts = [v_pts[i][0] for i in idx]
        t_max = ts[-1] or 1
        vals = {k: [self.series[k][i][1] for i in idx if i < len(self.series[k])] for k in actifs}

        plage = {}
        for k in actifs:
            lo, hi = min(vals[k]), max(vals[k])
            if k == "V" and self.seuil_v is not None:
                lo = min(lo, self.seuil_v)
            marge = max((hi - lo) * 0.12, 0.05)
            plage[k] = (lo - marge, hi + marge)

        larg, haut_plot = w - gauche - droite, h - bas - haut
        px = lambda t: gauche + t / t_max * larg
        py = lambda k, v: (h - bas) - (v - plage[k][0]) / (plage[k][1] - plage[k][0]) * haut_plot
        couleurs = {k: col for k, _, _, col in self.DEFS}

        for j in range(5):  # grille commune + graduations temps
            y = (h - bas) - haut_plot * j / 4
            c.create_line(gauche, y, w - droite, y, fill="#ececE8")
            tt = t_max * j / 4
            c.create_text(px(tt), h - bas + 5, text=time.strftime("%H:%M:%S", time.gmtime(tt)),
                          anchor="n" if j < 4 else "ne", fill=GRIS, font=f(10))
        for rang, k in enumerate(actifs):  # un axe coloré par grandeur : le premier à gauche, les autres à droite
            lo, hi = plage[k]
            dec = 2 if hi - lo < 2 else 1 if hi - lo < 50 else 0
            for j in range(5):
                y = (h - bas) - haut_plot * j / 4
                v = lo + (hi - lo) * j / 4
                if rang == 0:
                    c.create_text(gauche - 6, y, text=f"{v:.{dec}f}", anchor="e", fill=couleurs[k], font=f(10, True))
                else:
                    x = w - droite + 6 + self.LARGEUR_AXE * (rang - 1)
                    c.create_text(x, y, text=f"{v:.{dec}f}", anchor="w", fill=couleurs[k], font=f(10, True))
        if "V" in actifs and self.seuil_v is not None:
            y = py("V", self.seuil_v)
            c.create_line(gauche, y, w - droite, y, fill=ROUGE, dash=(5, 4))
            c.create_text(w - droite - 4, y - 4, text=f"coupure {self.seuil_v:g} V", anchor="se", fill=ROUGE, font=f(10))
        for k in actifs:
            c.create_line(*[xy for t, v in zip(ts, vals[k]) for xy in (px(t), py(k, v))],
                          fill=couleurs[k], width=3, joinstyle="round")
        self._ctx = dict(w=w, h=h, gauche=gauche, droite=droite, haut=haut, bas=bas, ts=ts, t_max=t_max,
                         vals=vals, actifs=actifs, px=px, py=py, couleurs=couleurs, larg=larg)

    # ---------- curseur ----------
    def _survol(self, e):
        c, x = self.canvas, self._ctx
        c.delete("curseur")
        if not x or not (x["gauche"] <= e.x <= x["w"] - x["droite"]):
            return
        t = (e.x - x["gauche"]) / x["larg"] * x["t_max"]
        i = min(bisect.bisect_left(x["ts"], t), len(x["ts"]) - 1)
        if i > 0 and t - x["ts"][i - 1] < x["ts"][i] - t:
            i -= 1
        xc = x["px"](x["ts"][i])
        c.create_line(xc, x["haut"], xc, x["h"] - x["bas"], fill="#9a9a94", dash=(3, 3), tags="curseur")
        lignes = [(time.strftime("%H:%M:%S", time.gmtime(x["ts"][i])), GRIS)]
        unites = {k: u for k, _, u, _ in self.DEFS}
        noms = {k: n for k, n, _, _ in self.DEFS}
        for k in x["actifs"]:
            v = x["vals"][k][i]
            y = x["py"](k, v)
            c.create_oval(xc - 5, y - 5, xc + 5, y + 5, fill=x["couleurs"][k], outline="white", width=2, tags="curseur")
            lignes.append((f"{noms[k]} : {v:.2f} {unites[k]}", x["couleurs"][k]))
        largeur_boite, hauteur_boite = 168, 12 + 20 * len(lignes)
        bx = xc + 14 if xc + 14 + largeur_boite < x["w"] - 6 else xc - 14 - largeur_boite
        by = x["haut"] + 6
        c.create_rectangle(bx, by, bx + largeur_boite, by + hauteur_boite, fill="white", outline=BORD, tags="curseur")
        for k, (texte, col) in enumerate(lignes):
            c.create_text(bx + 10, by + 10 + 20 * k, text=texte, anchor="nw", fill=col,
                          font=self.f(11, k > 0), tags="curseur")
