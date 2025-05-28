import struct
from typing import List, Optional

from pathlib import Path

class RoaEntry():
    def __init__(self, value: str) -> None:
        self.value: str = value

    def encode(self) -> bytes:
        return self.value.encode('utf-8')


def encode_le(number: int) -> bytes:
    return struct.pack('<H', number)


def encode_entry_list(strings: List[RoaEntry]) -> bytes:
    return b''.join(s.encode() + b'\x00' for s in strings)


def read_up_to_null(buffer: bytes, start_index: int) -> Optional[tuple[int, str]]:
    for i in range(start_index, len(buffer)):
        if buffer[i] == 0x00:
            return i, buffer[start_index:i].decode('utf-8')
    return None


class RoaFile:
    group_labels: list[str] = ['characters', 'buddies', 'stages', 'skins']

    @property
    def expected_group_count(self) -> int:
        return len(self.group_labels)

    def __init__(self, roa_path: Path, header=b"order.roa") -> None:
        self.characters: List[RoaEntry] = []
        self.buddies: List[RoaEntry] = []
        self.stages: List[RoaEntry] = []
        self.skins: List[RoaEntry] = []

        self.roa_path: Path = roa_path
        self.header: bytes = header

        with open(roa_path, 'rb') as fp:
            data = fp.read()

            if not self.check_file(data):
                raise ValueError("Bad input file")

            self.load_bytes(data)

            assert data == self.encode_bytes()

    @staticmethod
    def read_preamble_count(view: bytes, i: int) -> Optional[int]:
        if view[i:i+2] == b'\x00\x01' and view[i+4:i+6] == b'\x00\x00':
            return struct.unpack('<H', view[i+2:i+4])[0]
        return None

    def check_file(self, file: bytes) -> bool:
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

            if string == "order.roa":
                if len(curr_group) != expected_count:
                    print(f"Warning: Expected {expected_count} but got {len(curr_group)} elems!")
                groups.append(curr_group)
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

        self.characters, self.buddies, self.stages, self.skins = groups[:4]

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

        for group in [self.characters, self.buddies, self.stages, self.skins]:
            blob_parts.append(self.encode_group(group))

        return b''.join(blob_parts)

    def save_file(self) -> None:
        encoded: bytes = self.encode_bytes()

        if not self.check_file(encoded):
            raise ValueError("Bad output attempt")

        with open(self.roa_path, 'wb') as fp:
            fp.write(encoded)
