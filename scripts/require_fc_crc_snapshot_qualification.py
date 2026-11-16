import os,subprocess,json,zipfile,io,hashlib,base64
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',P+path]))
def archive(run,head,aid,digest):
 r=api('actions/runs/'+str(run));assert r['head_sha']==head and r['conclusion']=='success' and r['run_attempt']==1
 a=api('actions/artifacts/'+str(aid));assert not a['expired'] and a['workflow_run']['id']==run and a['workflow_run']['head_sha']==head and a['digest']=='sha256:'+digest
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 return zipfile.ZipFile(io.BytesIO(b))
sim=archive(43861451898,'939bff59f3b42aa4037d183d9e18ce4534fe92af',14223202920,'186a983ed4e9fb73e07e53fda4ece350c02527dde108f4b37deb399c7c2a1be7')
formal=archive(43863099819,'ed698cffa505c86b4837c4e774d9b8816df65a38',14224551838,'89383ea7fc1ea3ca830c1061f42c87f462d973af225a844f1ba47c64595c436f')
s=json.loads(sim.read('result.json'));f=json.loads(formal.read('result.json'))
assert s['passed'] and s['fault_rejected'] and len(s['cases'])==6
assert {(c['refresh'],c['seed'])for c in s['cases']}=={(r,seed)for r in [8,128]for seed in [17,12345,987654]}
assert all(c['passed'] and 'FC_CRC_SNAPSHOT_PASS cycles=40000'in c['tail']for c in s['cases'])
assert f['passed'] and f['fault_rejected'] and f['cases']==[dict(refresh=8,proved=True),dict(refresh=128,proved=True)]
for n,h in f['inputs'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h==s['source_hashes'][n]
for refresh in [8,128]:
 log=formal.read('miter-'+str(refresh)+'.log').decode()
 assert 'Base case for induction length 1 proven.'in log and 'Induction step proven: SUCCESS!'in log
assert 'proof did fail'in formal.read('fault.log').decode()
assert 'FC_CRC_CONTRIBUTION_MISMATCH'in sim.read('fault.log').decode()
# Bind the reference to the exact prior mapped RTL, not merely a test fixture name.
path='hw/soc/rtl/pcie/soc_pcie_fc_tx.v'
original=base64.b64decode(api('contents/'+path+'?ref=d941f409e24243f8f16d09c4a60f6385f9fb6bb9')['content']).decode()
assert original.count('module soc_pcie_fc_tx #(')==1
assert Path('tests/fc_crc_snapshot/reference.v').read_text()==original.replace('module soc_pcie_fc_tx #(','module soc_pcie_fc_tx_reference #(')
out=Path('out');out.mkdir(exist_ok=True)
(out/'fc-crc-snapshot-qualification.json').write_text(json.dumps(dict(passed=True,simulation=s,formal=f,reference_source='d941f409e24243f8f16d09c4a60f6385f9fb6bb9',candidate_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),full_phy_accepted=False,final_timing_complete=False),indent=2))
