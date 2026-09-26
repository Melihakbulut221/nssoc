# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check unpowered OpenROAD netlists across antenna/filler insertion.

Original cells, masters, pin connections, ports, aliases and wires must stay
unchanged. Only IHP antenna and pinless filler/decap additions are accepted.
This is not extracted LVS, a power-net comparison, or a timing check.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

from check_physical_eco import NET, parse


def check(before, after):
    before, after = Path(before), Path(after)
    original, ports, aliases = parse(before)
    routed, routed_ports, routed_aliases = parse(after)
    if ports != routed_ports or aliases != routed_aliases:
        raise ValueError('Original ports or aliases changed')
    if not original.keys() <= routed.keys():
        raise ValueError('Original instances removed')
    for name, cell in original.items():
        if cell != routed[name]:
            raise ValueError(('Original master/pin change', name))

    def wires(path):
        return {re.sub(r'\s+', ' ', raw.strip())
                for raw in path.read_text().split(';')
                if re.match(r'^\s*wire\b', raw)}

    if not wires(before) <= wires(after):
        raise ValueError('Original wire declaration removed/changed')
    original_nets = {net for _, pins in original.values()
                     for value in pins.values() for net in re.findall(NET, value)}
    additions = collections.Counter()
    for name in sorted(routed.keys() - original.keys()):
        master, pins = routed[name]
        if master == 'sg13g2_antennanp':
            if (set(pins) != {'A'} or not re.fullmatch(NET, pins['A'])
                    or pins['A'] not in original_nets):
                raise ValueError(('Unexpected antenna connection', name, pins))
            additions['antenna'] += 1
        elif re.fullmatch(r'sg13g2_(?:fill|decap)_[0-9]+', master):
            if pins:
                raise ValueError(('Unexpected pins on physical filler', name, pins))
            additions['filler_or_decap'] += 1
        else:
            raise ValueError(('Unexpected added master', name, master))
    return {
        'status': 'PASS within scope',
        'scope': ('Unpowered emitted netlists: original cells, masters, pins, ports, '
                  'aliases and wires preserved; added antenna/filler/decap only. '
                  'Does not compare extracted connectivity, geometry, power nets '
                  'or timing. Separate LVS required.'),
        'original_instances': len(original),
        'added_instances': dict(additions),
        'before': str(before),
        'before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
        'after': str(after),
        'after_sha256': hashlib.sha256(after.read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = json.dumps(check(args.before, args.after), indent=2) + '\n'
    # Preserve earlier verdicts instead of silently replacing their provenance.
    with args.output.open('x') as output:
        output.write(result)
    print(result, end='')


if __name__ == '__main__':
    main()
