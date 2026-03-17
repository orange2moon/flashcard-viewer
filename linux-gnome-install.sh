#!/bin/bash

BIN_DIR="${1:-$HOME/.local/bin}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESKTOP_SRC="$SCRIPT_DIR/flashcard-viewer.desktop"

DESKTOP_DEST="$HOME/.local/share/applications"
ICON_DEST="$HOME/.local/share/icons/hicolor/256x256/apps"
ASSETS_SRC="$SCRIPT_DIR/assets"
ASSETS_DEST="$HOME/.local/share/flashcard-viewer/assets"

ICON_SRC="$ASSETS_SRC/flashcard-viewer.png"

# Check source files exist
if [ ! -f "$DESKTOP_SRC" ]; then
    echo "Error: flashcard-viewer.desktop not found in current directory"
    exit 1
fi

if [ ! -f "$ICON_SRC" ]; then
    echo "Error: flashcard-viewer.png not found in current directory"
    exit 1
fi

if [ ! -d "$ASSETS_SRC" ]; then
    echo "Error: assets folder not found in current directory"
    exit 1
fi

# Create destination directories if they don't exist
mkdir -p "$DESKTOP_DEST"
mkdir -p "$ICON_DEST"
mkdir -p "$ASSETS_DEST"

sed "s|INSTALL_PREFIX|$BIN_DIR|g" "$DESKTOP_SRC" > "$DESKTOP_DEST/flashcard-viewer.desktop"
echo "Installed desktop file to $DESKTOP_DEST"

cp "$ICON_SRC" "$ICON_DEST/flashcard-viewer.png"
echo "Installed icon to $ICON_DEST"

cp "$ASSETS_SRC/"* "$ASSETS_DEST/"
echo "Installed assets to $ASSETS_DEST"

# Update caches
gtk-update-icon-cache ~/.local/share/icons/hicolor/
update-desktop-database "$DESKTOP_DEST"

echo "Done!"
echo "If you have not yes installed the python componentes of flashcard-viewer"
echo "you must do that before you will be able to run the app."
echo "you can install the python components with pipx or uv"
echo "Example:"
echo "pipx install . --force"
