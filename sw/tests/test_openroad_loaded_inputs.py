# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject stale-stage or ambiguous timing input evidence before reporting STA."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    'loaded_inputs', Path(__file__).resolve().parents[2] / 'scripts/check_openroad_loaded_inputs.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.fixture
def inputs(tmp_path):
    odb, sdc = tmp_path/'final.odb', tmp_path/'final.sdc'
    odb.write_bytes(b'final repaired design')
    sdc.write_text('create_clock -period 4 pcie_clk_i\n')
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (odb, sdc)}
    log = f"Reading OpenROAD database at '{odb}'…\nReading design constraints file at '{sdc}'…\n"
    return log, odb, sdc, pins


def test_expected_files_and_manifest(inputs):
    assert checker.validate(*inputs)['status'].startswith('PASS_LOADED')


def test_old_cts_database_is_not_final_repair(inputs):
    log, odb, sdc, pins = inputs
    with pytest.raises(ValueError, match='expected one load'):
        checker.validate(log.replace(str(odb), str(odb.with_name('old-cts.odb'))), odb, sdc, pins)


@pytest.mark.parametrize('mode', ['missing_odb', 'duplicate_odb', 'wrong_sdc', 'unpinned', 'changed'])
def test_ambiguous_or_modified_inputs_fail(inputs, mode):
    log, odb, sdc, pins = inputs
    if mode == 'missing_odb': log = log.split('\n', 1)[1]
    elif mode == 'duplicate_odb': log += log.split('\n')[0]+'\n'
    elif mode == 'wrong_sdc': log = log.replace(str(sdc), str(sdc.with_name('old.sdc')))
    elif mode == 'unpinned': pins.pop(str(odb))
    else: odb.write_bytes(b'different database')
    with pytest.raises(ValueError): checker.validate(log, odb, sdc, pins)
