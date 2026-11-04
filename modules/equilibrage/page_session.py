"""Page « Session d'équilibrage » : suivi supervisé d'une session, enregistrée en CSV, avec arrêt automatique."""
import os
import queue
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import envoi
import theme as T
from theme import BG, BORD, GRIS, ORANGE, ROUGE, TEAL, TEXTE, VERT, GraphesTemps

from .acquisition import Acquisition, CritereFin
from .widgets import BarresCellules, Mesures

ID = "equilibreur_daly"   # instrument utilisé (détecté par l'application)

INTERVALLE_S = 2.0       # une lecture toutes les 2 s : assez fin pour le suivi, fichier raisonnable sur des heures
SILENCE_MAX_S = 120      # l'appareil ne répond plus depuis 2 minutes : la session s'arrête (le CSV est conservé)


def _nombre(texte, nom, minimum=0.0, strict=True):
    try:
        v = float(texte.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"{nom} : entrez un nombre.") from None
    if v < minimum or (strict and v == minimum):
        raise ValueError(f"{nom} : doit être supérieur à {minimum:g}." if strict else f"{nom} : ne peut pas être négatif.")
    return v


class PageSession(tk.Frame):
    def __init__(self, parent, app, mod):
        super().__init__(parent, bg=BG)
        self.app, self.mod = app, mod
        f = app.f
        self.file = queue.Queue()
        self.acq = None
        self.series = {"ecart": [], "vpack": []}
        self.ecart_initial = None
        self.chemin = None
        self._visible = False
        self._dernier_etat_instrument = None

        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        corps.columnconfigure(1, weight=1)
        corps.rowconfigure(0, weight=1)

        # ---- gauche : paramètres + lancement ----
        gauche = tk.Frame(corps, bg=BG, width=330)
        gauche.grid(row=0, column=0, sticky="nsw", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Session d'équilibrage", f)
        self.vars = {"serie": tk.StringVar(), "cible": tk.StringVar(value="10"),
                     "duree": tk.StringVar(value="180"), "stable": tk.StringVar(value="60")}
        self.champs = []
        for cle, texte in (("serie", "N° de série du pack (facultatif)"), ("cible", "Écart cible max - min (mV)"),
                           ("duree", "Durée maximale (minutes)"), ("stable", "Tenir la cible pendant (secondes)")):
            tk.Label(gauche, text=texte, bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x", pady=(8, 2))
            e = ttk.Entry(gauche, textvariable=self.vars[cle], font=f(13))
            e.pack(fill="x")
            e.bind("<Return>", lambda ev: self._demarrer())
            self.champs.append(e)
        self.btn_start = ttk.Button(gauche, text="Lancer la session", style="Start.TButton", command=self._demarrer)
        self.btn_start.pack(fill="x", pady=(18, 0))
        self.btn_stop = ttk.Button(gauche, text="Arrêter la session", style="Stop.TButton", command=self._arreter, state="disabled")
        self.btn_stop.pack(fill="x", pady=(8, 0))
        self.lbl_etat = tk.Label(gauche, text="", bg=BG, fg=GRIS, font=f(12, True), anchor="w", justify="left", wraplength=320)
        self.lbl_etat.pack(fill="x", pady=(12, 0))
        outils = tk.Frame(gauche, bg=BG)
        outils.pack(side="bottom", fill="x")
        tk.Frame(outils, bg=BORD, height=1).pack(fill="x", pady=(0, 6))
        tk.Label(outils, text="L'équilibreur travaille seul : la session surveille les tensions, enregistre un CSV "
                              "et s'arrête dès que l'écart cible est tenu.", bg=BG, fg=GRIS, font=f(10), anchor="w",
                 justify="left", wraplength=320).pack(fill="x", pady=(0, 6))
        ttk.Button(outils, text="Ouvrir le dossier des sessions", style="Tool.TButton", command=self._ouvrir_dossier).pack(anchor="w")

        # ---- droite : mesures, cellules, graphe ----
        droite = tk.Frame(corps, bg=BG)
        droite.grid(row=0, column=1, sticky="nsew")
        self.mesures = Mesures(droite, f, [("ecart", "Écart actuel"), ("initial", "Écart initial"), ("v_pack", "Tension pack"),
                                           ("duree", "Durée"), ("haute", "Plus haute"), ("basse", "Plus basse")], taille=19)
        self.mesures.pack(fill="x")
        tk.Frame(droite, bg=BORD, height=1).pack(fill="x", pady=(8, 8))
        self.barres = BarresCellules(droite, f, hauteur=150)
        self.barres.pack(fill="x")
        tk.Frame(droite, bg=BORD, height=1).pack(fill="x", pady=(8, 8))
        self.graphes = GraphesTemps(droite, f, vide="La courbe d'écart apparaît dès les premières mesures",
                                    defs=[("ecart", "Écart max - min", "mV", ROUGE), ("vpack", "Tension pack", "V", TEAL)],
                                    libelle_seuil="cible")
        self.graphes.pack(fill="both", expand=True)
        self.graphes.definir(self.series)
        self._etat("Prêt.", GRIS)
        self.after(200, self._traiter)

    # ---------- cycle de vie ----------
    def on_show(self):
        self._visible = True
        if not self.occupe():
            self._dernier_etat_instrument = None
            if not self.app.instruments.port(ID):
                self.app.instruments.lancer_detection(ID)  # recherche en arrière-plan : prêt quand l'opérateur a rempli les champs
            self._surveiller_instrument()

    def on_hide(self):
        self._visible = False

    def _surveiller_instrument(self):
        """Affiche l'état de l'équilibreur tant qu'on est sur la page et qu'aucune session ne tourne."""
        if not self._visible or self.occupe():
            return
        inst = self.app.instruments
        etat, texte = inst.statut(ID)
        if (etat, texte) != self._dernier_etat_instrument:
            self._dernier_etat_instrument = (etat, texte)
            couleur = {"ok": VERT, "info": GRIS, "attention": ORANGE, "erreur": ROUGE}[etat]
            self._etat(texte if etat != "attention" else texte + " - ouvrez « Instruments » depuis l'accueil", couleur)
        self.after(700, self._surveiller_instrument)

    def occupe(self):
        """Vrai pendant la session : l'application verrouille la navigation."""
        return self.acq is not None and self.acq.vivant()

    def arreter_et_attendre(self):
        if self.acq:
            self.acq.arreter()
            self.acq.attendre(5)

    def _etat(self, texte, couleur=GRIS):
        self.lbl_etat.config(text=texte, fg=couleur)

    def _mode(self, actif):
        etat = "disabled" if actif else "normal"
        for w in (self.btn_start, self.app.btn_menu, *self.champs):
            w.config(state=etat)
        self.btn_stop.config(state="normal" if actif else "disabled")

    # ---------- session ----------
    def _demarrer(self):
        if self.occupe():
            return
        inst = self.app.instruments
        if inst.en_recherche(ID):
            return messagebox.showinfo("Recherche en cours", "Recherche de l'équilibreur en cours, patientez quelques secondes.")
        port = inst.port_ou_erreur(ID)
        if not port:
            return
        try:
            cible = _nombre(self.vars["cible"].get(), "Écart cible")
            duree = _nombre(self.vars["duree"].get(), "Durée maximale")
            stable = _nombre(self.vars["stable"].get(), "Durée de maintien", 0.0, strict=False)
        except ValueError as e:
            return messagebox.showwarning("Paramètre invalide", str(e))
        serie = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.vars["serie"].get().strip())
        nom = "_".join(x for x in ("equilibrage", serie, f"{datetime.now():%Y%m%d_%H%M%S}") if x)
        self.chemin = os.path.join(self.mod.dossier_sessions(), nom + ".csv")

        for s in self.series.values():
            s.clear()
        self.ecart_initial = None
        self.mesures.effacer()
        self.barres.vider()
        self.graphes.definir(self.series, seuil_v=cible)
        self.file = queue.Queue()
        self.acq = Acquisition(port, self.file, intervalle=INTERVALLE_S, chemin_csv=self.chemin, baud=inst.instrument(ID).baud,
                               critere=CritereFin(cible, stable, duree * 60), silence_max_s=SILENCE_MAX_S)
        self.acq.demarrer()
        self._mode(True)
        self._etat("Session en cours… ne débranchez pas l'équilibreur.", T.BLEU)

    def _arreter(self):
        if self.acq:
            self.acq.arreter()
        self.btn_stop.config(state="disabled")
        self._etat("Arrêt en cours…", ORANGE)

    def _ouvrir_dossier(self):
        T.ouvrir(self.mod.dossier_sessions())

    # ---------- affichage ----------
    def _traiter(self):
        try:
            while True:
                msg = self.file.get_nowait()
                if msg[0] == "donnees":
                    self._donnees(msg[1], msg[2])
                elif msg[0] == "silence":
                    self._etat(f"Pas de réponse de l'appareil ({msg[1]} essais)… la session continue d'essayer.", ORANGE)
                elif msg[0] == "fin":
                    self._fin(msg[1], msg[2])
        except queue.Empty:
            pass
        self.after(250, self._traiter)

    def _donnees(self, t, d):
        m = self.mesures
        ecart = d.get("ecart_mv")
        if ecart is not None:
            if self.ecart_initial is None:
                self.ecart_initial = ecart
                m.regler("initial", f"{ecart:.0f} mV")
            m.regler("ecart", f"{ecart:.0f} mV")
            m.regler("haute", f"{d['v_max']:.3f} V", f"Plus haute · C{d['i_max'] + 1}")
            m.regler("basse", f"{d['v_min']:.3f} V", f"Plus basse · C{d['i_min'] + 1}")
            self.series["ecart"].append((t, ecart))
            if d["v_pack"] is not None:
                self.series["vpack"].append((t, d["v_pack"]))
            self.graphes.tracer()
        m.regler("v_pack", "--" if d["v_pack"] is None else f"{d['v_pack']:.2f} V")
        m.regler("duree", T.duree(t))
        self.barres.definir(d["cellules"], d["equilibrage"])
        self._etat("Session en cours…", T.BLEU)

    def _fin(self, motif, detail):
        self._mode(False)
        envoi.envoyer("equilibrage", self.chemin, motif)
        if motif == "erreur":
            self._etat("Session interrompue sur erreur.", ROUGE)
            return messagebox.showerror("Erreur", detail)
        r = detail
        fin = "--" if r["ecart_final"] is None else f"{r['ecart_final']:.0f} mV"
        debut = "--" if r["ecart_initial"] is None else f"{r['ecart_initial']:.0f} mV"
        bilan = f"écart {debut} → {fin} en {T.duree(r['duree_s'])} · enregistré dans sessions/"
        if motif == "cible":
            self._etat("✔ Écart cible atteint et tenu · " + bilan, VERT)
        elif motif == "duree":
            self._etat("Durée maximale atteinte, écart cible non tenu · " + bilan, ORANGE)
        elif motif == "silence":
            self._etat("Session arrêtée : l'appareil ne répond plus · " + bilan, ROUGE)
        else:
            self._etat("Session arrêtée manuellement · " + bilan, GRIS)
