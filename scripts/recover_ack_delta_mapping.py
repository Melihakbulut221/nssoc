"""Recover completed ACK synthesis from an authenticated failed post-check run."""
import hashlib,io,json,os,subprocess,tarfile,zipfile
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=Path.cwd()
prefix='hw/soc/out/corrpre-pcie-mbist-native-boot'
dest=root/prefix
assert not dest.exists()
repo='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',repo+p]))
run=api('actions/runs/43809143447')
assert run['head_sha']=='bfdc8d57daacba32ea4238b73678a3da19c8e82a' and run['run_attempt']==1
assert run['status']=='completed' and run['conclusion']=='failure'
aid=14200723476
digest='e29ec35ecb7e4e778d586fb5facc3c0c8202818ec5ccc8325ea992e4ad18e433'
meta=api('actions/artifacts/'+str(aid))
assert not meta['expired'] and meta['digest']=='sha256:'+digest
assert meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
blob=subprocess.check_output(['gh','api',repo+'actions/artifacts/'+str(aid)+'/zip'])
assert hashlib.sha256(blob).hexdigest()==digest
archive=zipfile.ZipFile(io.BytesIO(blob))
assert archive.namelist()==['build.tgz']
tarbytes=archive.read('build.tgz')
tar=tarfile.open(fileobj=io.BytesIO(tarbytes),mode='r:gz')
members=tar.getmembers()
assert len({m.name for m in members})==len(members)
for m in members:
 p=Path(m.name)
 assert not p.is_absolute() and '..' not in p.parts and p.is_relative_to(prefix)
 assert m.isfile() or m.isdir(),m.name
 assert (root/p).resolve().is_relative_to(dest)
checks={
 'synthesis/soc_top.mapped.json':'e6b2b44049da71b74e9dd2adb30a551f7bb0883072f21d83e9bac93b70bc2ecd',
 'synthesis/soc_top_syn.ys':'22edd0da2983cdd3899516e1a4edf31c629b05608a8b40cb882ef589988cee34',
 'rtl-driver.log':'03fa3f2f5509b782ad0452b9aeac54df11d799b2a6ff49794b0e7e8340fc56cd',
 'synthesis-driver.log':'a0eb5b01426917a3553298efb8c0d66bb0646b3955e77a4ab5c64800249c6257'}
for name,h in checks.items():
 assert hashlib.sha256(tar.extractfile(prefix+'/'+name).read()).hexdigest()==h
rtl=tar.extractfile(prefix+'/rtl-driver.log').read().decode()
assert 'checks run: 0x0000001c  fail mask: 0x00000000' in rtl
assert 'RESULT PASS' in rtl and '[TB] PASS' in rtl
assert '[TB] watchdog: stage1 1, stage2 0, stage3 0' in rtl
before={}
for m in members:
 target=root/m.name
 if m.isdir():target.mkdir(parents=True,exist_ok=True)
 else:
  target.parent.mkdir(parents=True,exist_ok=True)
  data=tar.extractfile(m).read();target.write_bytes(data)
  before[m.name]=hashlib.sha256(data).hexdigest()
subprocess.run(['python3','scripts/check_predecode_mainchip_mapping.py',str(dest)],check=True)
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in before.items())
mapped=json.loads(Path('out/mapping.json').read_text())
assert mapped['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']=='0833d4a4126272253fd0cd35e7eca118c163c435a803ef32930f61f16948f554'
assert mapped['outputs']['synthesis/soc_top.mapped.json']==checks['synthesis/soc_top.mapped.json']
mapped['recovered_build']=dict(run=run['id'],source_head=run['head_sha'],artifact=aid,archive_sha256=digest,tar_sha256=hashlib.sha256(tarbytes).hexdigest(),all_restored_files_unchanged=True,source_files=before,scope='Original RTL boot and synthesis succeeded; stale baseline RTL hash rejected final mapping check. Revalidate exact preserved output, not a new synthesis or gate boot.')
Path('out/mapping.json').write_text(json.dumps(mapped,indent=2))
