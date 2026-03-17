import sqlite3
from flashcard_viewer.storage_errors import StorageErrors
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import tomllib
import tomli_w
import hashlib
import math


from dataclasses import dataclass


@dataclass
class GalleryImage:
    path: Path
    name: str

    def sort_key(self):
        return self.path.stem.lower()

    def __str__(self):
        return f"{self.name}:{self.path}"


class DataStorage:
    def __init__(self):
        self.BASE_PATH = Path.home() / ".local" / "share" / "flashcard-viewer"

        self.save_path = self.BASE_PATH / "galleries.db"

        self.CONFIG_DIR = Path.home() / ".config" / "flashcard-viewer"
        self.CONFIG_FILE = self.CONFIG_DIR / "config.toml"
        self.allowed_image_types = [".png", ".jpg", ".webp"]
        self.default_image_types = [".png", ".webp"]
        self.config = {}

        self.sort_style = ["random", "descending", "ascending"]

        self.CACHE_DIR = (
            Path.home() / ".local" / "share" / "flashcard-viewer" / "cache"
        )
        self.ASSETS_DIR = (
            Path.home() / ".local" / "share" / "flashcard-viewer" / "assets"
        )
        self.stinger_dir = self.CACHE_DIR / "stingers"
        self.default_thumbnail = None

        end_path = self.ASSETS_DIR / "end_flashcard.png"
        end_name = "The End"
        self.end_flashcard = GalleryImage(path=end_path, name=end_name)

    def _draw_green_checkmark(self):

        width, height = 800, 600
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        p1 = (200, 330)  # start
        p2 = (360, 480)  # bottom corner
        p3 = (620, 180)  # end

        draw.line([p1, p2, p3], fill=(0, 160, 0), width=70, joint="curve")
        return img

    def _draw_question_mark(self):
        size = 140
        img = Image.new(
            "RGB", (size, size), (220, 220, 220)
        )  # light gray background

        draw = ImageDraw.Draw(img)

        # Load a font (fallback to default if none available)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        except IOError:
            font = ImageFont.load_default()

        text = "?"

        # Measure text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Compute centered position
        x = (size - text_w) // 2
        y = (size - text_h) // 2

        # Draw text
        draw.text((x, y), text, fill=(80, 80, 80), font=font)

        return img

    def _draw_gear_icon(self):

        size = 32
        center = size // 2

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        gear_color = (70, 75, 85, 255)

        # Draw main gear body
        outer_radius = 10
        draw.ellipse(
            (
                center - outer_radius,
                center - outer_radius,
                center + outer_radius,
                center + outer_radius,
            ),
            fill=gear_color,
        )

        # Draw gear teeth
        teeth = 8
        tooth_length = 5
        tooth_width = 4

        for i in range(teeth):
            angle = (2 * math.pi / teeth) * i

            x = center + math.cos(angle) * outer_radius
            y = center + math.sin(angle) * outer_radius

            dx = math.cos(angle) * tooth_length
            dy = math.sin(angle) * tooth_length

            draw.line((x, y, x + dx, y + dy), fill=gear_color, width=tooth_width)

        # Draw center hole
        inner_radius = 4
        draw.ellipse(
            (
                center - inner_radius,
                center - inner_radius,
                center + inner_radius,
                center + inner_radius,
            ),
            fill=(220, 220, 220, 255),
        )

        return img

    def _draw_trash_icon(self):

        size = 32
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Colors
        # #FFFFFF
        # #FF4400
        outline = (40, 40, 40, 255)
        fill = (255, 68, 0, 255)

        # Lid
        draw.rectangle((8, 6, 24, 9), fill=fill, outline=outline)

        # Lid handle
        draw.rectangle((13, 4, 19, 6), fill=fill, outline=outline)

        # Trash can body
        draw.rectangle((10, 9, 22, 26), fill=fill, outline=outline)

        # Bottom lip
        draw.rectangle((9, 26, 23, 28), fill=fill, outline=outline)

        # Vertical slats
        draw.line((13, 11, 13, 25), fill=outline, width=1)
        draw.line((16, 11, 16, 25), fill=outline, width=1)
        draw.line((19, 11, 19, 25), fill=outline, width=1)

        return img

    def _ensure_default_end_flashcard(self):
        if not self.end_flashcard.path.exists():
            img = self._draw_green_checkmark()
            img.save(self.end_flashcard.path)

    def _ensure_default_thumbnail(self):
        if not self.default_thumbnail.exists():
            img = self._draw_question_mark()
            img.save(self.default_thumbnail)

    def _ensure_default_trash_icon(self):
        if not self.config["trash_icon_path"]:
            return

        elif not isinstance(self.config["trash_icon_path"], Path):
            return

        elif not self.config["trash_icon_path"].exists():
            img = self._draw_trash_icon()
            img.save(self.config["trash_icon_path"])

    def _ensure_default_settings_icon(self):
        if not self.config["settings_icon_path"]:
            return

        elif not isinstance(self.config["settings_icon_path"], Path):
            return

        elif not self.config["settings_icon_path"].exists():
            img = self._draw_gear_icon()
            img.save(self.config["settings_icon_path"])

    def start(self):
        """Load all the galleries from the database.
        Create the database if it doesn't exists.
        Validate the database if it exists"""

        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if not self.BASE_PATH.exists():
            self.BASE_PATH.mkdir(parents=True, exist_ok=True)

        if not self.CONFIG_DIR.exists():
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not self.ASSETS_DIR.exists():
            self.ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        if not self.stinger_dir.exists():
            self.stinger_dir.mkdir(parents=True, exist_ok=True)

        self.config = self.load_config()

        self.default_thumbnail = self.ASSETS_DIR / "default.png"

        trash = self.ASSETS_DIR / "trash.png"
        self.config["trash_icon_path"] = trash

        settings = self.ASSETS_DIR / "settings.png"
        self.config["settings_icon_path"] = settings

        # Check the filesystem
        if not self.BASE_PATH.is_dir():
            raise NotADirectoryError(self.BASE_PATH)

        if not self.save_path.exists():
            self.create_new_database()
            # done

        else:
            try:
                self.validate_database()
            except StorageErrors:
                self.remove_bad_db(self.save_path)
                self.create_new_database()

        self._ensure_default_thumbnail()
        self._ensure_default_trash_icon()
        self._ensure_default_settings_icon()
        self._ensure_default_end_flashcard()

        if not self.config.get("percent"):
            self.config["percent"] = 20

    def get_last_path(self):
        return self.config.get("last_path", None)

    def add_stinger_to_gallery(self, gallery_id, stinger_id):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO gsting (g_id, s_id) VALUES (?, ?)",
                (gallery_id, stinger_id),
            )

    def update_gallery_settings(
        self,
        id: int,
        path: Path,
        name: str,
        sort: str,
        loop: bool,
        captions: bool,
        stingers: dict,
    ):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute(
                """
                UPDATE galleries
                SET name = ?, path = ?, sort = ?, loop = ?, captions = ?
                WHERE id = ?
            """,
                (
                    name,
                    str(path.resolve()),
                    self.sort_to_int(sort),
                    loop,
                    captions,
                    id,
                ),
            )

        self.stinger_remove_from_gallery(id)
        for stinger in stingers:
            self.add_stinger_to_gallery(id, stinger)

    def load_config(self):
        if not self.CONFIG_FILE.exists():
            return {}

        with open(self.CONFIG_FILE, "rb") as f:
            mytoml = tomllib.load(f)

        # last path
        last_path = mytoml.get("last_path", None)
        if last_path:
            p = Path(last_path)
            mytoml["last_path"] = p if p.is_dir() else None

        # image types
        image_types = mytoml.get("image_types")
        if image_types:
            mytoml["image_types"] = [
                t.lower()
                for t in image_types
                if t.lower() in self.allowed_image_types
            ]

        if not image_types:
            mytoml["image_types"] = self.default_image_types

        return mytoml

    def save_config(self):
        if not self.CONFIG_DIR.exists():
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        serializable = {
            key: str(value) if isinstance(value, Path) else value
            for key, value in self.config.items()
        }

        with open(self.CONFIG_FILE, "wb") as f:
            tomli_w.dump(serializable, f)

    def remember_last_path(self, last_path):
        path = Path(last_path).resolve()
        if not path.is_dir():
            return None

        self.config["last_path"] = path

    def remove_bad_db(self, db_path: Path) -> Path | None:

        if db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bad_path = db_path.with_name(
                f"{db_path.stem}_{timestamp}{db_path.suffix}"
            )

            db_path.rename(bad_path)
            return bad_path

    def validate_database(self, load_file=None):
        """check for the presence of a table galleries
        raise an error if there is a problem"""

        if load_file is None:
            load_file = self.save_path

        if not load_file.exists():
            raise StorageErrors(f"File not found {load_file}")

        try:
            with sqlite3.connect(load_file) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys = ON")
                cur = conn.cursor()

                # Check tables
                cur.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                """)
                tables = {row[0] for row in cur.fetchall()}

                required_tables = {"galleries", "stingers", "images"}
                missing_tables = required_tables - tables

                if missing_tables:
                    raise StorageErrors(
                        f"Database Missing tables: {', '.join(missing_tables)}"
                    )

        except sqlite3.DatabaseError as e:
            raise StorageErrors(f"Database file is corrupt or invalid: {e}")

    def create_new_database(self, save_path=None):
        """Create a new database with the table galleries
        The galleries table should hold file paths
        and names."""

        if save_path is None:
            save_path = self.save_path

        with sqlite3.connect(save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS galleries (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    name TEXT,
                    icon TEXT,
                    sort INT DEFAULT 0,
                    loop BOOLEAN DEFAULT 1,
                    captions BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stingers (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    name TEXT,
                    icon TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    gallery_id INTEGER NOT NULL,
                    ipath TEXT NOT NULL,
                    iname TEXT,
                    FOREIGN KEY (gallery_id) REFERENCES galleries(id)
                )
            """)

            ## GALLERY STINGER RELATIONSHIP
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gsting (
                    g_id INTEGER NOT NULL,
                    s_id INTEGER NOT NULL,
                    FOREIGN KEY (g_id) REFERENCES galleries(id),
                    FOREIGN KEY (s_id) REFERENCES stingers(id)
                )
            """)

    def stinger_dict(self, id, path, name, icon):
        stinger = {}

        stinger["id"] = id
        stinger["name"] = name
        stinger["path"] = Path(path) if path else None
        stinger["icon"] = Path(icon) if icon else None

        return stinger

    def list_stingers(self):
        """Get all of the data from the stingers table
        path: the path to the image file
        name: the canonical name for the stinger
        icon: the 400x400 icon image file
        """

        stingers = []
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute("SELECT id, path, name, icon FROM stingers")
            for id, path, name, icon in res.fetchall():
                stinger = self.stinger_dict(id, path, name, icon)
                stingers.append(stinger)

        return stingers

    def get_stinger(self, id: int):
        """Get all of the data from the stingers table
        path: the path to the image file
        name: the canonical name for the stinger
        icon: the 400x400 icon image file
        """

        stinger = {}
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                """
                SELECT id, path, name, icon FROM stingers
                WHERE id = ?
                """,
                id,
            )
            data = res.fetchone()
            if data:
                id, path, name, icon = data
                stinger = self.stinger_dict(id, path, name, icon)

        return stinger

    def get_stingers_for_gallery(self, gallery_id):
        stinger_id_list = []
        with sqlite3.connect(self.save_path) as conn:
            res = conn.execute(
                """
                SELECT s_id FROM gsting
                WHERE g_id = ?
                """,
                (gallery_id,),
            )
            stinger_id_list = res.fetchall()

        total = []
        for id in stinger_id_list:
            stinger = self.get_stinger(id)
            if stinger:
                total.append(stinger)

        return total

    def get_or_create_thumbnail_path(self, path):

        # Use the gallery path as a unique cache key
        cache_key = hashlib.md5(str(path).encode()).hexdigest()
        thumb_path = self.CACHE_DIR / f"{cache_key}.png"

        if not thumb_path.exists():
            if (
                path.is_file()
                and path.suffix.lower() in self.config["image_types"]
            ):
                with Image.open(path) as img:
                    img.thumbnail((140, 140))
                    img.save(thumb_path, "PNG")

            elif path.is_dir():
                images = self.list_images(path)
                if images:
                    image = images[0].path
                    # Downscale and save to cache
                    with Image.open(image) as img:
                        img.thumbnail((140, 140))
                        img.save(thumb_path, "PNG")
                else:
                    thumb_path = self.default_thumbnail
            else:
                thumb_path = self.default_thumbnail

        return thumb_path

    def remember_gallery(self, path, name):
        """Save a path and a name to the database"""

        icon = self.get_or_create_thumbnail_path(path)

        path = Path(path).resolve()
        if not path.is_dir():
            return False

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT OR IGNORE INTO galleries (path, name, icon) VALUES (?, ?, ?)",
                (str(path), name, str(icon)),
            )

        return True

    def remember_stinger(self, path, name):
        """Save a path and a name to the database"""

        if path.is_dir():
            return False

        path = path.copy_into(self.stinger_dir)
        icon = self.get_or_create_thumbnail_path(path)

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT OR IGNORE INTO stingers (path, name, icon) VALUES (?, ?, ?)",
                (str(path), name, str(icon)),
            )

        return True

    def update_stinger(self, id, name):
        """Save a path and a name to the database"""

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "UPDATE stingers SET name = ? WHERE id = ?",
                (name, id),
            )

    def forget_stinger(self, path):
        """Remove a gallery from the database.
        Delete by path because name will not be unique."""

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                "SELECT icon FROM stingers WHERE path = ?",
                (str(path.resolve()),),
            )
            icon_path = res.fetchone()[0]
            conn.execute(
                "DELETE FROM stingers WHERE path = ?",
                (str(path.resolve()),),
            )
            if icon_path:
                icon_path = Path(icon_path)
                if icon_path != self.default_thumbnail:
                    icon_path.unlink()

            if path.exists():
                path.unlink()

    def stinger_remove_from_gallery(self, gallery_id):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                DELETE FROM gsting WHERE g_id = ?
            """,
                (gallery_id,),
            )

    def remember_gallery_icon(self, gallery_path, icon_path):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "UPDATE galleries SET icon = ? WHERE path = ?",
                (icon_path, str(gallery_path.resolve())),
            )

    def update_gallery_icon(self, gallery_path, icon_path):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "UPDATE galleries SET icon = ? WHERE path = ?",
                (icon_path, str(gallery_path.resolve())),
            )

    def forget_gallery(self, path):
        """Remove a gallery from the database.
        Delete by path because name will not be unique."""

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                "SELECT icon FROM galleries WHERE path = ?",
                (str(path.resolve()),),
            )
            icon_path = res.fetchone()[0]
            conn.execute(
                "DELETE FROM galleries WHERE path = ?",
                (str(path.resolve()),),
            )
            if icon_path:
                icon_path = Path(icon_path)
                if icon_path != self.default_thumbnail:
                    icon_path.unlink()

    def get_images_for_path(self, path):
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                """
                SELECT ipath, iname FROM images 
                JOIN galleries ON images.gallery_id = galleries.id
                WHERE path = ?
                """,
                (str(path.resolve()),),
            )
            images = res.fetchall()
            if images:
                d = {path: name for path, name in images}
                return d
            else:
                return {}

    def save_image_name(self, gallery_path, image_path, name):
        """Save or update the display name for a single image."""
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                "SELECT id FROM galleries WHERE path = ?",
                (str(gallery_path.resolve()),),
            )
            row = res.fetchone()
            if not row:
                return
            gallery_id = row[0]
            res = conn.execute(
                "SELECT id FROM images WHERE gallery_id = ? AND ipath = ?",
                (gallery_id, str(image_path.resolve())),
            )
            existing = res.fetchone()
            if existing:
                conn.execute(
                    "UPDATE images SET iname = ? WHERE id = ?",
                    (name, existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO images (gallery_id, ipath, iname) VALUES (?, ?, ?)",
                    (gallery_id, str(image_path.resolve()), name),
                )

    def list_images(self, path, recursive=False):

        named_images = self.get_images_for_path(path)

        f_and_names = []
        for f in path.iterdir():
            if f.is_file() and f.suffix.lower() in self.config["image_types"]:
                if named_images.get(str(f)):
                    name = named_images.get(str(f))
                else:
                    name = f.stem

                f_and_names.append(GalleryImage(path=Path(f), name=name))

        return f_and_names

    def sort_to_str(self, sort):
        try:
            return self.sort_style[sort]
        except ValueError:
            return self.sort_style[0]

    def sort_to_int(self, sort):
        try:
            return self.sort_style.index(sort.lower())
        except ValueError:
            return 0

    def gallery_query_to_dict(self, id, path, name, icon, sort, loop, captions):
        gallery = {}
        gallery_dir = Path(path)
        gallery["id"] = id
        gallery["path"] = gallery_dir
        gallery["name"] = name
        gallery["icon"] = Path(icon) if icon else None
        gallery["sort"] = self.sort_to_str(sort)
        gallery["loop"] = True if loop == 1 else False
        gallery["captions"] = True if captions == 1 else False
        gallery["stingers"] = self.get_stingers_for_gallery(id)

        if gallery_dir.is_dir():
            gallery["valid"] = True
            gallery["images"] = self.list_images(gallery_dir)

        else:
            gallery["valid"] = False
            gallery["images"] = None

        return gallery

    def list_galleries(self):
        """Get all of the data from the galleries table"""

        galleries = []
        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                "SELECT id, path, name, icon , sort, loop, captions FROM galleries"
            )
            for gallery_data in res.fetchall():
                if gallery_data:
                    id, path, name, icon, sort, loop, captions = gallery_data
                    gallery = self.gallery_query_to_dict(
                        id, path, name, icon, sort, loop, captions
                    )
                    galleries.append(gallery)

        return galleries

    def scan_gallery(self, gallery_path):
        """Scan one gallery and return its metadata."""

        gallery_path = gallery_path.resolve()

        with sqlite3.connect(self.save_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            res = conn.execute(
                "SELECT id, path, name, icon, sort, loop, captions FROM galleries WHERE path = ?",
                (str(gallery_path),),
            )

            row = res.fetchone()

            if row is None:
                return None
            else:
                if row:
                    id, path, name, icon, sort, loop, captions = row
                    return self.gallery_query_to_dict(
                        id, path, name, icon, sort, loop, captions
                    )
