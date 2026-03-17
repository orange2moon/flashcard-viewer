# Flashcard Viewer

This is a flashcard viewer intended for ESL classrooms. That is, it has some features that only ESL teachers would find useful. If this is not you, no need to read any further.


## How it works

1. Add a gallery of flashcards
2. Click on the gallery in the app
3. Use the flashcards in activities and games.

Need more? You can...
- Choose to have labels displayed on your flashcard.
- Choose to have a "stinger" flashcard displayed randomly during the game to cause a mixup in the way the game is played.

That's about it. I wanted to keep the app simple. I don't plan on adding more features to this version. Possibly if this app is useful to a lot of people then I will re-write it using a different gui framework that is faster.

## Important things to know

The app does not copy the flashcard images into it's own folder. That means when you add a gallery it doesn't copy (duplicate) the images. That also means, that if you download a bunch a images to your downloads folder and add that gallery to the app, then delete the downloads folder, you will get an error in the app, possibly crashing the app.

I will probably change this behavior soon because it can be confusing.

## Requirements

You need the following python packages.

- Python 3.9+
- Pillow
- ttkbootstrap
- tomli-w

## Install

Installation is easy if you are on Linux with the GNOME desktop and if you know how to user the command line a little bit. I hope to make it easy for everyone later on. But right now this is all I can offer.

```python
git clone https://github.com/orange2moon/flashcard-viewer
git@github.com:orange2moon/flashcard-viewer.git
cd flashcard-viewer
pipx install . --force
linux-gnome-install.sh
```

The script `linux-gnome-install.sh` does the following
1. Edits the flashcard-viewer.desktop file and installs it for the local user.
2. copies app assets to ~/.local/share/flashcard-viewer/assets
3. Installs an app icon for the local user

## License

This project is licensed under the GNU General Public License v3.0. See the COPYING file for details.

