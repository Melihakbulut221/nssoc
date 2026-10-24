# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from cloud_tx_assembled_sizing import resize_final


def source():
    text = '.subckt tree a b c d\n'
    for i in range(1, 55):
        nx = 6 if i <= 4 else 3 if 43 <= i <= 54 else 8
        text += f'XD{i:04d} c{i} b{i} e{i} bulk npn13g2 nx={nx} we=0.07u le=0.9u\n'
    return text + 'RUNCHANGED c1 b1 8.25\nCUNCHANGED c2 b2 3.5e-15\n.ends tree\n'


def test_exact_changed_devices_preserve_every_other_token_and_line():
    before = source()
    after, receipt = resize_final(before, 'data8_select10')
    assert len(receipt['changed_devices']) == 16
    assert receipt['physical_device_geometry_matches'] is False
    assert receipt['qualified_pex'] is False
    for old, new in zip(before.splitlines(), after.splitlines(), strict=True):
        name = old.split()[0].lower()
        if name in receipt['changed_devices']:
            row = receipt['changed_devices'][name]
            assert new == old.replace('nx='+str(row['original_nx']), 'nx='+str(row['candidate_nx']))
        else:
            assert old == new
    assert receipt['source_sha256'] != receipt['candidate_sha256']


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'wrong_model', 'wrong_nx', 'duplicate_nx', 'unknown_profile'])
def test_reject_incompatible_source_instead_of_silently_resizing(mutation):
    text = source()
    row = next(l for l in text.splitlines(keepends=True) if l.startswith('XD0043 '))
    if mutation == 'missing': text = text.replace(row, '')
    elif mutation == 'duplicate': text += row
    elif mutation == 'wrong_model': text = text.replace(row, row.replace('npn13g2', 'npn13g2l'))
    elif mutation == 'wrong_nx': text = text.replace(row, row.replace('nx=3', 'nx=4'))
    elif mutation == 'duplicate_nx': text = text.replace(row, row.rstrip()+' nx=3\n')
    with pytest.raises(AssertionError):
        resize_final(text, 'bad' if mutation == 'unknown_profile' else 'data8_select10')
