import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/';out=Path('peer-ready-certificate');out.mkdir()
src=Path('hw/soc/rtl/pcie/soc_pcie_credit_tx.v');ref=Path('sw/tests/fixtures/pcie_credit_tx/pre-peer-ready.v')
def sha(b):return hashlib.sha256(b).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
candidate=src.read_text();reference=ref.read_text()
assert sha(src.read_bytes())=='35b0b71994d793797c86f074f4d0d774789d64cf986049c5aec254b29121c530'
assert sha(ref.read_bytes())=='e69f70857c984ef5c86001cf5427a417d35665942a449f8cc25ec0b237c5cb70'
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,full_phy_accepted=False,final_timing_complete=False,native_boot_accepted=False)
def artifact(runid,head,aid,digest,conclusion):
 run=api('actions/runs/'+str(runid));assert run['head_sha']==head and run['conclusion']==conclusion and run['run_attempt']==1
 m=api('actions/artifacts/'+str(aid));assert not m['expired']and m['digest']=='sha256:'+digest and m['workflow_run']['id']==runid and m['workflow_run']['head_sha']==head
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert sha(b)==digest
 z=zipfile.ZipFile(io.BytesIO(b));report=json.loads(z.read('result.json'))
 assert report['source_head']==head
 for name,h in report['outputs'].items():assert sha(z.read(name))==h
 return z,report
try:
 z,inv=artifact(43831875078,'9accf8666ff5ba59f70bd0472badab3bf820e751',14208754814,'35c7707de0e09009e0a1ede4ed28b9467f5944f03cd39d2700a591c6a04a8d81','success')
 assert inv['passed']and inv['sources_unchanged']and inv['rtl_sha256']==sha(src.read_bytes()) and len(inv['cases'])==8
 defs=[[],['SOC_PCIE_CREDIT_PICK'],['SOC_PCIE_CREDIT_DATA_SIGN_REG'],['SOC_PCIE_CREDIT_PICK','SOC_PCIE_CREDIT_DATA_SIGN_REG']]
 for i,ds in enumerate(defs):
  good,bad=inv['cases'][2*i:2*i+2]
  assert good['defines']==bad['defines']==ds and good['mutant']is False and bad['mutant']is True
  assert good['passed']and good['returncode']==0 and good['complete_model']
  assert bad['negative_control_detected']and bad['returncode']!=0 and bad['complete_model']
  log=z.read(str(i)+'/proof.log').decode();assert 'Induction step proven: SUCCESS!'in log and 'SAT proof finished - no model found: SUCCESS!'in log
  recipe=z.read(str(i)+'/proof.ys').decode()
  assert 'clk2fflogic'in recipe and '-set-at 1 rst_ni 0'in recipe
  assert not any(x in recipe for x in ['async2sync','-prove-x','-prove-skip','-tempinduct-skip','-set-init-zero','-ignore_unknown_cells'])
 transforms=json.loads(r'''[["    // Precompute the peer-ready conjunction alongside its source registers.\n    // External reset/link/local-init qualification remains combinational.\n    reg peer_ready;\n\n","",1],["    assign initialized_o=rst_ni && link_up_i && peer_ready && local_init_done_i;","    assign initialized_o=peer_init1_done_o && confirmed && local_init_done_i;",1],["peer_ready<=0;","",2],["            peer_ready<=(&picked_seen) && picked_confirmed;\n","",1],["            peer_ready<=consume ? ((&next[1].seen_n) && next[1].confirmed_n) :\n                                  ((&next[0].seen_n) && next[0].confirmed_n);\n","",1]]''')
 def normalize(text):
  for old,new,count in transforms:
   assert text.count(old)==count
   text=text.replace(old,new)
  return text
 normalized=normalize(candidate)
 assert normalized==reference,'Unexpected non-peer-ready RTL difference'
 assert 'peer_ready'not in normalized
 # Invariant establishes peer_ready=all(seen)&confirmed. Qualifying the
 # output with reset/link/local-init is then exactly the original equation.
 rows=0
 for bits in range(128):
  seen=bits&7;confirmed=bool(bits&8);reset=bool(bits&16);link=bool(bits&32);local=bool(bits&64)
  peer=(seen==7)and confirmed
  original=(reset and link and seen==7)and confirmed and local
  optimized=reset and link and peer and local
  assert original==optimized;rows+=1
 rejected=[]
 for name,mut in [('unrelated_state_logic',candidate.replace('wire all_seen=&seen;','wire all_seen=|seen;')),('missing_reset_assignment',candidate.replace('peer_ready<=0;','',1)),('inverted_output',candidate.replace('&& peer_ready &&','&& !peer_ready &&'))]:
  assert mut!=candidate
  try:ok=normalize(mut)==reference
  except AssertionError:ok=False
  assert not ok;rejected.append(name)
 tz,traffic=artifact(43827501390,'881a146c716f4b345489279c5841b88e39a00e83',14207468693,'7337e607413eff444aa1944a9e06d58a59a109dd7dd1a38ea2e74be468bd6c12','failure')
 assert traffic['inputs']['hw/soc/rtl/pcie/soc_pcie_credit_tx.v']==sha(src.read_bytes())
 assert traffic['inputs']['sw/tests/fixtures/pcie_credit_tx/pre-peer-ready.v']==sha(ref.read_bytes())
 assert len(traffic['cases'])==4
 for i,c in enumerate(traffic['cases']):
  assert c['defines']==defs[i]and len(c['seeds'])==4
  for seed,x in enumerate(c['seeds'],1):
   assert x['seed']==seed and x['passed']and x['returncode']==0
   log=tz.read(str(i)+'/seed'+str(seed)+'.log').decode()
   assert re.search(r'^RESULT PASS$',log,re.M)and 'cycles=300000'in log and 'mismatches=0'in log
 r.update(passed=True,two_state_after_reset_equivalence=True,normalized_source_equals_reference=True,reference_sha256=sha(ref.read_bytes()),candidate_sha256=sha(src.read_bytes()),invariant_run=43831875078,traffic_run=43827501390,traffic_cycles=4800000,output_truth_table_rows=rows,negative_controls=rejected,scope='Composition: proven explicit-clock/reset invariant, exact bytewise reference after replacing initialized equation and removing unused peer_ready state, exhaustive Boolean output equation. Applies after initial reset in two-state symbolic model; four-state traffic supplemental. No native/SDF boot, mapped timing or full serial PHY acceptance.')
 (out/'normalized-reference.v').write_text(normalized)
except BaseException as e:r['error']=repr(e);raise
finally:
 (out/'result.json').write_text(json.dumps(r,indent=2))
