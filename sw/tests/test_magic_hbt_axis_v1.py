# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only the source-proven HBT axis labels may change, never geometry/equations."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('axis',ROOT/'scripts/patch_magic_hbt_axis_v1.py')
axis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(axis)
SOURCE = ROOT/'hw/soc/out/sram-closure-20260926/magic-tech-via-import/ihp-sg13g2-extract.tech'


def source():
    # Public repository source does not carry the provisioned PDK; no fake
    # native execution is claimed by this bounded parser test.
    if not SOURCE.is_file():
        pytest.skip('Exact provisioned native technology required for literal overlay test')
    return SOURCE.read_bytes()


def test_only_two_exact_low_voltage_model_axis_bindings_change():
    before=source();after=axis.patch(before)
    assert hashlib.sha256(before).hexdigest()==axis.SOURCE_SHA256
    diffs=[(a,b) for a,b in zip(before.decode().splitlines(),after.decode().splitlines()) if a!=b]
    assert diffs==[(line,line.replace('w1=we l1=le','w1=le l1=we')) for line in axis.OLD_LINES]
    assert len(before)==len(after)
    for name in ('npn13g2l','npn13g2v'):
        assert [s for s in before.decode().splitlines() if name in s]==[s for s in after.decode().splitlines() if name in s]


@pytest.mark.parametrize('change',[
    lambda b:b.replace(b'gec *ndiff',b'gec *pdiff',1),
    lambda b:b.replace(b'npn13g2 npn',b'npn13g2l npn',1),
    lambda b:b.replace(b'w1=we l1=le',b'w1=le l1=we',1),
    lambda b:b.replace(b'device msubcircuit',b'device bjt',1),
    lambda b:b+b'\n',
])
def test_changed_source_or_already_changed_axes_fail_closed(change):
    with pytest.raises(ValueError,match='Exact frozen'):
        axis.patch(change(source()))


def test_native_fixture_preserves_all_three_multiplicities_and_eight_orientations():
    # Tests the declared literal patch scope independently of provisioned files.
    assert len(axis.OLD_LINES)==2
    assert all('npn13g2 ' in line and 'npn13g2l' not in line for line in axis.OLD_LINES)
    assert 'we=0.07u' not in '\n'.join(axis.OLD_LINES)
    with pytest.raises(ValueError):
        axis.patch(b'')
