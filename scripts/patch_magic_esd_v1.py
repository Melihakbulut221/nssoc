#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private, additive native ESD recognition; unchanged PDK/runtime stay frozen.

Only the isolated ordinary 2-kV PCell family is supported by the accompanying
geometry/terminal auditor. The raw native emitter measurements are retained;
this does not qualify ESD stress, compact-model behavior, or full-bank PEX.
Modified Magic files retain the UC Regents notice; IHP files retain Apache-2.0.
"""
import argparse
import hashlib
from pathlib import Path

PINS = {
    'CIFrdtech.c': '2378e6866f798f93d39846cebcd2cde1a45530ad219892789ace9b35e930011c',
    'CIFgen.c': '06343b91387df59bca786bfacc38909c6b98dfdbc22f53793e2445436d875e77',
    'ihp-sg13g2.tech': 'b0dab0f98430668168b8060256bf9ede2a68332735616751db08c53272de8b56',
    'ihp-sg13g2-cifin.tech': 'b30270cf760f4372264528c10d764072c8b968852825735cec104156c74c4310',
    'ihp-sg13g2-extract.tech': '2a4f8e9b9fdc76f38be93c146243453905d397a8ad06a1357b31e3418b748241',
}

PARSER = '''    else if (strcmp(argv[0], "interacting") == 0)
    {
        newOp->co_opcode = CIFOP_INTERACT;
        newOp->co_client = (ClientData)CIFOP_INT_TOUCHING;
    }
    else if (strcmp(argv[0], "noninteracting") == 0)
    {
        newOp->co_opcode = CIFOP_INTERACT;
        newOp->co_client = (ClientData)(CIFOP_INT_TOUCHING | CIFOP_INT_NOT);
    }
'''

# Conservative exclusions: reject the entire recognition region if any of
# these unsupported device materials touches it. Never synthesize an ESD from
# a name, missing terminal, or expected inventory.
IMPORT = ''' # Source-proven ordinary diode-ESD geometry only. This is not an
 # isolated-well, 4-kV, clamp-MOS or general ESD-family implementation.
 templayer esdallowed ESDID
 noninteracting NSDBLOCK,NSD,BIPOLARID,EMITTER,HVEMITTER,POLYRES,EXTBLOCK,RESDEF,INDUCTOR,INDPIN,POLY,THKOX,SBLK,DNWELL,PWELLBLK
 templayer esdvddcore DIFF
 and PSD
 and NWELL
 and esdallowed
 templayer esdvsscore DIFF
 and-not PSD
 and-not NWELL
 and esdallowed
 templayer esdvddmark esdallowed
 interacting esdvddcore
 noninteracting esdvsscore
 templayer esdvssmark esdallowed
 interacting esdvsscore
 noninteracting esdvddcore
 layer esdpnp esdvddmark
 layer esdnpn esdvssmark
'''

DEVICES = ''' # The marker is on a separate plane; original well/diffusion is
 # untouched. Its first terminal reaches ONLY physically overlapping nwell:
 # VDD is PNP base / NPN collector; PAD is the measured emitter diffusion;
 # SUB is the actual substrate node reached through existing physical taps.
 # Preserve measured emitter area/perimeter as audit annotations, not extra
 # parameters passed silently into a foundry compact model.
 device subcircuit diodevdd_2kv esdpnp *pdiff pwell,space/w error a1=ea p1=ep
 device subcircuit diodevss_2kv esdnpn *ndiff pwell,space/w error a1=ea p1=ep
'''


def patch(name, data):
    if name not in PINS or hashlib.sha256(data).hexdigest() != PINS[name]:
        raise ValueError('Exact frozen finite-tap native parent required')
    text = data.decode()
    if name == 'CIFrdtech.c':
        edits = [
            ('    else if (strcmp(argv[0], "copyup") == 0)\n',
             PARSER+'    else if (strcmp(argv[0], "copyup") == 0)\n'),
            ('\tcase CIFOP_COPYUP:\n\t    if (argc != 2)',
             '\tcase CIFOP_COPYUP:\n        case CIFOP_INTERACT:\n\t    if (argc != 2)'),
        ]
    elif name == 'CIFgen.c':
        start = text.index('void\ncifInteractingRegions(')
        end = text.index('/*\n * ----------------------------------------------------------------------------', start)
        part = text[start:end]
        copy = part.index('\tTiSetClientINT(tile, CIF_IGNORE);')
        tail = part[copy:]
        if tail.count('PUSHTILEONLY') != 5:
            raise ValueError('Exact marked-region copy walk required')
        # These tiles were deliberately marked IGNORE before being queued.
        # Conditional PUSHTILEONLY accepts only UNPROCESSED and drops them.
        # Unconditional enqueue preserves the existing once-only marking.
        after = part[:copy]+tail.replace(
            'PUSHTILEONLY(tile, RegStack);', 'STACKPUSH(PTR2CD(tile), RegStack);').replace(
            'PUSHTILEONLY(tp, RegStack);', 'STACKPUSH(PTR2CD(tp), RegStack);')
        edits = [(part, after)]
    elif name == 'ihp-sg13g2.tech':
        edits = [
            ('\nplanes\n', '\nplanes\n  esddevice\n'),
            ('  well nbase,pnp\n', '  well nbase,pnp\n  esddevice esdpnp\n  esddevice esdnpn\n'),
            ('\nconnect\n', '\nconnect\n  esdpnp,esdnpn *nwell\n'),
        ]
    elif name == 'ihp-sg13g2-cifin.tech':
        edits = [(' layer nwell NWELL,WELLPIN\n', IMPORT+' layer nwell NWELL,WELLPIN\n')]
    else:
        edits = [
            (' planeorder comment    12\n', ' planeorder comment    12\n planeorder esddevice 13\n'),
            (' # Lateral PNP bipolar\n', DEVICES+' # Lateral PNP bipolar\n'),
        ]
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError('Missing or ambiguous source anchor')
        text = text.replace(old, new)
    inverse = text
    for old, new in reversed(edits):
        inverse = inverse.replace(new, old)
    if inverse.encode() != data:
        raise ValueError('Unexpected source delta')
    return text.encode()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    with a.output.open('xb') as f:
        f.write(patch(a.source.name, a.source.read_bytes()))


if __name__ == '__main__':
    main()
