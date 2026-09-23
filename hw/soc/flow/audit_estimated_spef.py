#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check capacitance conservation in grounded, PIN_CAP NONE estimated SPEF.

This catches omitted wire capacitance, including the pinned OpenROAD exporter's
omission of pin-node ground capacitance. It does not verify RC accuracy, coupling
models, connectivity or timing. Coupled SPEF is deliberately unsupported here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def audit(path):
    path = Path(path)
    digest = hashlib.sha256()
    net = None
    section = None
    scale = None
    pin_cap_none = False
    count = bad = 0
    declared_sum = serialized_sum = 0.0
    examples = []

    def number(value):
        result = float(value)
        if not math.isfinite(result) or result < 0:
            raise ValueError('Capacitances must be finite and nonnegative')
        return result

    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            line = raw.decode('utf-8').strip()
            words = line.split()
            if not words or line.startswith('//'):
                continue
            if words[0] == '*DESIGN_FLOW':
                pin_cap_none = '"PIN_CAP NONE"' in line
            elif words[0] == '*C_UNIT':
                if len(words) != 3 or words[2].upper() not in ('F', 'NF', 'PF', 'FF'):
                    raise ValueError('Unsupported capacitance unit')
                scale = number(words[1]) * {'F': 1e12, 'NF': 1e3,
                                           'PF': 1, 'FF': 1e-3}[words[2].upper()]
                if scale == 0:
                    raise ValueError('Zero capacitance unit')
            elif words[0] == '*D_NET':
                if net is not None or len(words) != 3 or scale is None or not pin_cap_none:
                    raise ValueError('Malformed net or missing PIN_CAP NONE/unit declaration')
                net = words[1]
                declared = number(words[2]) * scale
                actual = 0.0
                section = None
            elif words[0] == '*END':
                if net is None:
                    raise ValueError('END outside a net')
                count += 1
                declared_sum += declared
                serialized_sum += actual
                difference = declared - actual
                # The producer prints approximately six significant digits.
                if abs(difference) > max(1e-8, 1e-5 * max(declared, actual)):
                    bad += 1
                    if len(examples) < 20:
                        examples.append(dict(net=net, declared_pf=declared,
                                             serialized_pf=actual, difference_pf=difference))
                net = section = None
            elif words[0] in ('*CAP', '*RES', '*CONN'):
                if net is None:
                    raise ValueError('Net section outside a net')
                section = words[0]
            elif section == '*CAP':
                if len(words) != 3 or not words[0].isdigit():
                    raise ValueError('Only grounded capacitance entries are supported')
                actual += number(words[2]) * scale
    if net is not None or not count:
        raise ValueError('Truncated or empty estimated SPEF')
    return dict(status='FAIL' if bad else 'PASS within scope', nets=count,
                inconsistent_nets=bad, declared_total_pf=declared_sum,
                serialized_total_pf=serialized_sum,
                difference_pf=declared_sum-serialized_sum, examples=examples,
                input_sha256=digest.hexdigest(),
                scope='Grounded wire-capacitance conservation only; excludes RC accuracy, '
                      'connectivity, coupling, timing and manufacturing acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spef', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.spef)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['status']}: {result['inconsistent_nets']}/{result['nets']} nets inconsistent")
    return 2 if result['inconsistent_nets'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
