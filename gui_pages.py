import abc
import os
import tkinter as tk
import webbrowser
from abc import abstractmethod
from collections import OrderedDict
from tkinter import ttk
from tkinter.simpledialog import Dialog, askstring
from typing import Callable, Optional
# from gui import MainApp

from gui_itemlists import CatInfo, Direction, ItemListFrameCats, ItemListFrameRoa
from roa import RoaEntry


def sort_name(entry: RoaEntry) -> str:
    try:
        return entry.name.upper()
    except:
        return 'ERROR'


class Counter():
    def __init__(self, value: int = 0) -> None:
        self.value: int = value

    def inc(self) -> int:
        last_val = self.value
        self.value += 1
        return last_val


class MultiSelectDialog(Dialog):

    def __init__(self, parent, labels, option_lists, stagger_lists=False):
        self.labels = labels
        self.option_lists = option_lists
        self.pickers = []
        self.stagger_lists = stagger_lists
        self.results = None

        self.range = range(len(self.labels))
        super().__init__(parent=parent)

    def body(self, master):

        is_first = True
        first_picker = None
        for i in self.range:
            labeltext = self.labels[i]
            options = self.option_lists[i]
            ttk.Label(master, text=labeltext).grid(column=0, row=i)
            picker = ttk.Combobox(master, values=options)
            picker.grid(column=1, row=i, sticky="ew")
            if self.stagger_lists:
                picker.current(i)
            else:
                picker.current(0)
            if is_first:
                first_picker = picker
                is_first = False
            self.pickers.append(picker)

        text_width = max(len(str(text)) for list_ in self.option_lists for text in list_)
        for picker in self.pickers:
            picker.config(width=text_width)

        assert isinstance(first_picker, ttk.Combobox)
        first_picker.focus()

        master.columnconfigure(1, weight=1)
        master.pack(padx=5, pady=5, fill="x")

    def apply(self):
        self.results = [self.pickers[i].get() for i in self.range]


class DrivenFrame(tk.Frame, abc.ABC):
    def __init__(self, master, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

        self.app = master
        self.initwindow()
        self.load_gui_from_state()

    @abstractmethod
    def initwindow(self): pass

    @abstractmethod
    def load_gui_from_state(self): pass


class ListManagerFrame(DrivenFrame):
    def __init__(self, master, list_name: str, *args, **kwargs) -> None:
        self.list_name = list_name
        super().__init__(master, *args, **kwargs)

    # Window management

    def initwindow(self):
        self.list_items: ItemListFrameRoa = ItemListFrameRoa(
            self,
            multiple=True,
            icon_size=RoaEntry.image_sizes.get(self.list_name, (0, 20))
        )

        # for col in self.list_items.columns:
        #     self.list_items.tree.heading(
        #         col, text=col,
        #         command=lambda: treeview_sort_column(self.list_items.tree, col, False)
        #     )

        def frame_buttons_chars() -> tk.Frame:
            frame_buttons_chars = tk.Frame(self)
            y = Counter()

            def frame_updown():
                frame_updown = tk.Frame(frame_buttons_chars)
                btn_move_up = ttk.Button(
                    frame_updown, text="^",
                    command=self.fac_move_selected(-1))
                btn_move_down = ttk.Button(
                    frame_updown, text="v",
                    command=self.fac_move_selected(1))
                btn_move_up.grid(row=0, column=0)
                btn_move_down.grid(row=0, column=1)
                return frame_updown

            btn_sort_alpha = ttk.Button(
                master=frame_buttons_chars, text="Sort: A-Z",
                command=self.fac_sort_by(sort_name)
            )
            btn_char_info = ttk.Button(
                frame_buttons_chars, text="Open in Steam",
                command=self.open_info
            )
            btn_char_folder = ttk.Button(
                frame_buttons_chars, text="Open folder",
                command=self.open_folder
            )

            frame_updown().grid(row=y.inc(), sticky=tk.EW)
            btn_sort_alpha.grid(row=y.inc(), sticky=tk.EW)
            btn_char_info.grid(row=y.inc(), sticky=tk.EW)
            btn_char_folder.grid(row=y.inc(), sticky=tk.EW)

            return frame_buttons_chars

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.list_items.grid(row=0, column=0, sticky=tk.NSEW)
        frame_buttons_chars().grid(row=0, column=1, sticky=tk.N)

    def load_gui_from_state(self):
        self.list_items.set_items(self.app.order_roa.groups[self.list_name])

    # Data ordering

    def fac_move_selected(self, d: Direction):
        def do_move(event=None):  # noqa: ARG001
            prev_order = tuple(self.app.order_roa.groups[self.list_name])
            reordered_items: list[RoaEntry] = self.list_items.move_selected_items(d)
            self.app.order_roa.groups[self.list_name] = reordered_items
            self.app.log(f"Reordered {self.list_name} from {prev_order} to {reordered_items}")

        return do_move

    def fac_sort_by(self, key_fn):
        def do_move(event=None):  # noqa: ARG001
            group = self.app.order_roa.groups[self.list_name]
            sorted_group = sorted(group, key=key_fn)
            self.app.order_roa.groups[self.list_name] = sorted_group

            self.load_gui_from_state()
        return do_move

    # Selection actions

    def open_info(self, event=None):  # noqa: ARG002
        for char in self.list_items.selected_items():
            url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={char.id}"
            webbrowser.open(url, autoraise=True)

    def open_folder(self, event=None):  # noqa: ARG002
        for char in self.list_items.selected_items():
            path = char.value.decode('utf-8')
            os.startfile(path)  # noqa: S606


class CharacterManagerFrame(DrivenFrame):
    # Window management

    def initwindow(self) -> None:
        self.combo_cats: ttk.Combobox

        def widget_buttons_cats() -> tk.Frame:
            frame = tk.Frame(self)
            y = Counter()

            def frame_updown():
                frame_updown = tk.Frame(frame)

                btn_move_up = ttk.Button(
                    frame_updown, text="^",
                    command=self.fac_move_selected_cat(-1))
                btn_move_down = ttk.Button(
                    frame_updown, text="v",
                    command=self.fac_move_selected_cat(1))

                btn_move_up.grid(row=0, column=0)
                btn_move_down.grid(row=0, column=1)

                return frame_updown

            btn_add = ttk.Button(frame, text="Add", command=self.add_category)

            btn_del = ttk.Button(frame, text="Delete", command=self.delete_category)

            btn_rename = ttk.Button(
                frame, text="Rename",
                command=self.interactive_rename_category
            )

            frame_updown().grid(row=y.inc(), sticky=tk.EW)
            btn_add.grid(row=y.inc(), sticky=tk.EW)
            btn_del.grid(row=y.inc(), sticky=tk.EW)
            btn_rename.grid(row=y.inc(), sticky=tk.EW)

            return frame

        def widget_buttons_chars() -> tk.Frame:
            frame = tk.Frame(self)
            y = Counter()

            def frame_updown():
                frame_updown = tk.Frame(frame)
                btn_move_up = ttk.Button(
                    frame_updown, text="^",
                    command=self.fac_move_selected_chars(-1))
                btn_move_down = ttk.Button(
                    frame_updown, text="v",
                    command=self.fac_move_selected_chars(1))
                btn_move_up.grid(row=0, column=0)
                btn_move_down.grid(row=0, column=1)
                return frame_updown

            btn_sort_alpha = ttk.Button(
                frame, text="Sort: A-Z",
                command=self.fac_sort_chars_by(sort_name))

            btn_char_info = ttk.Button(
                frame, text="Open in Steam",
                command=self.open_info)
            btn_char_folder = ttk.Button(
                frame, text="Open folder",
                command=self.open_folder)

            btn_moveto = ttk.Button(
                frame, text="Move to...",
                command=self.interactive_move_sel_to_cat)

            # btn_char_movecat = ttk.Button(
            #     frame, text="TODO Move to...",
            #     # command=
            # )

            self.combo_cats = ttk.Combobox(frame)
            self.combo_cats.bind("<<ComboboxSelected>>", self.move_chars_to_combobox_cat)
            self.combo_cats.set("Move to category...")

            c = 0
            frame_updown().grid(row=y.inc(), column=c, sticky=tk.EW)
            btn_sort_alpha.grid(row=y.inc(), column=c, sticky=tk.EW)
            btn_moveto.grid(row=y.inc(), column=c, sticky=tk.EW)

            y.value = 0
            c = 1
            btn_char_info.grid(row=y.inc(), column=c, sticky=tk.EW)
            btn_char_folder.grid(row=y.inc(), column=c, sticky=tk.EW)
            self.combo_cats.grid(row=y.inc(), column=c, sticky=tk.EW)
            # btn_char_movecat.grid(row=y.inc(), sticky=tk.EW)

            return frame

        lab_cats = ttk.Label(self, text="Categories")
        self.list_cats: ItemListFrameCats = ItemListFrameCats(self)

        # frame_buttons_mid: tk.Frame = self.widget_buttons_middle()
        # frame_buttons_mid.grid(row=0, column=1)

        lab_chars = ttk.Label(self, text="Characters")
        self.list_chars: ItemListFrameRoa = ItemListFrameRoa(
            self, multiple=True,
            icon_size=RoaEntry.image_sizes['characters']
            # icon_size=(48, 32)
        )

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=4)

        lab_cats.grid(row=0, column=0)
        self.list_cats.grid(row=1, column=0, sticky=tk.NSEW)
        widget_buttons_cats().grid(row=2, column=0)

        lab_chars.grid(row=0, column=2)
        self.list_chars.grid(row=1, column=2, sticky=tk.NSEW)
        widget_buttons_chars().grid(row=2, column=2)

        self.list_cats.bind_select(self.open_selected_category)
        self.list_chars.tree.bind('m', self.interactive_move_sel_to_cat)

    def load_gui_from_state(self):
        category_items: list[CatInfo] = self.gen_listitems_categories()
        self.list_cats.set_items(category_items)

        # Be nice: automatically select the first group
        # Because of the unsorted group this will always exist
        self.list_cats.select_items((category_items[0],))

        self.combo_cats.configure(values=[
            *[c.label for c in category_items],
            "<NEW>"
        ])
        self.app.log(f"Loaded {len(category_items)} categories")

        # self.open_selected_category()  # done by select

    # Helpers

    def get_selected_category(self) -> CatInfo:
        selected_cats = self.list_cats.selected_items()
        if len(selected_cats) != 1:
            raise AssertionError("No category selected?")
        selected_cat: CatInfo = selected_cats[0]
        return selected_cat

    def gen_listitems_categories(self) -> list[CatInfo]:
        return [
            CatInfo(category, len(chars))
            for category, chars in self.app._inorder_items()
        ]

    # Category ordering

    def fac_move_selected_cat(self, d: Direction) -> Callable[..., None]:
        def do_move(event=None):  # noqa: ARG001
            selected_cat = self.get_selected_category()
            si: int = self.list_cats.items.index(selected_cat)
            if (si + d) < 0 or (si + d) >= len(self.app.category_order):
                return

            reordered_items: list[CatInfo] = self.list_cats.move_selected_items(d)

            self.app.category_order[si], self.app.category_order[si + d] = self.app.category_order[si + d], self.app.category_order[si]

            self.app.log(f"New key order: {self.app.category_order}")
            assert [v.name for v in reordered_items] == self.app.category_order
        return do_move

    # Character ordering

    def fac_sort_chars_by(self, key_fn) -> Callable[..., None]:
        def do_sort(event=None):
            category: CatInfo = self.get_selected_category()
            characters = self.app.nested_state[category.name]

            sorted_group = sorted(characters, key=key_fn)
            self.app.nested_state[category.name] = sorted_group
            self.app.is_dirty = True
            self.open_category(category.name)

            assert self.list_chars.items == self.app.nested_state[category.name]

        return do_sort

    def fac_move_selected_chars(self, direction: Direction) -> Callable[..., None]:
        def do_move(event=None):  # noqa: ARG001
            category = self.get_selected_category()
            prev_order = tuple(self.app.nested_state[category.name])

            reordered_items: list[RoaEntry] = self.list_chars.move_selected_items(direction)
            self.app.nested_state[category.name] = reordered_items
            self.app.is_dirty = True

            self.app.log(f"Reordered {category.name} from {prev_order} to {reordered_items}")
            assert self.list_chars.items == reordered_items
        return do_move

    # Category actions

    def open_selected_category(self, event=None) -> None:  # noqa: ARG002
        self.open_category(self.get_selected_category().name)

    def open_category(self, cat_name: str) -> None:
        if cat_name == self.get_selected_category().name:
            group_items: list[RoaEntry] = self.app.nested_state[cat_name]
            self.list_chars.set_items(group_items)
            self.app.log(f"Loaded {len(group_items)} chars from group {cat_name!r}")
        else:
            # Update UI in case category was opened programatically
            self.list_cats.select_items(tuple(
                c for c in self.list_cats.items
                if c.name == cat_name
            ))

    def interactive_rename_category(self):
        cur_cat_name = self.get_selected_category().name
        new_name = askstring(title=None, prompt=f"New name for {cur_cat_name!r}")
        if new_name:
            self.rename_category(cur_cat_name, new_name)
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
        self.app.category_order[self.app.category_order.index(cat)] = new_name
        self.app.is_dirty = True

        self.load_gui_from_state()

    def delete_category(self):
        cat_name: str = self.get_selected_category().name
        if cat_name is not None and len(self.app.nested_state[cat_name]) == 0:
            self.app.nested_state.pop(cat_name)
            self.app.category_order.remove(cat_name)
            self.app.is_dirty = True
            self.load_gui_from_state()
        else:
            self.app.log("Can only remove empty categories")

    def add_category(self):
        new_name = askstring(title=None, prompt="Name for new category")
        if new_name and new_name not in self.app.nested_state.keys():
            self.app.nested_state[new_name] = []
            self.app.category_order.append(new_name)
            self.app.is_dirty = True

            self.load_gui_from_state()
            self.open_category(new_name)

            return new_name
        return None

    # Character actions

    def open_info(self, event=None):  # noqa: ARG002
        for char in self.list_chars.selected_items():
            url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={char.id}"
            webbrowser.open(url, autoraise=True)

    def open_folder(self, event=None):  # noqa: ARG002
        for char in self.list_chars.selected_items():
            path = char.value.decode('utf-8')
            os.startfile(path)  # noqa: S606

    def interactive_move_sel_to_cat(self, event=None):
        # TODO mirror move char to category via message prommpt
        # ALSO bind this to the listbox as a key

        src_cat: str = self.get_selected_category().name
        chars_to_move = self.list_chars.selected_items()

        results: Optional[list[str]] = MultiSelectDialog(
            self,
            ["New category: "],
            [
                [
                    *[c.label for c in self.gen_listitems_categories()],
                    "<NEW>"
                ]
            ]
        ).results

        if results:
            dest_cat_label = results[0]
            if dest_cat_label == "<NEW>":
                dest_cat: Optional[str] = self.add_category()
                if dest_cat is None:
                    return
            else:
                dest_cat = {
                    c.label: c.name for c in
                    self.gen_listitems_categories()
                }[dest_cat_label]

            for char in chars_to_move:
                self.move_char_to_category(src_cat, dest_cat, char)

        self.load_gui_from_state()

    def move_char_to_category(self, src_cat: str, dest_cat: str, char: RoaEntry):
        self.app.log(f"Moving {char} from {src_cat} to {dest_cat}")
        self.app.nested_state[src_cat].remove(char)
        self.app.nested_state[dest_cat].append(char)
        self.app.is_dirty = True

        self.load_gui_from_state()

    def move_chars_to_combobox_cat(self, event=None):
        src_cat: str = self.get_selected_category().name
        dest_cat_label: str = self.combo_cats.get()

        chars_to_move = self.list_chars.selected_items()

        if dest_cat_label == "<NEW>":
            dest_cat: Optional[str] = self.add_category()
            if dest_cat is None:
                return
        else:
            dest_cat = {
                c.label: c.name for c in
                self.gen_listitems_categories()
            }[dest_cat_label]

        for char in chars_to_move:
            self.move_char_to_category(src_cat, dest_cat, char)

        self.open_category(src_cat)
        self.combo_cats.set("Move to category...")
