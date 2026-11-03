# SPDX-License-Identifier: Apache-2.0
from decimal import Decimal
import re
def require(ok, message):
    if not ok:
        raise ValueError(message)

def statements(text):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            require(bool(lines), "Unattached continuation")
            lines[-1] += " " + line[1:].strip()
        else:
            lines.append(line)
    return [line.split() for line in lines]

def number(value):
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)", str(value)
    )
    require(match is not None, "Unsupported numeric token")
    factors = {
        "": 0,
        "t": 12,
        "g": 9,
        "meg": 6,
        "k": 3,
        "m": -3,
        "u": -6,
        "n": -9,
        "p": -12,
        "f": -15,
        "a": -18,
    }
    suffix = match[2].lower()
    require(suffix in factors, "Unknown unit")
    result = Decimal(match[1]) * Decimal(10) ** factors[suffix]
    require(result.is_finite(), "Nonfinite value")
    return result

class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while x != root:
            x, self.parent[x] = self.parent[x], root
        return root

    def join(self, a, b):
        self.parent[self.find(a)] = self.find(b)
