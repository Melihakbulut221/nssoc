# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail before executing tools when evidence could be lost or models differ."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('scrub_native', ROOT/'scripts/check_scrub_native.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_existing_evidence_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    out = tmp_path/'hw/soc/out/test'
    out.mkdir(parents=True)
    (out/'result.json').write_text('old failure')
    with pytest.raises(ValueError, match='existing'):
        runner.check(out, tmp_path, tmp_path)
    assert (out/'result.json').read_text() == 'old failure'


def test_escaping_output_rejected(tmp_path, monkeypatch):
    # The test must remain outside its synthetic repository even when pytest's
    # --basetemp is inside the real repository's hw/soc/out directory.
    monkeypatch.setattr(runner, 'ROOT', tmp_path/'repo')
    with pytest.raises(ValueError, match='under hw/soc/out'):
        runner.check(tmp_path/'outside', tmp_path, tmp_path)
    assert not (tmp_path/'outside').exists()


def test_changed_native_library_rejected_before_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    lock = tmp_path/'hw/soc/pnr/ihp-native-boot.lock.json'
    lock.parent.mkdir(parents=True)
    lock.write_bytes((ROOT/'hw/soc/pnr/ihp-native-boot.lock.json').read_bytes())
    pdk = tmp_path/'pdk'
    lib = pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
    lib.parent.mkdir(parents=True)
    lib.write_text('corrupted library')
    out = tmp_path/'hw/soc/out/new'
    result = runner.check(out, pdk, tmp_path/'missing-tools')
    assert result['status'] == 'FAIL'
    assert 'differs from lock' in result['error']
    assert not result['commands']
    assert json.loads((out/'result.json').read_text()) == result
