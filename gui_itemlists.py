from dataclasses import dataclass
import tkinter as tk
from abc import abstractmethod
from functools import lru_cache
from tkinter import ttk
from typing import ClassVar, Generic, Literal, Sequence, TypeAlias, TypeVar, Union

from roa import RoaEntry

Direction: TypeAlias = Union[Literal[1], Literal[-1]]

T = TypeVar('T')

tkid: TypeAlias = str


@dataclass(frozen=True)
class CatInfo():
    name: str
    length: int

    @property
    def label(self):
        return f"{self.name} ({self.length})"


@lru_cache(maxsize=None)
def photoimage(path: str) -> tk.PhotoImage:
    return tk.PhotoImage(file=path)


class ItemListFrame(tk.Frame, Generic[T]):
    columns: ClassVar[tuple[str, ...]] = ('Value',)

    @staticmethod
    @abstractmethod
    def item_to_values(item: T) -> tuple[str, ...]: pass

    def __init__(
        self,
        parent,
        multiple=False,
        icon_size: tuple[int, int] = (0, 20)
    ) -> None:
        super().__init__(parent)
        self.items: list[T] = []
        self.map_ids: dict[T, tkid] = {}
        self.map_items: dict[tkid, T] = {}

        style_id = f"height{icon_size[1]}.Treeview"
        s = ttk.Style()
        s.configure(style_id, rowheight=icon_size[1])
        s.configure(style_id+".padding", border=0)
        s.configure(style_id+".treearea", border=0)

        myscroll = tk.Scrollbar(self)
        myscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree: ttk.Treeview = ttk.Treeview(
            self,
            selectmode=('extended' if multiple else 'browse'),
            yscrollcommand=myscroll.set,
            columns=self.columns,
            style=style_id
        )
        myscroll.config(command=self.tree.yview)

        self.tree.column('#0', width=0, minwidth=icon_size[0] + (20 if icon_size[0] > 0 else 0))
        for i, header in enumerate(self.columns):
            widths = {
                'Length': 30
            }
            self.tree.column(i, width=widths.get(header, 120), minwidth=40)
            self.tree.heading(column=i, text=header)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def set_items(self, items: Sequence[T]):
        self.items = list(items)
        self.tree.delete(*self.tree.get_children(''))
        for item in items:
            values: tuple[str, ...] = self.item_to_values(item)
            if isinstance(item, RoaEntry):
                try:
                    self.map_ids[item] = self.tree.insert(
                        '', tk.END,
                        image=photoimage(str(item.image_path())),
                        values=values
                    )

                    continue
                except tk.TclError as e:
                    print(item, item.image_path(), e)

            self.map_ids[item] = self.tree.insert(
                '', tk.END,
                values=values
            )
            continue
        self.map_items = {v: k for k, v in self.map_ids.items()}

    def bind_select(self, callback):
        self.tree.bind('<<TreeviewSelect>>', callback)

    def select_items(self, items: Union[T, tuple[T, ...]]) -> None:
        if not isinstance(items, tuple):
            items = (items,)
        ids: list[tkid] = [
            self.map_ids[entry]  # type: ignore
            for entry in items
        ]
        self.tree.selection_set(ids)

    def move_items(self, selected_items: Sequence[T], direction: Direction) -> list[T]:
        if direction == 1:
            selected_items = list(reversed(selected_items))
        for item in selected_items:
            i = self.items.index(item)
            if (i + direction) < 0 or (i + direction) >= len(self.items):
                continue

            self.items[i], self.items[i + direction] = self.items[i + direction], self.items[i]

            self.tree.move(self.map_ids[item], '', i + direction)

        return self.items

    def move_selected_items(self, direction: Direction) -> list[T]:
        return self.move_items(self.selected_items(), direction)

    def selected_items(self) -> list[T]:
        return [self.map_items[v] for v in self.tree.selection()]


class ItemListFrameRoa(ItemListFrame[RoaEntry]):
    columns: ClassVar[tuple[str, ...]] = ('Name', 'Author')

    @staticmethod
    def item_to_values(item: RoaEntry) -> tuple[str, ...]:
        return (item.name, item.author)


class ItemListFrameCats(ItemListFrame[CatInfo]):
    columns: ClassVar[tuple[str, ...]] = ('Name', 'Length')

    @staticmethod
    def item_to_values(item: CatInfo) -> tuple[str, ...]:
        return (item.name, str(item.length))
