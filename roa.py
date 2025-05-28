from collections import OrderedDict
from dataclasses import dataclass
import functools
import struct
from typing import ClassVar, List, Mapping, Optional
from typing_extensions import TypeAlias
from pathlib import Path
import os
import traceback
import configparser


class RoaEntry():
    def __init__(self, value: bytes) -> None:
        self.value: bytes = value

    @property
    def id(self) -> str:
        return Path(self.value.decode()).name

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} {self.name} {self.author}>"

    def decode(self) -> str:
        return self.value.decode('utf-8')

    @property
    def ini_path(self) -> Path:
        return Path(self.value.decode()) / 'config.ini'

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
        except configparser.Error as e:
            return {}

    @functools.cached_property
    def name(self):
        try:
            return self.ini['general'].get('name')
        except configparser.Error:
            print(self.ini_path)
            traceback.print_exc()
            return 'ERROR'
        except KeyError:
            return 'ERROR'

    @functools.cached_property
    def author(self):
        try:
            return self.ini['general'].get('author')
        except configparser.Error:
            print(self.ini_path)
            traceback.print_exc()
            return 'ERROR'
        except KeyError:
            return 'ERROR'

    @functools.cached_property
    def version(self) -> float:
        try:
            return float(eval(self.ini['general']['version']))
        except (KeyError, ValueError):
            return -1


def encode_le(number: int) -> bytes:
    return struct.pack('<H', number)


def encode_entry_list(strings: List[RoaEntry]) -> bytes:
    return b''.join(s.value + b'\x00' for s in strings)


def read_up_to_null(buffer: bytes, start_index: int) -> Optional[tuple[int, bytes]]:
    for i in range(start_index, len(buffer)):
        if buffer[i] == 0x00:
            return i, buffer[start_index:i]
    return None


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

    @staticmethod
    def read_preamble_count(view: bytes, i: int) -> Optional[int]:
        if view[i:i+2] == b'\x00\x01' and view[i+4:i+6] == b'\x00\x00':
            return struct.unpack('<H', view[i+2:i+4])[0]
        return None

    def check_file_header(self, file: bytes) -> bool:
        return file[:9] == self.header

    def load_bytes(self, data: bytes):
        view: bytes = data
        groups = []
        curr_group = []
        expected_count = 0
        i: int = 0

        while i < len(view) - 1:
            res = read_up_to_null(view, i)
            if res is None:
                break

            next_i, string = res
            i = next_i

            if string == self.header:
                # Beginning of list

                # Close previous list
                if len(curr_group) != expected_count:
                    print(f"Warning: Expected {expected_count} but got {len(curr_group)} elems!")
                groups.append(curr_group)

                # Begin next list
                curr_group = []

                expected_count = self.read_preamble_count(view, i)
                if expected_count is None:
                    raise ValueError("Parse error (expected preamble after order.roa)")
                i += 6
            else:
                curr_group.append(RoaEntry(string))
                i += 1

        if len(curr_group) != expected_count:
            print(f"Warning: Expected {expected_count} but got {len(curr_group)} elems!")
        groups.append(curr_group)

        if groups and groups[0] == []:
            groups.pop(0)

        if len(groups) < self.expected_group_count:
            raise ValueError(f"Parse error (expected >= {self.expected_group_count} groups but got {len(groups)})")

        for i, group in enumerate(groups):
            self.groups[self.group_labels[i]] = group

    def encode_group(self, group) -> bytes:
        blob_parts: list[bytes] = []

        blob_parts.append(self.header)
        blob_parts.append(b'\x00\x01')
        blob_parts.append(encode_le(len(group)))
        blob_parts.append(b'\x00\x00')
        blob_parts.append(encode_entry_list(group))

        return b''.join(blob_parts)

    def encode_bytes(self) -> bytes:
        blob_parts = []

        for group in self.groups.values():
            blob_parts.append(self.encode_group(group))

        return b''.join(blob_parts)

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
        view: bytes = data
        p: int = 0

        self.categories.clear()

        def _read_int() -> int:
            nonlocal p
            val = struct.unpack('<H', view[p:p+2])[0]
            p += 2
            return val

        def _read_null():
            nonlocal p
            assert view[p:p+1] == b'\x00'
            p += 1

        def _read_str() -> bytes:
            nonlocal p
            res = read_up_to_null(view, p)
            assert res is not None
            next_i, val = res
            p = next_i
            return val

        expected_count = _read_int()

        for _ in range(expected_count):
            category_index = _read_int()
            category_label = _read_str()

            self.categories.append(RoaCategory(index=category_index, label=category_label))
            _read_null()


    def encode_bytes(self) -> bytes:
        blob_parts = []

        blob_parts.append(encode_le(len(self.categories)))
        for c in self.categories:
            blob_parts.append(encode_le(c.index))
            blob_parts.append(c.label + b'\x00')

        return b''.join(blob_parts)

    def save_file(self) -> None:
        encoded: bytes = self.encode_bytes()

        print("Writing", self.roa_path)
        with open(self.roa_path, 'wb') as fp:
            fp.write(encoded)