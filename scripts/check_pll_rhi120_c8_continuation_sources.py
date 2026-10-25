import check_pll_rhi120_c8_initial_sources
import hashlib,json,pathlib
m=json.loads(pathlib.Path('scripts/pll-rhi120-c8-continuation-source-delta.json').read_text())
s=pathlib.Path(m['baseline_path']).read_text()
assert hashlib.sha256(s.encode()).hexdigest()==m['baseline_sha256']
for e in m['edits']:
    assert s.count(e['before'])==e['count']
    s=s.replace(e['before'],e['after'])
actual=pathlib.Path(m['candidate_path']).read_text()
assert s==actual and hashlib.sha256(actual.encode()).hexdigest()==m['candidate_sha256']
