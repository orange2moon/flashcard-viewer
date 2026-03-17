import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path
import random
from PIL import Image, ImageTk
import tkinter.font as tkfont
import threading
from queue import Queue

from flashcard_viewer.data_storage import DataStorage, GalleryImage
from flashcard_viewer.image_folder_browser import ImageFolderBrowser
from flashcard_viewer.image_file_browser import ImageFileBrowser
from flashcard_viewer.data_storage import SortOrder


class FlashCardViewer(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.style = ttk.Style()
        self.edit_mode = False
        self.stinger_edit_mode = False
        self.galleries = None
        self.edit_button = None
        self.image_path = None
        self.image_name = None
        self.gallery_canvas = None
        self.gallery_font = tkfont.Font(size=14, weight="bold")
        self.caption_font = tkfont.Font(size=85, weight="bold")
        font_height = self.caption_font.metrics("linespace")
        # Add some padding (e.g. the label's internal padding)
        # 20px for breathing room
        self.caption_font_clearance = font_height + 20
        self._resize_job = None

        self.setting_font = tkfont.Font(size=10, weight="bold")
        self.gallery_thumbs = {}
        self.root = root
        self.pack(fill=BOTH, expand=True)
        self.all_images_paths = []
        self.show_height = 1000
        self.show_width = 800
        self.image_img = None

        # storage system
        self.storage = DataStorage()
        self.storage.start()
        self.default_thumbnail_img = Image.open(self.storage.default_thumbnail)

        self.end_flashcard = self.storage.end_flashcard
        theme = self.storage.config.get("theme")
        allowed_themes = themes = self.style.theme_names()
        if theme and theme in allowed_themes:
            self.style.theme_use(theme)

        # application state
        self._resize_job = None
        self.current_gallery = None
        self.current_images = []
        self.current_image_index = 0
        self.current_image_index_max = 0
        self.current_photo = None
        self.sort = SortOrder(0)
        self.loop = True
        self.captions = True
        self.show_stinger = False

        # Trash icon for the gallery
        trash_icon_path = self.storage.config["trash_icon_path"]
        if isinstance(trash_icon_path, Path) and trash_icon_path.exists():
            self.trash_icon = ImageTk.PhotoImage(file=trash_icon_path)
        else:
            icon = Image.new("RGBA", (32, 32), (220, 60, 60, 255))
            self.trash_icon = ImageTk.PhotoImage(icon)

        # Setting for the gallery
        settings_icon_path = self.storage.config["settings_icon_path"]
        if isinstance(settings_icon_path, Path) and settings_icon_path.exists():
            self.settings_icon = ImageTk.PhotoImage(file=settings_icon_path)
        else:
            icon = Image.new("RGBA", (32, 32), (128, 128, 128, 255))
            self.settings_icon = ImageTk.PhotoImage(icon)

        # notebook
        self.noteb = ttk.Notebook(self, bootstyle="light")

        self.gallery_frame = self.gallery(self.noteb)
        self.show_frame = self.show(self.noteb)
        self.settings_frame = self.settings(self.noteb)

        self.noteb.add(self.gallery_frame, text="Gallery")
        self.noteb.add(self.show_frame, text="Show")
        self.noteb.add(self.settings_frame, text="App Settings")

        self.noteb.pack(fill=BOTH, expand=True)
        self.noteb.bind("<<NotebookTabChanged>>", self.on_tab_selection_changed)

        # initial gallery load
        # self.load_gallery_view()
        # self.refresh_gallery_grid(new=True)

    def on_tab_selection_changed(self, event):
        tab_text = self.noteb.tab("current", "text")
        if tab_text == "Gallery":
            self.refresh_gallery_grid()
        elif tab_text == "Settings":
            self.refresh_stinger_grid()

    # -------------------------
    # Gallery View
    # -------------------------
    def edit_mode_off(self):

        self.edit_mode = False
        self.edit_button.configure(text="Edit", bootstyle="danger")
        self.refresh_gallery_grid()

    def toggle_edit_mode(self):

        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            self.edit_button.configure(text="Done", bootstyle="warning")
        else:
            self.edit_button.configure(text="Edit", bootstyle="danger")

        self.refresh_gallery_grid()

    def gallery(self, notebook):
        frame = ttk.Frame(notebook, padding=10)

        # --- Scrollable area ---
        scroll_wrapper = ttk.Frame(frame)
        scroll_wrapper.pack(fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(scroll_wrapper, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)

        canvas = ttk.Canvas(scroll_wrapper, yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar.configure(command=canvas.yview)

        # This is the frame that actually holds the gallery tiles
        self.gallery_container = ttk.Frame(canvas)
        canvas_window = canvas.create_window(
            (0, 0), window=self.gallery_container, anchor=NW
        )

        # Update scroll region whenever the gallery content changes size
        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox(ALL))

        def on_canvas_resize(e):
            canvas.itemconfig(canvas_window, width=e.width)

        self.gallery_container.bind("<Configure>", on_frame_configure)
        # canvas.bind("<Configure>", on_canvas_resize)
        self.gallery_canvas = canvas
        canvas.bind(
            "<Configure>",
            lambda e: (on_frame_configure(e), self.refresh_gallery_grid()),
        )

        # Mousewheel scrolling
        def on_mousewheel(e):
            if self.gallery_container.winfo_height() > canvas.winfo_height():
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        self._gallery_mousewheel = on_mousewheel
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # --- Button bar stays OUTSIDE the canvas, so it doesn't scroll ---
        button_bar = ttk.Frame(frame)
        button_bar.pack(fill=X, pady=10)

        self.edit_button = ttk.Button(
            button_bar,
            text="Edit",
            bootstyle="danger",
            command=self.toggle_edit_mode,
        )
        self.edit_button.pack(side=LEFT)

        add_button = ttk.Button(
            button_bar,
            text="+ Add Gallery",
            bootstyle=SUCCESS,
            command=self.add_gallery,
        )
        add_button.pack(side=RIGHT)

        return frame

    def rounded_rect_points(self, x, y, w, h, radius):
        """Generate points for a rounded rectangle."""
        r = radius
        return [
            x + r,
            y,
            x + w - r,
            y,
            x + w,
            y,
            x + w,
            y + r,
            x + w,
            y + h - r,
            x + w,
            y + h,
            x + w - r,
            y + h,
            x + r,
            y + h,
            x,
            y + h,
            x,
            y + h - r,
            x,
            y + r,
            x,
            y,
        ]

    def refresh_gallery_grid(self, new=False):
        canvas = self.gallery_canvas
        canvas.delete("all")

        if new or self.galleries == None:
            self.galleries = self.storage.list_galleries()

        tile_width = 160
        tile_height = 180
        padding = 20

        cols = max(1, canvas.winfo_width() // (tile_width + padding))

        # Store references to PhotoImage objects to prevent garbage collection
        self._tile_images = []

        for i, gallery in enumerate(self.galleries):
            row = i // cols
            col = i % cols

            x = padding + col * (tile_width + padding)
            y = padding + row * (tile_height + padding)

            # Draw background rectangle
            bg = self.style.colors.bg
            canvas.create_polygon(
                self.rounded_rect_points(
                    x, y, tile_width, tile_height, radius=25
                ),
                fill=bg,
                outline=self.style.colors.border,
                width=1,
                smooth=True,
                tags=(
                    f"tile_{i}",
                    f"tile_bg_{i}",
                ),
            )
            # Draw thumbnail
            thumb = self.get_gallery_thumbnail(gallery)
            self._tile_images.append(thumb)  # prevent GC
            thumb_y = (
                y + (tile_height - 20) // 2
            )  # centered vertically, leaving room for text
            canvas.create_image(
                x + tile_width // 2,
                thumb_y,
                image=thumb,
                anchor=CENTER,
                tags=(f"tile_{i}",),
            )

            # Draw name text

            fg = self.style.colors.fg
            canvas.create_text(
                x + tile_width // 2,
                y + tile_height - 20,
                text=gallery["name"],
                fill=fg,
                font=self.gallery_font,
                tags=(f"tile_{i}",),
            )

            if self.edit_mode:
                canvas.create_image(
                    x + tile_width - 4,
                    y + tile_height - 4 - self.trash_icon.height(),
                    image=self.trash_icon,
                    anchor=NE,
                    tags=(f"trash_{i}",),
                )

            canvas.create_image(
                x + 4 + self.settings_icon.width(),
                y + 4,
                image=self.settings_icon,
                anchor=NE,
                tags=(f"settings_{i}",),
            )
            # Bind clicks per tile using tags
            canvas.tag_bind(
                f"tile_{i}",
                "<Button-1>",
                lambda e, g=gallery["path"]: self.open_gallery(g),
            )
            canvas.tag_bind(
                f"settings_{i}",
                "<Button-1>",
                lambda e, g=gallery: self.open_gallery_settings(g, x, y),
            )
            canvas.tag_bind(
                f"trash_{i}",
                "<Button-1>",
                lambda e, p=gallery["path"]: self.delete_gallery(p),
            )
            canvas.tag_bind(
                f"tile_{i}",
                "<Enter>",
                lambda e, tag=f"tile_bg_{i}": self.gallery_canvas.itemconfig(
                    tag, fill=self.style.colors.selectbg
                ),
            )
            canvas.tag_bind(
                f"tile_{i}",
                "<Leave>",
                lambda e, tag=f"tile_bg_{i}": self.gallery_canvas.itemconfig(
                    tag, fill=bg
                ),
            )
        # Update scroll region
        total_rows = -(-len(self.galleries) // cols)  # ceiling division
        total_height = total_rows * (tile_height + padding) + padding
        canvas.configure(scrollregion=(0, 0, canvas.winfo_width(), total_height))

    def _add_trash_icon(self, img_label, image_frame, gallery):
        trash = ttk.Label(
            image_frame,
            image=self.trash_icon,
            cursor="hand2",
            bootstyle="danger",
        )
        trash.image = self.trash_icon
        trash.place(relx=1, rely=0, anchor="ne", x=-4, y=4)
        trash.bind(
            "<Button-1>",
            lambda e, p=gallery["path"]: self.delete_gallery(p),
        )

    def dismiss_settings_popup(self):
        pass

    def open_gallery_settings(self, gallery, x, y):
        if hasattr(self, "_settings_popup"):
            self.gallery_canvas.delete("settings_popup")
            self._settings_popup.destroy()

        # update gallery
        gallery = self.storage.scan_gallery(gallery["path"])
        popup_w = 800
        popup_h = 900
        radius = 15
        shadow_offset = 6
        border = 2

        canvas = self.gallery_canvas
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        scroll_offset = canvas.canvasy(0)

        px = (canvas_width - popup_w) // 2
        py = (canvas_height - popup_h) // 2 + scroll_offset

        colors = self.style.colors

        # Drop shadow (slightly offset, dark and semi-transparent)
        canvas.create_polygon(
            self.rounded_rect_points(
                px + shadow_offset,
                py + shadow_offset,
                popup_w,
                popup_h,
                radius=radius,
            ),
            fill=colors.dark,
            outline="",
            smooth=True,
            tags=("settings_popup",),
        )

        # Border (slightly larger than the inner frame)
        canvas.create_polygon(
            self.rounded_rect_points(
                px - border,
                py - border,
                popup_w + border * 2,
                popup_h + border * 2,
                radius=radius + border,
            ),
            fill=colors.fg,
            outline="",
            smooth=True,
            tags=("settings_popup",),
        )

        # Background
        canvas.create_polygon(
            self.rounded_rect_points(px, py, popup_w, popup_h, radius=radius),
            fill=colors.fg,
            outline="",
            smooth=True,
            tags=("settings_popup",),
        )

        # Outer popup frame
        frame = ttk.Frame(canvas, padding=15)

        # Button bar packed first with side=BOTTOM so it stays visible while content scrolls
        button_bar = ttk.Frame(frame)
        button_bar.pack(side=BOTTOM, fill=X, pady=(5, 0))

        def _restore_gallery_scroll():
            canvas.bind_all("<MouseWheel>", self._gallery_mousewheel)

        def save_and_close():
            selected_stingers = [
                sid for sid, var in stinger_vars.items() if var.get()
            ]
            self.storage.update_gallery_settings(
                id=gallery["id"],
                path=gallery["path"],
                name=name_var.get(),
                sort=SortOrder.from_str(sort_var.get()),
                loop=loop_var.get(),
                captions=captions_var.get(),
                stingers=selected_stingers,
            )
            for img_path_str, iname_var in img_name_vars.items():
                self.storage.save_image_name(
                    gallery["path"], Path(img_path_str), iname_var.get()
                )
            _restore_gallery_scroll()
            canvas.delete("settings_popup")
            canvas.unbind("<Button-1>")
            frame.destroy()
            self.refresh_gallery_grid(new=True)

        def close():
            _restore_gallery_scroll()
            canvas.delete("settings_popup")
            canvas.unbind("<Button-1>")
            frame.destroy()

        ttk.Button(
            button_bar,
            text="Cancel",
            bootstyle="outline-secondary",
            command=close,
        ).pack(side=LEFT)

        ttk.Button(
            button_bar, text="Save", bootstyle="success", command=save_and_close
        ).pack(side=RIGHT)

        # Scrollable content area
        scroll_wrapper = ttk.Frame(frame)
        scroll_wrapper.pack(fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(scroll_wrapper, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)

        inner_canvas = ttk.Canvas(scroll_wrapper, yscrollcommand=scrollbar.set)
        inner_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.configure(command=inner_canvas.yview)

        inner_frame = ttk.Frame(inner_canvas, padding=(0, 0, 8, 0))
        inner_win = inner_canvas.create_window(
            (0, 0), window=inner_frame, anchor=NW
        )

        def on_inner_configure(e):
            inner_canvas.configure(scrollregion=inner_canvas.bbox(ALL))

        def on_inner_canvas_resize(e):
            inner_canvas.itemconfig(inner_win, width=e.width)

        inner_frame.bind("<Configure>", on_inner_configure)
        inner_canvas.bind("<Configure>", on_inner_canvas_resize)

        def _scroll_popup(e):
            inner_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        inner_canvas.bind_all("<MouseWheel>", _scroll_popup)

        ### Gallery ICON
        icon_path = gallery.get("icon")
        if icon_path and isinstance(icon_path, Path) and icon_path.exists():
            icon_img = Image.open(icon_path)
            icon_img.thumbnail((150, 150))
        else:
            icon_img = self.default_thumbnail_img
            icon_img.thumbnail((150, 150))

        self._settings_icon_photo = ImageTk.PhotoImage(icon_img)
        ttk.Label(inner_frame, image=self._settings_icon_photo).pack(pady=(0, 8))

        name_var = ttk.StringVar(value=gallery["name"])

        def _limit_name(*_):
            v = name_var.get()
            if len(v) > 16:
                name_var.set(v[:16])

        name_var.trace_add("write", _limit_name)
        ttk.Entry(
            inner_frame,
            textvariable=name_var,
            font=self.gallery_font,
            justify="center",
        ).pack(fill=X)

        ttk.Separator(inner_frame).pack(fill=X, pady=5)

        misc_grid = ttk.Frame(inner_frame)
        misc_grid.pack(anchor=W, pady=(2, 0))
        for col in range(4):
            misc_grid.columnconfigure(col, weight=1, uniform="misc_grid")

        ### SORT ORDER
        gsort = gallery.get("sort", SortOrder.RANDOM).name.title()
        ttk.Label(misc_grid, text="Sort Order", font=self.setting_font).grid(
            row=0, column=0, padx=(0, 0), pady=2
        )

        sort_var = ttk.Combobox(
            misc_grid,
            values=[order.name.title() for order in SortOrder],
            state="readonly",
        )
        sort_var.grid(row=0, column=1, padx=(0, 0), pady=2)
        sort_var.set(gsort)

        ## LOOP
        gloop = gallery.get("loop", True)
        loop_var = ttk.BooleanVar(value=gloop)
        ttk.Checkbutton(misc_grid, text="Loop", variable=loop_var).grid(
            row=0, column=2, padx=(0, 10), pady=2
        )

        ## Show CAPTIONS
        gcaptions = gallery.get("captions", True)
        captions_var = ttk.BooleanVar(value=gcaptions)
        ttk.Checkbutton(
            misc_grid, text="Show Labels", variable=captions_var
        ).grid(row=0, column=3, padx=(0, 10), pady=2)

        ttk.Separator(inner_frame).pack(fill=X, pady=5)

        # Stinger Flashcards
        ttk.Label(
            inner_frame, text="Stinger Flashcards", font=self.setting_font
        ).pack(anchor=W)
        stingers = self.storage.list_stingers()
        stinger_vars = {}
        all_stingers = gallery.get("stingers", [])
        all_stingers = [x["id"] for x in all_stingers]
        active_stingers = set(all_stingers)
        stinger_grid = ttk.Frame(inner_frame)
        stinger_grid.pack(anchor=W, pady=(2, 0))
        for col in range(3):
            stinger_grid.columnconfigure(col, weight=1, uniform="stinger_col")
        for i, stinger in enumerate(stingers):
            var = ttk.BooleanVar(value=stinger["id"] in active_stingers)
            stinger_vars[stinger["id"]] = var
            ttk.Checkbutton(
                stinger_grid,
                text=stinger["name"][:16],
                variable=var,
            ).grid(row=i // 3, column=i % 3, sticky=W, padx=(0, 10), pady=2)

        ttk.Separator(inner_frame).pack(fill=X, pady=5)

        # Images — one row per image with a thumbnail and an editable name
        ttk.Label(inner_frame, text="Images", font=self.setting_font).pack(
            anchor=W, pady=(0, 4)
        )
        img_name_vars = {}
        self._settings_image_photos = []
        images = gallery["images"]
        if images:
            for image in images:
                if (
                    image.path
                    and isinstance(image.path, Path)
                    and image.path.exists()
                ):
                    try:
                        pil_img = Image.open(image.path)
                        pil_img.thumbnail((80, 80))
                    except Exception:
                        pil_img = Image.new(
                            "RGB", (80, 80), color=(200, 200, 200)
                        )
                else:
                    pil_img = Image.new("RGB", (80, 80), color=(200, 200, 200))

                photo = ImageTk.PhotoImage(pil_img)
                self._settings_image_photos.append(photo)

                img_row = ttk.Frame(inner_frame)
                img_row.pack(fill=X, pady=2)

                ttk.Label(img_row, image=photo).pack(side=LEFT, padx=(0, 8))

                iname_var = ttk.StringVar(value=image.name)
                img_name_vars[str(image.path)] = iname_var
                ttk.Entry(img_row, textvariable=iname_var).pack(
                    side=LEFT, fill=X, expand=True
                )

        canvas.create_window(
            px,
            py,
            window=frame,
            anchor=NW,
            width=popup_w,
            height=popup_h,
            tags=("settings_popup",),
        )

        self._settings_popup = frame

    def get_gallery_thumbnail(self, gallery:dict) -> ImageTk:
        """Loads and caches gallery thumbnails"""

        path = gallery["path"]
        path = gallery.get("path")
        if not path:
            return ImageTk.PhotoImage(self.default_thumbnail_img)

        ## Load cached file
        elif path in self.gallery_thumbs:
            return self.gallery_thumbs[path]

        # Check if icon path is already stored in the database
        if gallery.get("icon") and gallery["icon"].exists():
            thumb = ImageTk.PhotoImage(Image.open(gallery["icon"]))
        else:
            thumb = ImageTk.PhotoImage(self.default_thumbnail_img)

        self.gallery_thumbs[path] = thumb
        return thumb

    def delete_gallery(self, path):
        self.gallery_thumbs.pop(path, None)
        self.storage.forget_gallery(path)
        self.refresh_gallery_grid(new=True)

    def add_gallery(self):
        self.edit_mode_off()
        last_path = self.storage.get_last_path()
        browser = ImageFolderBrowser(self.root, self.style, last_path)
        browser.protocol("WM_DELETE_WINDOW", browser.cancel)
        folder = browser.show()

        if not folder:
            return
        else:
            path = Path(folder)
            name = path.name

            self.storage.remember_last_path(path.parent)

            if self.storage.remember_gallery(path, name):
                # self.load_gallery_view()
                self.refresh_gallery_grid(new=True)

    # -------------------------
    # Show Flashcards
    # -------------------------
    def show(self, notebook):

        frame = ttk.Frame(notebook, padding=10)
        frame.pack_propagate(False)

        self.image_label = ttk.Label(
            frame,
            anchor="center",
            font=self.caption_font,
        )
        self.image_label.pack(fill=BOTH, expand=True)
        self.image_label.bind("<Button-1>", self.next_card)
        # Fires on initial draw and any resize
        frame.bind("<Configure>", self._on_frame_resize)

        return frame

    def _on_frame_resize(self, event):
        self.show_width = event.width
        self.show_height = event.height

        if self._resize_job:
            self.image_label.after_cancel(self._resize_job)

        self._resize_job = self.image_label.after(
            80, lambda: self._resize_image(self.show_width, self.show_height)
        )

    def _resize_image(self, width, height):
        if self.image_img is None:
            return

        # target bounds
        img = self.image_img.copy()
        w, h = img.size

        scale = min(
            (self.show_width - self.caption_font_clearance) / w,
            (self.show_height - self.caption_font_clearance) / h,
        )

        new_w = int(w * scale)
        new_h = int(h * scale)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        self.current_photo = ImageTk.PhotoImage(img)

        if self.captions:
            self.image_label.configure(
                image=self.current_photo,
                text=self.image_name,
                compound="top",
            )
        else:
            self.image_label.configure(
                image=self.current_photo,
                text="",
                compound="top",
            )

    def open_gallery(self, path):

        gallery = self.storage.scan_gallery(Path(path))
        if not gallery or not gallery["valid"]:
            return

        if len(self.current_images) > 0:
            for gimage in self.current_images:
                if gimage.img:
                    gimage.img.close()

        self.current_gallery = gallery
        self.current_images = gallery["images"]
        self.image_path = None
        self.image_name = None
        self.sort = gallery["sort"]
        self.loop = gallery["loop"]
        self.captions = gallery["captions"]
        self.current_stingers = gallery["stingers"]
        self.use_stingers = True if len(self.current_stingers) > 0 else False

        for gimage in self.current_images:
            gimage.load()

        if not self.current_images:
            return

        if self.sort == SortOrder.DESCENDING:
            self.current_images.sort(
                key=lambda c: c.path.stem.lower(), reverse=True
            )
        elif self.sort == SortOrder.ASCENDING:
            self.current_images.sort(
                key=lambda c: c.path.stem.lower(), reverse=False
            )
        elif self.sort == SortOrder.RANDOM:
            random.shuffle(self.current_images)

        self.current_image_index = 0
        self.current_image_index_max = len(self.current_images)

        self.noteb.select(self.show_frame)
        self.next_card()

    def stinger_time(self, percent):
        if percent > 100:
            percent = 100
        elif percent < 0:
            percent = 0

        return random.random() < percent / 100

    def next_card(self, event=None):

        show_end = False
        if self.loop:
            if self.current_image_index == self.current_image_index_max:
                self.current_image_index = 0
        else:
            if self.current_image_index == self.current_image_index_max:
                self.current_image_index = 0
                show_end = True

        ## Choose an image

        ## Ending Image
        if show_end:
            self.image_path = self.end_flashcard.path
            self.image_name = self.end_flashcard.name
            self.image_img = self.end_flashcard.img
            self.show_stinger = False

        ## Stinger Image
        elif (
            self.use_stingers
            and self.current_image_index > 0
            and not self.show_stinger
            and self.stinger_time(self.storage.config.get("percent", 20))
        ):
            selection = random.choice(self.current_stingers)
            self.image_path = selection["path"]
            self.image_name = selection["name"]
            self.image_img = selection["img"]
            self.show_stinger = True

        ## Gallery image
        else:
            selection = self.current_images[self.current_image_index]
            self.image_path = selection.path
            self.image_name = selection.name
            self.image_img = selection.img
            self.show_stinger = False

        # target bounds
        if not self.image_img:
            return

        img = self.image_img.copy()
        w, h = img.size

        scale = min(
            (self.show_width - self.caption_font_clearance) / w,
            (self.show_height - self.caption_font_clearance) / h,
        )

        new_w = int(w * scale)
        new_h = int(h * scale)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        self.current_photo = ImageTk.PhotoImage(img)

        if self.captions:
            self.image_label.configure(
                image=self.current_photo,
                text=self.image_name,
                compound="top",
            )
        else:
            self.image_label.configure(
                image=self.current_photo,
                text="",
                compound="top",
            )

        if not show_end:
            self.current_image_index += 1

    # -------------------------
    # Settings Tab
    # -------------------------
    def settings(self, notebook):
        frame = ttk.Frame(notebook, padding=10)

        ## --- Theme ---
        themes = self.style.theme_names()
        theme_var = ttk.StringVar(value=self.style.theme_use())

        ttk.Label(frame, text="Theme", font=self.gallery_font).pack(
            anchor=W, pady=(20, 15)
        )

        theme_box = ttk.Combobox(
            frame,
            textvariable=theme_var,
            values=themes,
            state="readonly",
            width=15,
        )

        theme_box.pack(anchor=W, padx=50, pady=(0, 20))

        def change_theme(event=None):
            theme = theme_var.get()
            self.style.theme_use(theme)
            self.storage.config["theme"] = theme
            self.storage.save_config()
            self.refresh_stinger_grid()

        theme_box.bind("<<ComboboxSelected>>", change_theme)

        # --- Image Types ---
        def update_image_types(*args):
            selected = [
                ext for ext, var in self._image_type_vars.items() if var.get()
            ]
            self.storage.config["image_types"] = selected

        ttk.Label(frame, text="Image Types", font=self.gallery_font).pack(
            anchor=W, pady=(0, 5)
        )

        type_map = [
            (".png", "PNG"),
            (".webp", "WEBP"),
            (".jpg", "JPEG"),
            (".tiff", "TIFF"),
        ]
        current_types = self.storage.config.get(
            "image_types", self.storage.default_image_types
        )
        self._image_type_vars = {}

        type_frame = ttk.Frame(frame)
        type_frame.pack(anchor=W, pady=(0, 10))
        for ext, label in type_map:
            var = ttk.BooleanVar(value=ext in current_types)
            var.trace_add("write", update_image_types)
            self._image_type_vars[ext] = var
            ttk.Checkbutton(type_frame, text=label, variable=var).pack(
                side=LEFT, padx=(50, 10)
            )

        ttk.Label(
            frame,
            text="Probability of showing a stinger flashcard",
            font=self.gallery_font,
        ).pack(anchor=W, pady=(20, 5))

        self.percent_meter = ttk.Meter(
            frame,
            amountused=self.storage.config["percent"],
            amounttotal=100,
            metersize=150,
            bootstyle="success",
            textright="%",
            meterthickness=15,
            interactive=True,
        )

        self.percent_meter.pack(anchor=W, padx=50, pady=10)

        def on_percent_change(*args):
            value = int(self.percent_meter.amountusedvar.get())
            self.storage.config["percent"] = value

        self.percent_meter.amountusedvar.trace_add("write", on_percent_change)

        ttk.Separator(frame).pack(fill=X, pady=10)

        # --- Stingers ---
        ttk.Label(
            frame, text="Add A Stinger Flashcard", font=self.gallery_font
        ).pack(anchor=W, pady=(10, 25))
        stinger_btn_bar = ttk.Frame(frame)
        stinger_btn_bar.pack(anchor=W, pady=(0, 4))
        self._stinger_delete_button = ttk.Button(
            stinger_btn_bar,
            text="Delete",
            bootstyle="danger",
            command=self.toggle_stinger_edit_mode,
        )
        self._stinger_delete_button.pack(side=LEFT, padx=(5, 5))
        ttk.Button(
            stinger_btn_bar,
            text="Browse...",
            bootstyle="primary",
            command=self.add_stinger,
        ).pack(side=LEFT)
        self._stinger_warning = ttk.Label(frame, text="", foreground="red")
        self._stinger_warning.pack(anchor=W, pady=10)

        ttk.Label(
            frame,
            text="Double click the name to edit it.",
            font=self.setting_font,
        ).pack(anchor=W, padx=(20, 0), pady=(0, 10))
        # Scrollable stinger canvas
        scroll_wrapper = ttk.Frame(frame)
        scroll_wrapper.pack(fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(scroll_wrapper, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.stinger_canvas = ttk.Canvas(
            scroll_wrapper, yscrollcommand=scrollbar.set
        )
        self.stinger_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.configure(command=self.stinger_canvas.yview)

        self.stinger_canvas.bind(
            "<Configure>", lambda e: self.refresh_stinger_grid()
        )

        return frame

    def save_app_settings(self):
        selected = [
            ext for ext, var in self._image_type_vars.items() if var.get()
        ]
        self.storage.config["image_types"] = selected
        self.storage.config["percent"] = int(
            self.percent_meter.amountusedvar.get()
        )
        self.storage.save_config()

    def add_stinger(self):
        if len(self.storage.list_stingers()) >= 10:
            self._stinger_warning.configure(
                text="Maximum of 10 stingers reached."
            )
            return
        self._stinger_warning.configure(text="")
        start_path = self.storage.config.get("stinger_browse_path", None)
        browser = ImageFileBrowser(self.root, start_path)
        browser.protocol("WM_DELETE_WINDOW", browser.cancel)
        file_path, parent_path = browser.show()
        if not file_path:
            return
        if parent_path:
            self.storage.config["stinger_browse_path"] = parent_path
        name = file_path.stem[:16]
        if self.storage.remember_stinger(file_path, name):
            self.refresh_stinger_grid()

    def toggle_stinger_edit_mode(self):
        self.stinger_edit_mode = not self.stinger_edit_mode
        if self.stinger_edit_mode:
            self._stinger_delete_button.configure(
                text="Done", bootstyle="warning"
            )
        else:
            self._stinger_delete_button.configure(
                text="Delete", bootstyle="danger"
            )
        self.refresh_stinger_grid()

    def delete_stinger(self, path):
        self.storage.forget_stinger(path)
        self.stinger_edit_mode = False
        self._stinger_delete_button.configure(text="Delete", bootstyle="danger")
        self.refresh_stinger_grid()

    def edit_stinger_name(self, event, stinger):
        canvas = self.stinger_canvas
        x = event.x
        if x < 86:
            x = 86

        entry = ttk.Entry(canvas)
        entry.insert(0, stinger["name"])

        canvas.create_window(
            x,
            event.y,
            window=entry,
            anchor="center",
            tags="stinger_editor",
        )

        entry.focus_set()
        entry.select_range(0, "end")

        saved = [False]

        def save_name(event=None):
            if saved[0]:
                return
            saved[0] = True
            new_name = entry.get().strip()
            if new_name:
                self.storage.update_stinger(stinger["id"], new_name)

            canvas.delete("stinger_editor")
            entry.destroy()
            self.refresh_stinger_grid()

        entry.bind("<Return>", save_name)
        entry.bind("<FocusOut>", save_name)

    def refresh_stinger_grid(self):
        canvas = self.stinger_canvas
        canvas.delete("all")

        stingers = self.storage.list_stingers()
        tile_width = 120
        tile_height = 145
        padding = 30

        cols = max(1, canvas.winfo_width() // (tile_width + padding))
        self._stinger_tile_images = []

        fg = self.style.colors.fg
        bg = self.style.colors.bg

        for i, stinger in enumerate(stingers):
            row = i // cols
            col = i % cols
            x = padding + col * (tile_width + padding)
            y = padding + row * (tile_height + padding)

            canvas.create_polygon(
                self.rounded_rect_points(
                    x, y, tile_width, tile_height, radius=15
                ),
                fill=bg,
                outline=self.style.colors.border,
                width=1,
                smooth=True,
            )

            icon_path = stinger.get("icon")
            if icon_path and isinstance(icon_path, Path) and icon_path.exists():
                img = Image.open(icon_path)
                img.thumbnail((80, 80))
            else:
                img = Image.new("RGB", (80, 80), color=(200, 200, 200))

            photo = ImageTk.PhotoImage(img)
            self._stinger_tile_images.append(photo)

            canvas.create_image(
                x + tile_width // 2,
                y + (tile_height - 25) // 2,
                image=photo,
                anchor=CENTER,
            )

            text_id = canvas.create_text(
                x + tile_width // 2,
                y + tile_height - 12,
                text=stinger["name"][:16],
                fill=fg,
                font=self.gallery_font,
                tags=(f"stinger_text_{i}",),
            )

            canvas.tag_bind(
                f"stinger_text_{i}",
                "<Double-Button-1>",
                lambda e, s=stinger: self.edit_stinger_name(e, s),
            )

            if self.stinger_edit_mode:
                canvas.create_image(
                    x + tile_width - 4,
                    y + 4,
                    image=self.trash_icon,
                    anchor=NE,
                    tags=(f"stinger_trash_{i}",),
                )
                canvas.tag_bind(
                    f"stinger_trash_{i}",
                    "<Button-1>",
                    lambda e, p=stinger["path"]: self.delete_stinger(p),
                )

        total_rows = max(1, -(-len(stingers) // cols)) if stingers else 1
        total_height = total_rows * (tile_height + padding) + padding
        canvas.configure(scrollregion=(0, 0, canvas.winfo_width(), total_height))

    # -------------------------
    # Clipboard helpers
    # -------------------------

    def my_popup(self, e):
        self.my_menu.tk_popup(e.x_root, e.y_root)

    def paste_text(self, e):
        pass

    def copy_text(self, e):
        pass

    def cut_text(self, e):
        pass

    def shutdown(self):
        self.storage.save_config()
        self.root.destroy()


def main():
    root = ttk.Window("Flashcard Viewer", "sandstone")

    # Get screen dimensions in pixels and DPI
    screen_width_px = root.winfo_screenwidth()
    screen_height_px = root.winfo_screenheight()
    dpi = root.winfo_fpixels("1i")  # pixels per inch

    # Convert to centimeters (1 inch = 2.54 cm)
    screen_width_cm = (screen_width_px / dpi) * 2.54
    screen_height_cm = (screen_height_px / dpi) * 2.54
    screen_diagonal_cm = ((screen_width_cm**2) + (screen_height_cm**2)) ** 0.5

    if screen_diagonal_cm >= 25:
        win_width = int(screen_width_px * (2 / 3))
        win_height = int(screen_height_px * (7 / 8))

        # Center the window on screen
        x = (screen_width_px - win_width) // 2
        y = (screen_height_px - win_height) // 2

        root.geometry(f"{win_width}x{win_height}+{x}+{y}")

    else:
        root.geometry("970x970")

    app = FlashCardViewer(root)
    root.protocol("WM_DELETE_WINDOW", app.shutdown)
    root.mainloop()


if __name__ == "__main__":
    main()
