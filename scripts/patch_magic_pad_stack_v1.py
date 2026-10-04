#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private correction of two same-plane metal/no-fill paint precedence rules.

No GDS, device, substrate, contact, runtime or extraction parameter changes.
Modified IHP technology retains its original Apache-2.0 notice.
"""
import argparse
import hashlib
from pathlib import Path

PARENT_SHA = '43e70494deef0d5c2e4ca182171c5da36b817ead2a5ac677b3528a8d3ab7fffa'


def patch(data):
    if hashlib.sha256(data).hexdigest() != PARENT_SHA:
        raise ValueError('Exact frozen ESD-v1 parent technology required')
    text = data.decode()
    for metal in (6,7):
        old = f'  paint  m{metal}      obsm5  m{metal}\n'
        new = f'  paint  m{metal}      obsm{metal}  m{metal}\n'
        if text.count(old) != 1:
            raise ValueError('Missing same-plane paint rule')
        text = text.replace(old,new)
    return text.encode()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path); p.add_argument('output',type=Path)
    a = p.parse_args()
    with a.output.open('xb') as out:
        out.write(patch(a.source.read_bytes()))


if __name__ == '__main__':
    main()
