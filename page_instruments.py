"""Page « Instruments » : appareils série connus de l'application, détection automatique, choix manuel et test."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import theme as T
from theme import BG, BORD, GRIS, ORANGE, ROUGE, TEXTE, VERT, ListeLignes

COULEURS = {"ok": VERT, "info": GRIS, "attention": ORANGE, "erreur": ROUGE}


def _decrire(infos):
    """Texte lisible pour le résultat d'un test de liaison."""
    if "identite" in infos:
        return infos["identite"]
    morceaux = []
    if infos.get("cellules"):
        morceaux.append(f"{infos['cellules']} cellules")
    if infos.get("v_pack") is not None:
        morceaux.append(f"pack {infos['v_pack']:.1f} V")
    if infos.get("ecart_mv") is not None:
        morceaux.append(f"écart {infos['ecart_mv']:.0f} mV")
    return ", ".join(morceaux) or "répond"


class PageInstruments(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.gest = app.instruments
        f = app.f
        self.ids = list(self.gest.registre)
        self.idx = 0
        self.ports = []
        self._visible = False
        self._signature = None
        self.file = queue.Queue()  # résultats des tests (thread -> interface)

        corps = tk.Frame(self, bg=BG)
        corps.pack(fill="both", expand=True, padx=28, pady=(18, 16))
        gauche = tk.Frame(corps, bg=BG, width=380)
        gauche.pack(side="left", fill="y", padx=(0, 30))
        gauche.pack_propagate(False)
        T.titre(gauche, "Appareils", f)
        self.liste_inst = ListeLignes(gauche, f, hauteur=200, radio=False, on_select=self._choisir_instrument,
                                      vide="Aucun appareil déclaré.")
        self.liste_inst.pack(fill="both", expand=True)

        droite = tk.Frame(corps, bg=BG)
        droite.pack(side="left", fill="both", expand=True)
        self.lbl_nom = tk.Label(droite, text="", bg=BG, fg=TEXTE, font=f(20, True), anchor="w")
        self.lbl_nom.pack(fill="x")
        self.lbl_desc = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(11), anchor="w", justify="left", wraplength=560)
        self.lbl_desc.pack(fill="x", pady=(2, 0))
        self.lbl_etat = tk.Label(droite, text="", bg=BG, font=f(13, True), anchor="w")
        self.lbl_etat.pack(fill="x", pady=(10, 4))
        tk.Frame(droite, bg=BORD, height=1).pack(fill="x", pady=(0, 8))
        tk.Label(droite, text="Port utilisé", bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x", pady=(0, 4))
        self.liste_ports = ListeLignes(droite, f, hauteur=150, on_select=self._choisir_port, vide="Aucun port série détecté.")
        self.liste_ports.pack(fill="both", expand=True)
        boutons = tk.Frame(droite, bg=BG)
        boutons.pack(fill="x", pady=(10, 0))
        self.btn_test = ttk.Button(boutons, text="Tester la connexion", style="Start.TButton", command=self._tester)
        self.btn_test.pack(side="left")
        self.btn_rech = ttk.Button(boutons, text="Rechercher automatiquement", style="Tool.TButton", command=self._rechercher)
        self.btn_rech.pack(side="left", padx=10)
        self.lbl_res = tk.Label(droite, text="", bg=BG, fg=GRIS, font=f(12, True), anchor="w", justify="left", wraplength=560)
        self.lbl_res.pack(fill="x", pady=(10, 0))

    # ---------- cycle de vie ----------
    def on_show(self):
        self._visible = True
        self._signature = None
        self.lbl_res.config(text="")
        self._boucle()

    def on_hide(self):
        self._visible = False

    def _courant(self):
        return self.ids[self.idx]

    def _boucle(self):
        """Rafraîchit périodiquement tant que la page est affichée."""
        if not self._visible:
            return
        self._rafraichir()
        self.after(500, self._boucle)

    def _rafraichir(self):
        """Met l'affichage à jour (ne reconstruit les listes que si quelque chose a changé)."""
        if not self._visible:
            return
        self.gest.ports(age_max=1.0)
        sig = (tuple(self.gest.statut(i) for i in self.ids), tuple(p.device for p in self.gest.candidats(self._courant())),
               self.gest.manuel(self._courant()), self.idx)
        if sig != self._signature:
            self._signature = sig
            self._actualiser()
        try:
            while True:
                ok, texte = self.file.get_nowait()
                self.lbl_res.config(text=("✔ " if ok else "") + texte, fg=VERT if ok else ROUGE)
                self.btn_test.config(state="normal")
        except queue.Empty:
            pass

    # ---------- affichage ----------
    def _actualiser(self):
        g = self.gest
        items = [(g.instrument(i).nom, g.statut(i)[1]) for i in self.ids]
        self.liste_inst.remplir(items, self.idx)
        inst, id_ = g.instrument(self._courant()), self._courant()
        self.lbl_nom.config(text=inst.nom)
        self.lbl_desc.config(text=inst.description)
        etat, texte = g.statut(id_)
        origine = {"manuel": "choix manuel", "memorise": "détecté et mémorisé", "auto": "détection automatique"}.get(g.origine(id_), "")
        self.lbl_etat.config(text="● " + texte + (f"  ({origine})" if origine else ""), fg=COULEURS[etat])

        self.ports = list(g.candidats(id_))
        manuel = g.manuel(id_)
        lignes = [("Automatique", "Recommandé : le logiciel trouve le port tout seul et le mémorise")]
        lignes += [(p.device, (p.description or "") + (f"  ·  n° de série {p.serial_number}" if p.serial_number else ""))
                   for p in self.ports]
        devices = [p.device for p in self.ports]
        if manuel and manuel not in devices:
            lignes.append((manuel, "absent : branchez l'appareil ou repassez en automatique"))
            devices.append(manuel)
        self._devices = devices
        self.liste_ports.remplir(lignes, devices.index(manuel) + 1 if manuel else 0)
        self.btn_test.config(state="normal" if g.port(id_) else "disabled")
        self.btn_rech.config(text="Rechercher automatiquement" if not inst.identification_directe else "Actualiser")

    def _choisir_instrument(self, i):
        self.idx = i
        self.lbl_res.config(text="")
        self._signature = None
        self.after(10, self._rafraichir)

    def _choisir_port(self, i):
        id_ = self._courant()
        self.gest.choisir(id_, None if i == 0 else self._devices[i - 1])
        self.lbl_res.config(text="")
        self._signature = None
        if i == 0 and not self.gest.instrument(id_).identification_directe:
            self.gest.lancer_detection(id_)  # retour en automatique : on relance la recherche
        self.after(10, self._rafraichir)  # (après la fin du clic : la liste cliquée est reconstruite)

    # ---------- actions ----------
    def _rechercher(self):
        id_ = self._courant()
        self.gest.choisir(id_, None)  # « automatiquement » : on abandonne un éventuel choix manuel
        self.gest.ports(age_max=0)
        if not self.gest.instrument(id_).identification_directe:
            self.gest.lancer_detection(id_)
        self.lbl_res.config(text="Recherche en cours…" if not self.gest.instrument(id_).identification_directe else "", fg=GRIS)
        self._signature = None
        self.after(10, self._rafraichir)

    def _tester(self):
        id_ = self._courant()
        self.btn_test.config(state="disabled")
        self.lbl_res.config(text="Test en cours…", fg=GRIS)

        def tache():
            ok, infos = self.gest.tester(id_)
            self.file.put((ok, _decrire(infos) if ok else infos))

        threading.Thread(target=tache, daemon=True).start()
