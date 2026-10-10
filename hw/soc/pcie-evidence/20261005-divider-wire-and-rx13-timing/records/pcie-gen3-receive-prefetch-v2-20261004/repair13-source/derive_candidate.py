# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Create separate candidate13 from measured immutableRX12; no native launch."""
from pathlib import Path
import ast,json,hashlib,difflib
S=Path(__file__).resolve().parent;B=S.parent;R=B.parents[3]
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
old=B/'postroute_repair12.py';before=old.read_text();assert pin(old)==json.loads((B/'repair12-delivery/ready-finite.json').read_text())['compact_files'][str(old.relative_to(R))]
selection=json.loads((S/'selected-targets.json').read_text());targets=selection['targets'];assert len(targets)==10
for p,v in selection['inputs'].items():assert pin(p)==v
D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01');P=B/'repair12-peer'
baseline=[old,P/'review.json',P/'release.json',P/'publication-review.json',S/'selected-targets.json',D/'routed.odb',D/'routed.v',D/'routed.sdc',RC/'routed.spef',RC/'result.json']
pins={str(p):pin(p) for p in baseline}
changes=[]
def sub(a,b):
 global before
 assert before.count(a)==1,(a,before.count(a));changes.append(dict(before=a,after=b));before=before.replace(a,b)
sub('Candidate12 isolates eight measured critical loads and upsizes two weak buffers; original11 immutable; fresh GRT after changes.','Candidate13 isolates six measured RX12 critical nets and upsizes four weak cells; original12 immutable; fresh GRT after changes.')
sub("B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-drt-02');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-detailed-rc-02');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-12')","B=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01');RC=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01');O=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13')")
line=next(x for x in before.splitlines() if x.startswith('EXACT_BASELINE_PINS = '));sub(line,'EXACT_BASELINE_PINS = '+repr(pins))
sub('# Baseline is immutable routed11;','# Baseline is immutable routed12;')
sub('CANDIDATE11_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION','CANDIDATE12_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
start=before.index('targets = ');end=before.index("lines += ['detailed_placement', 'check_placement -verbose']",start);original=before[start:end]
iso=[dict(name=x['driver'],master=x['master'],output_pin=x['output_pin'],net=x['net'],loads=[p['instance']+'/'+p['pin'] for p in x['loads']],buffer=x['target_master']) for x in targets if x['change']=='isolate']
up=[(x['driver'],x['master'],x['target_master']) for x in targets if x['change']=='upsize']
replacement='targets = '+repr(iso)+'''\nlines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,target in enumerate(targets):
 name,master,output_pin,netname,expected,buffer = (target[k] for k in ('name','master','output_pin','net','loads','buffer'))
 expected_tcl=' '.join(expected)
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {output_pin}]', 'set net [$driver_pin getNet]', f'if {{[$net getName] != "{netname}"}} {{error "Measured net changed {name}"}}', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{expected_tcl}}}]}} {{error "Exact measured load set changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{output_pin} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell {buffer} -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco13_wire_{number} -net_name eco13_sink_{number}']
upsizes = '''+repr(up)+'''
for name,old_master,new_master in upsizes:
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{old_master}"}} {{error "Unexpected measured upsize source {name}"}}', f'replace_cell {name} {new_master}']
'''
sub(original,replacement)
sub('Baseline11 actualRC is reported before changes; then freshGRT estimates. Eight single-load weak drivers gain buf4 at actual driver location and two measured buf1 become buf4.','Baseline12 actualRC is reported before changes; then freshGRT estimates. Six measured drivers gain exact-load buffer isolation at actual driver location and four measured weak cells are upsized with unchanged Boolean functions.')
sub('Separate candidate12 starts from actual11 detailed geometry and unchanged4nsIOconstraints; eight local critical-wire buffers/two upsizes only.','Separate candidate13 starts from actual12 detailed geometry and unchanged4nsIOconstraints; six local critical-wire buffers/four upsizes only.')
new=B/'postroute_repair13.py';assert not new.exists();ast.parse(before);new.write_text(before)
# All unchanged report and signal/resource/native cleanup definitions exact AST.
def defs(text):return {x.name:ast.dump(x) for x in ast.parse(text).body if isinstance(x,ast.FunctionDef)}
assert defs(old.read_text())==defs(before)
restored=before
for c in reversed(changes):assert restored.count(c['after'])==1;restored=restored.replace(c['after'],c['before'])
assert restored==old.read_text()
ledger=dict(status='EXACT_WHOLE_SOURCE_FORWARD_INVERSE_RX12_TO_RX13',before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),changes=changes,exact_unchanged_function_asts=list(defs(before)),baseline=pins)
(S/'derivation.json').write_text(json.dumps(ledger,indent=2)+'\n')
(S/'derivation.diff').write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),before.splitlines(True),fromfile=str(old),tofile=str(new))))
f=dict(candidate=dict(path=str(new),**pin(new)),derivation=pin(S/'derivation.json'),selected_targets=pin(S/'selected-targets.json'),method=pin(__file__),limits=dict(cpu=8,address_space=2684354560,entry_free=1073741824,shared_floor=553648128,healthy_elapsed_watchdog=None),scope='Source-only next candidate; no native execution and no new proof/port/DRT/RC acceptance.')
(S/'source-freeze.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f))
