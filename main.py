import csv
import os
import time
from datetime import datetime

import serial
import serial.tools.list_ports as lp

INTERVALLE_S = 1  # pause entre deux mesures (en secondes)
DOSSIER_CSV =os.path.join(os.path.dirname(os.path.abspath(__file__)), "mesures")

# Identifiants USB de la charge 
VID_EA = 0x232E
SN_CIBLE = "2289160002"  # id Propre a la charge EA dans l'atelier


def trouver_ports(sn=SN_CIBLE):
    return [
        p.device
        for p in lp.comports() #list port info
        if p.vid == VID_EA and (sn is None or p.serial_number == sn)
    ]


def identifier(s):
    s.write(b"*IDN?\n")
    return s.readline().decode(errors="ignore").strip()


def mesurer(s, commande):
    s.write(commande)
    reponse = s.readline().decode(errors="ignore").strip()  # ex : "0.00 V"
    return float(reponse.split()[0])  # garde le nombre, enlève l'unité


def lire_valeurs(s, v, i, p):
    if (v != None):
        v = mesurer(s, b"MEAS:VOLT?\n")
    if (i != None):
        i = mesurer(s, b"MEAS:CURR?\n")
    if (p != None):
        p = mesurer(s, b"MEAS:POW?\n")
    return v, i, p

def regler_charge(s, v, i, p):
    if (v != None):
        s.write(f"VOLT {v}\n".encode())
    if (i != None):
        s.write(f"CURR {i}\n".encode())
    if (p != None):
        s.write(f"POW {p}\n".encode())

def verrou(s, actif):
    s.write(b"SYST:LOCK ON\n" if actif else b"SYST:LOCK OFF\n")
    time.sleep(0.5)  # la charge ignore les requêtes pendant qu'elle change de mode
    s.reset_input_buffer()
    s.write(b"SYST:LOCK:OWN?\n")
    return (s.readline().decode(errors="ignore").strip() == "REMOTE") == actif  # vérifie l'état réel


def entree(s, actif):
    s.write(b"INP ON\n" if actif else b"INP OFF\n")
    s.write(b"INP?\n")
    return (s.readline().decode(errors="ignore").strip() == "ON") == actif  # vérifie l'état réel


def demander_nombre(question, defaut=None, optionnel=False):
    suffixe = f" [{defaut}]" if defaut is not None else " (optionnel, Entrée pour passer)" if optionnel else ""
    while True:
        texte = input(f"{question}{suffixe} : ").strip()
        if not texte and defaut is not None:
            return defaut
        if not texte and optionnel:
            return None
        try:
            return float(texte.replace(",", "."))
        except ValueError:
            print("  Entrez un nombre.")


def decharge(s):
    nom = input("Nom de la batterie : ").strip() or "batterie"
    v_coupure = demander_nombre("Tension de coupure (V)")
    courant = demander_nombre("Courant de décharge (A)", optionnel=True)
    if courant is None:
        puissance = demander_nombre("Puissance de décharge (W)")  # obligatoire sans courant
    else:
        puissance = demander_nombre("Puissance de décharge (W)", optionnel=True)

    os.makedirs(DOSSIER_CSV, exist_ok=True)
    chemin = os.path.join(DOSSIER_CSV, f"{nom}_{datetime.now():%Y%m%d_%H%M%S}.csv")

    if not verrou(s, True):  # sans le mode distant, la charge refuse INP ON
        print("La charge n'est pas passée en mode distant, arrêt.")
        return
    try:
        regler_charge(s, None, courant, puissance)
        input("Appuyez sur Entrée pour activer l'entrée de la charge et démarrer (Ctrl+C pour arrêter)...")
        enregistrer(s, chemin, v_coupure)
    finally:
        verrou(s, False)  # rend la main à la face avant de la charge


def enregistrer(s, chemin, v_coupure):
    ah = wh = 0.0
    with open(chemin, "w", newline="") as f:
        ecrivain = csv.writer(f)
        ecrivain.writerow(["temps_s", "V", "A", "W", "Ah", "Wh"])
        if not entree(s, True):
            print("La charge n'a pas activé son entrée, arrêt.")
            return
        t0 = t_prec = time.monotonic()
        try:
            while True:
                v, i, p = lire_valeurs(s, 1, 1, 1)
                t = time.monotonic()
                dt = t - t_prec  # temps réel écoulé depuis la mesure précédente
                t_prec = t
                ah += i * dt / 3600
                wh += p * dt / 3600
                ecrivain.writerow([f"{t - t0:.1f}", v, i, p, f"{ah:.4f}", f"{wh:.4f}"])
                f.flush()  # rien n'est perdu si le script est coupé
                print(f"\r{v:.2f}V {i:.2f}A {p:.1f}W | {ah:.3f}Ah {wh:.3f}Wh", end="", flush=True)
                if v < v_coupure:
                    print("\nTension de coupure atteinte")
                    break
                time.sleep(INTERVALLE_S)
        except KeyboardInterrupt:
            print("\nArrêt manuel")
        finally:
            entree(s, False)  # coupe toujours l'entrée à la fin

    print(f"Total : {ah:.3f} Ah, {wh:.3f} Wh")
    print("Fichier :", chemin)


def menu(s):
    while True:
        print("\n=== Menu ===")
        print("1. Identité de la charge")
        print("2. Mesure instantanée")
        print("3. Décharge d'une batterie (Ah / Wh + CSV)")
        print("0. Quitter")
        choix = input("> ").strip()
        if choix == "1":
            print("  ->", identifier(s) or "(pas de réponse)")
        elif choix == "2":
            v, i, p = lire_valeurs(s, 1, 1, 1)
            print(f"  -> {v:.2f}V {i:.2f}A {p:.1f}W")
        elif choix == "3":
            decharge(s)
        elif choix == "0":
            break
        else:
            print("  Choix invalide.")


def main():
    ports = trouver_ports()
    if not ports:
        print("Aucune charge EA trouvée")
        return

    print("Trouvé :", ports[0])
    try:
        with serial.Serial(ports[0], 115200, timeout=1) as s:  # ferme le port automatiquement à la fin du bloc
            menu(s)
    except (serial.SerialException, OSError) as e:
        print("  erreur :", e)


if __name__ == "__main__":
    main()