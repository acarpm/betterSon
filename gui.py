"""BetterSon : coque de l'application (navigation, mises à jour) qui charge des modules activables.

Lancement :  python gui.py
Dépendance : pyserial (tkinter est fourni avec Python).

Les fonctionnalités vivent dans des modules (paquet `modules/`) ; voir modules/__init__.py pour en ajouter.
"""
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import config
import dialogue_identite
import envoi
import identite
import synchro
import modules
import theme as T
import updater
import version
from instruments import TOUS as INSTRUMENTS
from instruments import Gestionnaire
from page_accueil import Accueil, PageModule
from page_instruments import PageInstruments
from page_modules import PageModules
from theme import ANTHRACITE, BG, CARTE, GRIS, LIME, ORANGE, ROUGE, TEXTE, VERT

COULEURS_ETAT = {"ok": VERT, "info": GRIS, "attention": ORANGE, "erreur": ROUGE}
GRAVITE = ["ok", "info", "attention", "erreur"]   # du moins au plus grave : la barre d'état prend la couleur du pire


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BetterSon - Test de batterie")
        self.configure(bg=BG)
        self.geometry("1100x760")
        self.minsize(960, 720)
        self.f = T.init_styles(self)
        self.modules = {m.id: m for m in modules.TOUS}
        self.instruments = Gestionnaire(INSTRUMENTS)   # détection et attribution des ports série, pour tous les modules
        self.pages = {}        # créées à la demande : un module jamais ouvert ne coûte rien
        self.courante = None
        self._maj_file = queue.Queue()  # messages du thread de mise à jour -> interface
        self._maj_info = None
        self._maj_en_cours = False

        self._entete()
        self.zone = tk.Frame(self, bg=BG)
        self.zone.pack(fill="both", expand=True)
        self._maj_poste()
        self.aller("accueil")
        self._rafraichir_statut()
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        updater.nettoyer()  # supprime l'ancienne version laissée par la dernière mise à jour
        self.after(2500, self._verifier_maj)
        self.after(500, self._traiter_maj)
        synchro.lancer(force=True)  # annuaire des techniciens : copie locale mise à jour dès que le serveur répond
        if not identite.poste():
            self.after(100, self._premier_lancement)  # une fois la fenêtre affichée

    # ---------- en-tête ----------
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
        lbl.bind("<Button-1>", lambda e: self.aller("accueil"))  # clic sur le logo = retour à l'accueil
        self.lbl_version = tk.Label(tete, text=f"v{version.__version__}", bg=CARTE, fg="#a5a5a0", font=self.f(10), cursor="hand2")
        self.lbl_version.pack(side="right", padx=(0, 20))
        self.lbl_version.bind("<Button-1>", lambda e: self._lancer_verification(manuel=True))  # clic = vérifier maintenant
        self.btn_poste = ttk.Button(tete, text="", style="Tool.TButton", command=self.changer_poste, takefocus=False)
        self.btn_poste.pack(side="right", padx=(0, 4))
        self.lbl_statut = tk.Label(tete, text="", bg=CARTE, fg=GRIS, font=self.f(12, True))
        self.lbl_statut.pack(side="right", padx=(24, 12))
        self.btn_menu = ttk.Button(tete, text="←  Retour", style="Tool.TButton", command=self.retour, takefocus=False)
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

    # ---------- poste ----------
    def _maj_poste(self):
        self.btn_poste.config(text=f"Poste : {identite.poste() or 'à renseigner'}")

    def _premier_lancement(self):
        """Premier démarrage : l'identifiant du poste est obligatoire, fermer la fenêtre quitte le logiciel."""
        if not dialogue_identite.demander_poste(self, self.f, obligatoire=True):
            return self.destroy()
        self._maj_poste()
        synchro.lancer(force=True)

    def changer_poste(self):
        if dialogue_identite.demander_poste(self, self.f, obligatoire=False):
            self._maj_poste()
            synchro.lancer(force=True)

    # ---------- mises à jour ----------
    def _etat_version(self, texte="", couleur="#a5a5a0"):
        """Numéro de version en en-tête, suivi de l'état des mises à jour."""
        self.lbl_version.config(text=f"v{version.__version__}" + (f" · {texte}" if texte else ""), fg=couleur)

    def _lancer_verification(self, manuel=False):
        """Interroge GitHub en tâche de fond (jamais bloquant). manuel : clic de l'opérateur -> résultat toujours expliqué."""
        if self._maj_en_cours:
            return
        if version.__version__ == "dev" or not updater.installe():
            if manuel:
                messagebox.showinfo("Mises à jour", "Version de développement : les mises à jour automatiques "
                                                    "ne concernent que le logiciel installé.")
            return
        if manuel:
            self._etat_version("vérification…", GRIS)
        threading.Thread(target=lambda: self._maj_file.put(("verif", *updater.verifier(), manuel)), daemon=True).start()

    def _verifier_maj(self):
        """Vérification automatique : au démarrage, puis toutes les 2 h."""
        self._lancer_verification()
        self.after(2 * 3600 * 1000, self._verifier_maj)

    def _resultat_verification(self, info, erreur, manuel):
        if erreur:  # jamais d'échec silencieux : visible en en-tête, détaillé si l'opérateur a cliqué
            self._etat_version("mises à jour : vérification impossible (cliquer pour réessayer)", ORANGE)
            if manuel:
                messagebox.showwarning("Mises à jour", f"Impossible de vérifier les mises à jour :\n{erreur}")
            return
        if updater.plus_recente(info) and not self._maj_en_cours:
            self._maj_info = info
            self._etat_version("mise à jour disponible", ORANGE)
            self.lbl_maj.config(text=f"Nouvelle version {info['tag']} disponible (installée : v{version.__version__})")
            self.btn_maj.config(state="normal", text="Mettre à jour maintenant")
            self.btn_plus_tard.config(state="normal")
            self.banniere.pack(fill="x", after=self.filet)
            return
        self._etat_version("à jour")
        if manuel:
            if info["version"] > updater._numeros(version.__version__):  # plus récente, mais inutilisable ici
                manquants = [n for n in (updater.ASSETS[updater.systeme()], updater.SOMMES) if n not in info["assets"]]
                messagebox.showwarning("Mises à jour", f"La version {info['tag']} existe mais ne contient pas les fichiers "
                                                       f"nécessaires pour ce poste ({', '.join(manquants)}).")
            else:
                messagebox.showinfo("Mises à jour", f"Vous avez la dernière version (v{version.__version__}).")

    def _traiter_maj(self):
        try:
            while True:
                msg = self._maj_file.get_nowait()
                if msg[0] == "verif":
                    self._resultat_verification(msg[1], msg[2], msg[3])
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
        if self.occupe():
            return messagebox.showinfo("Opération en cours", "Terminez l'opération en cours avant de mettre à jour.")
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
        if self.occupe():  # une opération a démarré entre-temps : on ne coupe surtout pas le programme
            self.lbl_maj.config(text="Mise à jour installée : elle sera active au prochain démarrage du logiciel.")
            return
        try:
            ailleurs = os.path.abspath(chemin) != os.path.abspath(updater._chemin_actuel())
        except updater.ErreurMaj:
            ailleurs = False
        self.lbl_maj.config(text="Mise à jour installée dans « Applications » de votre dossier personnel, redémarrage…"
                            if ailleurs else "Mise à jour installée, redémarrage…")
        self.update_idletasks()
        updater.relancer(chemin)
        self.destroy()

    # ---------- modules et navigation ----------
    def module_actif(self, module_id):
        return config.module_actif(module_id, self.modules[module_id].actif_par_defaut)

    def modules_actifs(self):
        return [m for m in modules.TOUS if self.module_actif(m.id)]

    @staticmethod
    def module_de(page_id):
        """Identifiant du module auquel appartient une page ('decharge.lancer', 'module:decharge'), sinon None."""
        if page_id and page_id.startswith("module:"):
            return page_id[7:]
        if page_id and "." in page_id:
            return page_id.split(".")[0]
        return None

    @staticmethod
    def parent_de(page_id):
        """Page vers laquelle ramène « Retour »."""
        if page_id and "." in page_id:
            return "module:" + page_id.split(".")[0]
        return "accueil"

    def page(self, page_id):
        """Page demandée, créée à la première utilisation."""
        if page_id not in self.pages:
            if page_id == "accueil":
                p = Accueil(self.zone, self)
            elif page_id == "modules":
                p = PageModules(self.zone, self)
            elif page_id == "instruments":
                p = PageInstruments(self.zone, self)
            elif page_id.startswith("module:"):
                p = PageModule(self.zone, self, self.modules[page_id[7:]])
            else:
                module_id, _, nom = page_id.partition(".")
                p = self.modules[module_id].creer_page(nom, self.zone, self)
            self.pages[page_id] = p
        return self.pages[page_id]

    def page_occupee(self):
        """Identifiant de la page qui verrouille la navigation (un test en cours, par ex.), sinon None."""
        for pid, p in self.pages.items():
            occupe = getattr(p, "occupe", None)
            if occupe and occupe():
                return pid
        return None

    def occupe(self):
        return self.page_occupee() is not None

    def aller(self, page_id):
        busy = self.page_occupee()
        if busy and page_id != busy:
            return  # pas de changement de page pendant une opération en cours
        module_id = self.module_de(page_id)
        if module_id and (module_id not in self.modules or not self.module_actif(module_id)):
            return
        page = self.page(page_id)
        if self.courante in self.pages:
            ancienne = self.pages[self.courante]
            quitter = getattr(ancienne, "on_hide", None)  # ex. une page qui lit un port série le libère en la quittant
            if quitter and self.courante != page_id:
                quitter()
            ancienne.pack_forget()
        self.courante = page_id
        page.pack(fill="both", expand=True)
        page.on_show()
        if page_id == "accueil":
            self.btn_menu.pack_forget()
        else:
            self.btn_menu.pack(side="right", padx=(0, 12))
        if not busy:  # l'état avant navigation : on ne sonde pas le matériel pendant une opération en cours
            self._maj_statut()

    def retour(self):
        self.aller(self.parent_de(self.courante))

    # ---------- statut des appareils (ceux que déclare le module affiché) ----------
    def _maj_statut(self):
        module_id = self.module_de(self.courante)
        ids = self.modules[module_id].instruments if module_id in self.modules else ()
        statuts = [self.instruments.statut(i) for i in ids]
        pire = max((s[0] for s in statuts), key=GRAVITE.index, default=None)
        self.lbl_statut.config(text="     ".join("● " + s[1] for s in statuts), fg=COULEURS_ETAT.get(pire, GRIS))

    def _rafraichir_statut(self):
        if not self.occupe():
            self._maj_statut()
        self.after(2000, self._rafraichir_statut)

    def _fermer(self):
        busy = self.page_occupee()
        if busy:
            if not messagebox.askyesno("Opération en cours", "Une opération est en cours. L'arrêter et quitter ?"):
                return
            arreter = getattr(self.pages[busy], "arreter_et_attendre", None)
            if arreter:
                arreter()
        self.destroy()


if __name__ == "__main__":
    envoi.reprendre()
    Application().mainloop()
