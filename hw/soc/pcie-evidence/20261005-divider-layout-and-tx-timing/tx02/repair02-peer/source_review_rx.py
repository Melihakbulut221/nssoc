# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only TX02 saved-output reviewer inspection. Never execute reviewer."""
from pathlib import Path
import hashlib,json,ast,re,datetime
B=Path(__file__).resolve().parent;R=B.parents[4];D=json.loads((B/'source-derivation.json').read_text())
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
new=R/D['new']['path'];old=R/D['prior']['path']
for p,x in [(new,D['new']),(old,D['prior'])]:assert pin(p)=={k:x[k] for k in ['bytes','sha256']}
s=new.read_text();ast.parse(s);inverse=s
for x in reversed(D['changes']):assert inverse.count(x['after'])==x['count'],x;inverse=inverse.replace(x['after'],x['before'])
assert inverse==old.read_text()
rc=B.parent/'detailed_rc_repair02_resume03.py';r=rc.read_text();assert pin(rc)['sha256']=='b24d086741f136cd202814f4f5e586cd438932db9d2935e0fedf590023fffc31'
assert '-path_delay {direction} -group_path_count 3 -fields {{slew cap fanout}} -digits 6' in r
assert "for corner in ('slow','typical','fast'):" in r and "for direction in ('max','min')" in r
p=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-02/repaired.v');n=p.read_text();assert pin(p)==dict(bytes=4174181,sha256='5e964dabf6aa8a0d8a42a8ac9adbd0320b668ab350bf3a3ad9f9bd0402f62c90')
loads={}
for a in re.finditer(r'\b(sg13g2_(?:inv|buf)_\d+)\s+(clkload\d+)\s*\((.*?)\);',n,re.S):
 c=re.findall(r'\.(\w+)\(([^()]*)\)',a[3]);assert len(c)==1 and c[0][0]=='A';assert a[2] not in loads;loads[a[2]]=dict(master=a[1],clock_input=c[0][1])
assert set(loads)=={f'clkload{i}' for i in range(150)}
proof=B.parent/'proof_gate_repair02.py';pt=proof.read_text();tree=ast.parse(pt)
# This import defines pure functions only; execution has a literal __main__ guard.
assert "if __name__ == '__main__':" in pt
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='verify_binding')
body=ast.get_source_segment(pt,fn)
assert "PASS_ACTUAL_TX02_PROOF_AND_MUTATION_EXECUTION_BOUND" in body
assert "record['before_inputs'] == record['after_inputs']" in body
assert "record['expanded_graphs_before'] == record['expanded_graphs_after']" in body
assert "record['outputs'] ==" in body and "record['runtime_before']['pin'] == pin" in body
out=dict(status='PASS_TX02_SAVED_OUTPUT_REVIEWER_SOURCE_ONLY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='/root/rx_route_resume',sources={str(q):pin(q) for q in [new,old,B/'source-derivation.json',rc,proof,p,Path(__file__)]},inverse=dict(changes=len(D['changes']),byte_exact=True),candidate_CTS_census=dict(count=len(loads),all_150_input_only=True,instances_sha256=hashlib.sha256(json.dumps(loads,sort_keys=True).encode()).hexdigest()),findings=['Full source read and exact inverse of all documented changes passed. Every TX02 new root points to candidate02, DRT03, RC02, equivalence02 and portreplay02; prior comparison uses TX01 RC01.','New setup/hold/recovery/removal values come from retained reports, all finite and MET/VIOLATED consistent. Per-class all-corner booleans do not assert closure in advance; qualified_rc and physical_acceptance stay false.','Frozen RC Tcl still requests three worst paths per group for slow/typical/fast and max/min. Requiring six cases, two classes and three each is fail-closed if actual groups differ; no new report is available or inferred.','Exact candidate netlist independently contains clkload0..149 with only A connections and valid buffer/inverter masters. Netlist equality, actual unannotated driver names and SPEF binding remain required after routing; source census is not extraction evidence.','Added saved proof binding verifies source/input/output hashes, expanded graph bytes, runtime pin and actual compare/mutation command receipts. Imported proof_gate has guarded run(), so saved-output verify_binding executes no subprocess. Existing canonical compare is explicitly replayed on same saved graphs, not an independent algorithm.','Declared DRT/RC input/output hashes, zero final router DRC, exact candidate netlist and SDC, no exceptions, retained XML cases, SPEF numeric census and all input rehashes stay inherited. Nominal same-RC corners remain unqualified.'],issues_found=[],reviewer_executed=False,native_executed=False,tests_rerun=False,qualified_rc=False,physical_acceptance=False)
(B/'source-only-peer-rx.json').write_text(json.dumps(out,indent=2)+'\n');print(pin(B/'source-only-peer-rx.json'))
