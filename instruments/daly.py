"""Protocole UART Daly (BMS / équilibreur actif) : trames de 13 octets, 9600 bauds, lecture seule.

Requête : A5 40 <cmd> 08 <8 octets> <somme>   Réponse : A5 01 <cmd> 08 <8 octets> <somme>
somme = total des 12 premiers octets modulo 256.

Commandes utilisées (toutes en lecture, aucune ne modifie l'appareil) :
  0x90 tension du pack, courant, SoC   0x94 nombre de cellules   0x95 tension de chaque cellule (3 par trame)
  0x97 état d'équilibrage par cellule (si l'appareil le fournit)
"""
import math
import time

from .base import Instrument

BAUD = 9600
# Mesuré sur l'appareil : réponse en ~75 ms, mais le 1er échange après une pause peut prendre 500-600 ms.
# Un délai de 300 ms perdait donc régulièrement des réponses (tension du pack absente, cellules manquantes).
DELAI_SERIE = 0.9
TENUE = 5   # une cellule dont la trame manque garde sa dernière valeur pendant TENUE lectures, puis passe à « inconnue »
DEBUT = 0xA5
ADRESSE_PC = 0x40
CMD_GLOBAL, CMD_ETAT, CMD_CELLULES, CMD_EQUILIBRAGE = 0x90, 0x94, 0x95, 0x97
CMD_PARAM_EQUILIBRAGE = 0x5F   # LECTURE : seuils de déclenchement de l'équilibrage (doc Daly p.18)
CMD_EQUILIBRAGE_ACTIF = 0x24   # ÉCRITURE, non documentée (trouvée par capture CAN) : octet 0 = 1 démarre, 0 arrête l'équilibrage actif
CMD_TEST_EQUILIBRAGE = 0xD7    # ÉCRITURE « Balanced test » : démarre/arrête l'équilibrage d'une cellule (doc Daly p.24)


def somme_controle(trame):
    return sum(trame[:12]) & 0xFF


def requete(cmd, donnees=()):
    """Trame de requête : 8 octets de données (réservés à zéro pour une lecture)."""
    donnees = list(donnees)
    if len(donnees) > 8:
        raise ValueError("8 octets de données au maximum")
    t = bytearray([DEBUT, ADRESSE_PC, cmd, 0x08] + donnees + [0] * (8 - len(donnees)) + [0])
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

    def __init__(self, ser, delai=DELAI_SERIE):
        self.ser = ser
        self.delai = delai
        self.n_cellules = None
        self._manques_equilibrage = 0
        self._prec = None          # dernières tensions connues (pour tenir les valeurs lors d'une trame perdue)
        self._manques_cell = []
        self._lectures_vides = 0
        self._pack_prec, self._pack_manques = None, 0
        self.seuils = None         # seuils d'équilibrage de l'appareil (0x5F), lus une fois
        self._essais_seuils = 0

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

    def _interroger(self, cmd, nombre=1, donnees=()):
        self.ser.reset_input_buffer()
        self.ser.write(requete(cmd, donnees))
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
        # Octets de données de la réponse 0x90 (t[4:12]) :  0-1 tension du pack (0,1 V) | 2-3 tension de collecte |
        #                                                    4-5 courant (0,1 A, décalage 30000) | 6-7 SoC (0,1 %)
        # Pour un équilibreur actif, « courant » est le courant d'équilibrage : 0 A au repos, non nul quand il équilibre.
        v, i, s = (t[4] << 8) | t[5], (t[8] << 8) | t[9], (t[10] << 8) | t[11]
        return {"v_pack": None if v in (0, 0xFFFF) else v / 10.0,
                "courant": None if i in (0, 0xFFFF) else (i - 30000) / 10.0,   # 0 ou 0xFFFF = champ non géré
                "soc": s / 10.0 if s <= 1000 else None}

    def lire_nombre_cellules(self):
        t = self._interroger(CMD_ETAT)
        return t[0][4] if t and t[0][4] > 0 else None

    def lire_cellules(self, tenir=True):
        """Tensions (V) de chaque cellule, dans l'ordre ; None pour une cellule dont la trame manque.

        tenir=False : aucune valeur n'est reportée d'une lecture à l'autre (mesures de précision, ex. résistance interne :
        une valeur ancienne fausserait le calcul).

        Si des trames manquent, la lecture est retentée une fois ; une cellule encore manquante garde sa dernière valeur
        pendant TENUE lectures (une trame perdue ne doit pas faire clignoter l'affichage).
        """
        nombre = math.ceil(self.n_cellules / 3) if self.n_cellules else 16
        par_numero = {}
        for _ in range(2 if self.n_cellules else 1):
            for tr in self._interroger(CMD_CELLULES, nombre):
                par_numero[tr[4]] = tr
            if len(par_numero) >= nombre:
                break
        if not par_numero:
            return self._tenir(None) if tenir else None
        base = min(par_numero)  # numéro de la première trame : 0 ou 1 selon les appareils
        par_indice = {}
        for numero, tr in par_numero.items():
            for k, off in enumerate((5, 7, 9)):
                par_indice[(numero - base) * 3 + k] = ((tr[off] << 8) | tr[off + 1]) / 1000.0
        liste = [par_indice.get(i) for i in range(max(par_indice) + 1)]
        if self.n_cellules:
            liste = (liste + [None] * self.n_cellules)[:self.n_cellules]
        else:
            while liste and not liste[-1]:  # nombre inconnu : on retire les voies non câblées (0 V)
                liste.pop()
        return self._tenir(liste or None) if tenir else (liste or None)

    def _tenir(self, liste):
        """Complète une lecture incomplète avec les dernières valeurs connues (au plus TENUE lectures de suite)."""
        if liste is None:
            if self._prec and self._lectures_vides < TENUE:
                self._lectures_vides += 1
                return list(self._prec)
            return None
        self._lectures_vides = 0
        if self._prec is None or len(self._prec) != len(liste):
            self._manques_cell = [0] * len(liste)
        else:
            for i, v in enumerate(liste):
                if v is None and self._manques_cell[i] < TENUE and self._prec[i] is not None:
                    liste[i] = self._prec[i]
                    self._manques_cell[i] += 1
                elif v is not None:
                    self._manques_cell[i] = 0
        self._prec = list(liste)
        return liste

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

    def lire_parametres_equilibrage(self):
        """Seuils de déclenchement de l'équilibrage (0x5F, lecture) : tension et écart d'ouverture en mV, ou None."""
        t = self._interroger(CMD_PARAM_EQUILIBRAGE)
        if not t:
            return None
        d = t[0][4:12]
        ouverture, ecart = (d[0] << 8) | d[1], (d[2] << 8) | d[3]
        if ouverture in (0, 0xFFFF) and ecart in (0, 0xFFFF):
            return None  # champs non renseignés
        return {"tension_ouverture_mv": ouverture, "ecart_ouverture_mv": ecart}

    def piloter_equilibrage(self, actif):
        """0x24 : démarre (True) ou arrête (False) l'équilibrage actif. Renvoie les 8 octets de la réponse, ou None."""
        t = self._interroger(CMD_EQUILIBRAGE_ACTIF, 1, [1 if actif else 0])
        return t[0][4:12] if t else None

    def commander_equilibrage(self, cellule, actif):
        """0xD7 « Balanced test » : ACTION SUR L'APPAREIL. Démarre (actif=True) ou arrête l'équilibrage de la cellule
        `cellule` (1..n). Renvoie True / False selon le résultat annoncé par l'appareil, None s'il ne répond pas.

        Commande de test d'usine : la sémantique exacte (équilibrage passif ou actif, direction du transfert) dépend du
        modèle. Elle n'est utilisée par aucune page de l'application tant qu'elle n'a pas été validée sur l'appareil réel.
        """
        maxi = self.n_cellules or 48
        if isinstance(cellule, bool) or not isinstance(cellule, int) or not 1 <= cellule <= maxi:
            raise ValueError(f"cellule invalide : {cellule!r} (1 à {maxi})")
        t = self._interroger(CMD_TEST_EQUILIBRAGE, 1, [cellule, 1 if actif else 0])
        if not t:
            return None
        return t[0][4] == 1  # octet 0 de la réponse : 0 = échec, 1 = succès

    def lire_tout(self):
        """Une lecture complète, ou None si l'appareil ne répond à rien (en veille, mauvais port...)."""
        g = self.lire_global()
        if self.n_cellules is None:
            self.n_cellules = self.lire_nombre_cellules()
        cellules = self.lire_cellules()
        if g is None and cellules is None:
            return None
        v_pack = g["v_pack"] if g else None
        if v_pack is not None:
            self._pack_prec, self._pack_manques = v_pack, 0
        elif self._pack_prec is not None and self._pack_manques < TENUE:  # réponse perdue : on tient la dernière valeur
            v_pack, self._pack_manques = self._pack_prec, self._pack_manques + 1
        res = {"v_pack": v_pack, "courant": g["courant"] if g else None,
               "soc": g["soc"] if g else None, "cellules": cellules or [], "equilibrage": None, "seuils": self.seuils}
        if cellules:
            if self.seuils is None and self._essais_seuils < 2:  # une seule lecture des seuils (2 essais au plus)
                self._essais_seuils += 1
                self.seuils = self.lire_parametres_equilibrage()
            res["seuils"] = self.seuils
            res["equilibrage"] = self.lire_equilibrage(len(cellules))
            res.update(resume_cellules(cellules) or {})
        return res


class EquilibreurDaly(Instrument):
    id = "equilibreur_daly"
    nom = "Équilibreur actif Daly"
    libelle = "Équilibreur Daly"
    description = ("Équilibreur / BMS Daly relié par un adaptateur USB-série (UART, 9600 bauds). L'USB ne l'identifie pas : "
                   "le port est trouvé en interrogeant les ports série disponibles, puis mémorisé.")
    aide = "Branchez l'adaptateur USB-série de l'équilibreur et vérifiez son alimentation."
    baud = BAUD
    delai_serie = DELAI_SERIE
    identification_directe = False

    def sonde(self, ser):
        d = Daly(ser).lire_tout()
        if d is None:
            return None
        return {"cellules": len(d["cellules"]), "v_pack": d["v_pack"], "ecart_mv": d.get("ecart_mv")}
