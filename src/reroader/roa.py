import configparser
import functools
import glob
import itertools
import os
import traceback
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from frozendict import frozendict

from .binutil import BinReader, BinWriter

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")


class RoaEntry():
    def __init__(self, value: bytes) -> None:
        self.value: bytes = value

    @property
    def directory(self) -> Path:
        return Path(self.value.decode())

    @property
    def id(self) -> str:
        return self.directory.name

    def __repr__(self):
        return f"<{self.name!r} {self.id} by {self.author!r}>"

    def decode(self) -> str:
        return self.value.decode('utf-8')

    @property
    def ini_path(self) -> Path:
        return self.directory / 'config.ini'

    @property
    def type(self) -> str:
        type_val = self.get_property('type')
        if type_val == '0':
            return 'characters'
        if type_val == '1':
            return 'buddies'
        if type_val == '2':
            return 'stages'
        if type_val == '3':
            return 'skins'
        raise NotImplementedError(type_val)

    image_sizes: ClassVar[frozendict[str, tuple[int, int]]] = frozendict({
        'characters': (79, 31),
        'stages': (56, 40),
        'buddies': (42, 32),
        'skins': (79, 31),
    })

    def image_path(self) -> Path:
        if self.type == 'characters':
            return self.directory / 'result_small.png'
        if self.type == 'buddies':
            return self.directory / 'icon.png'
        if self.type == 'skins':
            return self.directory / 'result_small.png'
        if self.type == 'stages':
            return self.directory / 'thumb.png'
        raise NotImplementedError(f"RoaEntry.image for type {self.type!r}")

    @functools.cached_property
    def ini(self) -> configparser.ConfigParser:
        filename = self.ini_path
        if not os.path.isfile(filename):
            print("File not found:", filename)
            return {}  # type: ignore
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            with open(filename, 'r', encoding='utf-8') as fp:
                parser.read_file(fp)
            return parser
        except configparser.Error:
            traceback.print_exc()
            return parser

    def get_property(self, key) -> str:
        try:
            return self.ini['general'].get(key)[1:-1]  # type: ignore
        except configparser.Error:
            print("Parser error reading", self.ini_path)
            traceback.print_exc()
            return '<INI ERROR>'
        except (KeyError, TypeError):
            print("Key error reading", self.ini_path)
            traceback.print_exc()
            return '<UNDEFINED>'

    @functools.cached_property
    def name(self) -> str:
        return self.get_property('name')

    @functools.cached_property
    def author(self) -> str:
        return self.get_property('author')

    @functools.cached_property
    def version(self) -> float:
        try:
            return self.ini['general'].getfloat('version')  # type: ignore
        except (KeyError, ValueError):
            return -1


class RoaOrderFile:
    group_labels: ClassVar[list[str]] = ['characters', 'buddies', 'stages', 'skins']
    header: bytes = b"order.roa"

    @property
    def expected_group_count(self) -> int:
        return len(self.group_labels)

    def __init__(self, roa_path: Path) -> None:
        self.roa_path: Path = roa_path

        self.groups: dict[str, list[RoaEntry]] = OrderedDict()
        self.state_on_disk: frozendict[str, list[RoaEntry]] = frozendict()

        self.load_from_disk()

        self.scan_for_new_chars()

    def is_dirty(self) -> bool:
        return self.groups != self.state_on_disk

    def check_file_header(self, file: bytes) -> bool:
        return file[:9] == self.header

    def load_from_disk(self) -> None:
        with open(self.roa_path, 'rb') as fp:
            data: bytes = fp.read()

        if not self.check_file_header(data):
            raise ValueError("Bad input file")

        self.load_bytes(data)
        assert data == self.encode_bytes()
        assert not self.is_dirty()

    def load_bytes(self, data: bytes) -> None:
        view: bytes = data
        groups = []
        curr_group = []
        group_type = self.group_labels[len(curr_group)]
        expected_count = 0

        reader = BinReader(data)

        while reader.p < len(view) - 1:
            string = reader.read_str()

            if string == self.header:
                # Close previous list
                if len(curr_group) != expected_count:
                    print(f"Warning: Expected {expected_count} but got {len(curr_group)} elems!")
                groups.append(curr_group)

                # Begin next list
                curr_group = []

                assert reader.read_raw(2) == b'\x00\x01'
                expected_count = reader.read_int()
                reader.read_null(2)
            else:
                group_type = self.group_labels[len(groups) - 1]
                curr_group.append(RoaEntry(value=string))
                reader.read_null()

        if len(curr_group) != expected_count:
            print(f"Warning: Expected {expected_count} but got {len(curr_group)} elems!")
        groups.append(curr_group)

        if groups and groups[0] == []:
            groups.pop(0)

        if len(groups) < self.expected_group_count:
            raise ValueError(f"Parse error (expected >= {self.expected_group_count} groups but got {len(groups)})")

        for i, group in enumerate(groups):
            self.groups[self.group_labels[i]] = group

        self.state_on_disk = frozendict(self.groups)
        assert not self.is_dirty()

    def encode_bytes(self) -> bytes:
        writer = BinWriter()

        for group in self.groups.values():
            writer.write_str(self.header)
            writer.parts.append(b'\x01')
            writer.write_strlist([g.value for g in group])

        return writer.blob

    def save_file(self) -> None:
        encoded: bytes = self.encode_bytes()

        if not self.check_file_header(encoded):
            raise ValueError("Bad output attempt")

        print("Writing", self.roa_path)
        with open(self.roa_path, 'wb') as fp:
            fp.write(encoded)

        self.state_on_disk = frozendict(self.groups)
        assert not self.is_dirty()

    def scan_for_new_chars(self) -> None:
        # 1. Find paths for all known entries
        all_entries = {*itertools.chain(*self.groups.values())}
        known_entry_dirs = {e.directory for e in all_entries}

        # 2. Find set of root directories
        root_dirs = {e.directory.parent for e in all_entries}

        # 3. Find paths on disk not in order list
        all_entry_dirs = {
            *(
                Path(s) for s in
                itertools.chain(
                    *(
                        glob.glob(str(parent) + '/*/')
                        for parent in root_dirs
                    )
                )
            )
        }

        # # 4. Add new order items to list state
        new_dirs = all_entry_dirs - known_entry_dirs
        for n in new_dirs:
            try:
                dir_bytes = str(n).encode('utf-8')
                new_entry = RoaEntry(dir_bytes)

                print("Adding new entry", new_entry, "to", new_entry.type)
                self.groups[new_entry.type].append(new_entry)
            except:
                traceback.print_exc()
                continue

        # raise NotImplementedError()

@dataclass
class RoaCategory():
    index: int
    label: bytes


class RoaCategoriesFile:
    def __init__(self, roa_path: Path) -> None:
        self.roa_path: Path = roa_path

        self.categories: list[RoaCategory] = []
        self.state_on_disk: tuple[RoaCategory, ...] = tuple()

        with open(roa_path, 'rb') as fp:
            data: bytes = fp.read()

        self.load_bytes(data)

        assert data == self.encode_bytes()

    def is_dirty(self) -> bool:
        return tuple(self.categories) != self.state_on_disk

    def load_bytes(self, data: bytes) -> None:
        self.categories.clear()
        reader = BinReader(data)
        expected_count = reader.read_int()

        for _ in range(expected_count):
            c_index = reader.read_int()
            c_label = reader.read_str()

            self.categories.append(RoaCategory(index=c_index, label=c_label))
            reader.read_null()

        self.state_on_disk = tuple(self.categories)
        assert not self.is_dirty()

    def encode_bytes(self) -> bytes:
        writer = BinWriter()

        writer.write_int(len(self.categories))
        for c in self.categories:
            writer.write_int(c.index)
            writer.write_str(c.label)

        return writer.blob

    def save_file(self) -> None:
        encoded: bytes = self.encode_bytes()

        print("Writing", self.roa_path)
        with open(self.roa_path, 'wb') as fp:
            fp.write(encoded)

        self.state_on_disk = tuple(self.categories)
        assert not self.is_dirty()
