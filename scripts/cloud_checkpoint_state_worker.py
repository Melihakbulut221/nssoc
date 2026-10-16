#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Stateful checkpoint fixture: deliberately unaware of checkpoint/restart."""
import hashlib,json,os,random,struct,time
from pathlib import Path
COUNT=3000
RECORD=struct.Struct('<IQQd16s')
SEED=0x65B12409
MASK=(1<<64)-1

def records(nonce,delay=0.):
    rng=random.Random(SEED);state=0xC947AFB517;acc=0.;heap=bytearray(range(256))*(256*1024)
    for i in range(COUNT):
        draw=rng.getrandbits(64);state=((state<<7)^(state>>3)^draw^i)&MASK
        acc+=((draw&65535)-32768)*1e-12
        heap[(i*7919)%len(heap)]=(heap[(i*7919)%len(heap)]+(draw&255))&255
        yield RECORD.pack(i,draw,state,acc,nonce)
        if delay:time.sleep(delay)
    yield hashlib.sha256(heap).digest()

def main():
    root=Path('/data');nonce=os.urandom(16)
    with (root/'boots.log').open('ab',buffering=0)as f:f.write(nonce.hex().encode()+b'\n')
    with (root/'wave.bin').open('wb',buffering=0)as f:
        for row in records(nonce,.01):f.write(row)
        os.fsync(f.fileno())
    (root/'done.json').write_text(json.dumps(dict(nonce=nonce.hex(),rows=COUNT,sha256=hashlib.sha256((root/'wave.bin').read_bytes()).hexdigest())))
if __name__=='__main__':main()
