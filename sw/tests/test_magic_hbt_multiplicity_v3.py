# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict Nx/source/terminal replay guards, independent of native geometry generation."""
from pathlib import Path
import importlib.util
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('nx_v3', ROOT / 'scripts/check_magic_hbt_multiplicity_v3.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def raw():
    spice = ['.subckt hbt_axis_flat ' + ' '.join(h.PORTS)]
    ext = ['scale 1000 1 0.5', 'parameters npn13g2 w1=le l1=we n1=Nx']
    for n in (1, 2, 4):
        for o in range(8):
            c, b, e = [f'{t}_N{n}_T{o}' for t in 'CBE']
            spice.append(f'X{n}_{o} {c} {b} {e} SUB npn13g2 we=70n le=0.9u Nx={n}')
            ext.append(f'device msubckt npn13g2 0 0 1 1 w1=180 l1=14 Nx={n} "SUB" "{b}" 0 0 "{e}" 0 2520,388 "{c}" 0 0')
    return '\n'.join(spice + ['.ends', '']), '\n'.join(ext) + '\n', 'exttospice finished.\n'


def test_all24_geometry_parameters_and_scope():
    result = h.assess(*raw())
    assert result['status'] == 'PASS_24_NATIVE_HBT_MULTIPLICITIES_ONLY'
    assert result['hbts'] == 24 and result['ports'] == 73
    assert result['finite_tap_retained'] is False and result['qualified_pex'] is False


@pytest.mark.parametrize('n,o', [(n, o) for n in (1, 2, 4) for o in range(8)])
def test_every_finger_count_orientation_required(n, o):
    spice, ext, log = raw()
    prefix = f'X{n}_{o} '
    spice = '\n'.join(s.replace(f'Nx={n}', 'Nx=3') if s.startswith(prefix) else s for s in spice.splitlines())
    ext = '\n'.join(s.replace(f'Nx={n}', 'Nx=3') if f'"C_N{n}_T{o}"' in s else s for s in ext.splitlines()) + '\n'
    assert h.assess(spice, ext, log)['status'] == 'GEOMETRY_MISMATCH_PRESERVED'


@pytest.mark.parametrize('old,new', [('we=70n', 'we=30n'), ('le=0.9u', 'le=0.8u'), ('Nx=4', 'Nx=1'), ('B_N4_T7 E_N4_T7', 'E_N4_T7 B_N4_T7')])
def test_spice_cannot_disagree_with_raw_ext(old, new):
    spice, ext, log = raw()
    header, body = spice.split('\n', 1)
    with pytest.raises(ValueError, match='EXT/SPICE'):
        h.assess(header + '\n' + body.replace(old, new, 1), ext, log)


@pytest.mark.parametrize('old,new', [('l1=14', 'l1=6'), ('w1=180', 'w1=100'), ('Nx=2', 'Nx=1')])
def test_raw_ext_cannot_be_replaced_with_unrelated_native_result(old, new):
    spice, ext, log = raw()
    with pytest.raises(ValueError, match='EXT/SPICE'):
        h.assess(spice, ext.replace(old, new, 1), log)


def test_real_native_equivalence_preserves_short_failure():
    spice, ext, log = raw()
    spice = spice.replace('B_N4_T7', 'C_N4_T7')
    # Native exporter drops the duplicate shorted public pin.
    first, *rest = spice.splitlines()
    first = first.replace('C_N4_T7 C_N4_T7', 'C_N4_T7')
    spice = '\n'.join([first, *rest])
    ext = ext.replace('"C_N4_T7"', '"B_N4_T7"') + 'equiv "B_N4_T7" "C_N4_T7"\n'
    result = h.assess(spice, ext, log)
    assert result['status'] == 'GEOMETRY_MISMATCH_PRESERVED' and result['ports'] == 72


def test_missing_tap_changes_body_and_does_not_become_acceptance():
    spice, ext, log = raw()
    spice = spice.replace(' SUB npn13g2', ' actual.sub npn13g2')
    ext = ext.replace('"SUB"', '"actual.sub!"')
    result = h.assess(spice, ext, log)
    assert result['status'] == 'GEOMETRY_MISMATCH_PRESERVED'
    assert result['finite_tap_retained'] is False


def test_component_geometry_error_is_not_positive():
    assert h.assess(*raw()[:2], 'NSSOC terminal component geometry/connectivity failure\nexttospice finished.\n')['status'] == 'GEOMETRY_MISMATCH_PRESERVED'


@pytest.mark.parametrize('log', ['', 'exttospice finished.\nexttospice finished.\n', 'Fatal: stopped\nexttospice finished.\n', 'Traceback: stopped\nexttospice finished.\n'])
def test_incomplete_or_non_native_failure_is_not_geometry_evidence(log):
    with pytest.raises(ValueError):
        h.assess(*raw()[:2], log)


def test_duplicate_and_missing_records_cannot_disappear():
    spice, ext, log = raw()
    duplicate = spice.replace('.ends', spice.splitlines()[1] + '\n.ends')
    with pytest.raises(ValueError, match='Duplicate native instance'):
        h.assess(duplicate, ext, log)
    with pytest.raises(ValueError, match='count differs'):
        h.assess('\n'.join(spice.splitlines()[0:1] + spice.splitlines()[2:]), ext, log)


def test_wrong_or_nonfinite_parameter_syntax_rejected():
    for value in ('nan', 'inf', '3e99', '2junk'):
        with pytest.raises(ValueError):
            h.assess(raw()[0].replace('Nx=1', 'Nx=' + value, 1), *raw()[1:])


def test_patch_and_overlay_reject_other_sources():
    with pytest.raises(ValueError, match='private v2'):
        h.patcher.patch(b'wrong source')
    with pytest.raises(ValueError, match='private v2'):
        h.patcher.patch_technology(b'wrong technology')


def test_native_recipe_preserves_gds_and_no_device_properties(tmp_path):
    fixture = {'ports': {n: {'layer': 8, 'box': [0, 0, .1, .2]} for n in h.PORTS}}
    script = h.native_tcl(tmp_path / 'fixture.gds', fixture, tmp_path / 'out')
    assert script.count(' class inout') == 73
    assert 'gds readonly true\n' in script and 'ext2spice global off\n' in script
    assert 'property' not in script and 'paint' not in script and 'Nx=' not in script
    assert 'ext2spice extresist off\n' in script
    fixture['ports'].pop('E_N4_T7')
    with pytest.raises(ValueError, match='port map'):
        h.native_tcl(tmp_path / 'fixture.gds', fixture, tmp_path,)


def test_native_paths_are_tcl_quoted_and_validated(tmp_path):
    fixture = {'ports': {n: {'layer': 8, 'box': [0, 0, .1, .2]} for n in h.PORTS}}
    with pytest.raises(ValueError, match='Unsafe'):
        h.native_tcl(Path('/tmp/};exit'), fixture, tmp_path)
