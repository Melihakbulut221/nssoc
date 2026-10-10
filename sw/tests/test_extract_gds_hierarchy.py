# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Byte preservation, malformed input, output safety and native geometry controls."""
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import extract_gds_hierarchy as gds


def rec(kind, payload=b'', dtype=None):
    if dtype is None:
        dtype = gds.RECORDS[kind][0]
    return struct.pack('>HBB', len(payload)+4, kind, dtype)+payload


def name(kind, value):
    data = value.encode('ascii') if isinstance(value, str) else value
    return rec(kind, data + b'\0'*(len(data)%2))


def coords(*points):
    return rec(0x10, b''.join(struct.pack('>ii', *point) for point in points))


def boundary():
    return (rec(8)+rec(13, struct.pack('>h', 1))+rec(14, b'\0\0')
            +coords((0, 0), (1200, 0), (1200, 600), (0, 600), (0, 0))
            +rec(43, struct.pack('>h', 2))+name(44, 'unchanged property')+rec(17))


def ref(cell, array=False):
    raw = rec(11 if array else 10)+name(18, cell)+rec(26, b'\x80\x00')
    if array:
        raw += rec(19, struct.pack('>hh', 2, 3))+coords((2000, 3000), (6000, 3000), (2000, 12000))
    else:
        raw += coords((1000, 5000))
    return raw+rec(17)


def cell(value, content=b''):
    return rec(5, b'\0'*24)+name(6, value)+content+rec(7)


def library(*cells):
    # Independent canonical GDS real8 encodings: .001 user units; 1e-9 meter.
    return (rec(0, struct.pack('>h', 600))+rec(1, b'\0'*24)+name(2, 'TEST')
            +rec(3, bytes.fromhex('3e4189374bc6a7f03944b82fa09b5a54'))+b''.join(cells)+rec(4))


def fixture():
    return library(cell('leaf', boundary()), cell('unused', boundary()),
                   cell('mid', ref('leaf')), cell('root', boundary()+ref('mid')+ref('leaf', True)))


def source(tmp_path, data=None):
    value = tmp_path/'source.gds'
    value.write_bytes(fixture() if data is None else data)
    return value


def test_transitive_sref_aref_exact_bytes_header_units_properties(tmp_path):
    original = source(tmp_path)
    before = original.read_bytes()
    receipt = gds.extract(original, ['root'], tmp_path/'out', hashlib.sha256(before).hexdigest())
    after = (tmp_path/'out/subset.gds').read_bytes()
    assert original.read_bytes() == before
    assert after == library(cell('leaf', boundary()), cell('mid', ref('leaf')),
                            cell('root', boundary()+ref('mid')+ref('leaf', True)))
    assert list(receipt['cells']) == ['leaf', 'mid', 'root']
    assert receipt['excluded_cells'] == ['unused']
    for row in receipt['cells'].values():
        a, b = row['source'], row['output']
        assert before[a['start']:a['end']] == after[b['start']:b['end']]
        assert a['sha256'] == b['sha256'] == hashlib.sha256(before[a['start']:a['end']]).hexdigest()
    assert receipt['cells']['root']['source']['references'] == ['leaf', 'mid']
    assert json.loads((tmp_path/'out/receipt.json').read_text()) == receipt
    assert receipt['geometry_records_modified'] is False
    assert receipt['lvs_accepted'] is False


@pytest.mark.parametrize('data,match', [
    (library(cell('root', ref('missing'))), 'Missing'),
    (library(cell('root'), cell('unused', ref('missing'))), 'Missing'),
    (library(cell('root'), cell('root')), 'Duplicate'),
    (library(cell('root', ref('root'))), 'Cyclic'),
    (library(cell('root', ref('child')), cell('child', ref('root'))), 'Cyclic'),
    (library(cell('root'), cell('unused', ref('unused'))), 'Cyclic'),
    (fixture()[:-1], 'Truncated'),
    (fixture()[:-4], 'Incomplete'),
    (fixture()+b'\0'*8, 'Invalid record'),
    (fixture()+rec(4), 'Trailing'),
    (b'\0\x03\0\x02', 'Invalid record'),
    (b'\0\x05\0\x02x', 'Invalid record'),
    (rec(0, b'\0\1', dtype=3)+fixture()[6:], 'Invalid data type'),
    (library(cell('root')).replace(rec(7), rec(7)+name(2, 'EXTRA')), 'between cells'),
    (library(cell('root')).replace(rec(7), rec(7)+b'\0\x04\xff\0'), 'Unsupported record'),
    (library(cell(b'ro\xfft')), 'non-ASCII'),
    (library(cell(b'ro\0ot')), 'non-ASCII'),
    (library(cell('root', rec(10)+coords((1, 2))+rec(17))), 'required'),
    (library(cell('root', name(18, 'hidden'))), 'Unsupported record'),
    (library(cell('root', rec(11)+name(18, 'root')+rec(19, b'\0\0\0\1')+coords((0, 0), (1, 0), (0, 1))+rec(17))), 'positive COLROW'),
    (library(cell('root', rec(10)+name(18, 'root')+coords((0, 0), (1, 2))+rec(17))), 'one XY'),
    (library(cell('root', boundary().replace(rec(17), name(44, 'unpaired')+rec(17)))), 'lacks PROPATTR'),
])
def test_fail_closed_on_malformed_or_unsupported_library(tmp_path, data, match):
    path = source(tmp_path, data)
    with pytest.raises(gds.GDSFormatError, match=match):
        gds.extract(path, ['root'], tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('roots', [[], ['absent']])
def test_root_selection_must_be_resolvable(tmp_path, roots):
    with pytest.raises(ValueError):
        gds.extract(source(tmp_path), roots, tmp_path/'out')


def test_multiple_roots_deduplicate_shared_children(tmp_path):
    result = gds.extract(source(tmp_path), ['root', 'mid', 'root'], tmp_path/'out')
    assert result['roots'] == ['root', 'mid']
    assert len(result['cells']) == 3


@pytest.mark.parametrize('kind', ['existing-file', 'existing-dir', 'output-symlink', 'parent-symlink', 'input-symlink'])
def test_reject_unsafe_output_or_source_paths(tmp_path, kind):
    src = source(tmp_path)
    out = tmp_path/'out'
    protected = tmp_path/'protected'
    protected.write_bytes(b'unchanged')
    if kind == 'existing-file': out.write_bytes(b'unchanged')
    if kind == 'existing-dir': out.mkdir()
    if kind == 'output-symlink': out.symlink_to(protected)
    if kind == 'parent-symlink':
        out.symlink_to(tmp_path, target_is_directory=True)
        out = out/'new'
    if kind == 'input-symlink':
        link = tmp_path/'source-link'
        link.symlink_to(src)
        src = link
    with pytest.raises((ValueError, FileExistsError)):
        gds.extract(src, ['root'], out)
    assert protected.read_bytes() == b'unchanged'
    if kind == 'existing-file': assert out.read_bytes() == b'unchanged'


def test_source_pin_mismatch_leaves_no_output(tmp_path):
    with pytest.raises(ValueError, match='SHA256'):
        gds.extract(source(tmp_path), ['root'], tmp_path/'out', '0'*64)
    assert not (tmp_path/'out').exists()


def test_source_mutation_even_in_excluded_cell_fails_closed(tmp_path, monkeypatch):
    src = source(tmp_path)
    copy = gds.copy_spans
    def mutate(stream, output, spans):
        raw = src.read_bytes()
        # Same-length geometry edit in the excluded cell, not selected output.
        start = raw.index(b'unused')
        offset = raw.index(struct.pack('>i', 1200), start)
        src.write_bytes(raw[:offset]+struct.pack('>i', 1300)+raw[offset+4:])
        return copy(stream, output, spans)
    monkeypatch.setattr(gds, 'copy_spans', mutate)
    # Defeat metadata detection: full second-pass SHA must still catch this.
    monkeypatch.setattr(gds, 'fingerprint', lambda stream: ('constant-stat',))
    with pytest.raises(ValueError, match='Source changed'):
        gds.extract(src, ['root'], tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_reads_are_bounded_and_not_whole_file():
    class BoundedReader(io.BytesIO):
        def read(self, count=-1):
            assert 0 <= count <= gds.COPY_BYTES
            return super().read(count)
    raw = library(cell('root', boundary()*20000), cell('unused', boundary()*20000))
    stream = BoundedReader(raw)
    result = gds.index_stream(stream)
    output = io.BytesIO()
    spans = [result['header'], result['cells']['root'], result['endlib']]
    sha, _, size = gds.copy_spans(stream, output, spans)
    assert sha == hashlib.sha256(raw).hexdigest() and size == len(raw)
    assert len(output.getvalue()) < len(raw)


def test_repeated_sref_aref_do_not_consume_unique_index_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(gds, 'MAX_REFERENCES', 1)
    data = library(cell('leaf', boundary()),
                   cell('root', (ref('leaf')+ref('leaf', True))*10))
    original = source(tmp_path, data)
    receipt = gds.extract(original, ['root'], tmp_path/'out')
    assert (tmp_path/'out/subset.gds').read_bytes() == data
    assert receipt['cells']['root']['source']['references'] == ['leaf']


@pytest.mark.parametrize('same_parent', [True, False])
def test_unique_reference_index_memory_guard_is_preserved(monkeypatch, same_parent):
    monkeypatch.setattr(gds, 'MAX_REFERENCES', 1)
    if same_parent:
        data = library(cell('a'), cell('b'), cell('root', ref('a')+ref('b')))
    else:
        data = library(cell('leaf'), cell('a', ref('leaf')), cell('b', ref('leaf')))
    with pytest.raises(gds.GDSFormatError, match='Reference index memory bound exceeded'):
        gds.index_stream(io.BytesIO(data))


NATIVE_CODE = r'''
import json, resource, sys
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS, (512*1024**2, 512*1024**2))
import klayout.db as db
source, subset, result = map(Path, sys.argv[1:])
a, b = db.Layout(), db.Layout()
a.read(str(source)); b.read(str(subset))
assert abs(a.dbu-.001) < 1e-15 and a.dbu == b.dbu
assert {c.name for c in b.each_cell()} == {'leaf','mid','root'}
assert {a.get_info(i).to_s() for i in a.layer_indices()} == {b.get_info(i).to_s() for i in b.layer_indices()}
for n in ('leaf','mid','root'):
    ca, cb = a.cell(n), b.cell(n)
    ia = sorted((a.cell(i.cell_index).name, str(i.cplx_trans), str(i.a), str(i.b), i.na, i.nb) for i in ca.each_inst())
    ib = sorted((b.cell(i.cell_index).name, str(i.cplx_trans), str(i.a), str(i.b), i.na, i.nb) for i in cb.each_inst())
    assert ia == ib
    for li in a.layer_indices():
        other = b.find_layer(a.get_info(li))
        assert (db.Region(ca.begin_shapes_rec(li)) ^ db.Region(cb.begin_shapes_rec(other))).is_empty()
root_instances = list(b.cell('root').each_inst())
assert len(root_instances)==2 and any(sorted((i.na,i.nb))==[2,3] for i in root_instances)
# A deliberately added polygon must break equivalence, proving the XOR control.
li = b.layer(1, 0)
b.cell('root').shapes(li).insert(db.Box(500000,500000,500100,500100))
assert not (db.Region(a.cell('root').begin_shapes_rec(a.layer(1,0))) ^ db.Region(b.cell('root').begin_shapes_rec(li))).is_empty()
record=dict(status='PASS', klayout_version=db.__version__, dbu=a.dbu, selected_cells=3,
            geometry_xor_negative_control_detected=True,
            sref_and_aref_hierarchy_equal=True, all_layer_geometry_xor_empty=True,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
result.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
'''


def test_pinned_native_klayout_geometry_units_and_reference_hierarchy(tmp_path):
    app = ROOT/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
    if not app.is_file():
        pytest.skip('Pinned KLayout runtime not installed')
    original = source(tmp_path)
    gds.extract(original, ['root'], tmp_path/'out')
    native = tmp_path/'native.py'
    native.write_text(NATIVE_CODE)
    child = subprocess.run([str(app), 'python', str(native), str(original),
                            str(tmp_path/'out/subset.gds'), str(tmp_path/'native-result.json')],
                           text=True, capture_output=True, timeout=45)
    assert child.returncode == 0, child.stdout+child.stderr
    assert json.loads((tmp_path/'native-result.json').read_text())['all_layer_geometry_xor_empty']
