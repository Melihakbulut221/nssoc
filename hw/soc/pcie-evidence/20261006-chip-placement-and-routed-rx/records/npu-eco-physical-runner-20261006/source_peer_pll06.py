# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read only full source bridges, actual failed command and saved68 controls."""
from pathlib import Path
import ast,hashlib,json,shlex,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze06.json').read_text());assert pin(B/'source-freeze06.json')['sha256']=='923e753533bb8d7f38d93a3e14b563137494b6a77031f2bb4f03e6dbcb60000f'
for sec in ['sources','dependencies']:
 for p,h in f[sec].items():assert pin(p)==h,p
for p,h in f['controls'].items():assert pin(B/p)==h,p
control=Path(f['native_control_method']['path']);assert pin(control)=={k:f['native_control_method'][k]for k in ('bytes','sha256')}
prior=json.loads((B/'source-freeze05.json').read_text());assert prior['sources']==f['sources']and prior['controls']==f['controls']
assert pin(B/'template_control04.py')==prior['native_control_method']
old=(B/'template_control04.py').read_text();new=control.read_text()
extra="inputs += [old/'COMMANDS',B/'pair01-original/config.json',pathlib.Path(__file__)] + [pathlib.Path(original[i+1]) for i,v in enumerate(original) if v=='--input-lef']\nf.verify_bundle(B/'bundle01',runtime)\n"
assert new.count(extra)==1 and new.replace(extra,'').replace('template-control06','template-control04')==old
old=(B/'pair01-original/methods/scripts/run_npu_eco_physical.py').read_text();new=(R/'scripts/run_npu_eco_physical.py').read_text()
def funcs(s):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a,b=funcs(old),funcs(new);assert {n for n in a if a[n]!=b[n]}=={'run'}
runnew=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef)and n.name=='run');runold=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)and n.name=='run')
bridge=ast.get_source_segment(new,runnew).replace('methods/hw/soc/pnr/npu_eco_physical_flow.py','methods/hw/soc/pnr/alu_physical_flow.py').replace("'NPUECOFreshPhysical'","'ALUFreshPhysical'")
assert bridge==ast.get_source_segment(old,runold)
assert (R/'scripts/npu_physical_process.py').read_bytes()==(B/'pair01-original/methods/scripts/npu_physical_process.py').read_bytes()
assert (R/'sw/tests/test_npu_eco_physical.py').read_bytes()==(B/'pair01-original/methods/sw/tests/test_npu_eco_physical.py').read_bytes()
xml=B/'controls04.xml';cases=list(ET.parse(xml).getroot().iter('testcase'));assert len(cases)==68 and all(not any(c.find(k)is not None for k in ['failure','error','skipped'])for c in cases)
counts={}
for c in cases:counts[c.get('classname')]=counts.get(c.get('classname'),0)+1
assert sorted(counts.values())==[11,24,33]
assert 'Traceback'not in(B/'flow-import04.log').read_text()and'Usage:'in(B/'flow-import04.log').read_text()
failed=B/'pair01-original/result.json';assert pin(failed)==f['preserved_failed_native_result'];failure=json.loads(failed.read_text());assert failure['status']=='FAILED_PRESERVED'
base=B/'pair01-original-work/run/18-odb-applydeftemplate';commands=shlex.split((base/'COMMANDS').read_text());assert commands.count('--input-lef')==3 and '--strict'in commands and '--permissive'not in commands
lefs=[Path(commands[i+1])for i,v in enumerate(commands)if v=='--input-lef'];cfg=json.loads((B/'pair01-original/config.json').read_text());macros={n:v['lef']for n,v in cfg['MACROS'].items()};assert set(macros)=={'DP8TSRAMDP256x16','SP6TSRAM512x64'}
assert all(len(v)==1 and Path(v[0]).name==n+'.lef'for n,v in macros.items())
macrofiles=[Path(v[0])for v in macros.values()];assert all(p.is_file()for p in lefs+macrofiles)
log=(base/'odb-applydeftemplate.log').read_text();assert all('unknown library cell referenced ('+n+')'in log for n in macros)
# Whole step list inheritance/readback is source-only; no librelane/EDA import.
flow=(R/'hw/soc/pnr/npu_eco_physical_flow.py').read_text();assert "class ApplyMacroDEFTemplate(Odb.ApplyDEFTemplate):"in flow and "command = super().get_command()"in flow and "return append_template_macro_lefs(command, macros)"in flow
assert 'Steps = [ApplyMacroDEFTemplate if step == Odb.ApplyDEFTemplate else step\n             for step in ALUFreshPhysical.Steps]'in flow
r=dict(status='PASS_SOURCE_ONLY_MACRO_AWARE_NPU_TEMPLATE_READER_AND_NATIVE_CONTROL',freeze=pin(B/'source-freeze06.json'),source_pins=f['sources'],native_control=dict(path=str(control),**pin(control)),prior_finding=pin(B/'source-only-peer-pll05-findings.json'),findings=[],method=pin(__file__),saved_controls=dict(cases=68,counts=counts,all_pass=True,xml=pin(xml),log=pin(B/'controls04.log'),actual_runtime_CLI_import_log=pin(B/'flow-import04.log'),rerun=False),actual_failed_basis=dict(result=pin(failed),command=pin(base/'COMMANDS'),raw_log=pin(base/'odb-applydeftemplate.log'),configuration=pin(B/'pair01-original/config.json'),original_three_lefs={str(p):pin(p)for p in lefs},two_macro_lefs={str(p):pin(p)for p in macrofiles},runtime_source=pin(B/'template-runtime-source01.txt')),reviewed_scope=['Pure helper appends exactly the two existing source-bound MACROS LEF paths, retains full original strict signal-only DEF command, and rejects missing/wrong/duplicate macro inventory or permissive/power-copy flags. Native runtime parent omitted MACROS LEFs, matching the actual retained unknown-master failure.','Subclass changes only ApplyDEFTemplate.get_command; original flow run and all other ordered step classes preserved. Runner run is whole-source identical after the exact new flow-path/class reversal; all other function ASTs and owned process helper unchanged.','Native parser control replays only retained failed command plus two LEFs and new output names. Original ODB, DEF, all five LEFs, config, COMMANDS, script, runtime and geometry method are pinned before/after; full frozen bundle is validated before native. Fresh output and terminal failure/log preservation remain required.','Source and output native geometry will each require exact32macro master/position/orientation against unchanged witness and301signal pins, samebounds; their pin/bounds/dbu byte hashes must match. This is a parser/geometry control, not use of old ODB as new matched-flow state. Fresh complete matchedpair is still independently gated and retains nl-only input and20ns constraints.','Existing SIGINT/TERM handoff block and WNOWAIT owned-group lifetime retained. No healthy elapsed timeout, native8GiBAS and9GiBmemory/3GiBdisk entry checks; no claimed continuous9GiB reserve.'],native_or_tests_executed_by_peer=False,scope='Source-only additive integration repair and saved68-control recount. Actual template-only native control and fresh matched pair have not run in this review; no full-chip timing/DRC/LVS/manufacturing acceptance.')
p=B/'source-only-peer-pll06.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
