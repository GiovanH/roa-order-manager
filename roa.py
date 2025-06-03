import ast
from collections import OrderedDict
from dataclasses import dataclass
import functools
from typing import ClassVar, Mapping
from pathlib import Path
import os
import traceback
import configparser

from bin import BinReader, BinWriter


class RoaEntry():
    def __init__(self, type: str, value: bytes) -> None:
        self.value: bytes = value
        self.type: str = type

    @property
    def id(self) -> str:
        return Path(self.value.decode()).name

    def __repr__(self):
        return f"<{self.name!r} {self.id} by {self.author!r}>"

    def decode(self) -> str:
        return self.value.decode('utf-8')

    @property
    def ini_path(self) -> Path:
        return Path(self.value.decode()) / 'config.ini'

    def image_path(self) -> Path:
        if self.type == 'characters':
            return Path(self.value.decode()) / 'hud.png'
        if self.type == 'buddies':
            return Path(self.value.decode()) / 'icon.png'
        if self.type == 'skins':
            return Path(self.value.decode()) / 'icon.png'
        if self.type == 'stages':
            return Path(self.value.decode()) / 'thumb.png'
        raise NotImplementedError(f"RoaEntry.image for type {self.type!r}")

    @functools.cached_property
    def ini(self) -> Mapping[str, Mapping[str, str]]:
        filename = self.ini_path
        if not os.path.isfile(filename):
            print(FileNotFoundError(filename))
            return {}
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            with open(filename, 'r', encoding='utf-8') as fp:
                parser.read_file(fp)
            return parser
        except configparser.Error:
            traceback.print_exc()
            return parser

    @functools.cached_property
    def name(self):
        try:
            return self.ini['general'].get('name')[1:-1]  # type: ignore
        except configparser.Error:
            print(self.ini_path)
            traceback.print_exc()
            return 'ERROR'
        except KeyError:
            return 'ERROR'

    @functools.cached_property
    def author(self):
        try:
            return self.ini['general'].get('author')[1:-1]  # type: ignore
        except configparser.Error:
            print(self.ini_path)
            traceback.print_exc()
            return 'ERROR'
        except (KeyError, TypeError):
            return 'ERROR'

    @functools.cached_property
    def version(self) -> float:
        try:
            return float(ast.literal_eval(self.ini['general']['version']))
        except (KeyError, ValueError):
            return -1


class RoaOrderFile:
    group_labels: ClassVar[list[str]] = ['characters', 'buddies', 'stages', 'skins']
    header: bytes = b"order.roa"

    @property
    def expected_group_count(self) -> int:
        return len(self.group_labels)

    def __init__(self, roa_path: Path) -> None:
        self.groups: dict[str, list[RoaEntry]] = OrderedDict()
        self.roa_path: Path = roa_path

        with open(roa_path, 'rb') as fp:
            data: bytes = fp.read()

        if not self.check_file_header(data):
            raise ValueError("Bad input file")

        self.load_bytes(data)
        assert data == self.encode_bytes()

    def check_file_header(self, file: bytes) -> bool:
        return file[:9] == self.header

    def load_bytes(self, data: bytes):
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
                group_type = self.group_labels[len(groups)-1]
                curr_group.append(RoaEntry(type=group_type, value=string))
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


@dataclass
class RoaCategory():
    index: int
    label: bytes


class RoaCategoriesFile:
    def __init__(self, roa_path: Path) -> None:
        self.categories: list[RoaCategory] = []

        self.roa_path: Path = roa_path

        with open(roa_path, 'rb') as fp:
            data: bytes = fp.read()

        self.load_bytes(data)

        assert data == self.encode_bytes()

    def load_bytes(self, data: bytes):
        self.categories.clear()
        reader = BinReader(data)
        expected_count = reader.read_int()

        for _ in range(expected_count):
            c_index = reader.read_int()
            c_label = reader.read_str()

            self.categories.append(RoaCategory(index=c_index, label=c_label))
            reader.read_null()

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
