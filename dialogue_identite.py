"""Fenêtres et widget d'identification : identifiant du poste, liste des techniciens, sélecteur de technicien."""
import tkinter as tk
from tkinter import ttk

import identite
import synchro
from theme import BG, BORD, GRIS, ROUGE, TEXTE


def _fenetre(parent, titre):
    fen = tk.Toplevel(parent, bg=BG)
    fen.title(titre)
    fen.transient(parent)
    fen.resizable(False, False)
    return fen


def _afficher_modale(parent, fen, focus):
    fen.update_idletasks()  # centrée sur la fenêtre principale
    x = parent.winfo_rootx() + (parent.winfo_width() - fen.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + max(40, (parent.winfo_height() - fen.winfo_reqheight()) // 3)
    fen.geometry(f"+{max(0, x)}+{max(0, y)}")
    fen.grab_set()
    focus.focus_set()
    parent.wait_window(fen)


def demander_poste(parent, f, obligatoire):
    """Identifiant de ce PC. obligatoire (premier lancement) : pas d'annulation, fermer renvoie False."""
    fen = _fenetre(parent, "Identification du poste")
    resultat = [False]
    cadre = tk.Frame(fen, bg=BG)
    cadre.pack(padx=28, pady=22)
    tk.Label(cadre, text="Identifiant de ce poste de test" if obligatoire else "Modifier l'identifiant du poste",
             bg=BG, fg=TEXTE, font=f(16, True), anchor="w").pack(fill="x")
    tk.Label(cadre, text="Il figure sur chaque test réalisé depuis ce PC (ex. banc-1).\nVous pourrez le modifier depuis "
                         "l'en-tête du logiciel.", bg=BG, fg=GRIS, font=f(11), anchor="w", justify="left"
             ).pack(fill="x", pady=(2, 14))
    var = tk.StringVar(value=identite.poste() or "")
    e = ttk.Entry(cadre, textvariable=var, font=f(14), width=28)
    e.pack(fill="x", pady=(0, 6))
    erreur = tk.Label(cadre, text="", bg=BG, fg=ROUGE, font=f(11), anchor="w", justify="left", wraplength=320)
    erreur.pack(fill="x")

    def valider(_=None):
        try:
            identite.definir_poste(var.get())
        except ValueError as ex:
            erreur.config(text=str(ex))
            return
        resultat[0] = True
        fen.destroy()

    boutons = tk.Frame(cadre, bg=BG)
    boutons.pack(fill="x", pady=(8, 0))
    ttk.Button(boutons, text="Enregistrer", style="Maj.TButton", command=valider).pack(side="right")
    if not obligatoire:
        ttk.Button(boutons, text="Annuler", style="Tool.TButton", command=fen.destroy).pack(side="right", padx=8)
        fen.bind("<Escape>", lambda ev: fen.destroy())
    fen.protocol("WM_DELETE_WINDOW", fen.destroy)
    fen.bind("<Return>", valider)
    _afficher_modale(parent, fen, e)
    return resultat[0]


def gerer_techniciens(parent, f):
    """Ajout et suppression de techniciens. Renvoie le dernier technicien ajouté (ou None)."""
    fen = _fenetre(parent, "Techniciens")
    ajoute = [None]
    cadre = tk.Frame(fen, bg=BG)
    cadre.pack(padx=28, pady=22)
    tk.Label(cadre, text="Techniciens", bg=BG, fg=TEXTE, font=f(16, True), anchor="w").pack(fill="x", pady=(0, 10))
    liste = tk.Listbox(cadre, height=8, width=34, font=f(13), bg="white", fg=TEXTE, relief="flat", exportselection=False,
                       highlightthickness=1, highlightbackground=BORD, selectbackground="#dfe7c0", selectforeground=TEXTE)
    liste.pack(fill="x")

    def remplir():
        liste.delete(0, "end")
        for t in identite.techniciens():
            liste.insert("end", t)

    def supprimer():
        for i in liste.curselection():
            identite.supprimer_technicien(liste.get(i))
        remplir()
        resynchroniser()

    ttk.Button(cadre, text="Supprimer le technicien sélectionné", style="Tool.TButton", command=supprimer).pack(anchor="w", pady=(4, 12))
    ligne = tk.Frame(cadre, bg=BG)
    ligne.pack(fill="x")
    var_prenom, var_nom = tk.StringVar(), tk.StringVar()
    for titre, var in (("Prénom", var_prenom), ("Nom", var_nom)):
        bloc = tk.Frame(ligne, bg=BG)
        bloc.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(bloc, text=titre, bg=BG, fg=GRIS, font=f(11), anchor="w").pack(fill="x")
        e = ttk.Entry(bloc, textvariable=var, font=f(13), width=14)
        e.pack(fill="x")
        if titre == "Prénom":
            premier = e
    erreur = tk.Label(cadre, text="", bg=BG, fg=ROUGE, font=f(11), anchor="w")
    erreur.pack(fill="x", pady=(6, 0))
    lbl_synchro = tk.Label(cadre, text="", bg=BG, fg=GRIS, font=f(10), anchor="w")
    lbl_synchro.pack(fill="x")

    def maj_synchro(tentatives=10):
        if not fen.winfo_exists():
            return
        etat = synchro.etat()
        lbl_synchro.config(text={"serveur": "Synchronisé avec le serveur.",
                                 "local": "Serveur injoignable : enregistré sur ce PC, transmis dès que possible.",
                                 "non_configure": "Serveur non configuré : enregistré sur ce PC uniquement."}.get(etat, "Synchronisation…"))
        if etat == "inconnu" and tentatives:
            fen.after(500, lambda: maj_synchro(tentatives - 1))

    def resynchroniser():
        synchro.lancer(force=True)
        lbl_synchro.config(text="Synchronisation…")
        fen.after(1200, maj_synchro)

    def ajouter(_=None):
        try:
            ajoute[0] = identite.ajouter_technicien(var_prenom.get(), var_nom.get())
        except ValueError as ex:
            erreur.config(text=str(ex))
            return
        var_prenom.set("")
        var_nom.set("")
        erreur.config(text="")
        remplir()
        resynchroniser()
        premier.focus_set()

    boutons = tk.Frame(cadre, bg=BG)
    boutons.pack(fill="x", pady=(8, 0))
    ttk.Button(boutons, text="Fermer", style="Tool.TButton", command=fen.destroy).pack(side="right")
    ttk.Button(boutons, text="Ajouter", style="Maj.TButton", command=ajouter).pack(side="right", padx=8)
    fen.bind("<Return>", ajouter)
    fen.bind("<Escape>", lambda ev: fen.destroy())
    remplir()
    maj_synchro()
    _afficher_modale(parent, fen, premier)
    return ajoute[0]


class SelecteurTechnicien(tk.Frame):
    """Liste déroulante des techniciens + bouton « Gérer ». valeur() : technicien choisi, ou None."""

    def __init__(self, parent, f, fond=BG):
        super().__init__(parent, bg=fond)
        self.f = f
        tk.Label(self, text="Technicien", bg=fond, fg=GRIS, font=f(11), anchor="w").pack(fill="x")
        ligne = tk.Frame(self, bg=fond)
        ligne.pack(fill="x")
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(ligne, textvariable=self.var, state="readonly", font=f(13))
        self.combo.pack(side="left", fill="x", expand=True)
        ttk.Button(ligne, text="Gérer", style="Tool.TButton", command=self._gerer, takefocus=False).pack(side="left", padx=(6, 0))

    def rafraichir(self, choisir=None, synchroniser=True):
        if synchroniser and synchro.lancer():
            self.after(1500, lambda: self.winfo_exists() and self.rafraichir(synchroniser=False))  # relit la liste du serveur
        liste = identite.techniciens()
        self.combo.config(values=liste)
        voulu = choisir or self.var.get() or identite.dernier_technicien()
        self.var.set(voulu if voulu in liste else (liste[0] if len(liste) == 1 else ""))

    def _gerer(self):
        ajoute = gerer_techniciens(self.winfo_toplevel(), self.f)
        self.rafraichir(ajoute)

    def valeur(self):
        v = self.var.get()
        if v:
            identite.retenir_technicien(v)
        return v or None
