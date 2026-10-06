from pathlib import Path
import ast,hashlib,json,runpy
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
f=B/'source-freeze03.json';assert pin(f)==dict(bytes=2837,sha256='c7ff40ed5045e9265a40fe8aa27fc073b335649f9fd65579372f22b3eaaa4e97');j=json.loads(f.read_text());assert len(j['sources'])==9
for p,v in j['sources'].items():assert pin(R/p)==v,p
for file,key in [('architecture-contract01.json','contract'),('architecture-contract-source-peer-rx01.json','contract_peer'),('architecture-contract02-nominal-relation.json','nominal_supplement')]:assert pin(B/file)==j[key]
g=runpy.run_path(str(R/'scripts/generate_pcie_integrity_pipeline_v21.py'));assert len(g['REPLACEMENTS'])==8
rtl=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v21.v';s=rtl.read_text();assert g['candidate']()==s;assert g['original'](s)==g['SOURCE'].read_text()
for a,z in [('scripts/check_pcie_gen3_continuous_rx_integrity_v17.py','scripts/check_pcie_gen3_continuous_rx_integrity_v21.py'),('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v17.v','hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v21.v'),('hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v17','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v21')]:assert(R/a).read_text().replace('v17','v21')==(R/z).read_text()
bench=R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py';baseline=R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v17.py';assert bench.read_text().startswith(baseline.read_text())
case=lambda text:[n.name for n in ast.parse(text).body if isinstance(n,ast.AsyncFunctionDef)and n.decorator_list]
assert len(case(baseline.read_text()))==13 and len(case(bench.read_text()))==16
old=R/'hw/soc/out/pcie-integrity-v21-20261005/source-candidate01/hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py'
assert old.exists()
a={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(old.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};z={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(bench.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};changed=[k for k in a if a[k]!=z[k]];assert changed==['descriptor_parser_fault_cancels_queue_after_sampling_edge']
t=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_integrity_v21_pipeline.py'));positive=t['component']();assert len(t['FAULTS'])==9
for fault in t['FAULTS']:assert t['component'](fault)!=positive
assert "wire retire_room=!retire_valid || retire_pop;"in s and'read_keep'not in g['RETIRE_CONTROL']
for field in t['FIELDS']:assert s.count('retire_'+field+'<=')==2
whole=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py'));assert len(whole['FAULTS'])==12
for name,module,before,after,count,case_name in whole['FAULTS']:
 assert s.count(before)==count,(name,count,s.count(before))
 assert case_name in case(bench.read_text())
r=dict(status='PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE',freeze=pin(f),findings=[],source_pins=j['sources'],contract=pin(B/'architecture-contract01.json'),previous_source_finding=pin(B/'source-peer-findings01-rx.json'),review=[
'Full generator, generated descriptor diffs and complete V17 inverse inspected. Eight exact regions implement only declarations, retire availability, atomic payload writer, reset/flush/fault descriptor ownership, old-head transfer/capture and EDS drain. All original parser/CRC/read tree/verdict/cache/ring writers preserved exactly.',
'Old descriptor moves to output on pop; same-edge capture writes all six fields and wins descriptor validity. Nonempty held descriptor cannot be overwritten; zero-keep descriptor may drain while old output holds. Separate payload writer may update invalid bytes on parser fault but validity priority blocks later leakage until complete new capture.',
'Full helper, wrapper and Makefile read and exact version-only inverse reproduced. Real XML expected case list is dynamically parsed; actual16 cases required for full profile and explicit skipped counts for targeted selections. Original13 public byte/event oracle prefix unchanged.',
'Literal component copies exact DUT snippets for control/payload/priority while queue oracle independently expresses old-state transfer.4096 declared binary control assignments,14 X/Z field cases/reset/wrap and nine separately constructed mutations remain actual simulation obligations, not source-only PASS.',
'Nominal dual-DUT observer samples V17 pre-NBA public output and compares V21 afterNBA at+1ps, with same-cycle ring/parser/verdict cadence only when both active/ready. No arbitrary stall/fault cycle-equivalence claim. Two declared ready1 traffic cases plus actual registered-payload-bypass negative required.',
'New public cases drive only physical raw/control ports; hierarchical descriptor reads are coverage witnesses. Held empty drain requires observed empty pops/simultaneous capture; eight explicit control epochs clear ring/descriptor/output before fresh transaction scoreboard. Parser-fault four modes now observe actual settled fault/valid/ready/keep one ns after drive, before the original2ns public sample, and require positive accepted bytes exactly for acceptance mode. Prior missing boundary witness was corrected additively; original draft retained.',
'Final freeze03 adds four whole-DUT negative edits (fault/start descriptor clear, blocked empty pop, full overwrite) bound to actual public cases. All12 distinct full-DUT edit counts and actual case names verified; these complement nine component mutations and still need real failure detection.',
'Original valid_o prospective fault policy remains unchanged: old public beat can handshake on parser fault edge, ownership clears thereafter. Fault test cancels only oracle remainder after actual error and requires clean fresh epoch bytes; no arbitrary invalid queue masking.'
],pure_source_construction_checks=dict(full_generator_forward_inverse=True,exact_version_helpers=3,public_original_cases=13,new_total_cases=16,distinct_component_mutant_constructions=9,whole_DUT_mutants_bound_to_actual_cases=12),HDL_or_native_executed=False,limitations=['Actual sixteen public cases, literal/sequential/XZ controls and all intended mutations have not yet passed.','Timing improvement is a hypothesis; new same4ns mapping/proof/three-cornerSTA required after real functional gates.','MAX4118 and main-chip/fullPHY acceptance remain separate.'],method=pin(__file__))
q=B/'source-only-peer-rx03.json';assert not q.exists();q.write_text(json.dumps(r,indent=2)+'\n');print(pin(q))
