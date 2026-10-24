# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Byte preservation and explicit annotation-only boundary/deck contracts."""
import io
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import io_parent_boundary as b  # noqa: E402
import run_io_parent_boundary as runner  # noqa: E402
from extract_gds_hierarchy import records, index_stream  # noqa: E402
from test_extract_gds_hierarchy import library, cell, boundary, ref  # noqa: E402


def labels():
    return [dict(name=n,layer=[126,25],point_nm=[10+20*i,50]) for i,n in enumerate(b.PORT_NAMES[:-1])]+[
        dict(name='SUB!',layer=[40,25],point_nm=[50,100])]


def fixture():
    conductive=b.text_record(dict(name='internal_rc',layer=[8,25],point_nm=[10,20]))
    recognition=b.text_record(dict(name='ptap1',layer=[63,0],point_nm=[30,40]))
    substrate=b.text_record(dict(name='unrelated',layer=[40,25],point_nm=[50,60]))
    return library(cell('CHILD',boundary()+conductive+recognition+substrate),cell(b.TOP,ref('CHILD')))


def test_only_conductive_texts_replaced_no_device_recognition_or_geometry_edit():
    original=fixture();changed,proof=b.annotate_bytes(original,labels())
    assert len(proof['removed_conductive_texts'])==1
    removal=proof['removed_conductive_texts'][0]
    assert removal['text']=='internal_rc' and removal['layer']==[8,25]
    assert proof['recognition_text_layers_untouched'] and proof['unchanged_non_text_bytes']
    stripped=original[:removal['offset']]+original[removal['offset']+removal['bytes']:]
    idx=index_stream(io.BytesIO(stripped));at=idx['cells'][b.TOP]['end']-4
    assert changed==stripped[:at]+b''.join(b.text_record(v) for v in labels())+stripped[at:]
    assert b.text_record(dict(name='ptap1',layer=[63,0],point_nm=[30,40])) in changed
    assert b.text_record(dict(name='unrelated',layer=[40,25],point_nm=[50,60])) in changed
    assert boundary() in changed and ref('CHILD') in changed
    assert list(records(io.BytesIO(changed)))


@pytest.mark.parametrize('fault',['name','case','order','layer','missing','truncated','absent-top'])
def test_annotation_contract_rejects_unproven_names_and_layers(fault):
    original=fixture();selected=labels()
    if fault=='name':selected[0]['name']='shorted'
    if fault=='case':selected[0]['name']='iovdd'
    if fault=='order':selected.reverse()
    if fault=='layer':selected[0]['layer']=[63,0]
    if fault=='missing':selected.pop()
    if fault=='truncated':original=original[:-1]
    if fault=='absent-top':original=library(cell('OTHER'))
    with pytest.raises(ValueError):b.annotate_bytes(original,selected)


def test_deck_overlay_adds_only_physical_annotation_attachment():
    source='prefix\n'+runner.BEFORE+'connect(pwell, ptap)\n'
    updated=runner.overlay_text(source)
    assert updated.replace(runner.AFTER,runner.BEFORE)==source
    assert updated.count('connect(pwell_sub, substrate_text)')==1
    assert 'connect_global' not in updated and 'connect_implicit' not in updated
    for wrong in ['',source+runner.BEFORE,updated]:
        with pytest.raises(ValueError):runner.overlay_text(wrong)


def test_wrapper_removes_only_seven_metal_label_layers():
    assert b.NET_LABELS=={(n,25) for n in (8,10,30,50,67,126,134)}
    assert (63,0) not in b.NET_LABELS and (40,25) not in b.NET_LABELS
    workflow=(ROOT/'.github/workflows/io-parent-boundary.yml').read_text()
    assert "run-id: '36995165800'" in workflow and 'include-hidden-files: true' in workflow
