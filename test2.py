import tkinter as tk
from tkinter import font

root = tk.Tk()

available_fonts = sorted(font.families())

selected_font = tk.StringVar(value=available_fonts[0])

def update_font(*args):
    label.config(font=(selected_font.get(), 16))

dropdown = tk.OptionMenu(root, selected_font, *available_fonts)
dropdown.pack()

label = tk.Label(root, text="Image Caption Preview")
label.pack(pady=20)

selected_font.trace_add("write", update_font)

root.mainloop()
