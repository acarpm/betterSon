# BatConnect - Test de batterie

Lancer l'interface : `.venv/bin/python gui.py`

## Utilisation

L'écran d'accueil propose trois actions :

- **Lancer un test** : on choisit un profil dans la liste (récapitulatif à droite), on saisit éventuellement le n° de série, puis « Lancer le test ». L'application passe alors sur la page **test en cours** (mesures en direct, graphe tension + courant + puissance, bouton Arrêter). À la fin : bilan, « Nouveau test » ou « Voir dans l'analyse ».
- **Créer / modifier un test** : gérer les profils (tension de coupure, courant et/ou puissance de décharge, notes).
- **Analyser les résultats** : liste des tests réalisés (filtre par profil / n° de série), synthèse
  (capacité, énergie, durée, tensions, moyennes) et graphe unique tension + courant + puissance (un axe par grandeur, valeurs au survol, courbes masquables).

Pendant un test, la navigation est verrouillée : on ne peut pas quitter la page « test en cours ».

## Fichiers

- `profils.json` : les profils de test, à côté du programme. Copier ce fichier suffit pour les partager entre postes.
- `mesures/` : un CSV par test, nommé `<profil>_<n° de série>_<date>_<heure>.csv`.

## Code

- `gui.py` : fenêtre, accueil, page de sélection du test (`PageLancer`), page de test en cours (`PageEnCours`)
- `page_profils.py`, `page_resultats.py` : les deux autres pages
- `theme.py` : couleurs de la charte, composants partagés (liste, courbe)
- `profils.py`, `resultats.py` : lecture / validation des profils, lecture / analyse des CSV (sans interface)
- `main.py` : communication avec la charge EA (version console)

## Générer un exécutable (à faire sur chaque système cible)

macOS / Linux :
    pyinstaller --onefile --windowed --add-data "assets:assets" gui.py

Windows :
    pyinstaller --onefile --windowed --add-data "assets;assets" gui.py
