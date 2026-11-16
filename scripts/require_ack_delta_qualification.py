"""Bind the new ACK distance source to its exact arithmetic and replay producer."""
import os,json,subprocess,hashlib,io,zipfile,time,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(path):
 return json.loads(subprocess.check_output(['gh','api',P+path]))
run_id=43808667103
head='31a9b7349474229b511f101acb5249655e6ce9f2'
deadline=time.monotonic()+1800
while True:
 run=api('actions/runs/'+str(run_id))
 assert run['head_sha']==head and run['run_attempt']==1
 if run['status']=='completed':break
 assert time.monotonic()<deadline,'Exact ACK qualification still pending; no synthesis authorized'
 print('Waiting for exact ACK qualification',run_id,run['status'],flush=True)
 time.sleep(45)
assert run['conclusion']=='success',run['conclusion']
arts=api('actions/runs/'+str(run_id)+'/artifacts')['artifacts']
arts=[a for a in arts if a['name']=='ack-delta-traffic-'+str(run_id) and not a['expired']]
assert len(arts)==1
a=arts[0];assert a['workflow_run']['id']==run_id and a['workflow_run']['head_sha']==head
blob=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(a['id'])+'/zip'])
digest=hashlib.sha256(blob).hexdigest();assert a['digest']=='sha256:'+digest
z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('ack-delta-traffic/result.json'))
proof=json.loads(z.read('ack-delta-proof/result.json'))
source=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v').read_bytes()
current=hashlib.sha256(source).hexdigest()
assert current==r['rtl_sha256']==proof['rtl_sha256']=='0833d4a4126272253fd0cd35e7eca118c163c435a803ef32930f61f16948f554'
assert r['source_head']==proof['source_head']==head
assert r['status']=='PASS_ACK_DELTA_ARITHMETIC_AND_SIX_REPLAY_TRAFFIC_CASES'
assert r['arithmetic_proof']==proof
assert proof['status']=='PASS_24BIT_ARITHMETIC_EQUIVALENCE_WITH_MUTATION_NOT_CHIP_ACCEPTANCE'
assert [(c['name'],c['returncode'],c['status'])for c in proof['cases']]==[('exact',0,'PASS'),('mutant_borrow',1,'REJECTED_EXPECTED_MUTANT')]
assert b'SUCCESS!' in z.read('ack-delta-proof/exact.log')
assert b'proof did fail' in z.read('ack-delta-proof/mutant_borrow.log')
common=['SOC_PCIE_ACK_STALE_PREFIX','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_WRITE_PREDECODE','SOC_PCIE_REPLAY_EOP_CACHE','SOC_PCIE_REPLAY_CRC_SELECT']
assert r['common_defines']==common and all(os.environ.get(k)=='1' for k in common)
want=[(4,38,256,1),(4,38,256,2),(4,38,1024,3),(4,38,256,4),(2,22,128,5),(2,22,128,6)]
assert [(x['depth'],x['max_bytes'],x['timeout'],x['seed'])for x in r['traffic']]==want
for x in r['traffic']:
 assert x['status']=='PASS' and x['cycles']==300000
 name=f"traffic-d{x['depth']}-b{x['max_bytes']}-t{x['timeout']}-s{x['seed']}.log"
 text=z.read('ack-delta-traffic/'+name).decode()
 assert re.search(r'^RESULT PASS',text,re.M) and not re.search(r'MISMATCH|FATAL|RESULT FAIL',text)
 assert [l for l in text.splitlines()if l.startswith(('SUMMARY','RESULT'))]==x['summary']
base=Path('hw/soc/tb/ack_delta_original.v').read_bytes()
assert hashlib.sha256(base).hexdigest()==r['reference_sha256']=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
s=source.decode();begin='    // BEGIN ACK_DELTA_GROUP_PREFIX';end='    // END ACK_DELTA_GROUP_PREFIX'
assert s.count(begin)==s.count(end)==1
assert (s.split(begin)[0]+'    wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;'+s.split(end)[1]).encode()==base
out=Path('out');out.mkdir(exist_ok=True)
(out/'ack-delta-qualification-gate.json').write_text(json.dumps(dict(run=run_id,source=head,artifact=a['id'],archive_sha256=digest,current_source_sha256=current,baseline_source_sha256=r['reference_sha256'],qualification=r,physical_accepted=False),indent=2))
