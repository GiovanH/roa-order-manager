import struct
from typing import Optional

class BinReader():
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.p = 0

    def read_null(self, count=1):
        assert isinstance(self.data, bytes)
        for _ in range(count):
            assert self.data[self.p:self.p+1] == b'\x00'
            self.p += 1

    def read_raw(self, length) -> bytes:
        val = self.data[self.p:self.p+length]
        self.p += length
        return val

    def read_int(self) -> int:
        assert isinstance(self.data, bytes)
        val = struct.unpack('<H', self.data[self.p:self.p+2])[0]
        self.p += 2
        return val

    def read_str(self) -> bytes:
        assert isinstance(self.data, bytes)

        def read_up_to_null(buffer: bytes, start_index: int) -> Optional[tuple[int, bytes]]:
            for i in range(start_index, len(buffer)):
                if buffer[i] == 0x00:
                    return i, buffer[start_index:i]
            return None

        res = read_up_to_null(self.data, self.p)
        assert res is not None
        next_i, val = res
        self.p = next_i
        return val

class BinWriter():
    def __init__(self) -> None:
        self.parts: list[bytes] = []

    @property
    def blob(self) -> bytes:
        return b''.join(self.parts)

    def write_null(self):
        self.parts.append(b'\x00')

    def write_int(self, val: int):
        self.parts.append(struct.pack('<H', val))

    def write_str(self, val: bytes):
        self.parts.append(val + b'\x00')

    def write_strlist(self, strings: list[bytes]):
        self.write_int(len(strings))
        self.parts.append(b'\x00\x00')
        part = b''.join(s + b'\x00' for s in strings)
        self.parts.append(part)
