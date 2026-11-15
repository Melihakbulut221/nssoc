import subprocess,json,pathlib,zipfile,tarfile,hashlib,base64,os
P='repos/Melihakbulut221/nssoc/';out=pathlib.Path('out');out.mkdir(exist_ok=True)
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
head='a233897f18e3eae27b130cdf3cf4d444802f3f01';run=api('actions/runs/43772035360');assert run['head_sha']==head and run['run_attempt']==1 and run['conclusion']=='failure'
assert os.environ['GITHUB_ACTIONS']=='true'
protected=['hw/soc/rtl/pcie/soc_pcie_rx_credit.v','hw/soc/rtl/pcie/soc_pcie_credit_tx.v','hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','hw/soc/rtl/pcie/soc_pcie_replay_tx.v','hw/soc/flow/syn_soc_top.sh','hw/soc/flow/sim_soc.sh','scripts/prepare_predecode_mainchip.sh']
for f in protected:assert pathlib.Path(f).read_bytes()==base64.b64decode(api('contents/'+f+'?ref='+head)['content'])
def archive(aid,digest,name):
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==43772035360 and m['workflow_run']['head_sha']==head and not m['expired']and m['digest']=='sha256:'+digest
 p=pathlib.Path(name)
 with p.open('wb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
 return zipfile.ZipFile(p)
z=archive(14185353889,'b9e64f1c5f4934483d7dda8495b9462ce952b6e0acc4769e6ac789d25b48028b','source.zip');assert z.namelist()==['build.tgz'];z.extract('build.tgz')
root=pathlib.Path('hw/soc/out/corrpre-pcie-mbist-native-boot');before={}
with tarfile.open('build.tgz')as t:
 for member in t:
  p=pathlib.Path(member.name);assert not p.is_absolute()and '..'not in p.parts and (p==root or root in p.parents)
  if member.isdir():continue
  assert member.isfile()and not p.exists();data=t.extractfile(member).read();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);before[str(p.relative_to(root))]=hashlib.sha256(data).hexdigest()
assert len(before)==63
assert before['synthesis/soc_top.mapped.json']=='5edb96033cc42e68a36f9be71ba7efd3b68f8c03fb4996f3dd9f170a4a9a66c7'
log=(root/'rtl/sim.log').read_text();assert 'RESULT PASS'in log and '[TB] PASS'in log and 'fail mask: 0x00000000'in log
z=archive(14185855237,'4fb54951f7855ea85932c931f15cc242d70a761c4ea096e03928bedb5450f6d7','qualification.zip')
expected={'credit-crc-qualification.json','rx-qualification-gate.json','ack-prefix-qualification-gate.json','queue-count-qualification.json'};assert set(z.namelist())==expected
for n in expected:(out/n).write_bytes(z.read(n))
subprocess.run(['python3','scripts/check_predecode_mainchip_mapping.py',str(root)],check=True)
r=json.loads((out/'mapping.json').read_text());after=r['outputs'];changed={n for n in before if before[n]!=after[n]};assert changed<={'replay-origin.ys','replay-origin.log','replay-origin.lowered.json'}
r['native_producer']=dict(run=43772035360,source_head=head,original_run_conclusion='failure',failure_scope='Original mapping checker expected aliases removed by reset polarity optimization; synthesis and RTL boot retained and revalidated.',native_artifact=14185353889,native_archive_sha256='b9e64f1c5f4934483d7dda8495b9462ce952b6e0acc4769e6ac789d25b48028b',before_hashes=before,rechecked_outputs=sorted(changed),resynthesized=False)
(out/'mapping.json').write_text(json.dumps(r,indent=2))
pathlib.Path('native').mkdir();subprocess.run(['tar','-czf','native/build.tgz',str(root)],check=True)
