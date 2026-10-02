# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure byte-level marker insertion and unchanged/model-bound reference controls."""
import hashlib
import io
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
import extract_gds_hierarchy as gds  # noqa: E402
import repair_parent_resistor_markers as repair  # noqa: E402
import run_io_parent_marker_repair as runner  # noqa: E402
from test_extract_gds_hierarchy import boundary, cell, library, ref  # noqa: E402


def fixture():
    return library(cell(repair.CELL, boundary()), cell('UNRELATED', boundary()),
                   cell('TOP', ref(repair.CELL)+ref('UNRELATED', True)))


def test_adds_only_exact_boundaries_preserves_all_original_bytes_properties_instances():
    original = fixture()
    changed, receipt = repair.insert_records(original)
    start = receipt['insertion_offset']; size = receipt['added_bytes']
    assert changed[:start]+changed[start+size:] == original
    before = gds.index_stream(io.BytesIO(original)); after = gds.index_stream(io.BytesIO(changed))
    assert before['cells'].keys() == after['cells'].keys()
    assert all(before['cells'][name]['sha256'] == after['cells'][name]['sha256'] for name in ['TOP', 'UNRELATED'])
    records = list(gds.records(io.BytesIO(changed[start:start+size])))
    assert len(records) == 26*5
    for index, box in enumerate(repair.BOXES):
        items = records[5*index:5*index+5]
        assert [r[1] for r in items] == [8, 13, 14, 16, 17]
        assert struct.unpack('>h', items[1][2]) == (128,)
        assert struct.unpack('>h', items[2][2]) == (0,)
        left, bottom, right, top = box
        assert struct.unpack('>10i', items[3][2]) == (left,bottom,right,bottom,right,top,left,top,left,bottom)
    assert receipt['every_original_byte_preserved'] and receipt['added_boundaries'] == 26


@pytest.mark.parametrize('data', [b'', fixture()[:-1], library(cell('WRONG')),
    library(cell('LEAF'), cell(repair.CELL, ref('LEAF'))), fixture()+b'\0\0'])
def test_unsupported_or_wrong_gds_rejected_before_any_mutation(data):
    before = data
    with pytest.raises(ValueError): repair.insert_records(data)
    assert data == before


def spacing_fixture():
    return '.GLOBAL sub!\n.SUBCKT R pin1 pin2\n'+''.join(
        f'RR{i} n{i} n{i+1} 5.239K $SUB=sub! $[rppd] m=1 l=20u w=1u ps=180n trise=0.0 b=0\n'
        for i in range(26))+'.ENDS R\n'


@pytest.mark.parametrize('fault', [None, 'model', 'reference', 'inventory', 'spacing', 'bent'])
def test_spacing_case_bound_to_model_reference_and_26_explicit_straight_devices(tmp_path, monkeypatch, fault):
    model = tmp_path/'model'; model.write_bytes(b'isolated test model')
    text = spacing_fixture()
    monkeypatch.setattr(runner, 'MODEL_SHA', hashlib.sha256(model.read_bytes()).hexdigest())
    if fault == 'inventory': text = text.replace('RR0 n0 n1', '*RR0 n0 n1')
    if fault == 'spacing': text = text.replace('ps=180n', 'ps=181n', 1)
    if fault == 'bent': text = text.replace('b=0', 'b=1', 1)
    monkeypatch.setattr(runner, 'REFERENCE_SHA', hashlib.sha256(text.encode()).hexdigest())
    if fault == 'model': model.write_bytes(b'wrong model')
    if fault == 'reference': text += '*changed\n'
    if fault:
        with pytest.raises(ValueError): runner.spacing_reference(text, model)
    else:
        changed, proof = runner.spacing_reference(text, model)
        assert changed == text.replace('ps=180n', 'ps=0')
        assert len(proof['edits']) == 26 and not proof['tap_parameters_changed']
        assert not proof['vendor_terminals_changed']


def test_wrong_baseline_receipt_rejected(tmp_path):
    (tmp_path/'result.json').write_text('{}')
    with pytest.raises(ValueError, match='baseline receipt'): runner.validate_baseline(tmp_path)


def test_workflow_and_native_guards(tmp_path):
    workflow = (ROOT/'.github/workflows/io-parent-marker-repair.yml').read_text()
    assert "run-id: '36992719056'" in workflow and 'include-hidden-files: true' in workflow
    for mode in ['deep', 'flat']:
        command = runner.baseline.command(tmp_path, tmp_path, tmp_path, mode)
        assert 'disable_tap_extraction=false' in command
        assert 'ignore_top_ports_mismatch=false' in command
        assert 'topcell=ACTUAL_IO_ADJACENCY' in command
