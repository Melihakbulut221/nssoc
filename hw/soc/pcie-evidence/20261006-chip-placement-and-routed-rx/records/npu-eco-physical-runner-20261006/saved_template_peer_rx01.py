"""Read only saved NPU template outputs and sample existing process births once."""
from collections import Counter
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

R=Path.cwd()
B=Path(__file__).resolve().parent
C=B/'template-control06'
checked={}


def pin(p):
    p=Path(p)
    with p.open('rb') as s:
        return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())


def verify(p, expected=None):
    p=Path(p)
    value=pin(p)
    if expected is not None:
        assert value==expected,str(p)
    checked[str(p)]=value
    return value


def read(p):
    return json.loads(Path(p).read_text())


def table(p):
    with Path(p).open() as stream:
        return list(csv.DictReader(stream,delimiter='\t'))


freeze=read(B/'source-freeze06.json')
peer=read(B/'source-only-peer-pll06.json')
assert peer['findings']==[] and peer['freeze']==verify(B/'source-freeze06.json')
verify(B/'source-only-peer-pll06.json')
for section in ('sources','dependencies'):
    for p,value in freeze[section].items():verify(p,value)
for p,value in freeze['controls'].items():verify(B/p,value)
control=read(C/'control.json')
assert control['status']=='PASS_NATIVE_MACRO_LEF_TEMPLATE_CONTROL_FIXED32MACROS301PINS'
assert control['all_input_pins_rechecked'] and not control['whole_chip_timing_accepted']
for p,value in control['inputs'].items():verify(p,value)
verify(B/'template_control06.py',{k:freeze['native_control_method'][k] for k in ('bytes','sha256')})
for name,value in control['output_views'].items():verify(C/name,value)

failure=read(B/'pair01-original/result.json')
verify(B/'pair01-original/result.json',freeze['preserved_failed_native_result'])
assert failure['status']=='FAILED_PRESERVED' and failure['execution']['returncode']!=0
for name,value in failure['outputs'].items():verify(B/'pair01-original'/name,value)
failed_log=B/'pair01-original/native-logs/18-odb-applydeftemplate/odb-applydeftemplate.log'
text=failed_log.read_text()
unknown=re.findall(r'unknown library cell referenced \(([^)]+)\) for instance \(([^)]+)\)',text)
assert len(unknown)==32 and Counter(x[0] for x in unknown)=={'SP6TSRAM512x64':16,'DP8TSRAMDP256x16':16}
assert len({x[1] for x in unknown})==32 and '[ERROR ODB-0421] DEF parser returns an error!' in text
old_command_path=B/'pair01-original-work/run/18-odb-applydeftemplate/COMMANDS'
old_command=shlex.split(old_command_path.read_text())
assert old_command==control['old_command']
cfg=read(B/'pair01-original/config.json')
assert cfg['CLOCK_PERIOD']==20
macros=cfg['MACROS']
assert set(macros)=={'SP6TSRAM512x64','DP8TSRAMDP256x16'}
assert all(len(x['lef'])==1 for x in macros.values())
extra=[path for name in sorted(macros) for path in macros[name]['lef']]
old_lefs=[old_command[i+1] for i,v in enumerate(old_command) if v=='--input-lef']
assert len(old_lefs)==3
for path in old_lefs:
    assert not set(macros)&set(re.findall(r'^MACRO\s+(\S+)',Path(path).read_text(),re.M))
for name,details in macros.items():
    assert re.findall(r'^MACRO\s+(\S+)',Path(details['lef'][0]).read_text(),re.M)==[name]
expected=list(old_command)
for option,name in (('-metrics','metrics.json'),('--output-odb','soc_top.odb'),('--output-def','soc_top.def')):
    assert expected.count(option)==1
    expected[expected.index(option)+1]=str(C/name)
expected=expected[:-1]+sum((['--input-lef',p] for p in extra),[])+expected[-1:]
assert expected==control['corrected_command']
assert '--strict' in expected and not {'--permissive','--copy-def-power'}&set(expected)
assert control['template_execution']['command']==[str(R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'),*expected]
assert all(control[k]['returncode']==0 for k in ('template_execution','source_execution','output_execution'))
native_log=(C/'fresh-physical.log').read_text()
assert 'unknown library cell' not in native_log and '[ERROR ' not in native_log
assert all(p in native_log for p in old_lefs+extra)
metrics=read(C/'metrics.json')
assert metrics['flow__errors__count']==0

witness_path=R/'hw/soc/pnr/alu-physical-macro-witness.json'
witness=read(witness_path)
assert witness['dbu']==1000 and len(witness['macros'])==32
expected_macros={r['native']:(r['master'],r['x_dbu'],r['y_dbu'],r['orientation']) for r in witness['macros']}
orientation={'N':'R0','FS':'MX'}
for row in witness['macros']:
    config_instance=macros[row['master']]['instances'][row['logical']]
    assert [round(x*1000) for x in config_instance['location']]==[row['x_dbu'],row['y_dbu']]
    assert orientation[config_instance['orientation']]==row['orientation']


def read_def(path):
    text=Path(path).read_text()
    assert re.search(r'^UNITS DISTANCE MICRONS 1000\s*;',text,re.M)
    die=tuple(map(int,re.search(r'^DIEAREA\s*\(\s*(\d+)\s+(\d+)\s*\)\s*\(\s*(\d+)\s+(\d+)\s*\)\s*;',text,re.M).groups()))
    section=text[text.index('\nCOMPONENTS '):text.index('\nEND COMPONENTS')]
    macro_rows=re.findall(r'^\s*-\s+(\S+)\s+(DP8TSRAMDP256x16|SP6TSRAM512x64)\b(.*?);',section,re.M|re.S)
    actual={}
    for name,master,body in macro_rows:
        match=re.fullmatch(r'\s*\+ FIXED \( (\d+) (\d+) \) (\S+)\s*',body)
        assert match and name not in actual
        x,y,o=match.groups();actual[name]=(master,int(x),int(y),orientation[o])
    assert actual==expected_macros
    section=text[text.index('\nPINS '):text.index('\nEND PINS')]
    assert re.match(r'\nPINS 303\s*;',section)
    pins={}
    for name,body in re.findall(r'^\s*-\s+(\S+)\s+(.*?);',section,re.M|re.S):
        direction=re.search(r'\+ DIRECTION (\w+)',body).group(1)
        use=re.search(r'\+ USE (\w+)',body).group(1)
        if use in ('POWER','GROUND'):continue
        assert use=='SIGNAL' and name not in pins
        boxes=re.findall(r'\+ LAYER (\w+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',body)
        placement=re.findall(r'\+ PLACED \( (\d+) (\d+) \) (\w+)',body)
        assert len(boxes)==len(placement)==1 and placement[0][2]=='N'
        layer,*box=boxes[0];offset=list(map(int,placement[0][:2]));box=list(map(int,box))
        pins[name]=(direction,use,layer,*(v+offset[i%2] for i,v in enumerate(box)),'PLACED')
    assert len(pins)==301
    return die,actual,pins


source_def=Path(old_command[old_command.index('--def-template')+1])
source_geometry=read_def(source_def)
output_geometry=read_def(C/'soc_top.def')
assert source_geometry==output_geometry
assert source_geometry[0]==tuple(round(x*1000) for x in cfg['DIE_AREA'])
for label in ('source','output'):
    folder=C/label
    geometry=control[label+'_geometry']
    for name,value in geometry.items():verify(folder/name,value)
    assert (folder/'dbu.txt').read_text().strip()=='1000'
    rows=table(folder/'macros.tsv')
    assert len(rows)==32 and Counter(x['master'] for x in rows)=={'SP6TSRAM512x64':16,'DP8TSRAMDP256x16':16}
    assert all(x['status']=='FIRM' for x in rows)
    actual={x['instance']:(x['master'],int(x['x_dbu']),int(x['y_dbu']),x['orientation']) for x in rows}
    assert actual==expected_macros
    pins=table(folder/'signal-pins.tsv')
    actual_pins={x['name']:(x['direction'],x['signal_type'],x['layer'],*[int(x[k]) for k in ('x0_dbu','y0_dbu','x1_dbu','y1_dbu')],x['status']) for x in pins}
    assert len(actual_pins)==len(pins)==301 and actual_pins==source_geometry[2]
    bounds=table(folder/'bounds.tsv')
    assert len(bounds)==2 and {x['kind'] for x in bounds}=={'die','core'}
    for row in bounds:
        key='DIE_AREA' if row['kind']=='die' else 'CORE_AREA'
        assert [int(row[k]) for k in ('x0_dbu','y0_dbu','x1_dbu','y1_dbu')]==[round(x*1000) for x in cfg[key]]
    tcl=(folder/'geometry.tcl').read_text()
    if label=='source':
        assert all('read_lef {'+p+'}' in tcl for p in old_lefs+extra)
        assert 'read_def {'+str(source_def)+'}' in tcl
    else:assert 'read_db {'+str(C/'soc_top.odb')+'}' in tcl
    assert control[label+'_execution']['command'][-1]==str(folder/'geometry.tcl')
    assert '[ERROR ' not in (folder/'fresh-physical.log').read_text()
assert control['source_geometry']==control['output_geometry']
assert Counter(x[1] for x in unknown)==Counter(expected_macros.keys())
for p in C.rglob('*'):
    if p.is_file():verify(p)


def identity(pid,start):
    p=Path('/proc')/str(pid)/'stat'
    if not p.exists():return dict(pid=pid,expected_start=start,present=False)
    fields=p.read_text().rsplit(') ',1)[1].split()
    return dict(pid=pid,expected_start=start,present=True,exact_birth=fields[19]==str(start),state=fields[0],ppid=int(fields[1]),process_group=int(fields[2]),start_ticks=fields[19],affinity=sorted(os.sched_getaffinity(pid)))


snapshot=dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),native_controls=[])
for row in (control,read(C/'source/result.json'),read(C/'output/result.json')):
    birth=row['native_identity'];seen=identity(birth['pid'],birth['start_ticks'])
    assert not seen.get('exact_birth') or seen['state']=='Z'
    snapshot['native_controls'].append(seen)
snapshot['pair02_owner']=identity(273309,'4802046')
snapshot['routes']={}
for label,base,ram,births in (
 ('RX16one',R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair16one-continuation01',Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-drt-01'),[(235510,'4403425'),(235511,'4403468'),(237298,'4431595')]),
 ('TX05',R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair05-continuation01',Path('/dev/shm/nssoc-tx-path-v4-repair05-drt-01'),[(225863,'4263948'),(225869,'4263984'),(246956,'4481198')])):
    log=(ram/'native.log').read_text()
    iterations=re.findall(r'Start (\d+(?:st|nd|rd|th)) optimization iteration\.',log)
    progress=re.findall(r'Completing (\d+)% with (\d+) violations\.',log)
    snapshot['routes'][label]=dict(identities=[identity(*x) for x in births],observer_status=read(base/'result.json')['status'],native_status=read(ram/'result.json')['status'],last_optimization_iteration=iterations[-1] if iterations else None,last_progress=progress[-1] if progress else None,scope='Intermediate router progress only; not final DRC count.')
report=dict(status='PASS_INDEPENDENT_SAVED_NPU_TEMPLATE_CONTROL06',findings=[],utc=snapshot['utc'],freeze=pin(B/'source-freeze06.json'),source_peer=pin(B/'source-only-peer-pll06.json'),control=pin(C/'control.json'),method=pin(Path(__file__)),
    prior_failure=dict(result=pin(B/'pair01-original/result.json'),raw_log=pin(failed_log),unknown_master_counts=dict(Counter(x[0] for x in unknown)),exact_all32_witness_names=True,error='ODB-0421 after unknown library cell warnings; original command had only technology, standard-cell and IO LEFs. Failure preserved.'),
    corrected_native=dict(command_exact_only_two_configured_macro_lefs_and_three_output_paths=True,strict_signal_only_retained=True,returncodes={k:control[k]['returncode'] for k in ('template_execution','source_execution','output_execution')},output_views=control['output_views'],all13_input_pins_rehashed=True,source_and_output_geometry=control['source_geometry'],errors=0,warnings='Inherited ORD-0039 and intentional signal-only POWER/GROUND omission messages retained.'),
    independent_geometry=dict(dbu=1000,macro_instances=32,master_counts={'SP6TSRAM512x64':16,'DP8TSRAMDP256x16':16},macro_witness=pin(witness_path),signal_terminals=301,signal_boxes=301,die_dbu=source_geometry[0],core_dbu=[round(x*1000) for x in cfg['CORE_AREA']],raw_DEF_parse='Independently reparsed both entire saved source/output DEF component and pin sections, exact fixed32 macro identities/positions/orientations and all301 absolute signal boxes; matched both native TSV captures and unchanged config/witness. Native ODB bytes rehashed, no OpenDB invocation.'),
    receipt_timing_note='control.json is the explicit terminal PASS receipt. The execute-generated result.json files in control/source/output remain immutable RUNNING snapshots written during the calls. Their recorded child births are now absent; all three terminal returncodes are0 in control.json. These snapshots do not assert a currently running control.',
    checked_pins=checked,live_observation=snapshot,
    scope='Saved parser/template geometry control only. Retained old PDN ODB was deliberately replayed; this is not a fresh matched-flow result or whole-chip timing/signoff. Active pair02 was observed once and left untouched; no native, tests, source edits, signals, reruns or extraction by this peer.')
out=B/'saved-template-peer-rx01.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],peer=pin(out),verified_files=len(checked),geometry=report['independent_geometry'],observation=snapshot),indent=2))
