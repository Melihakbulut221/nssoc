"""Independent additive V20 alignment source review; no HDL execution."""
from pathlib import Path
import ast
import hashlib
import json

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


old = json.loads((B / 'source-freeze03.json').read_text())
new = json.loads((B / 'source-freeze04.json').read_text())
assert pin(B / 'source-freeze04.json')['sha256'] == 'd90ec259ca0a524005dafc838feec3ef93598e056372b88bc9199e1c13e029db'
for p, v in new['files'].items():
    assert pin(R / p) == v
changed = [p for p in new['files'] if new['files'][p] != old['files'][p]]
bench = 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py'
assert changed == [bench]
delta = json.loads((B / 'stimulus-alignment-correction04.json').read_text())
text = (R / bench).read_text()
assert text.count(delta['new']) == 1
inverse = text.replace(delta['new'], delta['old'])
assert dict(bytes=len(inverse.encode()), sha256=hashlib.sha256(inverse.encode()).hexdigest()) == old['files'][bench]
# This alignment is independent of packet length and parameterized ring depth.
for length in range(0, 8192):
    assert (length + (60 - length) % 64) % 64 == 60
    assert 0 <= (60 - length) % 64 < 64
rtl = (R / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v20.v').read_text()
assert 'slice == 3' in rtl and 'control_word == 3' in rtl
launch = (B / 'launch_controls04.py').read_text()
assert "assert pin(freeze)['sha256']=='d90ec259ca0a524005dafc838feec3ef93598e056372b88bc9199e1c13e029db'" in launch
assert '2*1024**3' in launch and 'owner.check()' in launch
detach = (B / 'detach_controls04.py').read_text()
assert pin(B / 'launch_controls04.py')['sha256'] in detach
assert 'start_new_session=True' in detach and 'stdin=subprocess.DEVNULL' in detach
for name in ['launch_controls04.py', 'detach_controls04.py', 'targeted_controls04.py']:
    ast.parse((B / name).read_text())
target = (B / 'targeted_controls04.py').read_text()
assert target.count("case='stalled_output_retires_committed_zero_keep_words'") == 2
assert target.count('passed=1,failed=0,skipped=14') == 2
prior = json.loads((B / 'source-only-peer-rx03.json').read_text())
assert prior['findings'] == []
result = dict(
    status='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE',
    freeze=pin(B / 'source-freeze04.json'),
    findings=[],
    method=pin(Path(__file__)),
    source_pins=new['files'],
    unchanged_sources=8,
    exact_changed_source=bench,
    prior_peer=pin(B / 'source-only-peer-rx03.json'),
    supporting_methods={str(B / n): pin(B / n) for n in ['launch_controls04.py', 'detach_controls04.py', 'targeted_controls04.py', 'stimulus-alignment-correction04.json', 'launcher-pin-correction04.json']},
    review='Full sole bench delta is exact inverse to frozen03. Padding inserts only zero IDL bytes so EDS begins at byte60 of a64-byte block, matching slice3 DWORD3. All strict held/retirement/no-halt/no-overflow/scoreboard assertions and reference observer remain byte-identical. Same corrected stream reaches positive direct, V17 miter and formerly undetected retire_never_empty mutant. Only appended case is selected in direct/miter; 14 excluded cases remain honest skipped, with prior actual results retained. Old controls03 mutant PASS is not adopted without paired corrected positive/negative results. Four new selected predicates include inverse. Frozen DUT, generator, read logic and native constraints unchanged.',
    launcher_finding='Initial stale/mutated old freeze hash was found and preserved in draft01; final launch literal now exactly binds freeze04, detached launcher binds corrected launch bytes.',
    native_executed=False,
    limitations='Source-only approval for targeted actual tests. Actual new positive witnesses and same-stream mutant rejection remain pending. No native mapping, physical timing or MAX4118 acceptance inferred.'
)
out = B / 'source-only-peer-rx04.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(path=str(out), **pin(out))))
