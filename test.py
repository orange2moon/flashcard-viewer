import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from tkinter import font


def update_label(*args):
    label_font.config(family=selected_font.get())



root = tk.Tk()
root.geometry("700x400")


fonts = list(font.families())
fonts.sort()

selected_font = tk.StringVar(value=fonts[0])
selected_font.trace_add("write", update_label)

label_font = font.Font(family='Arial', name='labelFont', size=85, weight='bold')
my_label = ttk.Label(root, text='Attention!', font=label_font)
my_label.pack(anchor="center")

font_box = ttk.Combobox(
            root,
            textvariable=selected_font,
            values=[afont for afont in fonts],
            state="readonly",
        )

font_box.pack(anchor="center")


root.mainloop()


