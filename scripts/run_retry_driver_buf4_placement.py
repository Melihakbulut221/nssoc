# SPDX-License-Identifier: Apache-2.0
"""Cloud-only exact retry write-enable buffer placement hypothesis."""
import os,pathlib,hashlib,zipfile,tarfile,subprocess,json,time,shutil
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path;out=P('out');native=out/'native';derived=out/'derived';native.mkdir(parents=True);derived.mkdir()
def sha(p):
 digest=hashlib.sha256()
 with P(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()
r={'status':'RUNNING','accepted':False,'final_timing_complete':False,'manufacturing_approval':False,'source_artifact':14112212387,'target':'place31551','old_master':'sg13g2_buf_1','new_master':'sg13g2_buf_4','scope':'One positive buffer upsize and legal placement only. All other cell geometry/status, every pin connection and top port remain invariant. Old routing invalid after master/pin changes; new routing, RC, all-corner STA, DRC, antenna and LVS are mandatory.'}
code=2
try:
 assert sha('native.zip')=='be3f5242a66dbbc81708b43f83d707c58ccc07d944bc8fe8fc3c11a745013228'
 with zipfile.ZipFile('native.zip') as z:
  assert z.namelist()==['four-diode-native.tgz']
  with z.open(z.namelist()[0]) as packed,tarfile.open(fileobj=packed,mode='r|gz') as t:
   found=0
   for m in t:
    if m.name=='native/four-diode-legalized.odb':
     assert m.isfile();found+=1
     with t.extractfile(m) as src,(native/'source.odb').open('wb') as dst:shutil.copyfileobj(src,dst)
   assert found==1
 assert sha(native/'source.odb')=='c9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959'
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
 start=time.monotonic()
 for label,args in [('prepare',['-python','scripts/prepare_retry_driver_buf4.py']),('placement',['scripts/retry_driver_buf4_placement.tcl']),('verify',['-python','scripts/verify_retry_driver_buf4.py'])]:
  with (native/(label+'.log')).open('w') as log:
   proc=subprocess.run(['/mnt/s/librelane.AppImage','openroad','-exit']+args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  lines=(native/(label+'.log')).read_text(errors='replace').splitlines();r[label]={'returncode':proc.returncode,'tail':lines[-50:]}
  assert proc.returncode==0,(label,proc.returncode)
 r['elapsed_seconds']=time.monotonic()-start
 proof=json.loads((derived/'native-proof.json').read_text());assert proof['invariants_passed']
 assert 'NSSOC_PLACEMENT_CHECK_OK' in (native/'placement.log').read_text().splitlines()
 r.update(status='ONE_BUFFER_LEGAL_PLACEMENT_PASSED_NOT_ROUTED',placement_only_passed=True,proof=proof);code=0
except Exception as e:r.update(status='FAILED_OR_INCOMPLETE',error=repr(e))
finally:
 r['native_hashes']={p.name:sha(p) for p in native.iterdir() if p.is_file()}
 (derived/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
raise SystemExit(code)
