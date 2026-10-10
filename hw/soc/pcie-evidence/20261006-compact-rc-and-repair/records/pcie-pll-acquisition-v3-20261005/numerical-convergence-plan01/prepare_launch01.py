"""Bind the predeclared TMAX-only experiment; no native process or download."""
from pathlib import Path
import hashlib,json,sys
R=Path.cwd();B=Path(__file__).resolve().parent;L=B/'launch01';L.mkdir(exist_ok=False)
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v4 as m

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
peer=json.loads((B/'source-only-peer-rx01.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_PLL_RETAINED_TSTEP_MAXSTEP125' and not peer['findings'] and peer['freeze']==pin(B/'source-freeze01.json')
f=json.loads((B/'source-freeze01.json').read_text())
for p,v in (f['sources']|f['parent_methods']).items():assert pin(R/p)==v
assert pin(B/'method-controls03.xml')==f['controls']['xml']
d=dict(schema='PLL_RETAINED_TSTEP_MAXSTEP_REFINEMENT_V1',first_result_sha256=m.BASELINE_SHA,first_full_review_sha256=m.BASELINE_REVIEW_SHA,TSTEP_s=m.TSTEP,first_TMAX_s=m.TSTEP,second_TMAX_s=m.TMAX,stop_s=m.STOP,windows_s=[[800e-9,900e-9],[900e-9,1e-6]],frequency_difference_limit_ppm=100.0,matched_phase_limit_s=50e-12,phase_alignment_or_offset_removal=False,previous_5ps_2p5ps_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN')
(L/'declaration.json').write_text(json.dumps(d,indent=2)+'\n')
paths=dict(parent=Path('/dev/shm/nssoc-pll-acquisition-v1-evidence/second1us-prerequisites.json'),baseline=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02/result.json'),baseline_review=B.parent/'replay-step25-01/result.json',declaration=L/'declaration.json')
gate={k:dict(path=str(p.resolve()),sha256=pin(p)['sha256'])for k,p in paths.items()}
(L/'prerequisites.json').write_text(json.dumps(gate,indent=2)+'\n')
prior=m.verify_parent();validated=m.prerequisites(L/'prerequisites.json',m.sha(L/'prerequisites.json'),m.TSTEP,prior)
original=Path(m.namespace['ORIGINAL'])/'bench.cir';deck=m.stream_deck(original.read_text(),m.TSTEP,m.STOP)
assert deck==(B/'candidate-max125-source-only.cir').read_text()
proof=dict(status='PASS_OFFLINE_MAXSTEP125_PREREQUISITES',no_native=True,source_peer=pin(B/'source-only-peer-rx01.json'),source_freeze=pin(B/'source-freeze01.json'),prerequisites=pin(L/'prerequisites.json'),declaration=pin(L/'declaration.json'),devices=len(prior['devices']),exact_candidate_deck_sha256=hashlib.sha256(deck.encode()).hexdigest(),inputs={str(p):pin(p)for p in validated['paths']},prepare_method=pin(__file__))
assert proof['devices']==539
(L/'offline-prerequisites.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof['status'],len(proof['inputs']),pin(L/'offline-prerequisites.json'))
