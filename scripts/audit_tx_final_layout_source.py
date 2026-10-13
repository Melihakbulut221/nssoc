#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the layout core and generated native reference to the screened v5 circuit.

Compare ordered terminals and device multiplicities, not instance names. Only
lengths receive 1e-18 metre rounding (1e-12 um), to remove SPICE float-export
noise far below the PDK's 5 nm geometry grid. Public sub stays separate from
BULK; all 27 physical contacts are mandatory. No waveform or PEX acceptance.
"""
from collections import Counter
from decimal import Decimal
import hashlib

PORTS = set('ap an bp bn sp sn op on avdd avss sub iref'.split())
ALIASES = dict(n_42='qn', n_46='qp', n_40='ea', n_51='eb', n_62='tail', n_1='bulk')
TAP_R = Decimal('81.66666666666666666666666668')


def number(value):
    suffix = {'u': '1e-6', 'p': '1e-12'}
    return Decimal(value[:-1]) * Decimal(suffix[value[-1]]) if value[-1] in suffix else Decimal(value)


def length(value):
    return number(value).quantize(Decimal('1e-18'))


def parse(text):
    rows, names, ports = [], set(), None
    ended = False
    top = None
    for line in text.splitlines():
        fields = line.lower().split()
        if not fields or fields[0].startswith('*'):
            continue
        if fields[0] == '.subckt':
            assert ports is None and not ended
            top, ports = fields[1], fields[2:]
            assert len(ports) == 12 and set(ports) == PORTS
            continue
        if fields[0] == '.ends':
            assert ports is not None and not ended and fields[1:] == [top]
            ended = True
            continue
        assert ports is not None and not ended
        assert fields[0][0] in 'xqr' and fields[0] not in names
        names.add(fields[0])
        indexes = [i for i, f in enumerate(fields) if f in ('npn13g2', 'rppd', 'ptap1')]
        assert len(indexes) == 1
        index = indexes[0]
        model, nodes = fields[index], fields[1:index]
        assert len(nodes) == {'npn13g2': 4, 'rppd': 3, 'ptap1': 2}[model]
        pairs = [x.split('=') for x in fields[index+1:]]
        assert all(len(p) == 2 for p in pairs)
        params = dict(pairs)
        assert len(params) == len(pairs)
        rows.append((model, nodes, params))
    assert ended
    return rows


def signature(row, kind, profile='v5'):
    model, nodes, p = row
    nodes = [ALIASES.get(n, n) for n in nodes] if kind == 'native' else list(nodes)
    if kind == 'core':
        assert model != 'ptap1' and nodes[-1] == 'sub'
        nodes[-1] = 'bulk'  # Exact frozen generator's body mapping, not a short.
    if model == 'npn13g2':
        assert set(p) <= {'nx','we','le','m'} and 'nx' in p
        assert number(p.get('m','1')) == 1
        assert length(p.get('we','0.07u')) == length('0.07u')
        assert length(p.get('le','0.9u')) == length('0.9u')
        nx = number(p['nx'])
        assert profile in ('v5','v6')
        if profile == 'v5':
            assert nx in (1, 8)
        elif nodes[1] in ('ap','an','bp','bn','sp','sn'):
            assert nx == 4
        else:
            assert nodes[1] == 'iref' and nodes[2] == 'avss'
            assert nx == (1 if nodes[0] == 'iref' else 8)
        values = (nx,)
    elif model == 'rppd':
        assert {'w','l'} <= set(p) <= {'w','l','ps','b','m','sw_et'}
        assert number(p.get('ps','0')) == number(p.get('b','0')) == 0
        assert number(p.get('m','1')) == number(p.get('sw_et','1')) == 1
        values = (length(p['w']), length(p['l']))
    else:
        assert nodes == ['sub','bulk']
        if kind == 'generated':
            assert set(p) == {'a','p'}
            assert number(p['a']) == number('4p') and number(p['p']) == number('8u')
        else:
            assert set(p) == {'w','l','r'}
            assert length(p['w']) == length(p['l']) == length('2u')
            assert number(p['r']) == TAP_R
        values = (length('2u'), length('2u'))
    assert 'sub' not in nodes if model != 'ptap1' else True
    return model, tuple(nodes), values


def audit(core, native, generated=None, *, profile='v5'):
    assert profile in ('v5','v6')
    core_rows, native_rows = parse(core), parse(native)
    assert Counter(r[0] for r in core_rows) == {'npn13g2': 19, 'rppd': 8}
    assert Counter(r[0] for r in native_rows) == {'npn13g2': 19, 'rppd': 8, 'ptap1': 27}
    expected = Counter(signature(r, 'native', profile) for r in native_rows)
    adapted = Counter(signature(r, 'core', profile) for r in core_rows)
    adapted[('ptap1', ('sub','bulk'), (length('2u'),length('2u')))] = 27
    assert adapted == expected, 'Core differs from screened native54 circuit'
    if generated is not None:
        assert Counter(signature(r, 'generated', profile) for r in parse(generated)) == expected, 'Generated reference differs from native54 circuit'
    return dict(status='PASS_CORE_TO_NATIVE54_AND_GENERATED_REFERENCE' if generated is not None else 'PASS_CORE_TO_NATIVE54_GENERATOR_CONTRACT',
                core_sha256=hashlib.sha256(core.encode()).hexdigest(),
                native_sha256=hashlib.sha256(native.encode()).hexdigest(),
                generated_sha256=hashlib.sha256(generated.encode()).hexdigest() if generated is not None else None,
                profile=profile,hbts=19,resistors=8,substrate_contacts=27,body_port_separate=True,
                length_rounding_metres='1e-18',
                scope='Device connectivity, model parameters and contact geometry only. Native physical LVS/DRC and fresh extracted model remain required; contact resistance is checked in the input model, not extracted by this audit.')
