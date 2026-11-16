import os,subprocess,json,hashlib,zipfile,io,pathlib,stat
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path;out=P('global-guide-audit');out.mkdir()
repo='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',repo+s]))
def sha(b):return hashlib.sha256(b).hexdigest()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False)
try:
 run=api('actions/runs/43793553628');assert run['head_sha']=='fc1b53d5641b2ca885ac3fac661984c366352e06' and run['conclusion']=='failure' and run['run_attempt']==1
 aid=14194108006;h='c6c6f10140841c0cc6a115853c17ca823b30a2c3443b6753a68dd64de7d9efe1'
 meta=api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 data=subprocess.check_output(['gh','api',repo+'actions/artifacts/'+str(aid)+'/zip']);assert sha(data)==h
 z=zipfile.ZipFile(io.BytesIO(data));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['error']=='AssertionError({})'
 assert 'assert len(guides)==1,guides' in report['traceback']
 selected=[n for n in z.namelist() if n.endswith('/soc_top.odb') and 'validatedglobalrouting' in n];assert len(selected)==1
 n=selected[0];db=z.read(n);assert sha(db)==report['outputs'][n];odb=out/'global.odb';odb.write_bytes(db)
 state_name=n.rsplit('/',1)[0]+'/state_out.json';state_bytes=z.read(state_name);assert sha(state_bytes)==report['outputs'][state_name]
 state=json.loads(state_bytes);assert state['odb'].endswith('/'+n)
 baseline_name=n.rsplit('/',1)[0]+'/baseline-reproduction.json';baseline_bytes=z.read(baseline_name);assert sha(baseline_bytes)==report['outputs'][baseline_name]
 baseline=json.loads(baseline_bytes);assert baseline['measured_baseline_matches'] and baseline['source_run']==43791735845
 r.update(parent_run=run['id'],parent_head=run['head_sha'],native_artifact=aid,native_sha256=h,odb_sha256=sha(db),baseline_reproduction=baseline,scope='Read-only native OpenDB guide audit of failed wrapper output. No routing rerun, no detailed routing or timing acceptance.')
 app=P(os.environ['CLOUD_APPIMAGE']);import sys;sys.path.insert(0,'scripts');import cloud_predecode_postcts as prior;prior.verify(app,'x86_64')
 env=dict(os.environ,NSSOC_AUDIT_ODB=str(odb.resolve()),NSSOC_AUDIT_OUT=str(out.resolve()))
 with (out/'native.log').open('w') as log:r['returncode']=subprocess.call([str(app),'openroad','-exit','-python','scripts/inspect_global_guides_native.py'],env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0
 assert sha(odb.read_bytes())==r['odb_sha256']
 r['guide_inventory']=json.loads((out/'guide-inventory.json').read_text());assert r['guide_inventory']['guide_count']>0
 r['audit_passed']=True
except BaseException as e:r['error']=repr(e);raise
finally:
 r['outputs']={p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name not in ('global.odb','result.json')}
 (out/'result.json').write_text(json.dumps(r,indent=2))
