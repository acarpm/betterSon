# BatConnect - Test de batterie

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
(`BatConnect-Setup.exe` sous Windows, `BatConnect-macos.zip` sous macOS, `BatConnect-linux` sous Linux).
Les fichiers téléchargés par navigateur ne sont pas signés : Windows (SmartScreen) et macOS (Gatekeeper) demandent
une confirmation au premier lancement (macOS : clic droit sur l'application > Ouvrir). Les commandes ci-dessus évitent ce message.

Linux : l'utilisateur doit être dans le groupe `dialout` pour accéder à la charge (`sudo usermod -aG dialout $USER`).

### Où sont les données ?

Dans le dossier **Documents/BatConnect** de l'opérateur : `profils.json` (profils de test) et `mesures/` (un CSV par test).
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

L'écran d'accueil propose trois actions :

- **Lancer un test** : choisir un profil dans la liste (récapitulatif à droite), saisir éventuellement le n° de série, puis
  « Lancer le test ». La page **test en cours** affiche les mesures et le graphe tension + courant + puissance (un axe par
  grandeur, valeurs au survol, courbes masquables). À la fin : bilan, « Nouveau test » ou « Voir dans l'analyse ».
- **Créer / modifier un test** : gérer les profils (tension de coupure, courant et/ou puissance de décharge, notes).
- **Analyser les résultats** : liste des tests réalisés (filtre par profil / n° de série), synthèse
  (capacité, énergie, durée, tensions, moyennes) et graphe des mesures.

Pendant un test, la navigation est verrouillée : on ne peut pas quitter la page « test en cours ».

## Développement

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows : .venv\Scripts\pip
.venv/bin/python gui.py
```

Lancé depuis les sources, le logiciel garde ses données dans le dossier du projet (`profils.json`, `mesures/`, ignorés par git)
et ne vérifie pas les mises à jour (`version.py` vaut `dev`). La variable d'environnement `BATCONNECT_DATA` force un autre dossier de données.
Tkinter est nécessaire (macOS Homebrew : `brew install python-tk@3.x`).

| Fichier | Rôle |
|---|---|
| `gui.py` | fenêtre, accueil, page de sélection du test, page de test en cours, bannière de mise à jour |
| `page_profils.py`, `page_resultats.py` | pages de gestion des profils et d'analyse |
| `theme.py` | couleurs de la charte, composants partagés (liste, graphe), dossiers de données |
| `profils.py`, `resultats.py` | lecture / validation des profils, lecture / analyse des CSV (sans interface) |
| `updater.py`, `version.py` | mise à jour depuis les releases GitHub, numéro de version |
| `main.py` | communication avec la charge EA (version console) |
| `install.sh`, `install.ps1` | installation en une commande |
| `installer/batconnect.iss` | installateur Windows (Inno Setup), construit par la CI |

Construction locale (même commande que la CI) :

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name BatConnect --add-data "assets:assets" --collect-submodules serial gui.py
# Windows : --add-data "assets;assets" ; macOS : remplacer --onefile par --onedir
```
