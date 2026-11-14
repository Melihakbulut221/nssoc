# SPDX-License-Identifier: Apache-2.0
"""Cloud-only four-diode legalization screen; no antenna/timing acceptance."""
import pathlib,subprocess,hashlib,zipfile,tarfile,io,json,time
P=pathlib.Path
out=P('out');native=out/'native';derived=out/'derived'
native.mkdir(parents=True);derived.mkdir()
r={'accepted':False,'routed':False,'manufacturing_approval':False,'parent_run':43590389460,'targets':['ANTENNA_482','ANTENNA_1342','ANTENNA_457','ANTENNA_458'],'max_displacement':[1000,1000],'scope':'Only four target diodes movable. All other instances locked during placement and location/orientation invariant checked; original placement statuses restored afterward. check_placement required. Routing, antenna, timing and connectivity acceptance still pending.'}
code=2
try:
 blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='5a745c683ff7e1adec765b3ef73ffb13ad21900f6e7567f5d7e9cdc663144176'
 z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['route-incomplete.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('route-incomplete.tgz')),mode='r:gz') as t:
  for filename in ['diode-diagnostic.odb','before-status.tsv','after-status.tsv']:
   hits=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/1-nssoc-resumeantennadrt/'+filename)];assert len(hits)==1,(filename,len(hits))
   (native/filename).write_bytes(t.extractfile(hits[0]).read())
 r['input_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in native.iterdir()}
 start=time.monotonic()
 with (native/'legalize.log').open('w') as f:proc=subprocess.run(['/mnt/s/librelane.AppImage','openroad','-exit','scripts/diagnose_four_diode_legalization.tcl'],stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 r['elapsed_seconds']=time.monotonic()-start;r['returncode']=proc.returncode
 lines=(native/'legalize.log').read_text(errors='replace').splitlines()
 r['markers']=[l for l in lines if l.startswith('NSSOC_')]
 r['errors']=[l for l in lines if '[ERROR ' in l or '[WARNING ' in l or l.startswith('Error:')]
 r['placement_only_passed']=proc.returncode==0 and 'NSSOC_PLACEMENT_CHECK_OK' in lines and 'NSSOC_PLACEMENT_ONLY_DONE_NOT_ROUTED' in lines
 r['status']='PLACEMENT_SCREEN_COMPLETE';code=0
except Exception as e:r['status']='INCOMPLETE_DIAGNOSIS';r['error']=type(e).__name__+': '+str(e)
finally:
 r['native_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in native.iterdir() if p.is_file()}
 (derived/'placement-result.json').write_text(json.dumps(r,indent=2))
raise SystemExit(code)
