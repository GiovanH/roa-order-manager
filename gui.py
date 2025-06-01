from collections import OrderedDict
from dataclasses import dataclass
import os
import webbrowser
from pathlib import Path
from tkinter.simpledialog import askstring
from typing import Any, Callable, Literal, Optional, TypeAlias, Union

from roa import RoaCategoriesFile, RoaCategory, RoaEntry, RoaOrderFile

import tkinter as tk
from tkinter import ttk

from yaml_sync import roa_zip_chars

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")

Direction: TypeAlias = Union[Literal[1], Literal[-1]]


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
        super().__init__(parent)
        self.items: list[ListboxItem] = []

        myscroll = tk.Scrollbar(self)
        myscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            self,
            relief=tk.GROOVE,
            selectmode=selectmode,
            exportselection=False,
            yscrollcommand=myscroll.set
        )

        myscroll.config(command=self.listbox.yview)

        self.listbox.pack(side=tk.TOP, fill=tk.Y, expand=1)

    def set_items(self, items: list[ListboxItem]):
        self.items = items
        self.listbox.configure(state=tk.NORMAL)
        self.listbox.delete(0, self.listbox.size())
        for i in self.items:
            self.listbox.insert(tk.END, i.label)

    def move_selected_items(self, sel_indexes, direction: Direction) -> list[ListboxItem]:
        selected_items = [self.items[si] for si in sel_indexes]
        if direction == 1:
            selected_items = reversed(selected_items)
        for item in selected_items:
            i = self.items.index(item)
            if (i+direction) < 0 or (i+direction) >= len(self.items):
                continue

            self.items[i], self.items[i+direction] = self.items[i+direction], self.items[i]

            self.listbox.delete(i)
            self.listbox.insert(i+direction, item.label)

            self.listbox.selection_set(i+direction)

        return self.items


class CharacterManager(tk.Tk):  # noqa: PLR0904
    def __init__(
        self,
        order_roa: RoaOrderFile,
        categories_roa: RoaCategoriesFile
    ) -> None:
        super().__init__()
        self.title("Re-ROAder")

        self.text_status: tk.StringVar = tk.StringVar(value="Status")
        self.initwindow()

        self.order_roa: RoaOrderFile = order_roa
        self.categories_roa: RoaCategoriesFile = categories_roa

        self.load_state_from_roa()
        self.load_gui_from_state()

        self.mainloop()

    def log(self, line) -> None:
        line = str(line)
        print(line)
        self.text_status.set(line)

    def load_state_from_roa(self):
        self.nested_state: dict[str, list[RoaEntry]] = roa_zip_chars(order_roa, categories_roa)

    # Widget management

    def widget_buttons_middle(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        btn_export = ttk.Button(
            frame, text="Reload discarding changes",
            command=self.load_state_from_roa)
        btn_export.grid(row=y.inc(), sticky=tk.EW)

        btn_export = ttk.Button(
            frame, text="Export to ROA",
            command=self.save_state_to_roas)
        btn_export.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def widget_buttons_cats(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        # btn_open = ttk.Button(frame, text="Open", command=self.open_selected_category)
        # btn_open.grid(row=y.inc(), sticky=tk.EW)

        frame_updown = tk.Frame(frame)

        btn_move_up = ttk.Button(frame_updown, text="^", command=self.fac_move_selected_cat(-1))
        btn_move_up.grid(row=0, column=0)

        btn_move_down = ttk.Button(frame_updown, text="v", command=self.fac_move_selected_cat(1))
        btn_move_down.grid(row=0, column=1)

        frame_updown.grid(row=y.inc(), sticky=tk.EW)

        btn_add = ttk.Button(frame, text="Add", command=self.add_category)
        btn_add.grid(row=y.inc(), sticky=tk.EW)

        btn_del = ttk.Button(frame, text="Delete", command=self.delete_category)
        btn_del.grid(row=y.inc(), sticky=tk.EW)

        btn_rename = ttk.Button(frame, text="Rename",
                                command=self.interactive_rename_category)
        btn_rename.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def widget_buttons_chars(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

        frame_updown = tk.Frame(frame)
        btn_move_up = ttk.Button(
            frame_updown, text="^",
            command=self.fac_move_selected_chars(-1)
        )
        btn_move_up.grid(row=0, column=0)

        btn_move_down = ttk.Button(
            frame_updown, text="v",
            command=self.fac_move_selected_chars(1)
        )
        btn_move_down.grid(row=0, column=1)

        frame_updown.grid(row=y.inc(), sticky=tk.EW)

        btn_sort_alpha = ttk.Button(
            frame, text="Sort: A-Z",
            command=self.fac_sort_chars_by(sort_name)
        )
        btn_sort_alpha.grid(row=y.inc(), sticky=tk.EW)

        btn_char_info = ttk.Button(
            frame, text="Open in Steam",
            command=self.open_info
        )
        btn_char_info.grid(row=y.inc(), sticky=tk.EW)

        # btn_char_movecat = ttk.Button(
        #     frame, text="TODO Move to...",
        #     # command=
        # )
        # btn_char_movecat.grid(row=y.inc(), sticky=tk.EW)

        self.combo_cats = ttk.Combobox(frame)
        self.combo_cats.bind("<<ComboboxSelected>>", self.move_chars_to_combobox_cat)
        self.combo_cats.set("Move to category...")
        self.combo_cats.grid(row=y.inc(), sticky=tk.EW)

        return frame

    def initwindow(self) -> None:
        self.geometry("500x600")

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
        self.list_chars.grid(row=0, column=2, sticky=tk.NS)
        frame_buttons_chars: tk.Frame = self.widget_buttons_chars()
        frame_buttons_chars.grid(row=1, column=2)

        lab_context_label = ttk.Label(self, textvariable=self.text_status, relief=tk.GROOVE)
        lab_context_label.grid(row=2, column=0, columnspan=3, sticky=tk.SW)

    # State management
    def gen_listitems_categories(self) -> list[ListboxItem]:
        return [
            ListboxItem(f"{category} ({len(chars)})", category)
            for category, chars in self.nested_state.items()
        ]

    def load_gui_from_state(self):
        category_items: list[ListboxItem] = self.gen_listitems_categories()
        self.list_cats.set_items(category_items)
        self.log(f"Loaded {len(category_items)} categories")

        self.list_cats.listbox.selection_set(0)

        self.combo_cats.configure(values=[c.label for c in category_items])

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
                print(char)
                try:
                    characters.append(char)
                except KeyError:
                    if label == '_removed': continue
                    self.log(f"Couldn't find {char}")
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

        # Update UI in case category was opened programatically
        self.list_cats.listbox.select_clear(0, tk.END)
        cat_index = [i.value for i in self.list_cats.items].index(category)
        self.list_cats.listbox.selection_set(cat_index)

    def fac_sort_chars_by(self, key_fn) -> Callable[..., None]:
        def do_sort(event=None):
            category = self.get_selected_category()
            characters = self.nested_state[category]

            sorted_group = sorted(characters, key=key_fn)
            self.nested_state[category] = sorted_group
            self.open_category(category)

            assert self.list_chars.items == self.gen_listboxitems_chars(category)

        return do_sort

    def fac_move_selected_chars(self, direction: Direction) -> Callable[..., None]:
        def do_move(event=None):
            category = self.get_selected_category()
            sel_indexes = self.list_chars.listbox.curselection()
            reordered_items: list[ListboxItem] = self.list_chars.move_selected_items(sel_indexes, direction)
            self.nested_state[category] = [i.value for i in reordered_items]
            assert self.list_chars.items == self.gen_listboxitems_chars(category)
        return do_move

    def fac_move_selected_cat(self, direction: Direction) -> Callable[..., None]:
        def do_move(event=None):
            (sel_index,) = self.list_cats.listbox.curselection()
            if (sel_index+direction) < 0 or (sel_index+direction) >= len(self.nested_state.keys()):
                return
            reordered_items: list[ListboxItem] = self.list_cats.move_selected_items([sel_index], direction)

            tups = list(self.nested_state.items())
            tups[sel_index], tups[sel_index+direction] = tups[sel_index+direction], tups[sel_index]
            self.nested_state = OrderedDict(tups)

            self.log(f"New key order: {self.nested_state.keys()}")
            assert reordered_items == self.gen_listitems_categories()
        return do_move

    def open_info(self, event=None):
        sel_index, *_ = self.list_chars.listbox.curselection()
        char: RoaEntry = self.list_chars.items[sel_index].value
        url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={char.id}"
        webbrowser.open(url, autoraise=True)

    def move_char_to_category(self, src_cat: str, dest_cat: str, char: RoaEntry):
        self.log(f"Moving {char} from {src_cat} to {dest_cat}")
        self.nested_state[src_cat].remove(char)
        self.nested_state[dest_cat].append(char)

        self.load_gui_from_state()

    def interactive_rename_category(self):
        cur_cat = self.get_selected_category()
        new_name = askstring(title=None, prompt=f"New name for {cur_cat!r}")
        if new_name:
            self.rename_category(cur_cat, new_name)
            self.open_category(new_name)

    def rename_category(self, cat: str, new_name: str):
        tups = list(self.nested_state.items())
        for i, t in enumerate(tups):
            label, charlist = t
            if label == cat:
                tups[i] = (new_name, charlist)
                break
            else:
                self.log(f"Couldn't find {cat} in {tups}")
        self.nested_state = OrderedDict(tups)

        self.load_gui_from_state()

    def delete_category(self):
        cat_name = self.get_selected_category()
        if cat_name and len(self.nested_state[cat_name]) == 0:
            self.nested_state.pop(cat_name)
            self.load_gui_from_state()
        else:
            self.log("Can only remove empty categories")

    def add_category(self):
        new_name = askstring(title=None, prompt=f"Name for new category")
        if new_name and new_name not in self.nested_state.keys():
            self.nested_state[new_name] = []
            self.load_gui_from_state()
            self.open_category(new_name)

    def move_chars_to_combobox_cat(self, event=None):
        self.log(event)
        src_cat = self.get_selected_category()
        dest_cat_label = self.combo_cats.get()
        dest_cat = {c.label: c.value for c in self.gen_listitems_categories()}[dest_cat_label]
        for sel_index in self.list_chars.listbox.curselection():
            char = self.list_chars.items[sel_index].value
            self.move_char_to_category(src_cat, dest_cat, char)

        self.open_category(src_cat)
        self.combo_cats.set("Move to category...")

if __name__ == '__main__':
    order_roa = RoaOrderFile(ROA_DIR / 'order.roa')
    categories_roa = RoaCategoriesFile(ROA_DIR / 'categories.roa')
    CharacterManager(order_roa, categories_roa)

