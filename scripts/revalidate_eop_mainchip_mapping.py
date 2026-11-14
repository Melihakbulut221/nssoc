import json,subprocess,hashlib,zipfile,tarfile,io,os
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def blob(aid,digest,run,head):
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest and not m['expired']
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 return zipfile.ZipFile(io.BytesIO(b))
original='bdd7cc588490425ff98c4718ea8986ecc06a128a'
r=api('actions/runs/43630345267');assert r['status']=='completed' and r['head_sha']==original
z=blob(14128109532,'35beed7b520d53ca66bb19af49c8c9a470aa92f5ad5763d6e7704f1d570f911b',43631823524,'638a04f294270b7970b02976bdf76eb4492d255d');diag=json.loads(z.read('mapping-diagnosis.json'));assert diag['source_head']==original and len(diag['files'])==60
z=blob(14128012721,'d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570',43630345267,original)
root=Path('hw/soc/out/corrpre-pcie-mbist-native-boot');assert not root.exists();seen=set()
with tarfile.open(fileobj=io.BytesIO(z.read('build.tgz')),mode='r:gz') as t:
 for m in t:
  p=Path(m.name);assert not p.is_absolute() and '..'not in p.parts and (p==root or root in p.parents)
  if m.isdir():continue
  assert m.isfile() and m.name not in seen;seen.add(m.name)
  b=t.extractfile(m).read();assert hashlib.sha256(b).hexdigest()==diag['files'][m.name]
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
assert seen==set(diag['files'])
assert 'checks run: 0x0000001c  fail mask: 0x00000000' in (root/'rtl-driver.log').read_text() and '== soc: PASS' in (root/'rtl-driver.log').read_text()
assert 'End of script.' in (root/'synthesis/syn.log').read_text()
env=dict(os.environ);env['GITHUB_SHA']=original
subprocess.run(['python3','scripts/check_predecode_mainchip_mapping.py',str(root)],env=env,check=True)
p=Path('out/mapping.json');report=json.loads(p.read_text());assert report['source_head']==original and len(report['cached_eop_register'])==1
report.update(validation_run=int(os.environ['GITHUB_RUN_ID']),validation_head=os.environ['GITHUB_SHA'],original_producer_run=43630345267,original_producer_conclusion=r['conclusion'],native_artifact=14128012721,native_archive_sha256='d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570',validated_preserved_source_without_resynthesis=True)
p.write_text(json.dumps(report,indent=2))
