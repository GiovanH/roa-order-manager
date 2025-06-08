import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Generator
from tkinter import messagebox

from .gui_pages import CharacterManagerFrame, DrivenFrame, ListManagerFrame
from .roa import ROA_DIR, RoaCategoriesFile, RoaCategory, RoaEntry, RoaOrderFile
from .yaml_sync import roa_zip_chars

_nogc = []

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
        self.is_dirty: bool = False

        self.load_state_from_roa()

        self.initwindow()

        self.protocol("WM_DELETE_WINDOW", self.delete_window)
        self.mainloop()

    def initwindow(self) -> None:
        self.geometry("800x600+40+40")

        def frame_btns():
            frame_btns = tk.Frame(self)

            btn_folder = ttk.Button(
                frame_btns, text="Open ROA folder",
                command=self.open_folder)
            btn_reload = ttk.Button(
                frame_btns, text="🔄 Reload discarding changes",
                command=self.load_state_from_roa)
            btn_export = ttk.Button(
                frame_btns, text="💾 Save and export to ROA",
                command=self.save_state_to_roas,
                underline=3
            )

            btn_folder.pack(side=tk.LEFT)
            btn_reload.pack(side=tk.RIGHT)
            btn_export.pack(side=tk.RIGHT)
            return frame_btns

        def notebook():
            notebook = ttk.Notebook(self)

            frame_chars = CharacterManagerFrame(self)
            notebook.add(frame_chars, text="Characters")
            self.childframes.append(frame_chars)

            for simple_list in ['buddies', 'stages', 'skins']:
                frame = ListManagerFrame(self, simple_list)
                notebook.add(frame, text=simple_list.capitalize())
                self.childframes.append(frame)
            return notebook

        def frame_info():
            frame_info = tk.Frame(self)
            lab_context_label = ttk.Label(frame_info, textvariable=self.text_status, relief=tk.GROOVE)

            var_db = tk.IntVar(value=0)
            check_db = ttk.Checkbutton(
                frame_info,
                text='Dark blockchain',
                variable=var_db
            )
            _nogc.append(var_db)

            def trace(a, b, c):  # noqa: ARG001
                self.log("woah!")
            var_db.trace_add('write', trace)

            lab_context_label.pack(fill='x', expand=1, side=tk.LEFT)
            check_db.pack(side=tk.RIGHT)
            return frame_info

        frame_btns().pack(fill='x', side=tk.TOP)
        notebook().pack(fill='both', expand=1)
        frame_info().pack(fill='x', side=tk.BOTTOM)

        self.bind_all("<Control-s>", self.save_state_to_roas)

    def delete_window(self) -> None:
        if self.is_dirty or self.order_roa.is_dirty() or self.categories_roa.is_dirty():
            resp = messagebox.askyesnocancel("Unsaved changes!", "You have not exported your changes back to Rivals of Aether yet. Save before quitting?")
            if resp is None:
                return
            elif resp is False:
                self.destroy()
            elif resp is True:
                self.save_state_to_roas()
                self.destroy()
        else:
            self.destroy()

    def log(self, line) -> None:
        max_old_lines = 2
        line = str(line)
        lines = self.text_status.get().split('\n')
        self.text_status.set('\n'.join([*lines[-max_old_lines:], line]))

    def _inorder_items(self) -> Generator[tuple[str, list[RoaEntry]], Any, None]:
        assert set(self.category_order) == set(self.nested_state.keys())
        for k in self.category_order:
            yield (k, self.nested_state[k])

    def load_state_from_roa(self) -> None:
        self.order_roa.load_from_disk()

        self.nested_state: dict[str, list[RoaEntry]] = roa_zip_chars(self.order_roa, self.categories_roa)
        self.category_order = list(self.nested_state.keys())
        self.load_gui_from_state()

    def load_gui_from_state(self) -> None:
        for child in self.childframes:
            child.load_gui_from_state()

    def save_state_to_roas(self, event=None) -> None:  # noqa: ARG002
        self.log("Zipping nested groups with category labels")
        all_characters: list[RoaEntry] = []
        self.categories_roa.categories.clear()
        for label in self.category_order:
            cat_char_list: list[RoaEntry] = self.nested_state[label]
            if len(cat_char_list) < 1:
                continue
            new_cat = RoaCategory(len(all_characters), label.encode('utf-8'))
            print(new_cat)
            self.categories_roa.categories.append(new_cat)
            for char in cat_char_list:
                print(char)
                try:
                    all_characters.append(char)
                except KeyError:
                    if label == '_removed': continue  # noqa: E701
                    self.log(f"Couldn't find {char}")
                    raise

        self.order_roa.groups['characters'] = all_characters

        self.order_roa.save_file()
        self.categories_roa.save_file()
        self.is_dirty = False
        self.log("Saved groups and order to ROA")

    def open_folder(self, event=None) -> None:  # noqa: ARG002
        os.startfile(ROA_DIR)  # noqa: S606


def main() -> None:
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')
    MainApp(order_roa, categories_roa)


if __name__ == '__main__':
    main()
