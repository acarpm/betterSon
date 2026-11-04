"""Interface graphique BatConnect pour la charge EA (Windows / Linux / macOS).

Lancement :  python gui.py
Dépendance : pyserial (tkinter est fourni avec Python).

Pages : accueil (menu), lancer un test, créer/modifier un test (profils), analyser les résultats.
"""
import csv
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import serial

import main as charge  # fonctions de communication avec la charge
import profils
import resultats
import theme as T
import updater
import version
from page_profils import PageProfils
from page_resultats import PageResultats
from theme import (ANTHRACITE, BG, BLEU, BORD, CARTE, GRIS, LIME, ORANGE, ROUGE, TEAL, TEXTE, VERT,
                   GraphesTemps, ListeLignes)


class Accueil(tk.Frame):
    """Menu principal : trois grandes tuiles."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        f = app.f
        centre = tk.Frame(self, bg=BG)
        centre.place(relx=0.5, rely=0.46, anchor="center", relwidth=0.92)
        tk.Label(centre, text="Que souhaitez-vous faire ?", bg=BG, fg=TEXTE, font=f(24, True)).pack(pady=(0, 26))
        grille = tk.Frame(centre, bg=BG)
        grille.pack(fill="x")
        self.infos = {}
        tuiles = [
            ("test", LIME, "Lancer un test", "Choisir un profil et démarrer la décharge de la batterie."),
            ("profils", TEAL, "Créer / modifier un test", "Définir les paramètres d'un type de batterie."),
            ("resultats", ANTHRACITE, "Analyser les résultats", "Consulter les tests passés : capacité, énergie, courbes."),
        ]
        for col, (cible, couleur, titre, desc) in enumerate(tuiles):
            grille.columnconfigure(col, weight=1, uniform="t")
            self.infos[cible] = self._tuile(grille, col, cible, couleur, titre, desc)

    def _tuile(self, parent, col, cible, couleur, titre, desc):
        f = self.app.f
        teinte = {"test": "#eef3c0", "profils": "#dcebf1", "resultats": "#e8e8e5"}[cible]
        t = tk.Frame(parent, bg=CARTE, highlightbackground=BORD, highlightcolor=couleur,
                     highlightthickness=2, cursor="hand2", height=330)
        t.grid(row=0, column=col, sticky="nsew", padx=10)
        t.pack_propagate(False)
        corps = tk.Frame(t, bg=CARTE)
        corps.pack(fill="both", expand=True, padx=26, pady=24)
        ico = T.icone(corps, cible, CARTE, teinte)
        ico.pack(anchor="w")
        lbl_t = tk.Label(corps, text=titre, bg=CARTE, fg=TEXTE, font=f(18, True), anchor="w",
                         justify="left", wraplength=260)
        lbl_t.pack(fill="x", pady=(18, 0))
        lbl_d = tk.Label(corps, text=desc, bg=CARTE, fg=GRIS, font=f(12), anchor="w", justify="left",
                         wraplength=260)
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
            w.bind("<Button-1>", lambda e: self.app.aller(cible))
            w.bind("<Enter>", lambda e: survol(True))
            w.bind("<Leave>", lambda e: survol(False))
        return info

    def on_show(self):
        a = self.app
        n = len(a.profils)
        self.infos["test"].config(text=f"Profil : {a.dernier}" if a.dernier else
                                  ("Choisissez un profil" if n else "Créez d'abord un profil"))
        self.infos["profils"].config(text=f"{n} profil{'s' if n > 1 else ''} enregistré{'s' if n > 1 else ''}")
        k = len(resultats.lister(T.DOSSIER_CSV))
        self.infos["resultats"].config(text=f"{k} test{'s' if k > 1 else ''} enregistré{'s' if k > 1 else ''}")


def _propre(texte):
    """Nettoie un texte pour un nom de fichier."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in texte.strip())


class PageLancer(tk.Frame):
    """Sélection du profil + préparation du test (puis bascule sur la page « test en cours »)."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
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
                                    command=lambda: app.aller("profils"))
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
        noms = [p["nom"] for p in self.app.profils]
        i = noms.index(self.app.dernier) if self.app.dernier in noms else (0 if noms else -1)
        self.liste.remplir([(p["nom"], T.resume_profil(p)) for p in self.app.profils], i)
        self._resume()

    # ---------- profils ----------
    def _profil_courant(self):
        i = self.liste.index
        return self.app.profils[i] if 0 <= i < len(self.app.profils) else None

    def _profil_choisi(self, i):
        self.app.dernier = self.app.profils[i]["nom"]
        profils.sauver(T.FICHIER_PROFILS, self.app.profils, self.app.dernier)  # retient le dernier profil
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
        port = self.app.port_ou_erreur()
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
        port = self.app.port_ou_erreur()
        if not port:
            return
        serie = self.var_serie.get().strip()
        nom = "_".join(x for x in (_propre(p["nom"]), _propre(serie)) if x) or "batterie"
        os.makedirs(T.DOSSIER_CSV, exist_ok=True)
        chemin = os.path.join(T.DOSSIER_CSV, f"{nom}_{datetime.now():%Y%m%d_%H%M%S}.csv")
        self.app.pages["encours"].demarrer(p, serie, port, chemin)
        self.var_serie.set("")  # prêt pour la batterie suivante
        self.app.aller("encours")


class PageEnCours(tk.Frame):
    """Test en cours : mesures en direct, courbe, arrêt. Affiche le bilan à la fin."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        f = app.f
        self.file = queue.Queue()  # messages du thread de test -> interface
        self.stop_evt = threading.Event()
        self.thread = None
        self.series = {"V": [], "A": [], "W": []}  # (temps_s, valeur) pour les graphes
        self.dernier_csv = None

        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))

        # bandeau : profil + état  |  boutons
        haut = tk.Frame(corps, bg=BG)
        haut.pack(fill="x")
        self.zone_btn = tk.Frame(haut, bg=BG)
        self.zone_btn.pack(side="right", padx=(20, 0))
        self.btn_stop = ttk.Button(self.zone_btn, text="Arrêter le test", style="Stop.TButton", command=self._arreter)
        self.btn_nouveau = ttk.Button(self.zone_btn, text="Nouveau test", style="Start.TButton",
                                      command=lambda: app.aller("test"))
        self.btn_analyse = ttk.Button(self.zone_btn, text="Voir dans l'analyse", style="Tool.TButton",
                                      command=self._voir_analyse)
        textes = tk.Frame(haut, bg=BG)
        textes.pack(side="left", fill="x", expand=True)
        self.lbl_profil = tk.Label(textes, text="", bg=BG, fg=TEXTE, font=f(22, True), anchor="w")
        self.lbl_profil.pack(fill="x")
        self.lbl_detail = tk.Label(textes, text="", bg=BG, fg=GRIS, font=f(12), anchor="w")
        self.lbl_detail.pack(fill="x")
        self.lbl_etat = tk.Label(textes, text="", bg=BG, fg=GRIS, font=f(14, True), anchor="w")
        self.lbl_etat.pack(fill="x", pady=(6, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(12, 12))

        # mesures en direct
        grille = tk.Frame(corps, bg=BG)
        grille.pack(fill="x")
        self.vals = {}
        mesures = [("V", "Tension"), ("A", "Courant"), ("W", "Puissance"),
                   ("Ah", "Capacité"), ("Wh", "Énergie"), ("t", "Durée")]
        for col, (cle, titre) in enumerate(mesures):
            grille.columnconfigure(col, weight=1, uniform="m")
            bloc = tk.Frame(grille, bg=BG)
            bloc.grid(row=0, column=col, sticky="w")
            tk.Label(bloc, text=titre, bg=BG, fg=GRIS, font=f(11)).pack(anchor="w")
            lbl = tk.Label(bloc, text="--", bg=BG, fg=TEXTE, font=f(30 if cle == "V" else 22, True))
            lbl.pack(anchor="w")
            self.vals[cle] = lbl

        tk.Label(corps, text="Évolution au cours du temps", bg=BG, fg=TEXTE, font=f(14, True),
                 anchor="w").pack(fill="x", pady=(14, 0))
        tk.Frame(corps, bg=BORD, height=1).pack(fill="x", pady=(4, 8))
        self.graphes = GraphesTemps(corps, f, vide="Les courbes apparaissent dès les premières mesures")
        self.graphes.pack(fill="both", expand=True)
        self.graphes.definir(self.series)

        self.after(200, self._traiter_file)

    def on_show(self):
        pass  # l'état est mis en place par demarrer()

    def _etat(self, texte, couleur=GRIS):
        self.lbl_etat.config(text=texte, fg=couleur)

    def en_test(self):
        return self.thread is not None and self.thread.is_alive()

    def _boutons(self, mode):
        for w in self.zone_btn.winfo_children():
            w.pack_forget()
        if mode == "test":
            self.btn_stop.config(state="normal")
            self.btn_stop.pack()
        else:
            self.btn_nouveau.pack(side="left")
            self.btn_analyse.pack(side="left", padx=(10, 0))
        self.app.btn_menu.config(state="disabled" if mode == "test" else "normal")

    # ---------- test ----------
    def demarrer(self, p, serie, port, chemin):
        if self.en_test():
            return
        for serie in self.series.values():
            serie.clear()
        for lbl in self.vals.values():
            lbl.config(text="--")
        self.lbl_profil.config(text=p["nom"])
        morceaux = [f"N° de série : {serie}"] if serie else []
        morceaux.append(T.resume_profil(p))
        self.lbl_detail.config(text="   ·   ".join(morceaux))
        self.graphes.definir(self.series, seuil_v=p["tension_coupure"])
        self.dernier_csv = chemin
        self.stop_evt.clear()
        self._boutons("test")
        self._etat("Test en cours… ne débranchez pas la batterie.", BLEU)
        self.thread = threading.Thread(
            target=self._test, args=(port, chemin, p["tension_coupure"], p["courant"], p["puissance"]), daemon=True)
        self.thread.start()

    def _arreter(self):
        self.stop_evt.set()
        self.btn_stop.config(state="disabled")
        self._etat("Arrêt en cours…", ORANGE)

    def arreter_et_attendre(self):
        self.stop_evt.set()
        if self.thread:
            self.thread.join(timeout=5)  # laisse le temps de couper l'entrée de la charge

    def _test(self, port, chemin, v_cut, courant, puissance):
        """Thread de test : seul à parler à la charge pendant toute sa durée."""
        q = self.file
        try:
            with serial.Serial(port, 115200, timeout=1) as s:
                if not charge.verrou(s, True):
                    q.put(("fin", "erreur", "La charge n'est pas passée en mode distant."))
                    return
                try:
                    charge.regler_charge(s, None, courant, puissance)
                    ah = wh = 0.0
                    with open(chemin, "w", newline="") as f:
                        ecr = csv.writer(f)
                        ecr.writerow(["temps_s", "V", "A", "W", "Ah", "Wh"])
                        if not charge.entree(s, True):
                            q.put(("fin", "erreur", "La charge n'a pas activé son entrée."))
                            return
                        t0 = t_prec = time.monotonic()
                        motif = "stop"
                        try:
                            while not self.stop_evt.is_set():
                                v, i, p = charge.lire_valeurs(s, 1, 1, 1)
                                t = time.monotonic()
                                dt, t_prec = t - t_prec, t
                                ah += i * dt / 3600
                                wh += p * dt / 3600
                                ecr.writerow([f"{t - t0:.1f}", v, i, p, f"{ah:.4f}", f"{wh:.4f}"])
                                f.flush()
                                q.put(("mesure", t - t0, v, i, p, ah, wh))
                                if v < v_cut:
                                    motif = "coupure"
                                    break
                                self.stop_evt.wait(charge.INTERVALLE_S)
                        finally:
                            charge.entree(s, False)  # toujours couper l'entrée
                    q.put(("fin", motif, (ah, wh)))
                finally:
                    charge.verrou(s, False)  # rend la main à la face avant
        except (serial.SerialException, OSError, ValueError) as e:
            q.put(("fin", "erreur", f"Communication perdue : {e}"))

    def _traiter_file(self):
        try:
            while True:
                msg = self.file.get_nowait()
                if msg[0] == "mesure":
                    _, t, v, i, p, ah, wh = msg
                    self.vals["V"].config(text=f"{v:.2f} V")
                    self.vals["A"].config(text=f"{i:.2f} A")
                    self.vals["W"].config(text=f"{p:.1f} W")
                    self.vals["Ah"].config(text=f"{ah:.3f} Ah")
                    self.vals["Wh"].config(text=f"{wh:.3f} Wh")
                    self.vals["t"].config(text=time.strftime("%H:%M:%S", time.gmtime(t)))
                    self.series["V"].append((t, v))
                    self.series["A"].append((t, i))
                    self.series["W"].append((t, p))
                    self.graphes.tracer()
                else:
                    self._fin_test(msg[1], msg[2])
        except queue.Empty:
            pass
        self.after(200, self._traiter_file)

    def _fin_test(self, motif, detail):
        self._boutons("fin")
        if motif == "erreur":
            self._etat("Test interrompu sur erreur - vérifiez la charge.", ROUGE)
            messagebox.showerror("Erreur", f"{detail}\n\nL'entrée de la charge a été coupée (vérifiez-le sur la charge).")
            return
        ah, wh = detail
        raison = "Tension de coupure atteinte" if motif == "coupure" else "Arrêt manuel"
        self._etat(f"✔ {raison} · {ah:.3f} Ah · {wh:.2f} Wh · enregistré dans mesures/", VERT)

    def _voir_analyse(self):
        self.app.pages["resultats"].a_selectionner = self.dernier_csv
        self.app.aller("resultats")


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BatConnect - Test de batterie")
        self.configure(bg=BG)
        self.geometry("1100x760")
        self.minsize(960, 720)
        self.f = T.init_styles(self)
        self.profils, self.dernier = profils.charger(T.FICHIER_PROFILS)
        self.port = None
        self._maj_file = queue.Queue()  # messages du thread de mise à jour -> interface
        self._maj_info = None
        self._maj_en_cours = False

        self._entete()
        zone = tk.Frame(self, bg=BG)
        zone.pack(fill="both", expand=True)
        self.pages = {"accueil": Accueil(zone, self), "test": PageLancer(zone, self),
                      "encours": PageEnCours(zone, self),
                      "profils": PageProfils(zone, self), "resultats": PageResultats(zone, self)}
        self.courante = None
        self.aller("accueil")
        self._rafraichir_port()
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        updater.nettoyer()  # supprime l'ancienne version laissée par la dernière mise à jour
        self.after(2500, self._verifier_maj)
        self.after(500, self._traiter_maj)

    def _entete(self):
        tete = tk.Frame(self, bg=CARTE)
        tete.pack(fill="x")
        try:
            self.logo = tk.PhotoImage(file=os.path.join(T.RES, "assets", "logo.png"))
            lbl = tk.Label(tete, image=self.logo, bg=CARTE, cursor="hand2")
            lbl.pack(side="left", padx=(24, 0), pady=6)
        except tk.TclError:
            lbl = tk.Label(tete, text="BATCONNECT", bg=CARTE, fg=ANTHRACITE, font=self.f(20, True), cursor="hand2")
            lbl.pack(side="left", padx=24, pady=14)
        lbl.bind("<Button-1>", lambda e: self.aller("accueil"))  # clic sur le logo = retour au menu
        tk.Label(tete, text=f"v{version.__version__}", bg=CARTE, fg="#a5a5a0", font=self.f(10)).pack(
            side="right", padx=(0, 20))
        self.lbl_port = tk.Label(tete, text="Recherche de la charge…", bg=CARTE, fg=GRIS, font=self.f(12, True))
        self.lbl_port.pack(side="right", padx=(24, 12))
        self.btn_menu = ttk.Button(tete, text="←  Menu", style="Tool.TButton", command=lambda: self.aller("accueil"), takefocus=False)
        self.filet = tk.Frame(self, bg=LIME, height=4)
        self.filet.pack(fill="x")

        # bannière de mise à jour (masquée tant qu'aucune nouvelle version n'est détectée)
        self.banniere = tk.Frame(self, bg="#fbf6d5")
        self.lbl_maj = tk.Label(self.banniere, text="", bg="#fbf6d5", fg=TEXTE, font=self.f(12, True), anchor="w")
        self.lbl_maj.pack(side="left", padx=(24, 12), pady=8)
        self.btn_plus_tard = ttk.Button(self.banniere, text="Plus tard", style="Tool.TButton",
                                        command=self.banniere.pack_forget)
        self.btn_plus_tard.pack(side="right", padx=(0, 20))
        self.btn_maj = ttk.Button(self.banniere, text="Mettre à jour maintenant", style="Maj.TButton",
                                  command=self._installer_maj)
        self.btn_maj.pack(side="right", padx=8)

    # ---------- mises à jour ----------
    def _verifier_maj(self):
        """Interroge GitHub en tâche de fond (jamais bloquant) ; se répète toutes les 2 h."""
        if updater.installe() and version.__version__ != "dev" and not self._maj_en_cours:
            threading.Thread(target=lambda: self._maj_file.put(("info", updater.derniere_version())),
                             daemon=True).start()
        self.after(2 * 3600 * 1000, self._verifier_maj)

    def _traiter_maj(self):
        try:
            while True:
                msg = self._maj_file.get_nowait()
                if msg[0] == "info":
                    if updater.plus_recente(msg[1]) and not self._maj_en_cours:
                        self._maj_info = msg[1]
                        self.lbl_maj.config(text=f"Nouvelle version {msg[1]['tag']} disponible "
                                                 f"(installée : v{version.__version__})")
                        self.btn_maj.config(state="normal", text="Mettre à jour maintenant")
                        self.btn_plus_tard.config(state="normal")
                        self.banniere.pack(fill="x", after=self.filet)
                elif msg[0] == "progression":
                    fait, total = msg[1], msg[2]
                    self.lbl_maj.config(text="Téléchargement de la mise à jour… "
                                             + (f"{fait * 100 // total} %" if total else f"{fait // 1024} Ko"))
                elif msg[0] == "pret":
                    self._maj_pret(msg[1])
                elif msg[0] == "erreur":
                    self._maj_en_cours = False
                    self.lbl_maj.config(text="Mise à jour impossible : " + msg[1])
                    self.btn_maj.config(state="normal", text="Réessayer")
                    self.btn_plus_tard.config(state="normal")
        except queue.Empty:
            pass
        self.after(300, self._traiter_maj)

    def _installer_maj(self):
        if self.en_test():
            return messagebox.showinfo("Test en cours", "Terminez le test en cours avant de mettre à jour.")
        info = self._maj_info
        if not info or self._maj_en_cours:
            return
        self._maj_en_cours = True
        self.btn_maj.config(state="disabled")
        self.btn_plus_tard.config(state="disabled")
        self.lbl_maj.config(text="Téléchargement de la mise à jour… 0 %")

        def tache():
            try:
                fichier = updater.telecharger(info, lambda a, t: self._maj_file.put(("progression", a, t)))
                self._maj_file.put(("pret", updater.appliquer(fichier)))
            except updater.ErreurMaj as e:
                self._maj_file.put(("erreur", str(e)))
            except Exception as e:  # noqa: BLE001 - jamais de plantage silencieux du thread
                self._maj_file.put(("erreur", f"erreur inattendue ({e})"))
        threading.Thread(target=tache, daemon=True).start()

    def _maj_pret(self, chemin):
        if self.en_test():  # un test a été lancé entre-temps : on ne coupe surtout pas le programme
            self.lbl_maj.config(text="Mise à jour installée : elle sera active au prochain démarrage du logiciel.")
            return
        self.lbl_maj.config(text="Mise à jour installée, redémarrage…")
        self.update_idletasks()
        updater.relancer(chemin)
        self.destroy()

    def aller(self, nom):
        if self.en_test() and nom != "encours":
            return  # pas de changement de page pendant un test
        if self.courante:
            self.pages[self.courante].pack_forget()
        self.courante = nom
        page = self.pages[nom]
        page.pack(fill="both", expand=True)
        page.on_show()
        if nom == "accueil":
            self.btn_menu.pack_forget()
        else:
            self.btn_menu.pack(side="right", padx=(0, 12))

    def en_test(self):
        return self.pages["encours"].en_test() if "encours" in getattr(self, "pages", {}) else False

    def _rafraichir_port(self):
        if not self.en_test():
            ports = charge.trouver_ports()
            if ports:
                self.lbl_port.config(text="● Charge connectée", fg=VERT)
            else:
                self.lbl_port.config(text="● Charge non détectée - vérifiez le câble USB", fg=ROUGE)
            self.port = ports[0] if ports else None
        self.after(2000, self._rafraichir_port)

    def port_ou_erreur(self):
        self.port = (charge.trouver_ports() or [None])[0]
        if not self.port:
            messagebox.showerror("Charge introuvable",
                                 "Aucune charge EA détectée.\nBranchez le câble USB et allumez la charge.")
        return self.port

    def _fermer(self):
        if self.en_test():
            if not messagebox.askyesno("Test en cours", "Un test est en cours. L'arrêter et quitter ?"):
                return
            self.pages["encours"].arreter_et_attendre()
        self.destroy()


if __name__ == "__main__":
    Application().mainloop()
