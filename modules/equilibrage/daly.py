"""Protocole UART Daly (BMS / équilibreur actif) : trames de 13 octets, 9600 bauds, lecture seule.

Requête : A5 40 <cmd> 08 <8 octets> <somme>   Réponse : A5 01 <cmd> 08 <8 octets> <somme>
somme = total des 12 premiers octets modulo 256.

Commandes utilisées (toutes en lecture, aucune ne modifie l'appareil) :
  0x90 tension du pack, courant, SoC   0x94 nombre de cellules   0x95 tension de chaque cellule (3 par trame)
  0x97 état d'équilibrage par cellule (si l'appareil le fournit)
"""
import math
import time

BAUD = 9600
DEBUT = 0xA5
ADRESSE_PC = 0x40
CMD_GLOBAL, CMD_ETAT, CMD_CELLULES, CMD_EQUILIBRAGE = 0x90, 0x94, 0x95, 0x97


def somme_controle(trame):
    return sum(trame[:12]) & 0xFF


def requete(cmd):
    t = bytearray([DEBUT, ADRESSE_PC, cmd, 0x08] + [0] * 9)
    t[12] = somme_controle(t)
    return bytes(t)


def trame_valide(t, cmd=None):
    return len(t) == 13 and t[0] == DEBUT and t[12] == somme_controle(t) and (cmd is None or t[2] == cmd)


def resume_cellules(cellules):
    """Écart max-min (mV), indices (0-based) et tensions de la cellule la plus haute / la plus basse."""
    mesurees = [(v, i) for i, v in enumerate(cellules) if v is not None]
    if not mesurees:
        return None
    (v_min, i_min), (v_max, i_max) = min(mesurees), max(mesurees)
    return {"ecart_mv": (v_max - v_min) * 1000.0, "i_min": i_min, "v_min": v_min, "i_max": i_max, "v_max": v_max}


class Daly:
    """Dialogue avec l'appareil sur un port série déjà ouvert (9600 8N1, timeout court)."""

    def __init__(self, ser, delai=0.5):
        self.ser = ser
        self.delai = delai
        self.n_cellules = None
        self._manques_equilibrage = 0

    # ---------- bas niveau ----------
    def _lire_trame(self, cmd):
        """Prochaine trame valide de la commande `cmd` (en ignorant le bruit), ou None si le port se tait."""
        while True:
            b = self.ser.read(1)
            if not b:
                return None  # délai dépassé
            if b[0] != DEBUT:
                continue
            corps = self.ser.read(12)
            if len(corps) < 12:
                return None
            t = bytes([DEBUT]) + bytes(corps)
            if trame_valide(t, cmd):
                return t

    def _interroger(self, cmd, nombre=1):
        self.ser.reset_input_buffer()
        self.ser.write(requete(cmd))
        trames = []
        limite = time.monotonic() + self.delai * (nombre + 1)
        while len(trames) < nombre and time.monotonic() < limite:
            t = self._lire_trame(cmd)
            if t is None:
                break
            trames.append(t)
        return trames

    # ---------- lectures ----------
    def lire_global(self):
        t = self._interroger(CMD_GLOBAL)
        if not t:
            return None
        t = t[0]
        return {"v_pack": ((t[4] << 8) | t[5]) / 10.0,
                "courant": (((t[6] << 8) | t[7]) - 30000) / 10.0,
                "soc": ((t[8] << 8) | t[9]) / 10.0}

    def lire_nombre_cellules(self):
        t = self._interroger(CMD_ETAT)
        return t[0][4] if t and t[0][4] > 0 else None

    def lire_cellules(self):
        """Tensions (V) de chaque cellule, dans l'ordre ; None pour une cellule dont la trame manque."""
        nombre = math.ceil(self.n_cellules / 3) if self.n_cellules else 16
        trames = self._interroger(CMD_CELLULES, nombre)
        if not trames:
            return None
        base = min(t[4] for t in trames)  # numéro de la première trame : 0 ou 1 selon les appareils
        par_indice = {}
        for t in trames:
            for k, off in enumerate((5, 7, 9)):
                par_indice[(t[4] - base) * 3 + k] = ((t[off] << 8) | t[off + 1]) / 1000.0
        liste = [par_indice.get(i) for i in range(max(par_indice) + 1)]
        if self.n_cellules:
            return (liste + [None] * self.n_cellules)[:self.n_cellules]
        while liste and not liste[-1]:  # nombre inconnu : on retire les voies non câblées (0 V)
            liste.pop()
        return liste or None

    def lire_equilibrage(self, n):
        """Liste de booléens (cellule en cours d'équilibrage), ou None si l'appareil ne répond pas à cette commande."""
        if self._manques_equilibrage >= 3:
            return None  # non pris en charge : on n'insiste plus
        t = self._interroger(CMD_EQUILIBRAGE)
        if not t:
            self._manques_equilibrage += 1
            return None
        self._manques_equilibrage = 0
        return [bool((t[0][4 + i // 8] >> (i % 8)) & 1) for i in range(min(n, 64))]

    def lire_tout(self):
        """Une lecture complète, ou None si l'appareil ne répond à rien (en veille, mauvais port...)."""
        g = self.lire_global()
        if self.n_cellules is None:
            self.n_cellules = self.lire_nombre_cellules()
        cellules = self.lire_cellules()
        if g is None and cellules is None:
            return None
        res = {"v_pack": g["v_pack"] if g else None, "courant": g["courant"] if g else None,
               "soc": g["soc"] if g else None, "cellules": cellules or [], "equilibrage": None}
        if cellules:
            res["equilibrage"] = self.lire_equilibrage(len(cellules))
            res.update(resume_cellules(cellules) or {})
        return res
