from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Callable, Optional

from roa import RoaCategoriesFile, RoaCategory, RoaEntry, RoaOrderFile

import tkinter as tk
from tkinter import ttk

from yaml_sync import roa_zip_chars

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")

@dataclass
class ListboxItem():
    label: str
    value: Any

class Counter():
    def __init__(self, value=0):
        self.value = value

    def inc(self):
        last_val = self.value
        self.value += 1
        return last_val

def sort_name(entry: RoaEntry):
    try:
        return entry.name.upper()
    except:
        return 'ERROR'

class ItemListFrame(tk.Frame):
    def __init__(
        self,
        parent,
        selectmode=tk.SINGLE
    ) -> None:
        super().__init__(parent, bg="yellow")

        self.items: list[ListboxItem] = []

        self.listbox = tk.Listbox(
            self,
            relief=tk.GROOVE,
            selectmode=selectmode,
            exportselection=False
        )

        self.listbox.grid(sticky=tk.NSEW)

    def set_items(self, items: list[ListboxItem]):
        self.items = items
        print(items)
        self.listbox.configure(state=tk.NORMAL)
        self.listbox.delete(0, self.listbox.size())
        for i in self.items:
            self.listbox.insert(tk.END, i.label)



class CharacterManager(tk.Tk):
    def __init__(
        self,
        order_roa: RoaOrderFile,
        categories_roa: RoaCategoriesFile
    ) -> None:
        super().__init__()

        self.text_status: tk.StringVar = tk.StringVar(value="Status")
        self.initwindow()

        self.order_roa: RoaOrderFile = order_roa
        self.categories_roa: RoaCategoriesFile = categories_roa

        self.nested_state: dict[str, list[RoaEntry]] = roa_zip_chars(order_roa, categories_roa)

        self.load_roa_state()

        self.mainloop()

    def log(self, line) -> None:
        line = str(line)
        print(line)
        self.text_status.set(line)

    # Widget management

    def widget_buttons_middle(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        btn_export = ttk.Button(frame, text="Export to ROA",
                              command=self.save_state_to_roas)
        btn_export.grid(row=y.inc(), sticky=tk.EW)
        btn_two = ttk.Button(frame, text="2")
        btn_two.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def widget_buttons_cats(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        # btn_open = ttk.Button(frame, text="Open", command=self.open_selected_category)
        # btn_open.grid(row=y.inc(), sticky=tk.EW)

        btn_2 = ttk.Button(frame, text="2")
        btn_2.grid(row=y.inc(), sticky=tk.EW)

        btn_move_up = ttk.Button(frame, text="^")
        btn_move_up.grid(row=y.inc(), sticky=tk.EW)

        btn_move_up = ttk.Button(frame, text="v")
        btn_move_up.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def widget_buttons_chars(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        btn_move_up = ttk.Button(
            frame, text="^",
            command=self.fac_move_selected_chars(-1)
        )
        btn_move_up.grid(row=y.inc(), sticky=tk.EW)

        btn_move_down = ttk.Button(
            frame, text="v",
            command=self.fac_move_selected_chars(1)
        )
        btn_move_down.grid(row=y.inc(), sticky=tk.EW)

        btn_sort_alpha = ttk.Button(
            frame, text="Sort: A-Z",
            command=self.fac_sort_chars_by(sort_name)
        )
        btn_sort_alpha.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def initwindow(self) -> None:
        self.geometry("860x600")

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)

        self.list_cats: ItemListFrame = ItemListFrame(self)
        self.list_cats.grid(row=0, column=0, sticky=tk.NS)
        frame_buttons_cats: tk.Frame = self.widget_buttons_cats()
        frame_buttons_cats.grid(row=1, column=0)

        self.list_cats.listbox.bind('<<ListboxSelect>>', self.open_selected_category)


        frame_buttons_mid: tk.Frame = self.widget_buttons_middle()
        frame_buttons_mid.grid(row=0, column=1)

        self.list_chars: ItemListFrame = ItemListFrame(self, selectmode=tk.MULTIPLE)
        self.list_chars.grid(row=0, column=2)
        frame_buttons_chars: tk.Frame = self.widget_buttons_chars()
        frame_buttons_chars.grid(row=1, column=2)

        lab_context_label = ttk.Label(self, textvariable=self.text_status, relief=tk.GROOVE)
        lab_context_label.grid(row=2, column=0, columnspan=3, sticky="EW")

    # State management
    def gen_listitems_categories(self) -> list[ListboxItem]:
        return [
            ListboxItem(f"{category} ({len(chars)})", category)
            for category, chars in self.nested_state.items()
        ]

    def load_roa_state(self):
        category_items: list[ListboxItem] = self.gen_listitems_categories()
        self.list_cats.set_items(category_items)
        self.log(f"Loaded {len(category_items)} categories")

        self.list_cats.listbox.selection_set(0)
        self.open_selected_category()

    def save_state_to_roas(self, event=None) -> None:
        self.log("Zipping nested groups with category labels")
        characters = []
        categories_roa.categories.clear()
        for label, char_list in self.nested_state.items():
            if len(char_list) < 1:
                continue
            new_cat = RoaCategory(len(characters), label.encode('utf-8'))
            print(new_cat)
            categories_roa.categories.append(new_cat)
            for char in char_list:
                try:
                    characters.append(char)
                except KeyError:
                    if label == '_removed': continue
                    print("Couldn't find", char)
                    raise

        order_roa.groups['characters'] = characters

        order_roa.save_file()
        categories_roa.save_file()
        self.log("Saved groups and order to ROA")

    # GUI manipulation

    def get_selected_category(self) -> str:
        sel_index = self.list_cats.listbox.curselection()
        if len(sel_index) != 1:
            raise AssertionError("No category selected?")
        selected_cat: ListboxItem = self.list_cats.items[sel_index[0]]
        return selected_cat.value

    def open_selected_category(self, event=None) -> None:
        self.open_category(self.get_selected_category())

    def gen_listboxitems_chars(self, category) -> list[ListboxItem]:
        return [
            ListboxItem(character.name, character)
            for character in self.nested_state[category]
        ]

    def open_category(self, category: str) -> None:
        group_items: list[ListboxItem] = self.gen_listboxitems_chars(category)
        self.list_chars.set_items(group_items)
        self.log(f"Loaded {len(group_items)} chars from group {category!r}")

    def fac_sort_chars_by(self, key_fn) -> Callable[..., None]:
        def do_sort(event=None):
            category = self.get_selected_category()
            characters = self.nested_state[category]

            sorted_group = sorted(characters, key=key_fn)
            self.nested_state[category] = sorted_group
            self.open_category(category)

            assert self.list_chars.items == self.gen_listboxitems_chars(category)

        return do_sort

    def fac_move_selected_chars(self, direction: int) -> Callable[..., None]:
        def do_move(event=None):
            c = self.get_selected_category()
            print(self.nested_state[c])

            # Reorder nested state
            sel_indexes = self.list_chars.listbox.curselection()
            selected_items = [self.nested_state[c][si] for si in sel_indexes]
            for item in selected_items:
                i = self.nested_state[c].index(item)
                self.nested_state[c][i], self.nested_state[c][i+direction] = self.nested_state[c][i+direction], self.nested_state[c][i]
                self.log(f"Moved {item!r} from {i} to {i+direction}")

            # TODO: Edit list inplace
            self.open_category(c)
            print(self.nested_state[c])
            assert self.list_chars.items == self.gen_listboxitems_chars(c)

        return do_move

if __name__ == '__main__':
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')
    CharacterManager(order_roa, categories_roa)

