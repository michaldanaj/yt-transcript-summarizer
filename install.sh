#!/usr/bin/env bash
# Instaluje lub aktualizuje aplikację Transkrypcje YouTube.
#
# Użycie:
#   ./install.sh            # instalacja lub aktualizacja
#   ./install.sh --remove   # odinstalowanie
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="transkrypcje"
ICON_NAME="transkrypcje-gui"
ICON_SRC="$SCRIPT_DIR/$ICON_NAME.svg"
ICON_DST="$HOME/.local/share/icons/$ICON_NAME.svg"
DESKTOP_SRC="$SCRIPT_DIR/$ICON_NAME.desktop"
DESKTOP_DST="$HOME/.local/share/applications/$ICON_NAME.desktop"

# --- Odinstalowanie ---
if [[ "${1:-}" == "--remove" ]]; then
    echo "Odinstalowuję $APP_NAME..."
    uv tool uninstall "$APP_NAME" 2>/dev/null && echo "  Pakiet usunięty" || echo "  Pakiet nie był zainstalowany"
    rm -f "$ICON_DST"   && echo "  Ikona usunięta"
    rm -f "$DESKTOP_DST" && echo "  Wpis .desktop usunięty"
    echo "Gotowe."
    exit 0
fi

# --- Sprawdź uv ---
if ! command -v uv &>/dev/null; then
    echo "Błąd: uv nie jest zainstalowane (https://docs.astral.sh/uv/)" >&2
    exit 1
fi

# --- Instalacja / aktualizacja pakietu ---
echo "Instaluję $APP_NAME..."
if uv tool list 2>/dev/null | grep -q "^$APP_NAME "; then
    uv tool install --reinstall "$SCRIPT_DIR"
    echo "  Zaktualizowano."
else
    uv tool install "$SCRIPT_DIR"
    echo "  Zainstalowano."
fi

# --- Ikona ---
mkdir -p "$(dirname "$ICON_DST")"
cp "$ICON_SRC" "$ICON_DST"
echo "  Ikona: $ICON_DST"

# --- Wpis .desktop ---
mkdir -p "$(dirname "$DESKTOP_DST")"
cp "$DESKTOP_SRC" "$DESKTOP_DST"
echo "  Desktop: $DESKTOP_DST"

echo "Gotowe. Uruchom: transkrypcje-gui"
