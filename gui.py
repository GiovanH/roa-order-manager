import abc
import os
import tkinter as tk
import uuid
import webbrowser
from abc import abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from tkinter.simpledialog import askstring
from typing import Any, Callable, Literal, Optional, Sequence, TypeAlias, Union

from roa import RoaCategoriesFile, RoaCategory, RoaEntry, RoaOrderFile
from yaml_sync import roa_zip_chars

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")

Direction: TypeAlias = Union[Literal[1], Literal[-1]]

# from tkit import MultiColumnListbox

@dataclass
class ListboxItem():
    label: str
    value: Any


class Counter():
    def __init__(self, value: int = 0) -> None:
        self.value: int = value

    def inc(self) -> int:
        last_val = self.value
        self.value += 1
        return last_val


def sort_name(entry: RoaEntry) -> str:
    try:
        return entry.name.upper()
    except:
        return 'ERROR'


class ItemListFrame(tk.Frame):
    def __init__(
        self,
        parent,
        multiple=False,
        rowheight: Optional[int] = 20
    ) -> None:
        super().__init__(parent)
        self.items: list[ListboxItem] = []

        myscroll = tk.Scrollbar(self)
        myscroll.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ('Value',)

        style_id = f"height{rowheight}.Treeview"
        s = ttk.Style()
        s.configure(style_id, rowheight=rowheight)

        self.tree: ttk.Treeview = ttk.Treeview(
            self,
            # relief=tk.GROOVE,
            selectmode=('extended' if multiple else 'browse'),  # type: ignore
            # exportselection=False,
            yscrollcommand=myscroll.set,
            columns=columns,
            style=style_id
        )

        # self.listbox.heading(0, text='Value')

        self.tree.bind("<Escape>", lambda event: self.tree.selection_clear())  # noqa: ARG005

        self.tree.column('#0', width=32)
        for i, header in enumerate(columns):
            self.tree.heading(column=i, text=header)

        myscroll.config(command=self.tree.yview)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.tree.update_idletasks()


    def selected_indexes(self) -> Sequence[int]:
        return [
            i
            for i, item in enumerate(self.tree.get_children(''))
            if item in self.tree.selection()
        ]

    def set_selection_indices(self, indexes: Sequence[int]) -> None:
        items = [
            item
            for i, item in enumerate(self.tree.get_children(''))
            if i in indexes
        ]
        self.tree.selection_set(items)

    image_cache = {}

    def photoimage(self, path: str):
        if path not in self.image_cache:
            self.image_cache[path] = tk.PhotoImage(file=path)
        return self.image_cache[path]

    def set_items(self, items: list[ListboxItem]):
        self.items = items
        for item in items:
            if isinstance(item.value, RoaEntry) and os.path.isfile(item.value.image_path()):
                try:
                    _img = self.photoimage(str(item.value.image_path()))
                    self.tree.insert('', tk.END, image=_img, values=(item.label,))
                    continue
                except tk.TclError as e:
                    print(item.value.image_path(), e)
                    pass

            self.tree.insert('', tk.END, values=(item.label,))
            continue

    def move_item(self, index, direction: Direction):
        item: ListboxItem = self.items[index]

        raise NotImplementedError()
        # self.listbox.delete(index)
        # self.listbox.insert(index + direction, item.label)

        # self.listbox.selection_set(i + direction)

    def bind_select(self, callback):
        self.tree.bind('<<ListboxSelect>>', callback)

    def move_selected_items(self, sel_indexes, direction: Direction) -> list[ListboxItem]:
        selected_items = [self.items[si] for si in sel_indexes]
        if direction == 1:
            selected_items = reversed(selected_items)
        for item in selected_items:
            i = self.items.index(item)
            if (i + direction) < 0 or (i + direction) >= len(self.items):
                continue

            self.items[i], self.items[i + direction] = self.items[i + direction], self.items[i]

            self.move_item(i, direction)

        return self.items


class DrivenFrame(tk.Frame, abc.ABC):
    def __init__(self, master: 'MainApp', *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

        self.app: MainApp = master
        self.initwindow()
        self.load_gui_from_state()

    @abstractmethod
    def initwindow(self): pass

    @abstractmethod
    def load_gui_from_state(self): pass


class ListManagerFrame(DrivenFrame):
    def __init__(self, master: 'MainApp', list_name: str, *args, **kwargs) -> None:
        self.list_name = list_name
        super().__init__(master, *args, **kwargs)

    def initwindow(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        rowheight = 20
        if self.list_name == 'stages':
            rowheight = 40
        if self.list_name == 'buddies':
            rowheight = 32

        self.itemlist: ItemListFrame = ItemListFrame(self, multiple=True, rowheight=rowheight)
        self.itemlist.grid(row=0, column=0, sticky=tk.NSEW)

        frame_buttons_chars = tk.Frame(self)
        y = Counter()

        frame_updown = tk.Frame(frame_buttons_chars)

        btn_move_up = ttk.Button(frame_updown, text="^", command=self.fac_move_selected(-1))
        btn_move_up.grid(row=0, column=0)

        btn_move_down = ttk.Button(frame_updown, text="v", command=self.fac_move_selected(1))
        btn_move_down.grid(row=0, column=1)

        frame_updown.grid(row=y.inc(), sticky=tk.EW)

        btn_sort_alpha = ttk.Button(
            master=frame_buttons_chars, text="Sort: A-Z",
            command=self.fac_sort_by(sort_name)
        )
        btn_sort_alpha.grid(row=y.inc(), sticky=tk.EW)

        btn_char_info = ttk.Button(
            frame_buttons_chars, text="Open in Steam",
            command=self.open_info
        )
        btn_char_info.grid(row=y.inc(), sticky=tk.EW)
        btn_char_info = ttk.Button(
            frame_buttons_chars, text="Open folder",
            command=self.open_folder
        )
        btn_char_info.grid(row=y.inc(), sticky=tk.EW)
        frame_buttons_chars.grid(row=0, column=1)

    def gen_listitems(self) -> list[ListboxItem]:
        return [
            ListboxItem(f"{entry.name!r} by {entry.author}", entry)
            for entry in self.app.order_roa.groups[self.list_name]
        ]

    def load_gui_from_state(self):
        items: list[ListboxItem] = self.gen_listitems()
        self.itemlist.set_items(items)

    def fac_move_selected(self, d: Direction):
        def do_move(event=None):  # noqa: ARG001
            sel_indexes = self.itemlist.selected_indexes()
            reordered_items: list[ListboxItem] = self.itemlist.move_selected_items(sel_indexes, d)
            self.app.order_roa.groups[self.list_name] = [i.value for i in reordered_items]

            assert self.itemlist.items == self.gen_listitems()

        return do_move

    def fac_sort_by(self, key_fn):
        def do_move(event=None):  # noqa: ARG001
            group = self.app.order_roa.groups[self.list_name]
            sorted_group = sorted(group, key=key_fn)
            self.app.order_roa.groups[self.list_name] = sorted_group

            self.load_gui_from_state()
            assert self.itemlist.items == self.gen_listitems()
        return do_move

    def open_info(self, event=None):  # noqa: ARG002
        si, *_ = self.itemlist.selected_indexes()
        char: RoaEntry = self.itemlist.items[si].value
        url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={char.id}"
        webbrowser.open(url, autoraise=True)

    def open_folder(self, event=None):  # noqa: ARG002
        si, *_ = self.itemlist.selected_indexes()
        char: RoaEntry = self.itemlist.items[si].value
        path = char.value.decode('utf-8')
        os.startfile(path)  # noqa: S606

class CharacterManagerFrame(DrivenFrame):  # noqa: PLR0904
    # State management
    def gen_listitems_categories(self) -> list[ListboxItem]:
        return [
            ListboxItem(f"{category} ({len(chars)})", category)
            for category, chars in self.app._inorder_items()
        ]

    def load_gui_from_state(self):
        category_items: list[ListboxItem] = self.gen_listitems_categories()
        self.list_cats.set_items(category_items)
        self.app.log(f"Loaded {len(category_items)} categories")

        self.list_cats.set_selection_indices((0,))

        self.combo_cats.configure(values=[c.label for c in category_items])

        self.open_selected_category()

    # Widget management

    def widget_buttons_cats(self) -> tk.Frame:
        frame = tk.Frame(self)
        y = Counter()

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

        btn_rename = ttk.Button(
            frame, text="Rename",
            command=self.interactive_rename_category
        )
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
        btn_char_folder = ttk.Button(
            frame, text="Open folder",
            command=self.open_folder
        )
        btn_char_folder.grid(row=y.inc(), sticky=tk.EW)

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
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)

        lab_cats = ttk.Label(self, text="Categories")
        lab_cats.grid(row=0, column=0)
        self.list_cats: ItemListFrame = ItemListFrame(self)
        self.list_cats.grid(row=1, column=0, sticky=tk.NSEW)
        frame_buttons_cats: tk.Frame = self.widget_buttons_cats()
        frame_buttons_cats.grid(row=2, column=0)

        self.list_cats.bind_select(self.open_selected_category)

        # frame_buttons_mid: tk.Frame = self.widget_buttons_middle()
        # frame_buttons_mid.grid(row=0, column=1)

        lab_cats = ttk.Label(self, text="Characters")
        lab_cats.grid(row=0, column=2)
        self.list_chars: ItemListFrame = ItemListFrame(self, multiple=True, rowheight=32)
        self.list_chars.grid(row=1, column=2, sticky=tk.NSEW)
        frame_buttons_chars: tk.Frame = self.widget_buttons_chars()
        frame_buttons_chars.grid(row=2, column=2)

    # GUI manipulation

    def get_selected_category(self) -> str:
        sel_index = self.list_cats.selected_indexes()
        if len(sel_index) != 1:
            raise AssertionError("No category selected?")
        selected_cat: ListboxItem = self.list_cats.items[sel_index[0]]
        return selected_cat.value

    def open_selected_category(self, event=None) -> None:
        self.open_category(self.get_selected_category())

    def gen_listboxitems_chars(self, category) -> list[ListboxItem]:
        return [
            ListboxItem(f"{entry.name!r} by {entry.author}", entry)
            for entry in self.app.nested_state[category]
        ]

    def open_category(self, category: str) -> None:
        group_items: list[ListboxItem] = self.gen_listboxitems_chars(category)
        self.list_chars.set_items(group_items)
        self.app.log(f"Loaded {len(group_items)} chars from group {category!r}")

        # Update UI in case category was opened programatically
        cat_index = [i.value for i in self.list_cats.items].index(category)
        self.list_cats.set_selection_indices((cat_index,))

    def fac_sort_chars_by(self, key_fn) -> Callable[..., None]:
        def do_sort(event=None):
            category = self.get_selected_category()
            characters = self.app.nested_state[category]

            sorted_group = sorted(characters, key=key_fn)
            self.app.nested_state[category] = sorted_group
            self.open_category(category)

            assert self.list_chars.items == self.gen_listboxitems_chars(category)

        return do_sort

    def fac_move_selected_chars(self, direction: Direction) -> Callable[..., None]:
        def do_move(event=None):  # noqa: ARG001
            category = self.get_selected_category()
            sel_indexes = self.list_chars.selected_indexes()
            reordered_items: list[ListboxItem] = self.list_chars.move_selected_items(sel_indexes, direction)
            self.app.nested_state[category] = [i.value for i in reordered_items]
            assert self.list_chars.items == self.gen_listboxitems_chars(category)
        return do_move

    def fac_move_selected_cat(self, d: Direction) -> Callable[..., None]:
        def do_move(event=None):  # noqa: ARG001
            (si,) = self.list_cats.selected_indexes()
            if (si + d) < 0 or (si + d) >= len(self.app.category_order):
                return
            reordered_items: list[ListboxItem] = self.list_cats.move_selected_items([si], d)

            self.app.category_order[si], self.app.category_order[si + d] = self.app.category_order[si + d], self.app.category_order[si]

            self.app.log(f"New key order: {self.app.category_order}")
            assert reordered_items == self.gen_listitems_categories()
        return do_move

    def open_info(self, event=None):  # noqa: ARG002
        si, *_ = self.list_chars.selected_indexes()
        char: RoaEntry = self.list_chars.items[si].value
        url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={char.id}"
        webbrowser.open(url, autoraise=True)

    def open_folder(self, event=None):  # noqa: ARG002
        si, *_ = self.list_chars.selected_indexes()
        char: RoaEntry = self.list_chars.items[si].value
        path = char.value.decode('utf-8')
        os.startfile(path)

    def move_char_to_category(self, src_cat: str, dest_cat: str, char: RoaEntry):
        self.app.log(f"Moving {char} from {src_cat} to {dest_cat}")
        self.app.nested_state[src_cat].remove(char)
        self.app.nested_state[dest_cat].append(char)

        self.load_gui_from_state()

    def interactive_rename_category(self):
        cur_cat = self.get_selected_category()
        new_name = askstring(title=None, prompt=f"New name for {cur_cat!r}")
        if new_name:
            self.rename_category(cur_cat, new_name)
            self.open_category(new_name)

    def rename_category(self, cat: str, new_name: str):
        tups = list(self.app.nested_state.items())
        for i, t in enumerate(tups):
            label, charlist = t
            if label == cat:
                tups[i] = (new_name, charlist)
                break
            self.app.log(f"Couldn't find {cat} in {tups}")
        self.app.nested_state = OrderedDict(tups)

        self.load_gui_from_state()

    def delete_category(self):
        cat_name = self.get_selected_category()
        if cat_name and len(self.app.nested_state[cat_name]) == 0:
            self.app.nested_state.pop(cat_name)
            self.load_gui_from_state()
        else:
            self.app.log("Can only remove empty categories")

    def add_category(self):
        new_name = askstring(title=None, prompt="Name for new category")
        if new_name and new_name not in self.app.nested_state.keys():
            self.app.nested_state[new_name] = []
            self.load_gui_from_state()
            self.open_category(new_name)

    def move_chars_to_combobox_cat(self, event=None):
        self.app.log(event)
        src_cat = self.get_selected_category()
        dest_cat_label = self.combo_cats.get()
        dest_cat = {c.label: c.value for c in self.gen_listitems_categories()}[dest_cat_label]
        for si in self.list_chars.selected_indexes():
            char = self.list_chars.items[si].value
            self.move_char_to_category(src_cat, dest_cat, char)

        self.open_category(src_cat)
        self.combo_cats.set("Move to category...")


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
        self.mainloop()

    def initwindow(self):
        self.geometry("500x600")

        self.notebook = ttk.Notebook(self)

        frame_chars = CharacterManagerFrame(self)
        self.notebook.add(frame_chars, text="Characters")
        self.childframes.append(frame_chars)

        for simple_list in ['buddies', 'stages', 'skins']:
            frame = ListManagerFrame(self, simple_list)
            self.notebook.add(frame, text=simple_list.capitalize())
            self.childframes.append(frame)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.notebook.grid(row=1, sticky=tk.NSEW)

        frame_btns = tk.Frame()

        btn_export = ttk.Button(
            frame_btns, text="Reload discarding changes",
            command=self.load_state_from_roa)
        btn_export.grid(row=0, column=0, sticky=tk.EW)

        self.bind("<Control-S>", self.save_state_to_roas)
        btn_export = ttk.Button(
            frame_btns, text="Export to ROA",
            command=self.save_state_to_roas)
        btn_export.grid(row=0, column=1, sticky=tk.EW)

        db = tk.BooleanVar()
        tk.Checkbutton(
            frame_btns,
            text='Dark blockchain',
            variable=db
        ).grid(row=0, column=2, sticky=tk.E)

        frame_btns.grid(row=2, sticky=tk.EW)

        lab_context_label = ttk.Label(self, textvariable=self.text_status, relief=tk.GROOVE)
        lab_context_label.grid(row=3, sticky=tk.EW)

    def log(self, line) -> None:
        line = str(line)
        print(line)
        self.text_status.set(line)

    def _inorder_items(self):
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
