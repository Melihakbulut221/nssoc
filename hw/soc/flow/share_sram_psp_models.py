#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Specialize the PDK's default single-finger PSP wrapper per SRAM geometry.

Avoid re-parsing identical per-instance model cards. The original PDK model
expressions and every circuit node/dimension remain explicit. This experiment
requires independent original-wrapper comparison before any SRAM acceptance.
Only the exact l/w-only, ng=1, pre-layout wrapper profile is supported.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def specialize(circuit, parameters, wrapper):
    defaults = 'w=0.35u l={length} ng=1 m=1 mm_ok=1 as=0 ad=0 pd=0 ps=0 trise=0 z1=0.34e-6 z2=0.38e-6 wmin=0.15e-6 rfmode=0 pre_layout=1'
    for kind, length in [('nmos', '0.34u'), ('pmos', '0.28u')]:
        match = re.search(r'(?m)^\.subckt sg13_lv_'+kind+r' d g s b\n\+ (.*)', wrapper)
        if not match or match[1] != defaults.format(length=length):
            raise ValueError('Unsupported PDK wrapper defaults')
        # Pin the exact executable wrapper separately in each run. These
        # expressions are ng=1, as=ad=ps=pd=0, rfmode=0, trise=0.
    blocks = {}
    for part in re.split(r'(?m)(?=^\.model )', parameters)[1:]:
        name = part.split()[1]
        if name in ['sg13g2_lv_nmos_psp', 'sg13g2_lv_pmos_psp']:
            blocks[name] = '\n'.join(line for line in part.splitlines()
                                     if line.startswith(('.model', '+')))
    if len(blocks) != 2:
        raise ValueError('Missing original PSP model definitions')
    records, output, models = {}, [], []
    for line in circuit.splitlines():
        if line[:1].lower() == 'n':
            raise ValueError('Input already contains native device instances')
        if not re.search(r' sg13_lv_[np]mos\b', line):
            output.append(line)
            continue
        fields = line.split()
        if len(fields) != 8 or not fields[0].startswith('X'):
            raise ValueError('Unsupported transistor adapter syntax')
        kind = fields[5]
        if kind not in ['sg13_lv_nmos', 'sg13_lv_pmos']:
            raise ValueError('Unsupported primitive')
        values = dict(s.split('=') for s in fields[6:])
        if set(values) != {'l', 'w'}:
            raise ValueError('Only explicit l/w with default wrapper profile supported')
        length, width = float(values['l']), float(values['w'])
        if not (math.isfinite(length) and math.isfinite(width)
                and 0.13e-6 <= length <= 10e-6 and 0.15e-6 <= width <= 10e-6):
            raise ValueError('Dimensions outside documented model domain')
        key = (kind, length, width)
        if key not in records:
            name = 'sram_shared_'+hashlib.sha256(repr(key).encode()).hexdigest()[:16]
            original = kind.replace('sg13_lv_', 'sg13g2_lv_')+'_psp'
            body = blocks[original].replace('.model '+original+' ', '.model '+name+' ', 1)
            bindings = {'w': width, 'l': length, 'ng': 1, 'pre_layout': 1}
            for symbol, value in bindings.items():
                body = re.sub(r'\b'+symbol+r'\b', format(value, '.17g'), body)
            models.append(body)
            records[key] = dict(model=name, primitive=kind, length_m=length, width_m=width,
                                area_m2=width*.34e-6, perimeter_m=2*(width+.34e-6))
        row = records[key]
        output.append('N'+fields[0][1:]+' '+' '.join(fields[1:5])+f' {row["model"]} '
                      f'l={length:.17g} w={width:.17g} nf=1 mult=1 '
                      f'as={row["area_m2"]:.17g} ad={row["area_m2"]:.17g} '
                      f'ps={row["perimeter_m"]:.17g} pd={row["perimeter_m"]:.17g} '
                      'dta=0 ngcon=2 delvto=0 factuo=1')
    if not records:
        raise ValueError('No SRAM transistors found')
    return '\n'.join(output)+'\n', '\n\n'.join(models)+'\n', list(records.values())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('circuit', type=Path)
    p.add_argument('--models', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    params = args.models/'sg13g2_moslv_parm.lib'
    wrapper = args.models/'sg13g2_moslv_mod.lib'
    circuit, models, geometry = specialize(args.circuit.read_text(), params.read_text(),
                                           wrapper.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'circuit.spice').write_text(circuit)
    (args.output/'models.lib').write_text(models)
    record = dict(status='GENERATED_REQUIRES_ORIGINAL_WRAPPER_EQUIVALENCE',
                  geometry=geometry, input_sha256={str(q.resolve()): sha(q) for q in
                  [args.circuit, params, wrapper, Path(__file__)]},
                  output_sha256={n: sha(args.output/n) for n in ['circuit.spice', 'models.lib']},
                  profile='Single finger, multiplicity 1, calculated junction geometry, rfmode 0, pre_layout 1; no PEX claim')
    (args.output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(len(geometry), 'specialized models; verification required')


if __name__ == '__main__':
    main()
