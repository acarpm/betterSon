"""Mise à jour automatique depuis les releases GitHub (sans interface graphique).

Principe : la CI publie à chaque tag vX.Y.Z un binaire par système + SHA256SUMS.txt.
Le logiciel interroge la dernière release, télécharge le binaire de son système, vérifie la somme de
contrôle, remplace son propre exécutable puis se relance. Les données (profils, mesures) ne sont jamais touchées.
"""
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from urllib.error import HTTPError, URLError

import version

DEPOT = "acarpm/betterSon"
API = f"https://api.github.com/repos/{DEPOT}/releases/latest"
ASSETS = {"windows": "BetterSon-windows.exe", "macos": "BetterSon-macos.zip", "linux": "BetterSon-linux"}
SOMMES = "SHA256SUMS.txt"


class ErreurMaj(Exception):
    """Erreur de mise à jour, avec un message lisible par l'opérateur."""


def systeme():
    if sys.platform.startswith("win"):
        return "windows"
    return "macos" if sys.platform == "darwin" else "linux"


def installe():
    """True si on tourne depuis un exécutable packagé (les mises à jour ne concernent que ce cas)."""
    return bool(getattr(sys, "frozen", False))


def _numeros(v):
    """'v1.2.3' -> (1, 2, 3) ; 'dev' -> ()."""
    return tuple(int(x) for x in re.findall(r"\d+", v.lstrip("vV").split("-")[0]))


def _requete(url):
    return urllib.request.Request(url, headers={"User-Agent": "BetterSon-updater",
                                                "Accept": "application/vnd.github+json"})


def _contexte_ssl():
    """Certificats HTTPS : ceux de certifi, embarqués avec le logiciel.

    Une application packagée ne peut pas compter sur ceux du système : son OpenSSL cherche les certificats dans le dossier
    de la machine où elle a été construite, qui n'existe pas sur le poste de l'opérateur (échec silencieux de toute requête HTTPS).
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - sans certifi on retombe sur les certificats du système
        return ssl.create_default_context()


def _ouvrir(url, timeout):
    return urllib.request.urlopen(_requete(url), timeout=timeout, context=_contexte_ssl())


def _expliquer(e):
    """Message lisible pour une erreur réseau."""
    if isinstance(e, HTTPError):
        if e.code == 403:
            return "limite de requêtes GitHub atteinte, réessayez dans un moment"
        if e.code == 404:
            return "aucune release trouvée (dépôt privé ou sans release ?)"
        return f"GitHub a répondu {e.code}"
    raison = getattr(e, "reason", e)
    if isinstance(raison, ssl.SSLError):
        return f"certificats HTTPS invalides ou introuvables ({raison})"
    return f"réseau indisponible ({raison})"


def verifier(timeout=8):
    """(infos, erreur) : infos de la dernière release publiée (hors brouillons / préversions) ; en cas d'échec,
    infos vaut None et erreur explique pourquoi (jamais d'échec silencieux)."""
    try:
        with _ouvrir(API, timeout) as r:
            data = json.load(r)
    except (URLError, OSError) as e:
        return None, _expliquer(e)
    except ValueError:
        return None, "réponse de GitHub illisible"
    tag = str(data.get("tag_name") or "")
    return {"tag": tag, "version": _numeros(tag), "notes": data.get("body") or "",
            "assets": {a["name"]: a["browser_download_url"] for a in data.get("assets", []) if "name" in a}}, None


def derniere_version(timeout=8):
    """Comme verifier(), sans le message d'erreur : infos de la dernière release, ou None."""
    return verifier(timeout)[0]


def plus_recente(info, courante=None):
    """True si `info` est une version plus récente que celle installée, avec le binaire de ce système."""
    courante = version.__version__ if courante is None else courante
    if not info or courante == "dev" or not info["version"]:
        return False
    return (info["version"] > _numeros(courante)
            and ASSETS[systeme()] in info["assets"] and SOMMES in info["assets"])


# ---------- téléchargement ----------
def _somme_attendue(info, nom):
    with _ouvrir(info["assets"][SOMMES], 15) as r:
        for ligne in r.read().decode("utf-8", "replace").splitlines():
            morceaux = ligne.split()
            if len(morceaux) == 2 and morceaux[1].lstrip("*") == nom:
                return morceaux[0].lower()
    raise ErreurMaj("Somme de contrôle introuvable pour ce fichier : mise à jour annulée.")


def telecharger(info, progression=None):
    """Télécharge le binaire du système dans un dossier temporaire et vérifie sa somme SHA-256."""
    nom = ASSETS[systeme()]
    try:
        attendu = _somme_attendue(info, nom)
        dest = os.path.join(tempfile.mkdtemp(prefix="betterson-maj-"), nom)
        h = hashlib.sha256()
        with _ouvrir(info["assets"][nom], 30) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            fait = 0
            while True:
                bloc = r.read(1 << 16)
                if not bloc:
                    break
                f.write(bloc)
                h.update(bloc)
                fait += len(bloc)
                if progression:
                    progression(fait, total)
    except (URLError, OSError) as e:
        raise ErreurMaj(f"Téléchargement impossible : {e}") from e
    if h.hexdigest() != attendu:
        os.remove(dest)
        raise ErreurMaj("Le fichier téléchargé est corrompu (somme de contrôle différente) : mise à jour annulée.")
    return dest


# ---------- remplacement ----------
def _app_macos():
    p = os.path.abspath(sys.executable)
    while p != os.path.dirname(p) and not p.endswith(".app"):
        p = os.path.dirname(p)
    if not p.endswith(".app"):
        raise ErreurMaj("Application macOS introuvable : réinstallez le logiciel.")
    return p


def _chemin_actuel():
    return _app_macos() if systeme() == "macos" else os.path.abspath(sys.executable)


def _remplacer_fichier(nouveau, cible):
    """Windows / Linux : l'exécutable en cours peut être renommé (pas supprimé) ; on glisse le nouveau à sa place."""
    voisin, ancien = cible + ".new", cible + ".old"
    try:
        shutil.copyfile(nouveau, voisin)  # même dossier que la cible : renommage atomique
        os.chmod(voisin, 0o755)
        if os.path.exists(ancien):
            os.remove(ancien)
        os.replace(cible, ancien)
        try:
            os.replace(voisin, cible)
        except OSError:
            os.replace(ancien, cible)  # échec : on remet l'ancienne version
            raise
    except OSError as e:
        raise ErreurMaj(f"Impossible de remplacer le programme ({e}). Dossier non modifiable ?") from e
    finally:
        if os.path.exists(voisin):
            os.remove(voisin)


def _remplacer_app(archive, app):
    """macOS : décompresse l'archive (ditto conserve la signature) puis échange le dossier .app."""
    ancien = app + ".old"
    try:
        tmp = tempfile.mkdtemp(dir=os.path.dirname(app), prefix=".maj-")
    except OSError as e:
        raise ErreurMaj(f"Impossible d'écrire à côté de l'application ({e}). Réinstallez le logiciel.") from e
    try:
        subprocess.run(["ditto", "-x", "-k", archive, tmp], check=True, capture_output=True)
        nouveau = os.path.join(tmp, os.path.basename(app))
        if not os.path.isdir(nouveau):
            raise ErreurMaj("Archive de mise à jour invalide.")
        if os.path.exists(app):
            shutil.rmtree(ancien, ignore_errors=True)
            os.rename(app, ancien)
        try:
            os.rename(nouveau, app)
        except OSError:
            if os.path.exists(ancien):
                os.rename(ancien, app)
            raise
    except (OSError, subprocess.CalledProcessError) as e:
        raise ErreurMaj(f"Impossible de remplacer l'application ({e}).") from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cible_macos(app):
    """Où installer la mise à jour sur macOS.

    Une application téléchargée puis lancée sans avoir été déplacée tourne depuis un emplacement TEMPORAIRE en lecture seule
    (« App Translocation » : /private/var/folders/.../AppTranslocation/...) : on ne peut ni l'y remplacer ni écrire à côté.
    Il en va de même d'un dossier non modifiable. Dans ces cas, la nouvelle version est installée dans ~/Applications
    (toujours modifiable, sans droits administrateur) et c'est elle qui est relancée.
    """
    if "/AppTranslocation/" in app or not os.access(os.path.dirname(app), os.W_OK):
        dossier = os.path.join(os.path.expanduser("~"), "Applications")
        os.makedirs(dossier, exist_ok=True)
        return os.path.join(dossier, os.path.basename(app))
    return app


def appliquer(fichier, cible=None):
    """Remplace le programme installé par le fichier téléchargé ; renvoie le chemin à relancer
    (qui peut différer du programme en cours sur macOS, voir _cible_macos)."""
    cible = cible or _chemin_actuel()
    if systeme() == "macos":
        cible = _cible_macos(cible)
        _remplacer_app(fichier, cible)
    else:
        _remplacer_fichier(fichier, cible)
    return cible


def relancer(chemin):
    """Démarre la nouvelle version (le programme actuel doit ensuite se fermer)."""
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")  # le fils ne doit pas réutiliser le dossier temporaire du père
    if systeme() == "macos":
        subprocess.Popen(["open", "-n", chemin], env=env)
    elif systeme() == "windows":
        subprocess.Popen([chemin], env=env, close_fds=True,
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        subprocess.Popen([chemin], env=env, close_fds=True, start_new_session=True)


def nettoyer():
    """Supprime les restes de l'ancienne version laissés par la mise à jour précédente."""
    if not installe():
        return
    try:
        ancien = _chemin_actuel() + ".old"
        if os.path.isdir(ancien):
            shutil.rmtree(ancien, ignore_errors=True)
        elif os.path.exists(ancien):
            os.remove(ancien)
    except (OSError, ErreurMaj):
        pass
