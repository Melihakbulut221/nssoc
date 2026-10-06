# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent frozen sources and actual prior proof/ports readback only."""
from pathlib import Path
import ast,gzip,hashlib,json,xml.etree.ElementTree as ET
S=Path(__file__).resolve().parent;B=S.parent;E=Path('/dev/shm/nssoc-tx-path-v4-repair05-equivalence');P=Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-02')
cache={}
def pin(p):
 p=Path(p);s=p.stat();k=(str(p),s.st_size,s.st_mtime_ns)
 if k not in cache:
  with p.open('rb') as f:cache[k]=dict(bytes=s.st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
 return cache[k]
fpath=S/'route-rc-source-freeze.json';f=json.loads(fpath.read_text());assert f['files']=={p:pin(p) for p in f['files']}
brpath=S/'route-rc-source-bridge.json';assert pin(brpath)==f['bridge'];bridges=json.loads(brpath.read_text());assert len(bridges)==2
for r in bridges:
 a,z=Path(r['before']['path']),Path(r['after']['path']);assert pin(a)=={k:r['before'][k] for k in ('bytes','sha256')};assert pin(z)=={k:r['after'][k] for k in ('bytes','sha256')};assert a.read_text()==''.join(x['before'] for x in r['opcodes']);assert z.read_text()==''.join(x['after'] for x in r['opcodes'])
 old=ast.parse(a.read_text());new=ast.parse(z.read_text());of={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,ast.FunctionDef)};nf={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,ast.FunctionDef)};assert of==nf
 # Native Tcl construction expressions are unchanged; only B/OUT paths differ.
 def tcl(tree):return [ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.Assign,ast.AugAssign,ast.For)) and ('lines' in ast.unparse(n).split('=')[0] or isinstance(n,ast.For) and 'lines +=' in ast.unparse(n))]
 assert tcl(old)==tcl(new)
 text=z.read_text();assert 'owned_popen(' in text and 'subprocess.Popen(' not in text and 'fn=next(' not in text
helper_peer=json.loads((S/'proof-source-only-peer-rx02.json').read_text());assert not helper_peer['findings'] and pin(B/'owned_lifecycle05.py')==helper_peer['source_pins'][str(B/'owned_lifecycle05.py')]
binding=json.loads((E/'proof-execution-binding.json').read_text());assert binding['status']=='PASS_ACTUAL_TX05_PROOF_AND_MUTATION_EXECUTION_BOUND';assert binding['before_inputs']==binding['after_inputs']=={p:pin(p) for p in binding['before_inputs']};assert binding['outputs']=={n:pin(E/n) for n in binding['outputs']};assert binding['runtime_before']==binding['runtime_after'];assert binding['runtime_before']['pin']==pin(binding['runtime_before']['path']);assert [(r['method'],r['returncode']) for r in binding['runs']]==[('compare.py',0),('mutations.py',0)]
expanded={}
for n in ('gold','gate'):
 p=E/(n+'.json.gz');h=hashlib.sha256();sz=0
 with gzip.open(p,'rb') as stream:
  while b:=stream.read(1024**2):sz+=len(b);h.update(b)
 expanded[n]=dict(compressed=pin(p),expanded=dict(bytes=sz,sha256=h.hexdigest()))
assert expanded==binding['expanded_graphs_before']==binding['expanded_graphs_after']
eq=json.loads((E/'equivalence.json').read_text());assert eq['states']==3850 and eq['matched']==eq['targets']==11680 and not eq['mismatches']
mut=json.loads((E/'mutation-controls.json').read_text());assert len(mut['controls'])==10 and all(r['status'].startswith('REJECTED_') for r in mut['controls'])
r=json.loads((P/'result.json').read_text());assert r['status']=='PASS_EXACT_BOUND_TX05_PHYSICAL_NETLIST_PORT_REPLAY' and r['returncode']==0;assert r['inputs']=={p:pin(p) for p in r['inputs']};assert r['outputs']=={n:pin(P/n) for n in r['outputs']}
cases=list(ET.parse(P/'results.xml').getroot().iter('testcase'));assert len(cases)==3 and not any(list(c) for c in cases);assert [c.get('name') for c in cases]==['masks_headers_and_backpressure','sustained_word_rate','flushes_clear_partial_blocks_and_lfsrs']
for n in ('nssoc-tx-path-v4-repair05-drt-01','nssoc-tx-path-v4-repair05-detailed-rc-01'):assert not (Path('/dev/shm')/n).exists()
p=S/'route-rc-source-only-peer-rx.json';out=dict(status='PASS_SOURCE_ONLY_TX05_ROUTE_RC_AND_ACTUAL_PROOF_PORT_GATES',findings=[],freeze=pin(fpath),method=pin(__file__),source_pins=f['files'],whole_source_inverse_bridges=2,inherited_all_function_ASTs_equal=True,native_Tcl_ASTs_unchanged=True,owned_helper_prior_peer=pin(S/'proof-source-only-peer-rx02.json'),proof_binding=pin(E/'proof-execution-binding.json'),expanded_graphs=expanded,actual_binary_proof=dict(states=3850,targets=11680,matched=11680),actual_kernel_rejections=10,native_ports=dict(result=pin(P/'result.json'),xml=pin(P/'results.xml'),passed=3,failed=0,skipped=0,simulation_ns=sum(float(c.get('sim_time_ns')) for c in cases)),checks=['DRT requires exact bound proof and nativeports before launch, same netlist and zero routerDRC before successful terminal status.','RC rehashes completed DRT all inputs/outputs and byte-identical candidate, same nominal extraction rules/three cell corners and noqualifiedRC claim.','WNOWAIT owned helper pinned and used by all native creation/failurecleanup; old dynamic cleanup AST injection removed. Same CPU4/2.5GiB/floors/nohealthyelapsedtimeout.'],scope='Source-only review plus complete saved actual proof/input/gzip/XML readback. No producer, route, extraction, equivalence or native port execution by reviewer. Existing GPI interpreter path warning preserved; no cleanlog/fullchip/physicalclosure claim.')
assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
