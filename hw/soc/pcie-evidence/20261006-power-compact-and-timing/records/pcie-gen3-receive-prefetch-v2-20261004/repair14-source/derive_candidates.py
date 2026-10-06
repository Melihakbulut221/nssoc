# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare two exact-source constrained GRT alternatives; no native execution."""
from pathlib import Path
import ast,difflib,hashlib,json
S=Path(__file__).resolve().parent;B=S.parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def defs(text):return {n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
old=B/'postroute_repair13.py';ready=json.loads((B/'repair13-delivery/ready-finite.json').read_text());assert pin(old)==ready['compact_files'][str(old.relative_to(R))]
selection=json.loads((S/'selected-targets.json').read_text());targets=selection['targets'];assert len(targets)==11
for path,value in selection['inputs'].items():assert pin(path)==value
D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01');P=B/'repair13-peer'
baseline=[old,P/'review.json',P/'release.json',P/'publication-review.json',S/'selected-targets.json',D/'routed.odb',D/'routed.v',D/'routed.sdc',RC/'routed.spef',RC/'result.json']
pins={str(p):pin(p) for p in baseline};original=old.read_text();outputs={}
for version,drive in [('14a',2),('14b',4)]:
 text=original;changes=[]
 def replace(before,after):
  global text
  assert text.count(before)==1,(before,text.count(before));text=text.replace(before,after);changes.append(dict(before=before,after=after))
 replace('Candidate13 isolates six measured RX12 critical nets and upsizes four weak cells; original12 immutable; fresh GRT after changes.',f'Candidate{version} isolates eleven measured RX13 critical single loads using drive{drive}; original13 immutable; fresh GRT comparison only.')
 replace("B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13')",f"B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-{version}')")
 line=next(x for x in text.splitlines() if x.startswith('EXACT_BASELINE_PINS = '));replace(line,'EXACT_BASELINE_PINS = '+repr(pins))
 replace('# Baseline is immutable routed12;','# Baseline is immutable routed13;')
 replace('CANDIDATE12_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION','CANDIDATE13_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
 line=next(x for x in text.splitlines() if x.startswith('targets = '))
 chosen=[dict(name=x['driver'],master=x['master'],output_pin=x['output_pin'],net=x['net'],loads=[p['instance']+'/'+p['pin'] for p in x['loads']],buffer=f'sg13g2_buf_{drive}') for x in targets]
 replace(line,'targets = '+repr(chosen))
 replace('eco13_wire_{number}',f'eco{version}_wire_{{number}}');replace('eco13_sink_{number}',f'eco{version}_sink_{{number}}')
 line=next(x for x in text.splitlines() if x.startswith('upsizes = '));replace(line,'upsizes = []')
 replace('Baseline12 actualRC is reported before changes; then freshGRT estimates. Six measured drivers gain exact-load buffer isolation at actual driver location and four measured weak cells are upsized with unchanged Boolean functions.',f'Baseline13 actualRC is reported before changes; then freshGRT estimates. Eleven measured single-load drivers gain drive{drive} buffer isolation at actual driver location; no cell function or clock/hold/constraint change.')
 replace('Separate candidate13 starts from actual12 detailed geometry and unchanged4nsIOconstraints; six local critical-wire buffers/four upsizes only.',f'Separate candidate{version} starts directly from actual13 detailed geometry and unchanged4nsIOconstraints; eleven drive{drive} local critical-wire buffers and no direct upsizes. Compare with independent drive'+str(4 if drive==2 else 2)+' alternative before selecting any new DRT.')
 assert defs(text)==defs(original)
 inverse=text
 for c in reversed(changes):assert inverse.count(c['after'])==1;inverse=inverse.replace(c['after'],c['before'])
 assert inverse==original
 new=B/f'postroute_repair{version}.py';assert not new.exists();new.write_text(text)
 ledger=dict(status='EXACT_FULL_SOURCE_FORWARD_INVERSE_RX13_TO_RX'+version,original=dict(path=str(old),**pin(old)),candidate=dict(path=str(new),**pin(new)),changes=changes,unchanged_function_asts=list(defs(text)),baseline=pins)
 path=S/f'derivation-{version}.json';assert not path.exists();path.write_text(json.dumps(ledger,indent=2)+'\n')
 (S/f'derivation-{version}.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(old),tofile=str(new))))
 outputs[version]=dict(candidate=dict(path=str(new),**pin(new)),derivation=pin(path),output=f'/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-{version}')
f=dict(status='FROZEN_SOURCE_ONLY_TWO_RX14_CONSTRAINED_GRT_ALTERNATIVES',method=pin(__file__),selection=pin(S/'selected-targets.json'),alternatives=outputs,baseline=pins,limits=dict(cpu=8,address_space=2684354560,entry_free=1073741824,shared_floor=553648128,healthy_elapsed_watchdog=None),selection_policy='Run sequentially from immutable RX13, compare fresh three-corner GRT setup and hold with each identical before context. Select only measured functional netlist candidate; GRT is not acceptance. New exact proof/tenfaults/sixports and fresh detailed route/nominal RC remain mandatory. No 4ns/IO/clock/hold constraint relaxation.',scope='No native run yet; source peer required. Drive strengths of a22oi/nand4/nor4 actual critical source cells cannot be further upsized in this PDK. Two real buffer alternatives explicitly compared instead of assumed gain.')
p=S/'source-freeze.json';assert not p.exists();p.write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p),alternatives=outputs)))
