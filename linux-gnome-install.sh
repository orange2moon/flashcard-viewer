#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if flashcard-viewer is installed; if not, offer to install it
if ! command -v flashcard-viewer &>/dev/null; then
    echo "flashcard-viewer command not found."

    HAS_PIPX=false
    HAS_UV=false
    command -v pipx &>/dev/null && HAS_PIPX=true
    command -v uv &>/dev/null && HAS_UV=true

    if ! $HAS_PIPX && ! $HAS_UV; then
        echo "Error: Neither pipx nor uv was found. Please install flashcard-viewer manually."
        exit 1
    fi

    if $HAS_PIPX && $HAS_UV; then
        echo "Both pipx and uv are available. Which would you like to use to install flashcard-viewer?"
        echo "  1) pipx"
        echo "  2) uv"
        read -rp "Enter choice [1/2]: " INSTALL_CHOICE
        case "$INSTALL_CHOICE" in
            1) INSTALLER="pipx" ;;
            2) INSTALLER="uv" ;;
            *) echo "Invalid choice. Exiting."; exit 1 ;;
        esac
    elif $HAS_PIPX; then
        read -rp "Install flashcard-viewer using pipx? [Y/n]: " CONFIRM
        [[ "$CONFIRM" =~ ^[Nn] ]] && exit 0
        INSTALLER="pipx"
    else
        read -rp "Install flashcard-viewer using uv? [Y/n]: " CONFIRM
        [[ "$CONFIRM" =~ ^[Nn] ]] && exit 0
        INSTALLER="uv"
    fi

    echo "Installing flashcard-viewer from $SCRIPT_DIR using $INSTALLER..."
    if [ "$INSTALLER" = "pipx" ]; then
        pipx install "$SCRIPT_DIR" --force
    else
        uv tool install "$SCRIPT_DIR" --force
    fi

    if ! command -v flashcard-viewer &>/dev/null; then
        echo "Error: Installation failed or flashcard-viewer is not in PATH."
        exit 1
    fi

    echo "flashcard-viewer installed successfully."
else
    read -rp "flashcard-viewer is already installed. Reinstall? [y/N]: " CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy] ]]; then
        HAS_PIPX=false
        HAS_UV=false
        command -v pipx &>/dev/null && HAS_PIPX=true
        command -v uv &>/dev/null && HAS_UV=true

        if ! $HAS_PIPX && ! $HAS_UV; then
            echo "Error: Neither pipx nor uv was found. Please reinstall flashcard-viewer manually."
            exit 1
        fi

        if $HAS_PIPX && $HAS_UV; then
            echo "Both pipx and uv are available. Which would you like to use to reinstall flashcard-viewer?"
            echo "  1) pipx"
            echo "  2) uv"
            read -rp "Enter choice [1/2]: " INSTALL_CHOICE
            case "$INSTALL_CHOICE" in
                1) INSTALLER="pipx" ;;
                2) INSTALLER="uv" ;;
                *) echo "Invalid choice. Exiting."; exit 1 ;;
            esac
        elif $HAS_PIPX; then
            INSTALLER="pipx"
        else
            INSTALLER="uv"
        fi

        echo "Reinstalling flashcard-viewer from $SCRIPT_DIR using $INSTALLER..."
        if [ "$INSTALLER" = "pipx" ]; then
            pipx install "$SCRIPT_DIR" --force
        else
            uv tool install "$SCRIPT_DIR" --force
        fi
    fi
fi

BIN_DIR="${1:-$(dirname "$(command -v flashcard-viewer)")}"

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
