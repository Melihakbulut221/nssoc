# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed isolated HBT source and extracted-device bridge controls."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


p = module('patch_magic_hbt_contract_v2')
h = module('check_magic_hbt_hybrid_v2')


def schematic():
    ports = ['SUB']
    rows = ['Rtap SUB \\$1 ptap1 A=4p P=8u']
    for nx in (1, 2, 4):
        for orientation in range(8):
            tag = f'N{nx}_T{orientation}'
            nodes = [f'{terminal}_{tag}' for terminal in 'CBE']
            ports += nodes
            rows.append('Q' + tag + ' ' + ' '.join(nodes) + f' \\$1 npn13G2 we=70n le=900n Nx={nx} m=1')
    return '.subckt nssoc_hbt_axis ' + ' '.join(ports) + '\n' + '\n'.join(rows) + '\n.ends nssoc_hbt_axis\n'


def test_native_device_contract_positive(tmp_path):
    path = tmp_path / 'native.cir'
    path.write_text(schematic())
    result = h.devices(path)
    assert len(result['hbts']) == 24 and len(result['ports']) == 73
    assert result['tap'][1:3] == ['SUB', '\\$1']


@pytest.mark.parametrize('old,new', [
    ('Nx=4', 'Nx=1'), ('Nx=2', 'Nx=1'), ('we=70n', 'we=900n'),
    ('le=900n', 'le=70n'), ('m=1', 'm=2'), ('npn13G2', 'npn13G2l'),
    ('B_N4_T7 E_N4_T7 \\$1', 'E_N4_T7 B_N4_T7 \\$1'),
    ('Rtap SUB \\$1', 'Rtap SUB SUB'), ('A=4p', 'A=0p'), ('P=8u', 'P=4u'),
])
def test_changed_native_devices_rejected(tmp_path, old, new):
    path = tmp_path / 'native.cir'
    path.write_text(schematic().replace(old, new, 1))
    with pytest.raises(ValueError):
        h.devices(path)


@pytest.mark.parametrize('tag', [f'N{nx}_T{o}' for nx in (1, 2, 4) for o in range(8)])
def test_every_orientation_device_is_required(tmp_path, tag):
    path = tmp_path / 'native.cir'
    path.write_text('\n'.join(line for line in schematic().splitlines() if not line.startswith('Q' + tag + ' ')))
    with pytest.raises(ValueError, match='25 extracted devices'):
        h.devices(path)


@pytest.mark.parametrize('name', p.PINS)
def test_wrong_patch_preimage_rejected(name):
    with pytest.raises(ValueError, match='immutable source'):
        p.patch(name, b'not the exact source')


def test_patch_is_narrow_per_tile_side_and_local_contact():
    edits = p.EDITS
    assert len(edits['ExtBasic.c']) == 3
    assert edits['ExtBasic.c'][-1][1] == 'extTransFindSubs(lt->t, lt->dinfo, tmask, def,'
    assert ' and CONT' not in ''.join(b for pairs in edits.values() for _, b in pairs)
    assert not any('ndiff' in b or 'space/w' in b for pairs in edits.values() for _, b in pairs)


def test_bridge_has_exact_terminal_anchors_and_no_reduction(tmp_path):
    mapping = {name: dict(layer=8, anchors_dbu=[[0, 0], [100, 0]], cluster=i)
               for i, name in enumerate(['SUB'] + [f'{t}_N{n}_T{o}' for n in (1, 2, 4) for o in range(8) for t in 'CBE'])}
    text = h.wire_tcl(mapping, tmp_path / 'wire.gds', tmp_path / 'output')
    assert text.count(' class inout') == 146
    assert 'extresist simplify off\n' in text and 'extresist tolerance 0.000001\n' in text
    assert 'ext2spice global off\n' in text and 'ext2spice extresist on\n' in text
    mapping['SUB; bad'] = mapping.pop('SUB')
    with pytest.raises(ValueError, match='terminal name'):
        h.wire_tcl(mapping, tmp_path / 'wire.gds', tmp_path)


def test_frozen_auditor_pins_are_real():
    for name, digest in h.DEPENDENCIES.items():
        assert h.pin(ROOT / name)['sha256'] == digest


def test_cap_record_order_normalization_preserves_every_value_and_duplicate():
    a = 'node x 0 1\ncap "z" "x" 2\ncap "a" "x" 1\ncap "a" "x" 1\n'
    b = 'node x 0 1\ncap "a" "x" 1\ncap "z" "x" 2\ncap "a" "x" 1\n'
    assert h.stable_ext(a) == h.stable_ext(b)
    assert h.stable_ext(a).count('cap "a" "x" 1') == 2
    assert h.stable_ext(a) != h.stable_ext(b.replace('"x" 2', '"x" 3'))
