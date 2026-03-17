import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path
from PIL import Image, ImageTk


class ImageFolderBrowser(ttk.Toplevel):
    def __init__(self, master, style, start_path=None):

        super().__init__(master)
        self.title("Select Image Folder")
        self.geometry("900x600")

        self.selected_path = None
        self.thumb_cache = {}
        self._hovered_item = None
        self._style = style

        self.current_path = Path(start_path) if start_path else Path.home()

        self.build_ui()
        self.load_directory(self.current_path)

        self.grab_set()

    # ----------------------------
    # UI
    # ----------------------------

    def build_ui(self):

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self.path_var = ttk.StringVar()

        topbar = ttk.Frame(self)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        topbar.columnconfigure(1, weight=1)

        up_btn = ttk.Button(topbar, text="⬆ Up", command=self.go_up)
        up_btn.grid(row=0, column=0, padx=(0, 5))

        pathbar = ttk.Entry(topbar, textvariable=self.path_var)
        pathbar.grid(row=0, column=1, sticky="ew")

        self.dir_list = ttk.Treeview(self)
        self.dir_list.grid(row=1, column=0, sticky="nsw", padx=(10, 5), pady=5)
        self.dir_list.tag_configure("hover", background=self._style.colors.selectbg)

        self.dir_list.bind("<<TreeviewSelect>>", self.on_dir_selected)
        self.dir_list.bind("<Motion>", self._on_tree_motion)
        self.dir_list.bind("<Leave>", self._on_tree_leave)

        self.preview_canvas = ttk.Canvas(self)
        self.preview_canvas.grid(
            row=1, column=1, sticky="nsew", padx=(5, 10), pady=5
        )

        self.preview_frame = ttk.Frame(self.preview_canvas)
        self.preview_canvas.create_window(
            (0, 0), window=self.preview_frame, anchor="nw"
        )

        self.preview_frame.bind(
            "<Configure>",
            lambda e: self.preview_canvas.configure(
                scrollregion=self.preview_canvas.bbox("all")
            ),
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(
            row=2, column=0, columnspan=2, sticky="e", pady=10, padx=10
        )

        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(
            side=RIGHT, padx=5
        )

        ttk.Button(btn_frame, text="Select Folder", command=self.confirm).pack(
            side=RIGHT
        )

    # ----------------------------
    # Directory navigation
    # ----------------------------
    def go_up(self):

        parent = self.current_path.parent

        if parent != self.current_path:
            self.load_directory(parent)

    def load_directory(self, path):

        self.current_path = path
        self.path_var.set(str(path))
        self._hovered_item = None

        self.dir_list.delete(*self.dir_list.get_children())

        try:
            subdirs = [
                p for p in path.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ]

            self.selected_path = path
            select_name = None
            if not subdirs:
                select_name = path.name
                parent = path.parent
                self.current_path = path.parent
                subdirs = [
                    p for p in parent.iterdir()
                    if p.is_dir() and not p.name.startswith(".")
                ]

            for p in sorted(subdirs, key=lambda x: x.name.lower()):
                item = self.dir_list.insert("", END, text=p.name)
                if p.name == select_name:
                    self.dir_list.selection_set(item)
                    self.dir_list.see(item)

        except PermissionError:
            pass

        self.load_previews(path)

    def on_dir_selected(self, event):

        item = self.dir_list.focus()
        if not item:
            return

        folder_name = self.dir_list.item(item)["text"]
        new_path = self.current_path / folder_name

        self.load_directory(new_path)

    def _on_tree_motion(self, event):
        item = self.dir_list.identify_row(event.y)
        if item == self._hovered_item:
            return
        if self._hovered_item:
            tags = [t for t in self.dir_list.item(self._hovered_item, "tags") if t != "hover"]
            self.dir_list.item(self._hovered_item, tags=tags)
        self._hovered_item = item
        if item:
            tags = list(self.dir_list.item(item, "tags"))
            tags.append("hover")
            self.dir_list.item(item, tags=tags)

    def _on_tree_leave(self, event):
        if self._hovered_item:
            tags = [t for t in self.dir_list.item(self._hovered_item, "tags") if t != "hover"]
            self.dir_list.item(self._hovered_item, tags=tags)
        self._hovered_item = None

    # ----------------------------
    # Image previews
    # ----------------------------

    def load_previews(self, path):

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        image_types = {".png", ".jpg", ".jpeg", ".webp"}

        col = 0
        row = 0

        try:
            entries = sorted(path.iterdir(), key=lambda f: f.name.lower())
        except PermissionError:
            return

        for file in entries:
            if not file.is_file():
                continue

            if file.suffix.lower() not in image_types:
                continue

            thumb = self.get_thumbnail(file)
            if thumb is None:
                continue

            lbl = ttk.Label(self.preview_frame, image=thumb)
            lbl.image = thumb
            lbl.grid(row=row, column=col, padx=5, pady=5)

            col += 1
            if col > 4:
                col = 0
                row += 1

    def get_thumbnail(self, path):

        if path in self.thumb_cache:
            return self.thumb_cache[path]

        try:
            img = Image.open(path)
            img.thumbnail((120, 120))
            tkimg = ImageTk.PhotoImage(img)
        except Exception:
            return None

        self.thumb_cache[path] = tkimg

        return tkimg

    # ----------------------------
    # Result
    # ----------------------------
    def cancel(self):
        print("User canceled")
        self.selected_path = None
        self.destroy()

    def confirm(self):

        #self.selected_path = self.current_path
        self.destroy()

    def show(self):

        self.wait_window()
        return self.selected_path
