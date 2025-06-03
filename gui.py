import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Generator
from tkinter import messagebox

from gui_pages import CharacterManagerFrame, DrivenFrame, ListManagerFrame
from roa import RoaCategoriesFile, RoaCategory, RoaEntry, RoaOrderFile
from yaml_sync import roa_zip_chars

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")

class MainApp(tk.Tk):
    def __init__(
        self,
        order_roa: RoaOrderFile,
        categories_roa: RoaCategoriesFile
    ) -> None:
        super().__init__()
        self.title("Re-ROAder")

        self.text_status: tk.StringVar = tk.StringVar(value="Status")

        self.order_roa: RoaOrderFile = order_roa
        self.categories_roa: RoaCategoriesFile = categories_roa

        self.childframes: list[DrivenFrame] = []

        self.load_state_from_roa()

        self.initwindow()

        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.mainloop()

    def initwindow(self):
        self.geometry("800x600+40+40")

        self.notebook = ttk.Notebook(self)

        frame_chars = CharacterManagerFrame(self)
        self.notebook.add(frame_chars, text="Characters")
        self.childframes.append(frame_chars)

        for simple_list in ['buddies', 'stages', 'skins']:
            frame = ListManagerFrame(self, simple_list)
            self.notebook.add(frame, text=simple_list.capitalize())
            self.childframes.append(frame)

        # self.grid_columnconfigure(0, weight=1)
        # self.grid_rowconfigure(2, weight=1)

        frame_btns = self.frame_btns()

        lab_context_label = ttk.Label(self, textvariable=self.text_status, relief=tk.GROOVE)

        frame_btns.pack(fill='x', side=tk.TOP)
        self.notebook.pack(fill='both', expand=1)
        lab_context_label.pack(fill='x', side=tk.BOTTOM)

    def frame_btns(self) -> tk.Frame:
        frame_btns = tk.Frame(background='yellow')

        btn_export = ttk.Button(
            frame_btns, text="🔄 Reload discarding changes",
            command=self.load_state_from_roa)
        btn_export.grid(row=0, column=0, sticky=tk.E)

        self.bind_all("<Control-S>", self.save_state_to_roas)
        btn_export = ttk.Button(
            frame_btns, text="💾 Export to ROA",
            command=self.save_state_to_roas)
        btn_export.grid(row=0, column=1, sticky=tk.E)

        db = tk.BooleanVar()
        tk.Checkbutton(
            frame_btns,
            text='Dark blockchain',
            variable=db
        ).grid(row=0, column=2, sticky=tk.EW)
        self.grid_columnconfigure(2, weight=1)

        btn_export = ttk.Button(
            frame_btns, text="❌ Cancel discarding changes",
            command=self.destroy)
        btn_export.grid(row=0, column=3, sticky=tk.E)
        return frame_btns

    def log(self, line) -> None:
        line = str(line)
        print(line)
        self.text_status.set(line)

    def _inorder_items(self) -> Generator[tuple[str, list[RoaEntry]], Any, None]:
        assert set(self.category_order) == set(self.nested_state.keys())
        for k in self.category_order:
            yield (k, self.nested_state[k])

    def load_state_from_roa(self):
        self.nested_state: dict[str, list[RoaEntry]] = roa_zip_chars(order_roa, categories_roa)
        self.category_order = list(self.nested_state.keys())
        self.load_gui_from_state()

    def load_gui_from_state(self):
        for child in self.childframes:
            child.load_gui_from_state()

    def save_state_to_roas(self, event=None) -> None:  # noqa: ARG002
        self.log("Zipping nested groups with category labels")
        all_characters: list[RoaEntry] = []
        categories_roa.categories.clear()
        for label in self.category_order:
            cat_char_list: list[RoaEntry] = self.nested_state[label]
            if len(cat_char_list) < 1:
                continue
            new_cat = RoaCategory(len(all_characters), label.encode('utf-8'))
            print(new_cat)
            categories_roa.categories.append(new_cat)
            for char in cat_char_list:
                print(char)
                try:
                    all_characters.append(char)
                except KeyError:
                    if label == '_removed': continue  # noqa: E701
                    self.log(f"Couldn't find {char}")
                    raise

        order_roa.groups['characters'] = all_characters

        order_roa.save_file()
        categories_roa.save_file()
        self.log("Saved groups and order to ROA")


if __name__ == '__main__':
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')
    MainApp(order_roa, categories_roa)
