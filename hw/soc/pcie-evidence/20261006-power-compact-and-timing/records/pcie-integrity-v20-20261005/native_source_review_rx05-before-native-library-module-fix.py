"""Additive source and saved-map peer; no native work or analysis rerun."""
from pathlib import Path
import ast,hashlib,json
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def funcs(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(Path(p).read_text()).body if isinstance(n,ast.FunctionDef)}
p=B/'continuation-policy05.json';assert pin(p)==dict(bytes=8291,sha256='8aa3ab3065ff88d308b14f0d0f254342d9bc6257bc5da990b68d3ce7b0d1f1b6')
policy=json.loads(p.read_text())
for k,v in policy['method_pins'].items():assert pin(k)==v,k
for k,v in policy['source_pins'].items():assert pin(R/k)==v,k
basis_path=Path(policy['recovery_basis']['path']);basis=json.loads(basis_path.read_text());assert pin(basis_path)=={k:policy['recovery_basis'][k]for k in ('bytes','sha256')}
old_path=Path(basis['old_continuation']['path']);assert pin(old_path)=={k:basis['old_continuation'][k]for k in ('bytes','sha256')}
old=json.loads(old_path.read_text());assert old['status']=='FAILED_RETAINED'
assert [(r['name'],r['status'],r['returncode'])for r in old['stages']]==[('map','COMPLETE',0),('read_depth','FAILED_RETAINED',1)]
births=[old['controller'],*[r['identity']for r in old['stages']]]
assert all(not Path(f"/proc/{r['pid']}").exists()for r in births)
mapped_path=Path(basis['map_result']['path']);assert pin(mapped_path)=={k:basis['map_result'][k]for k in ('bytes','sha256')}
mapped=json.loads(mapped_path.read_text());assert mapped['status']=='COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'and mapped['returncode']==0 and mapped['cells']==98417
for k,v in mapped['inputs'].items():assert pin(k)==v,k
for k,v in mapped['outputs'].items():assert pin(mapped_path.parent/k)==v,k
reader=B/'measure_native_read_depth05.py';old_reader=B/'measure_native_read_depth.py'
assert old_reader.read_text().count('candidate=analyze(a.candidate,19)')==1
assert old_reader.read_text().replace('candidate=analyze(a.candidate,19)','candidate=analyze(a.candidate,20)')==reader.read_text()
module=json.loads((mapped_path.parent/'mapped.json').read_text())['modules']
assert list(module)==['soc_pcie_gen3_continuous_rx_integrity_v20']
assert len(module['soc_pcie_gen3_continuous_rx_integrity_v20']['cells'])==98417
a,b=funcs(B/'continue_native04.py'),funcs(B/'continue_native05.py');same=['pin','explicit_stop','verify_sources','stage']
assert all(a[n]==b[n]for n in same)
controller=(B/'continue_native05.py').read_text();assert "stage('map',"not in controller
for name in ['balanced_import.py','prove_balanced_import.py','balanced_preplacement.py','analyze_critical_path.py']:
 text=(B/name).read_text();assert 'integrity_v19'not in text and 'integrity-v19'not in text
assert 'analyze(a.candidate,20)'in reader.read_text()
detach=B/'detach_native05.py';assert pin(p)['sha256']in detach.read_text();assert 'start_new_session=True'in detach.read_text()and'stdin=subprocess.DEVNULL'in detach.read_text()
assert not (B/'continuation-status05.json').exists()
r=dict(status='PASS_SOURCE_ONLY_V20_NATIVE_RECOVERY',policy=pin(p),findings=[],method=pin(Path(__file__)),prior_peer=pin(B/'native-source-only-peer04.json'),basis=pin(basis_path),reader=pin(reader),detacher=pin(detach),source_pins=policy['source_pins'],method_pins=policy['method_pins'],reused_map=basis['map_result'],saved_native_cells=98417,old_closed_identities=births,map_input_count=len(mapped['inputs']),map_output_count=len(mapped['outputs']),unchanged_function_asts=same,
 review='Full recovery/controller/detacher diff read. Exactly the stale numeric candidate19 selector changes to20; the rejectedV14 comparison stays14. The actual saved map has only the expectedV20 module and98417 cells, nativeexit0 and complete unchanged input/output hashes. Original controller records mapCOMPLETE then read-depthFAIL and all three prior birth PIDs are absent. Recovery requires that exact failed receipt and exact completed map, records reuse explicitly, omits map launch and starts only corrected read_depth05 plus previously untouched import/proof/4nsSTA. Remaining helper bodies were read beyond textual inverse: their module/root bindings are V20; only intended V19 comparative timing baseline remains. No process is adopted or signaled. Same owner lifecycle, CPU6/2GiB/floors and constraints retained.',
 preserved_failure='Peer04 source-version inverse did not detect the inherited numeric19 module selector. Its approval, actual analysis KeyError, failed continuation, old reader and successful map remain immutable. This additive receipt corrects that runtime binding; it does not rewrite prior failures.',
 native_executed=False,limitations='Saved-map/source review only, no analysis/native stage rerun. Actual corrected reader/import/proof/timing outcomes remain pending. No physical or fullPHY acceptance.')
out=B/'native-source-only-peer05.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out))))
