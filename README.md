# BetterSon - Test de batterie

Logiciel de test de décharge de batteries sur charge électronique EA (USB).
Fonctionne sous Windows, macOS (Apple Silicon) et Linux (x86_64).

## Installer (opérateurs)

Une seule commande dans un terminal. Elle télécharge la dernière version, vérifie son intégrité et crée les raccourcis.

| Système | Commande |
|---|---|
| **Windows** (PowerShell) | `irm https://raw.githubusercontent.com/acarpm/betterSon/main/install.ps1 \| iex` |
| **macOS** (Terminal) | `curl -fsSL https://raw.githubusercontent.com/acarpm/betterSon/main/install.sh \| bash` |
| **Linux** (Terminal) | `curl -fsSL https://raw.githubusercontent.com/acarpm/betterSon/main/install.sh \| bash` |

Sans terminal : télécharger le fichier de la dernière version sur la page **Releases** du dépôt
(`BetterSon-Setup.exe` sous Windows, `BetterSon-macos.zip` sous macOS, `BetterSon-linux` sous Linux).
Les fichiers téléchargés par navigateur ne sont pas signés : Windows (SmartScreen) et macOS (Gatekeeper) demandent
une confirmation au premier lancement (macOS : clic droit sur l'application > Ouvrir). Les commandes ci-dessus évitent ce message.

Linux : l'utilisateur doit être dans le groupe `dialout` pour accéder à la charge (`sudo usermod -aG dialout $USER`).

### Où sont les données ?

Dans le dossier **Documents/BetterSon** de l'opérateur : `profils.json` (profils de test) et `mesures/` (un CSV par test) pour le module Décharge, `config.json` (modules activés), et un sous-dossier par futur module.
Elles ne sont jamais touchées par les mises à jour ni par une réinstallation. Copier `profils.json` suffit pour partager des profils.

## Mises à jour automatiques

Au démarrage (puis toutes les 2 h), le logiciel regarde si une nouvelle release existe sur GitHub. Si oui, un bandeau
propose **Mettre à jour maintenant** : le fichier est téléchargé, sa somme SHA-256 est vérifiée, le logiciel se remplace
puis redémarre. Impossible pendant un test (le bouton est refusé) ; un échec laisse l'ancienne version intacte.
Le dépôt doit être **public** pour que les mises à jour et les commandes d'installation fonctionnent sans identifiants.

## Publier une nouvelle version (développeur)

```bash
git tag v1.2.0
git push origin v1.2.0
```

GitHub Actions ([.github/workflows/release.yml](.github/workflows/release.yml)) construit le logiciel sur Windows, macOS et Linux,
crée la release `v1.2.0` avec les fichiers et `SHA256SUMS.txt`, puis les postes installés proposent la mise à jour.
Le numéro de version du logiciel est celui du tag (écrit dans `version.py` pendant la construction).
Numérotation conseillée : `vMAJEUR.MINEUR.CORRECTIF` (ex. `v1.2.1`) ; une version n'est proposée que si elle est plus grande.

## Utilisation

Le logiciel est organisé en **modules** que l'on peut activer ou désactiver (bouton **Gérer les modules**, en bas à droite de l'accueil).
L'accueil affiche une tuile par module activé ; un module désactivé disparaît (ses données sont conservées).

### Module « Décharge de batteries »

Trois actions :

- **Lancer un test** : choisir un profil dans la liste (récapitulatif à droite), saisir éventuellement le n° de série, puis
  « Lancer le test ». La page **test en cours** affiche les mesures et le graphe tension + courant + puissance (un axe par
  grandeur, valeurs au survol, courbes masquables). À la fin : bilan, « Nouveau test » ou « Voir dans l'analyse ».
- **Créer / modifier un test** : gérer les profils (tension de coupure, courant et/ou puissance de décharge, notes).
- **Analyser les résultats** : liste des tests réalisés (filtre par profil / n° de série), synthèse
  (capacité, énergie, durée, tensions, moyennes) et graphe des mesures.

Pendant une opération (un test, par ex.), la navigation est verrouillée : on ne peut pas quitter la page en cours.

### Module « Équilibrage de batteries » (équilibreur actif Daly)

Lit l'équilibreur Daly par son port série (adaptateur USB-UART, 9600 bauds, protocole Daly en **lecture seule**). Trois actions :

- **Connexion** : choisir le port série de l'équilibreur (la charge EA n'est jamais proposée) et tester la liaison.
  Le port est mémorisé dans `config.json`.
- **Lire les tensions** : tension de chaque cellule en direct (une barre par cellule, échelle zoomée), tension / courant / SoC du pack,
  écart max - min, cellule la plus haute et la plus basse, cellules en cours d'équilibrage si l'appareil le signale.
  La lecture s'arrête et libère le port quand on quitte la page.
- **Session d'équilibrage** : suivi supervisé. On fixe l'écart cible (mV), la durée maximale et la durée de maintien ; la session
  enregistre un CSV (`Documents/BetterSon/equilibrage/sessions/`), trace l'écart en fonction du temps et **s'arrête seule**
  quand l'écart cible est tenu (ou à la durée maximale). La navigation est verrouillée pendant la session.

Le logiciel **ne commande pas** l'équilibreur (aucune commande d'écriture n'est envoyée) : il surveille et enregistre pendant
que l'appareil équilibre de lui-même.

### Module à venir

Calcul de la résistance interne des cellules : voir « Ajouter un module » ci-dessous.

## Développement

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows : .venv\Scripts\pip
.venv/bin/python gui.py
```

Lancé depuis les sources, le logiciel garde ses données dans le dossier du projet (`profils.json`, `mesures/`, `config.json`, ignorés par git)
et ne vérifie pas les mises à jour (`version.py` vaut `dev`). La variable d'environnement `BATCONNECT_DATA` force un autre dossier de données.
Tkinter est nécessaire (macOS Homebrew : `brew install python-tk@3.x`).

| Fichier | Rôle |
|---|---|
| `gui.py` | coque de l'application : fenêtre, navigation, verrouillage, bannière de mise à jour |
| `page_accueil.py`, `page_modules.py` | accueil (une tuile par module), menu d'un module, activation des modules |
| `config.py` | réglages (modules activés) dans `config.json` |
| `theme.py` | couleurs de la charte, composants partagés (tuile, liste, graphe, interrupteur), dossiers de données |
| `updater.py`, `version.py` | mise à jour depuis les releases GitHub, numéro de version |
| `modules/base.py` | contrat d'un module (`Module`, `Action`) |
| `modules/__init__.py` | **registre des modules** (`TOUS`) |
| `modules/decharge/` | module Décharge : pages, profils, analyse des CSV, chemins de données |
| `modules/equilibrage/` | module Équilibrage : protocole Daly (`daly.py`), lecture périodique + CSV (`acquisition.py`), pages |
| `modules/_modele/` | squelette commenté à copier pour un nouveau module (non enregistré) |
| `main.py` | communication avec la charge EA (version console) |
| `install.sh`, `install.ps1` | installation en une commande |
| `installer/betterson.iss` | installateur Windows (Inno Setup), construit par la CI |

### Ajouter un module

1. Copier `modules/_modele/` en `modules/<id>/` (ex. `modules/resistance/`) et adapter la classe : `id`, `nom`, `description`,
   `actions()` (les tuiles du menu du module), `creer_page()` (une classe `tk.Frame` par page), `statut()` (matériel connecté, facultatif).
2. L'enregistrer dans `modules/__init__.py` : `from .resistance import Resistance`, puis `TOUS = [Decharge(), Equilibrage(), Resistance()]`.
3. C'est tout : tuile sur l'accueil, activation / désactivation, navigation, verrouillage pendant une opération
   (méthode `occupe()` d'une page), dossier de données (`self.dossier()`) et mises à jour automatiques sont fournis.

Un module est aussi livré à tous les postes par la mise à jour ; l'opérateur choisit ensuite de l'activer ou non.

Construction locale (même commande que la CI) :

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name BetterSon --add-data "assets:assets" --collect-submodules serial gui.py
# Windows : --add-data "assets;assets" ; macOS : remplacer --onefile par --onedir
```

new versions git tag v ** && git push origin v **