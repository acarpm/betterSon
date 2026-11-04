#!/usr/bin/env bash
# Installe BatConnect (macOS Apple Silicon / Linux x86_64) depuis la dernière release GitHub.
#   curl -fsSL https://raw.githubusercontent.com/acarpm/betterSon/main/install.sh | bash
# Relancer la même commande réinstalle la dernière version. Les données (profils, mesures) ne sont pas touchées.
set -euo pipefail

DEPOT="acarpm/betterSon"
URL="${BATCONNECT_BASE_URL:-https://github.com/${DEPOT}/releases/latest/download}"
OS="$(uname -s)"
ARCH="$(uname -m)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Installation de BatConnect"

telecharger() { curl -fsSL --retry 3 -o "$2" "$1" || { echo "Téléchargement impossible : $1" >&2; exit 1; }; }

verifier() {  # $1 = fichier, $2 = nom dans SHA256SUMS.txt
  local attendu reel
  attendu="$(grep -E "[ *]$2\$" "$TMP/SHA256SUMS.txt" | awk '{print $1}' | head -1)"
  [ -n "$attendu" ] || { echo "Somme de contrôle introuvable pour $2" >&2; exit 1; }
  if command -v sha256sum >/dev/null 2>&1; then reel="$(sha256sum "$1" | awk '{print $1}')"
  else reel="$(shasum -a 256 "$1" | awk '{print $1}')"; fi
  [ "$attendu" = "$reel" ] || { echo "Fichier corrompu (somme de contrôle différente), installation annulée." >&2; exit 1; }
}

case "$OS" in
  Darwin)
    [ "$ARCH" = "arm64" ] || { echo "Seuls les Mac Apple Silicon (M1 et suivants) sont pris en charge." >&2; exit 1; }
    ASSET="BatConnect-macos.zip"
    telecharger "$URL/$ASSET" "$TMP/$ASSET"
    telecharger "$URL/SHA256SUMS.txt" "$TMP/SHA256SUMS.txt"
    verifier "$TMP/$ASSET" "$ASSET"
    DEST="$HOME/Applications"
    mkdir -p "$DEST"
    rm -rf "$DEST/BatConnect.app"
    ditto -x -k "$TMP/$ASSET" "$DEST"
    xattr -dr com.apple.quarantine "$DEST/BatConnect.app" 2>/dev/null || true
    echo "==> Installé : $DEST/BatConnect.app"
    echo "    Lancez-le depuis le Finder (Dossier Applications de votre session) ou avec : open \"$DEST/BatConnect.app\""
    ;;
  Linux)
    [ "$ARCH" = "x86_64" ] || { echo "Seul Linux x86_64 est pris en charge (ici : $ARCH)." >&2; exit 1; }
    ASSET="BatConnect-linux"
    telecharger "$URL/$ASSET" "$TMP/$ASSET"
    telecharger "$URL/SHA256SUMS.txt" "$TMP/SHA256SUMS.txt"
    verifier "$TMP/$ASSET" "$ASSET"
    DEST="$HOME/.local/share/BatConnect"
    mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications"
    install -m 755 "$TMP/$ASSET" "$DEST/BatConnect.new"
    mv -f "$DEST/BatConnect.new" "$DEST/BatConnect"   # remplacement atomique, même si le logiciel est ouvert
    ln -sf "$DEST/BatConnect" "$HOME/.local/bin/batconnect"
    cat > "$HOME/.local/share/applications/batconnect.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=BatConnect
Comment=Test de batterie
Exec=$DEST/BatConnect
Terminal=false
Categories=Utility;
DESKTOP
    echo "==> Installé : $DEST/BatConnect  (commande : batconnect)"
    if ! id -nG | tr ' ' '\n' | grep -qx dialout; then
      echo
      echo "!!  Pour accéder à la charge en USB, votre utilisateur doit être dans le groupe « dialout » :"
      echo "      sudo usermod -aG dialout \$USER   puis fermez et rouvrez votre session."
    fi
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "    (ajoutez ~/.local/bin à votre PATH pour utiliser la commande « batconnect »)";; esac
    ;;
  *)
    echo "Système non pris en charge : $OS. Sous Windows, utilisez install.ps1 (voir le README)." >&2
    exit 1
    ;;
esac
echo "==> Terminé. Les prochaines versions seront proposées automatiquement dans le logiciel."
