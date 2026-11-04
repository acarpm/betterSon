"""Page « Test en cours » : mesures en direct, graphe, arrêt, bilan final."""
import csv
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import serial

import main as charge  # communication avec la charge EA
import theme as T
from theme import BG, BLEU, BORD, GRIS, ORANGE, ROUGE, TEXTE, VERT, GraphesTemps


class PageEnCours(tk.Frame):
    """Test en cours : mesures en direct, courbe, arrêt. Affiche le bilan à la fin."""

    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app = app
        self.mod = mod
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
                                      command=lambda: app.aller("decharge.lancer"))
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

    def occupe(self):
        """Vrai tant qu'un test tourne : l'application verrouille alors la navigation."""
        return self.en_test()

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
        self.app.page("decharge.resultats").a_selectionner = self.dernier_csv
        self.app.aller("decharge.resultats")
