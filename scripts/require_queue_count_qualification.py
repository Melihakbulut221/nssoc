"""Source-bound queue count composition and exact-switch traffic admission."""
import os,pathlib,json,subprocess,hashlib,zipfile,io,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_bytes();sha=hashlib.sha256(source).hexdigest()
assert sha=='ea123da56f450bdde9183b43083ca6c8df3086494feff54be7bf9a201ecbc391'
flags=['SOC_PCIE_RX_COUNT_FLAGS','SOC_PCIE_RX_READ2','SOC_PCIE_RESET_COPIES','SOC_PCIE_RX_COMMIT_COPIES','SOC_PCIE_RX_CURSOR_LOCAL_RESET','SOC_PCIE_RX_LOCAL_LANE_NEXT','SOC_PCIE_RX_DLLP_LAST_COMPARE']
assert all(os.environ.get(f)=='1'for f in flags)
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def archive(run,head,aid,digest):
 r=api('actions/runs/'+str(run));assert r['head_sha']==head and r['run_attempt']==1 and r['conclusion']=='success'
 m=api('actions/artifacts/'+str(aid));assert not m['expired']and m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()));return z
formal=archive(43770004136,'5b9156fd971eae72bb3365bc9e4f4acc2570db24',14183687428,'ca4e5bc48384cc8e92525e917c40f35a02f55cb4e779d3a3d9cf27d2c6ed3598')
r=json.loads(formal.read('composition.json'));lemma=json.loads(formal.read('result.json'))
assert r['source_sha256']==lemma['source_sha256']==sha
assert r['reference_sha256']=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
assert len(r['cases'])==2 and {(c['dw'],c['slots'])for c in r['cases']}=={(8,2),(4,1)}
assert all(c['passed']and c['returncode']==0 for c in r['cases'])
assert len(lemma['cases'])==4 and all(c['passed']for c in lemma['cases'])
assert {(c['dw'],c['slots'],c['mutation'])for c in lemma['cases']}=={(8,2,False),(8,2,True),(4,1,False),(4,1,True)}
for name,h in lemma['outputs'].items():assert hashlib.sha256(formal.read(name)).hexdigest()==h
for dw,slots,count in [(8,2,9155),(4,1,3756)]:
 log=formal.read(f'dw{dw}-s{slots}-composition.log').decode();assert log.count('Equivalence successfully proven!')==2 and 'ERROR:'not in log
 assert re.search(r'Found '+str(count)+r' unproven \$equiv cells',log)
 for mutation in (False,True):
  key=f'dw{dw}-s{slots}-'+('wrong-empty'if mutation else'positive');text=formal.read(key+'.log').decode()
  assert ('ERROR: Called with -verify and proof did fail!'if mutation else'Induction step proven: SUCCESS!')in text
traffic=archive(43770275976,'4f381f31caf8bc761301ac98012837701890b3c7',14184109103,'6c6ba4912c724c1b6803a7b2f4cc07cd5ffb8d8b60c9d5ca6b5cdfad1f1bf8ad')
# Authenticate the exact compiled candidate against current source and switches.
compiled=''.join('`define '+f+'\n'for f in flags)+source.decode()+''.join('`undef '+f+'\n'for f in flags)
assert traffic.read('exact-mapped-count/candidate.v').decode()==compiled
expected={'dw8_s2_c1_seed'+str(i)for i in range(1,5)}|{'dw8_s2_c0_seed5','dw8_s2_c0_seed6','dw4_s1_c0_seed7','dw4_s1_c1_seed8'}
logs={pathlib.PurePosixPath(n).stem:n for n in traffic.namelist()if n.startswith('exact-mapped-count/')and n.endswith('.log')}
assert set(logs)==expected
for name,path in logs.items():
 log=traffic.read(path).decode();assert re.search(r'^RESULT PASS$',log,re.M)and 'cycles=300000'in log and 'mismatches=0 copy_mismatches=0'in log
negative=json.loads(traffic.read('exact-mapped-mutant/result.json'));assert negative['source_sha256']==sha and negative['returncode']!=0 and negative['detected']
mutant=compiled.replace('count_empty_q<=count_next==0;','count_empty_q<=count_next!=0;');assert mutant!=compiled
assert traffic.read('exact-mapped-mutant/candidate.v').decode()==mutant
assert any('RX_COUNT_FLAGS_MISMATCH'in traffic.read(n).decode()for n in traffic.namelist()if n.startswith('exact-mapped-mutant/')and n.endswith('.log'))
out=pathlib.Path('out');out.mkdir(exist_ok=True)
(out/'queue-count-qualification.json').write_text(json.dumps(dict(source_sha256=sha,reference_sha256=r['reference_sha256'],formal=r,lemmas=lemma['cases'],traffic_cases=sorted(logs),cycles=2400000,mutation=negative,physical_accepted=False,scope='Compositional proof under initial reset/zero initialization, exact-switch traffic and actual wrong-empty mutation. Not mapped boot or physical timing.'),indent=2))
