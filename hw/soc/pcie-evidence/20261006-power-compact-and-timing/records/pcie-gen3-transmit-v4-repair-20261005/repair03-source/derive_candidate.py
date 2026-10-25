# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Derive TX03 from the unchanged TX02 owner and measured completed route."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re

R = Path.cwd()
B = R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
S = B/'repair03-source'


def pin(path):
    p = Path(path)
    with p.open('rb') as stream:
        return {'bytes':p.stat().st_size, 'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}


before = (B/'postroute_repair02.py').read_text()
after = before
changes = []


def replace(old, new):
    global after
    assert after.count(old) == 1, old[:120]
    changes.append({'before':old,'after':new})
    after = after.replace(old, new, 1)


replace('TX candidate02 isolates six measured slow drivers, upsizes nine measured buffers and delays one measured hold endpoint; baseline01 immutable.',
        'TX candidate03 isolates seven measured complex/XOR drivers and upsizes three buffers; completed TX02 hold/recovery repairs remain in immutable baseline.')
replace("B=Path('/dev/shm/nssoc-tx-path-v4-repair01-drt-01');RC=Path('/dev/shm/nssoc-tx-path-v4-repair01-detailed-rc-01');O=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-02')",
        "B=Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03');RC=Path('/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02');O=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03')")
route = Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03')
rc = Path('/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02')
paths = [B/'postroute_repair02.py', B/'repair02-peer/review.json',
         B/'repair02-peer/release02.json', B/'repair02-peer/package.json',
         S/'selected-targets.json', S/'measure_saved_targets.py',
         *[route/n for n in ('routed.odb','routed.v','routed.sdc','routed.def','result.json')],
         *[rc/n for n in ('routed.spef','result.json','native.log')]]
pins = {str(p):pin(p) for p in paths}
oldpins = re.search(r'^EXACT_BASELINE_PINS = .*$',after,re.M)[0]
replace(oldpins,'EXACT_BASELINE_PINS = '+repr(pins))
replace('Baseline is immutable TX routed01;', 'Baseline is immutable TX routed02;')
replace('TX01_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION','TX02_GRT_BEFORE_EXPLICIT_LOAD_ISOLATION')
rows = json.loads((S/'selected-targets.json').read_text())['targets']
targets = [{'name':t['driver'],'master':t['master'],'output_pin':t['output_pin'],
            'net':t['net'],'loads':sorted(q['instance']+'/'+q['pin'] for q in t['loads']),
            'buffer':t['target_master']} for t in rows if t['change']=='isolate']
upsizes = [(t['driver'],t['master'],t['target_master']) for t in rows if t['change']=='upsize']
assert len(targets)==7 and len(upsizes)==3
newblock = 'targets = '+repr(targets)+'\n'
newblock += '''lines += ['set eco_block [ord::get_db_block]', 'set eco_scale [$eco_block getDbUnitsPerMicron]']
for number,target in enumerate(targets):
 name,master,port,netname,expected_loads,buffer = (target[k] for k in ('name','master','output_pin','net','loads','buffer'))
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{master}"}} {{error "Unexpected measured driver {name}"}}', f'set driver_pin [$driver findITerm {port}]', 'set net [$driver_pin getNet]', f'if {{[$net getName] != "{netname}"}} {{error "Measured net changed {name}"}}', 'set loads {}', 'foreach term [$net getITerms] {if {[$term getIoType] == "INPUT"} {lappend loads "[[$term getInst] getName]/[[$term getMTerm] getName]"}}', f'if {{[lsort $loads] ne [lsort {{{" ".join(expected_loads)}}}] || [llength [$net getBTerms]] != 0}} {{error "Measured load census changed {name}"}}', 'set xy [$driver getLocation]', 'set x [expr {double([lindex $xy 0])/$eco_scale}]', 'set y [expr {double([lindex $xy 1])/$eco_scale}]', f'puts "MEASURED_CRITICAL_BUFFER {name}/{port} [$net getName] $loads at $x $y"', f'insert_buffer -buffer_cell {buffer} -load_pins [get_pins $loads] -location [list $x $y] -buffer_name eco03_wire_{number} -net_name eco03_sink_{number}']
'''
newblock += 'upsizes = '+repr(upsizes)+'\n'
newblock += '''for name,old_master,new_master in upsizes:
 lines += [f'set driver [$eco_block findInst {name}]', f'if {{$driver == "NULL" || [[$driver getMaster] getName] != "{old_master}"}} {{error "Unexpected measured upsize source {name}"}}', f'replace_cell {name} {new_master}']
'''
start=after.index('targets = ')
end=after.index("lines += ['detailed_placement', 'check_placement -verbose']",start)
replace(after[start:end],newblock)
replace('BaselineTX01 actualRC is reported before changes; then freshGRT estimates. Six exact measured driver-load sets gain buf4 at driver location; nine measured buf1 become buf4; measured _55164_/D gains buf1 at load location.',
        'BaselineTX02 actualRC is reported before changes; then freshGRT estimates. Seven exact measured complex/XOR driver-load sets gain buf4 or buf8 at driver location and three measured buffers are upsized. Existing TX02 hold buffer remains untouched; no new hold insertion is made.')
replace('Separate TX candidate02 starts from actual01 detailed geometry and unchanged4nsIOconstraints; six driver buffers/nine upsizes/one hold buffer only.',
        'Separate TX candidate03 starts from actual02 detailed geometry and unchanged4nsIOconstraints; seven exact load isolations/three buffer upsizes only.')
f=lambda s:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
assert f(before)==f(after)
back=after
for item in reversed(changes):
    assert back.count(item['after'])==1
    back=back.replace(item['after'],item['before'],1)
assert back==before
candidate=B/'postroute_repair03.py'
assert not candidate.exists()
candidate.write_text(after)
(S/'derivation.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='TX02',tofile='TX03')))
bridge={'status':'EXACT_WHOLE_SOURCE_FORWARD_INVERSE_TX02_TO_TX03',
        'before':{'path':str(B/'postroute_repair02.py'),**pin(B/'postroute_repair02.py')},
        'after':{'path':str(candidate),**pin(candidate)},'changes':changes,
        'unchanged_function_asts':sorted(f(before)),'baseline':pins}
(S/'derivation.json').write_text(json.dumps(bridge,indent=2)+'\n')
freeze={'candidate':{'path':str(candidate),**pin(candidate)},'derivation':pin(S/'derivation.json'),
        'census':pin(S/'selected-targets.json'),'method':pin(__file__),
        'limits':{'cpu':4,'address_space_bytes':2684354560,'entry_free_bytes':1073741824,
                  'shared_floor_bytes':553648128,'healthy_elapsed_timeout':None},
        'scope':'Source-only TX03. Independent peer before fresh native candidate; downstream equivalence/ports/DRT/RC mandatory. Existing hold repair retained; no new timing gain claim.'}
(S/'source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
