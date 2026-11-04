#!/usr/bin/env bash
# Installe BetterSon (macOS Apple Silicon / Linux x86_64) depuis la dernière release GitHub.
#   curl -fsSL https://raw.githubusercontent.com/acarpm/betterSon/main/install.sh | bash
# Relancer la même commande réinstalle la dernière version. Les données (profils, mesures) ne sont pas touchées.
set -euo pipefail

DEPOT="acarpm/betterSon"
URL="${BATCONNECT_BASE_URL:-https://github.com/${DEPOT}/releases/latest/download}"
OS="$(uname -s)"
ARCH="$(uname -m)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Installation de BetterSon"

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
    ASSET="BetterSon-macos.zip"
    telecharger "$URL/$ASSET" "$TMP/$ASSET"
    telecharger "$URL/SHA256SUMS.txt" "$TMP/SHA256SUMS.txt"
    verifier "$TMP/$ASSET" "$ASSET"
    DEST="$HOME/Applications"
    mkdir -p "$DEST"
    rm -rf "$DEST/BetterSon.app"
    ditto -x -k "$TMP/$ASSET" "$DEST"
    xattr -dr com.apple.quarantine "$DEST/BetterSon.app" 2>/dev/null || true
    echo "==> Installé : $DEST/BetterSon.app"
    echo "    Lancez-le depuis le Finder (Dossier Applications de votre session) ou avec : open \"$DEST/BetterSon.app\""
    ;;
  Linux)
    [ "$ARCH" = "x86_64" ] || { echo "Seul Linux x86_64 est pris en charge (ici : $ARCH)." >&2; exit 1; }
    ASSET="BetterSon-linux"
    telecharger "$URL/$ASSET" "$TMP/$ASSET"
    telecharger "$URL/SHA256SUMS.txt" "$TMP/SHA256SUMS.txt"
    verifier "$TMP/$ASSET" "$ASSET"
    DEST="$HOME/.local/share/BetterSon"
    mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications"
    install -m 755 "$TMP/$ASSET" "$DEST/BetterSon.new"
    mv -f "$DEST/BetterSon.new" "$DEST/BetterSon"   # remplacement atomique, même si le logiciel est ouvert
    ln -sf "$DEST/BetterSon" "$HOME/.local/bin/betterson"
    cat > "$HOME/.local/share/applications/betterson.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=BetterSon
Comment=Test de batterie
Exec=$DEST/BetterSon
Terminal=false
Categories=Utility;
DESKTOP
    echo "==> Installé : $DEST/BetterSon  (commande : betterson)"
    if ! id -nG | tr ' ' '\n' | grep -qx dialout; then
      echo
      echo "!!  Pour accéder à la charge en USB, votre utilisateur doit être dans le groupe « dialout » :"
      echo "      sudo usermod -aG dialout \$USER   puis fermez et rouvrez votre session."
    fi
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "    (ajoutez ~/.local/bin à votre PATH pour utiliser la commande « betterson »)";; esac
    ;;
  *)
    echo "Système non pris en charge : $OS. Sous Windows, utilisez install.ps1 (voir le README)." >&2
    exit 1
    ;;
esac
echo "==> Terminé. Les prochaines versions seront proposées automatiquement dans le logiciel."
