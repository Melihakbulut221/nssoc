"""Independent saved-byte/source audit. Does not import the reader or producer."""
from pathlib import Path
import ast
import gzip
import hashlib
import json
import os
import resource

os.sched_setaffinity(0, {2})
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
B = Path(__file__).resolve().parent
R = Path.cwd()


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


freeze_path = B / 'source-freeze01.json'
assert pin(freeze_path) == dict(bytes=178087,
    sha256='a131b301cffe20cbd94643e09c7d05d1e87fc151fc27f3f7815436ec0a5dabf7')
freeze = json.loads(freeze_path.read_text())
for path, expected in freeze['pins'].items():
    assert pin(path) == expected, path
assert len(freeze['pins']) == 726
controls_path = B / 'controls01.json'
assert pin(controls_path) == freeze['controls']
controls = json.loads(controls_path.read_text())
assert controls['status'] == 'PASS_SAVED_STREAMING_READER_EQUIVALENCE_AND_CORRUPTION_CONTROLS'
assert len(controls['checks']) == 20
assert controls['source'] == pin(B / 'raw_table01.py')
for path, expected in controls['inputs'].items():
    assert pin(path) == expected
reader = (B / 'raw_table01.py').read_text()
tests = (B / 'test_reader01.py').read_text()
tree = ast.parse(tests)
case_calls = [node.value for node in tree.body
              if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Name) and node.value.func.id == 'run_case']
expected_cases = {ast.literal_eval(call.args[0]): ast.literal_eval(call.args[1])
                  for call in case_calls}
assert len(expected_cases) == 17
saved_cases = controls['checks'][3:]
assert {row['name']: row['expected_diagnostic'] for row in saved_cases} == expected_cases
assert all(row['actual_diagnostic'] == row['expected_diagnostic'] and row['anonymous_cleanup']
           for row in saved_cases)
assert "matrix=np.memmap(backing,dtype='<f8',mode='r',shape=(rows,len(columns)))" in reader
assert 'finally:\n            matrix._mmap.close()' in reader
assert "with tempfile.TemporaryFile(mode='w+b',dir=directory)as backing:" in reader
assert 'assert expected<=scratch_limit' in reader
assert all(text in reader for text in ('SSD entry floor', 'SSD continuous floor',
                                       'SSD terminal floor', 'SSD post-context floor'))
assert controls['peak_rss_kib'] == 657272
native = []
for index, label in enumerate(('wire', 'halfstep', 'quarterstep')):
    folder = Path('/dev/shm') / f'nssoc-vco-v6-divider-tail115-v1-{label}-06-01'
    result_path = folder / 'result.json'
    wave = folder / 'wave.raw.gz'
    result = json.loads(result_path.read_text())
    saved = controls['checks'][index]
    assert saved['name'] == f'complete_{label}_saved_equivalence'
    assert saved['native_status'] == result['status']
    assert saved['rows'] == result['rows'] and saved['values'] == result['values']
    assert all(saved[key] is True for key in ('all455_bounds_equal', 'all_measurements_equal',
                                            'full_payload_bit_equal', 'anonymous_cleanup'))
    contacts = [item for item in result['devices'] if item['model'] in ('ptap1', 'ntap1')]
    assert len(result['devices']) == len(result['safety']['all_device_bounds']) == 455
    assert len(contacts) == 31 and len(result['devices']) - len(contacts) == 424
    assert [item['path'] for item in contacts] == [item['path'] for item in result['safety']['all_device_bounds'][424:]]
    whole = hashlib.sha256()
    payload = hashlib.sha256()
    with gzip.open(wave, 'rb') as stream:
        header = bytearray()
        while not header.endswith(b'Binary:\n'):
            line = stream.readline(4 * 1024**2 + 1 - len(header))
            assert line and len(header) + len(line) <= 4 * 1024**2
            header.extend(line)
        lines = bytes(header).split(b'Variables:\n', 1)[1].split(b'Binary:\n', 1)[0].splitlines()
        columns = []
        for expected_index, line in enumerate(lines):
            words = line.split()
            assert len(words) == 3 and int(words[0]) == expected_index
            columns.append(words[1].decode('ascii'))
        expected_bytes = result['rows'] * len(columns) * 8
        assert result['values'] == result['rows'] * len(columns)
        whole.update(header)
        remaining = expected_bytes
        while remaining:
            part = stream.read(min(1024**2, remaining))
            assert part and len(part) % 8 == 0
            whole.update(part)
            payload.update(part)
            remaining -= len(part)
        trailer = stream.read(64)
        assert trailer == str(result['rows']).encode() and stream.read(1) == b''
        whole.update(trailer)
    assert len(header) + expected_bytes + len(trailer) == result['raw_bytes']
    assert whole.hexdigest() == result['raw_sha256']
    assert payload.hexdigest() == result['payload_sha256']
    native.append(dict(label=label, result=pin(result_path), compressed=pin(wave),
                       status=result['status'], rows=result['rows'], columns=len(columns),
                       raw_bytes=result['raw_bytes'], raw_sha256=whole.hexdigest(),
                       payload_bytes=expected_bytes, payload_sha256=payload.hexdigest(),
                       device_bounds=455, contacts=31))
for path, expected in freeze['pins'].items():
    assert pin(path) == expected, path
record = dict(
    status='PASS_SOURCE_ONLY_BOUNDED_SAVED_RAW_MEMMAP_READER', reviewer='PLL agent',
    freeze=pin(freeze_path), sources=freeze['sources'], controls=pin(controls_path),
    pins_rechecked=726, actual_saved_controls=20,
    control_names=[row['name'] for row in controls['checks']], native_saved_bytes=native,
    method=pin(__file__), findings=[],
    reviewed_properties=[
        'Whole reader and test bodies read; bounded gzip header/payload/trailer consumption, three exact digests/counts, finite data scan and all four SSD floors.',
        'Anonymous SSD TemporaryFile owns backing lifetime; read-only memmap is closed in finally before backing closes, including consumer exceptions. No named payload copy survives.',
        'Chunk size is multiple of8; every expected float is checked finite before yield. Full raw/payload digests and exact copied backing bytes provide bit identity beyond np.array_equal numerical equality.',
        'Three saved positive controls use original455 bounds/measurement/time-grid functions; independent review confirms complete424+31 census,20 saved control names and exact diagnostic equality.',
        'All three saved gzip/raw/payload hashes and full row/column/trailer counts independently streamed without importing producer/reader or running controls.'
    ],
    scope='Standalone bounded reader only. Existing failed numerical/native statuses retained. '
          'No reviewed controls, simulator, network or extraction rerun. Not authorization for '
          'a future native run or adoption into sealer/comparator without separate derivative peer.',
    integration_obligations=[
        'Caller must supply externally pinned immutable result/header/column declarations; raw hashes alone do not establish provenance.',
        'Future consumers must preserve complete original safety/startup/measurement/numerical predicates and release all mapped views within context.',
        'Future caller must include input rehash before/after its complete comparison, signal ownership and original2GiB resource bound; this reader creates no child process.',
        'Saved controls materialize old arrays only as the finite reference; new reader removes full raw/payload copies, but future consumer temporary allocations still require resource verification.'
    ])
target = B / 'source-only-peer-pll01.json'
with target.open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(target), **pin(target), controls=20, pins=726)))
