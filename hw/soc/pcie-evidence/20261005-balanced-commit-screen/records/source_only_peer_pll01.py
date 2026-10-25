"""Independent read-only commit-reduction source and helper bridge review."""
from pathlib import Path
import ast,hashlib,json,runpy,datetime
R=Path.cwd();B=Path(__file__).resolve().parent;RTL=R/'hw/soc/rtl/pcie'
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
names=['scripts/generate_pcie_integrity_commit_v18.py','scripts/check_pcie_gen3_continuous_rx_integrity_v18.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v18.v','hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v18.v','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v18.py','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v18','sw/tests/test_pcie_gen3_integrity_v18_miter.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v18.py']
G=runpy.run_path(str(R/names[0]));candidate=(RTL/'soc_pcie_gen3_framer_rx_integrity_v18.v').read_text();old=(RTL/'soc_pcie_gen3_framer_rx_integrity_v17.v').read_text()
assert candidate==G['candidate']() and G['restore'](candidate)==old
# Only declaration/default/five old writes and final reduction differ. No old
# commit_n RHS is consumed by any combinational parser statement.
parser=old[old.index(' integer j;\n always @* begin\n'):old.index(' // BEGIN V6 SHARED OLD VERDICT READS')]
assert parser.count('commit_n=')==6
assert parser.count('commit_n')==6
assert parser.count("commit_n=position+1'b1;")==4 and parser.count('commit_n=position;')==1
for name in names[1:]:
 if 'framer_rx' in name:continue
 previous=R/name.replace('_v18','_v17');expected=previous.read_text().replace('_v17','_v18')
 if name.endswith('test_pcie_gen3_integrity_v18_miter.py'):
  expected=expected.replace('test_pcie_gen3_integrity_v18_read.py','test_pcie_gen3_integrity_v18_commit.py')
 if name.endswith('test_pcie_gen3_continuous_rx_integrity_v18.py'):
  expected=expected.replace('commit_n=position;state_n=TOKEN;',"begin commit_write[j]=1;commit_value[j*PW+:PW]=position;end state_n=TOKEN;")
 assert (R/name).read_text()==expected,name
focused=R/'sw/tests/test_pcie_gen3_integrity_v18_commit.py';snapshot=B/'focused-harness-snapshot-public01.py';assert not snapshot.exists();snapshot.write_bytes(focused.read_bytes())
module=ast.parse(focused.read_text());helper=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='test_exact_generated_inverse_and_wrapper_bridge');helpertext=ast.get_source_segment(focused.read_text(),helper)
# Source inverse only; this invokes no HDL/tool simulation or public test run.
loaded=runpy.run_path(str(focused));loaded['test_exact_generated_inverse_and_wrapper_bridge']()
helperpin=dict(bytes=len(helpertext.encode()),sha256=hashlib.sha256(helpertext.encode()).hexdigest(),AST_sha256=hashlib.sha256(ast.dump(helper,include_attributes=False).encode()).hexdigest())
f=dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),files={n:pin(R/n) for n in names},live_focused_harness_snapshot=dict(path=str(snapshot),**pin(snapshot)),frozen_inverse_helper=helperpin,dependency_scope='Focusedharnessnegativecontrols still evolving underroot. Publicmiter imports only exactinversehelper with stableROOT/RTL/GEN/globalrunpy bindings; nofocusedHDLtest called. Helper andall8main/publicfiles mustremainidenticalthroughpublicrun. Finalninefilefreeze followsfocusedcontrols.')
(B/'source-public-freeze01.json').write_text(json.dumps(f,indent=2)+'\n')
checks=['Fullgeneratedframer inverse restores exactpinnedV17, includingreadtree,eventlist,allwriters/fault/commitregisterpriority andotherparseroutputs.','Originalcommit_n appears onlysixparserassignments(default+fivewrites), neverasparserRHS; delayedreduction cannotalterotherparseroutputs.','Eachlane flagzero/defaultandoneonactualproceduralwrite, alloriginalif/casebranches retained withbegin/end aroundpairedflag/valuewrites. Multiplewriteswithinlane retainlastvalue; laterlanepriority preserved.','Balanced pairmux chooseslaterwrittenlane; finalupperpair thenlowerpair thenoriginalcommit_ptr. Flags alwaysknown0/1, so literalX/Zpayload/fallbackpropagatewithoutORconversion. PWpartselect matchesoriginalassignmentwidth.','Wholewrapper/serialoracle/Makefile/checker versionbridges exact. Publicmiter onlyswitchesinversehelper; directlook_drops_successor actualmutant updated toexactnewbegin/endpair. Noothercoverage change.','Independent inversehelper executed withoutHDL; helperbytes/AST andcurrentfocusedharnesssnapshot pinned. Known uppervalueORzero negative maybeequivalent becausepositionarithmetic convertsZ; root correctingtarget separatelybeforemapping.']
r=dict(status='PASS_V18_COMMIT_REDUCTION_SOURCE_ONLY_PEER',reviewer='/root/pll_integrity_resume',findings=[],source_freeze=pin(B/'source-public-freeze01.json'),method=pin(Path(__file__)),checks=checks,full_public_controls_complete=False,focused_controls_complete=False,HDL_or_native_rerun=False,physical_acceptance=False)
(B/'source-only-peer-pll01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'peer':pin(B/'source-only-peer-pll01.json'),'freeze':pin(B/'source-public-freeze01.json')}))
