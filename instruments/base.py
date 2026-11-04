"""Contrat d'un instrument (appareil relié par port série) : comment le reconnaître et comment lui parler."""


class Instrument:
    """Décrit un type d'appareil. Le gestionnaire (instruments.gestionnaire) s'occupe de trouver son port.

    Deux façons de reconnaître un appareil :
      - identification directe : l'USB l'annonce (identifiant fabricant `vid`...) -> reconnu_par_vid() ;
      - par sondage : on interroge les ports série candidats et on garde celui qui répond correctement -> sonde().
    """

    id = ""                      # identifiant stable (réglages, appels du gestionnaire)
    nom = ""                     # nom complet affiché
    libelle = ""                 # nom court (barre d'état)
    description = ""
    aide = ""                    # conseil affiché quand l'appareil est introuvable
    baud = 9600
    delai_serie = 0.4            # délai de lecture du port série (secondes) pour les dialogues de reconnaissance
    identification_directe = False

    def reconnu_par_vid(self, port):
        """Vrai si l'USB identifie ce port comme étant cet appareil (sans lui parler)."""
        return False

    def candidats(self, ports):
        """Ports (objets pyserial ListPortInfo) pouvant correspondre à l'appareil. Aucune communication."""
        return list(ports)

    def sonde(self, ser):
        """Dialogue de reconnaissance sur un port ouvert. Dict d'infos si l'appareil répond, sinon None."""
        return None
