"""Source-bound EOP composition and exact-switch traffic admission."""
import os,pathlib,json,subprocess,hashlib,zipfile,io,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_bytes();sha=hashlib.sha256(source).hexdigest()
assert sha=='a83699c6311ba0ac6414060f68699ee29510bf5ed99fee64f92168546bf16223'
flags=['SOC_PCIE_RX_EOP_FLAGS','SOC_PCIE_RX_READ2','SOC_PCIE_RESET_COPIES','SOC_PCIE_RX_COMMIT_COPIES','SOC_PCIE_RX_CURSOR_LOCAL_RESET','SOC_PCIE_RX_LOCAL_LANE_NEXT','SOC_PCIE_RX_DLLP_LAST_COMPARE']
assert all(os.environ.get(f)=='1'for f in flags)
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def archive(run,head,aid,digest):
 r=api('actions/runs/'+str(run));assert r['head_sha']==head and r['run_attempt']==1 and r['conclusion']=='success'
 m=api('actions/artifacts/'+str(aid));assert not m['expired']and m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()));return z
formal=archive(43780244322,'68a9f6438b6c31314a78aa1f287595e0c7208b1e',14187863524,'acbdee94d7b223978843765935d552b2d259f236e285298ae94746495f4ce5fe')
r=json.loads(formal.read('composition.json'));lemma=json.loads(formal.read('result.json'))
assert r['source_sha256']==lemma['source_sha256']==sha
assert r['reference_sha256']=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
assert len(r['cases'])==2 and {(c['dw'],c['slots'])for c in r['cases']}=={(8,2),(4,1)}
assert all(c['passed']and c['returncode']==0 for c in r['cases'])
assert len(lemma['cases'])==6 and all(c['passed']for c in lemma['cases'])
assert {(c['dw'],c['slots'],c['mutation'])for c in lemma['cases']}=={(dw,slots,m)for dw,slots in [(8,2),(4,1)]for m in ['none','tlp','dllp']}
for name,h in lemma['outputs'].items():assert hashlib.sha256(formal.read(name)).hexdigest()==h
for dw,slots,count in [(8,2,9122),(4,1,3747)]:
 log=formal.read(f'dw{dw}-s{slots}-composition.log').decode();assert log.count('Equivalence successfully proven!')==2 and 'ERROR:'not in log
 assert re.search(r'Found '+str(count)+r' unproven \$equiv cells',log)
 for mutation in ('none','tlp','dllp'):
  key=f'dw{dw}-s{slots}-'+mutation;text=formal.read(key+'.log').decode()
  assert ('ERROR: Called with -verify and proof did fail!'if mutation!='none' else'Induction step proven: SUCCESS!')in text
traffic=archive(43778898014,'bfcc3273a276c5b8e9d01e37e742888aca88172f',14187469910,'3f398128f89b3c8e1a500dd55dfae66a47300afad7f57caa6bb0772187c8c251')
# Authenticate the exact compiled candidate against current source and switches.
compiled=''.join('`define '+f+'\n'for f in flags)+source.decode()+''.join('`undef '+f+'\n'for f in flags)
assert traffic.read('exact-mapped-eop/candidate.v').decode()==compiled
expected={'dw8_s2_c1_seed'+str(i)for i in range(1,5)}|{'dw8_s2_c0_seed5','dw8_s2_c0_seed6','dw4_s1_c0_seed7','dw4_s1_c1_seed8'}
logs={pathlib.PurePosixPath(n).stem:n for n in traffic.namelist()if n.startswith('exact-mapped-eop/')and n.endswith('.log')}
assert set(logs)==expected
for name,path in logs.items():
 log=traffic.read(path).decode();assert re.search(r'^RESULT PASS$',log,re.M)and 'cycles=300000'in log and 'mismatches=0 copy_mismatches=0'in log
negative=json.loads(traffic.read('exact-mapped-mutant/result.json'));assert negative['source_sha256']==sha and negative['returncode']!=0 and negative['detected']
mutant=compiled.replace('assign out_eop_o=select_dllp ? eop_dllp_q : eop_tlp_q;','assign out_eop_o=select_dllp ? eop_dllp_q : !eop_tlp_q;');assert mutant!=compiled
assert traffic.read('exact-mapped-mutant/candidate.v').decode()==mutant
assert any('MISMATCH'in traffic.read(n).decode()for n in traffic.namelist()if n.startswith('exact-mapped-mutant/')and n.endswith('.log'))
out=pathlib.Path('out');out.mkdir(exist_ok=True)
(out/'eop-flags-qualification.json').write_text(json.dumps(dict(source_sha256=sha,reference_sha256=r['reference_sha256'],formal=r,lemmas=lemma['cases'],traffic_cases=sorted(logs),cycles=2400000,mutation=negative,physical_accepted=False,scope='Compositional proof under initial reset/zero initialization, exact-switch traffic and actual wrong-EOP mutation. Not mapped boot or physical timing.'),indent=2))
