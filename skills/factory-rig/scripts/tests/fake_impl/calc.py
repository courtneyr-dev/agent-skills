"""Tiny calculator."""


def add(a, b):
    return a + b


def multiply(a, b):
    for x in (a, b):
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError("integers only")
    return a * b
