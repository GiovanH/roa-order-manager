from typing import Callable, TypeVar

T = TypeVar('T')


def assign(f: Callable[[], T]) -> T:
    """Define a variable with a nested block to prepare it"""
    return f()


if __name__ == '__main__':
    @assign
    def frame() -> list:
        v = []
        v.append(2)
        return v

    q = frame

    assert q == [2]
