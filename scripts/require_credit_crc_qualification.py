import subprocess,json,hashlib,io,zipfile,pathlib,re,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def sha(b):return hashlib.sha256(b).hexdigest()
def artifact(run,head,aid,digest):
    r=api('actions/runs/'+str(run));assert r['head_sha']==head and r['conclusion']=='success' and r['run_attempt']==1
    a=api('actions/artifacts/'+str(aid));assert a['workflow_run']['id']==run and a['workflow_run']['head_sha']==head and not a['expired'] and a['digest']=='sha256:'+digest
    data=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert sha(data)==digest
    z=zipfile.ZipFile(io.BytesIO(data));assert len(z.namelist())==len(set(z.namelist()));return z
subprocess.run(['python3','scripts/require_peer_ready_qualification.py'],check=True)
current_credit=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_credit_tx.v').read_bytes()
assert sha(current_credit)=='35b0b71994d793797c86f074f4d0d774789d64cf986049c5aec254b29121c530'
# Legacy credit/sign proofs bind the exact frozen pre-peer-ready reference.
# Current output/state change is independently certified above.
credit=pathlib.Path('sw/tests/fixtures/pcie_credit_tx/pre-peer-ready.v').read_bytes()
crc=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v').read_bytes()
assert sha(credit)=='e69f70857c984ef5c86001cf5427a417d35665942a449f8cc25ec0b237c5cb70'
assert sha(crc)=='20101056e4518fb5e14c882cacde089f618ad06cce20f2435b79bea4527668be'
z=artifact(43768395911,'bca723941a6c05bee185cf235079b5be1fb5ce03',14183093336,'4857ff38b5be3b220b0ae1a16fe65aa36a9bce9579c556aa610a6e1156b455c8')
f=json.loads(z.read('credit-formal/result.json'));assert f['passed'] and f['returncode']==0 and all(int(p)>0 and int(u)==0 for p,u in f['counts']) and f['counts']
for name,h in f['outputs'].items():assert sha(z.read('credit-formal/'+name))==h
assert 'Equivalence successfully proven!' in z.read('credit-formal/proof.log').decode()
temp=re.sub(r'\bd_ok\b','candidate_data_ok',credit.decode()).replace('soc_pcie_credit_pick','gate_credit_pick').replace('module soc_pcie_credit_tx (','module gate (')
assert z.read('credit-formal/gate.v').decode()==temp
mutation=json.loads(z.read('credit-mutation-evidence/result.json'));assert mutation['returncode']!=0 and mutation['detected'] and not mutation['accepted_mutation'] and mutation['source_sha256']==sha(credit)
for name,h in mutation['logs'].items():
    data=z.read('credit-mutant/'+name);assert sha(data)==h and b'CREDIT_DATA_SIGN_MISMATCH' in data
z=artifact(43768241980,'0c6892e572519dd370e5e8a4cbc2c0ea95c1dc9d',14183620525,'5061f5ad7733dcfe2922effac966a9d3cb601992f4378d4fdaaa5dbc4706a57c')
c=json.loads(z.read('result.json'));assert c['source_sha256']==sha(crc)
assert [(x['case'],x['expect'],x['passed'],x['returncode'])for x in c['cases']]==[('invariant','induction',True,0),('wrong_flag','reject',True,1),('full_module','equivalence',True,0)]
for name,h in c['outputs'].items():assert sha(z.read(name))==h
assert b'Induction step proven: SUCCESS!' in z.read('invariant.log')
assert b'Equivalence successfully proven!' in z.read('full_module.log')
assert b'ERROR: Called with -verify and proof did fail!' in z.read('wrong_flag.log')
assert all(os.environ.get(k)=='1'for k in ['SOC_PCIE_CREDIT_DATA_SIGN_REG','SOC_PCIE_CREDIT_PICK','SOC_PCIE_CRC_UPPER_COMPARE_REG','SOC_PCIE_SEQ_RX_REG'])
out=pathlib.Path('out');out.mkdir(exist_ok=True)
(out/'credit-crc-qualification.json').write_text(json.dumps(dict(credit_source_sha256=sha(current_credit),legacy_credit_source_sha256=sha(credit),peer_ready_qualification=json.loads((out/'peer-ready-qualification-gate.json').read_text()),crc_source_sha256=sha(crc),credit_formal=f,credit_mutation=mutation,crc_composition=c,physical_accepted=False),indent=2))
