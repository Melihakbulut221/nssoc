import subprocess,json,hashlib,zipfile,io,pathlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
p='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',p+s]))
r=api('actions/runs/43801732196');assert r['head_sha']=='9abe18746e8f6ece5ccc74d9c22f14ca31391a97' and r['conclusion']=='failure' and r['run_attempt']==1
m=api('actions/artifacts/14196806624');h='5dab6cb3f41ec9709ef519aa3bd7ca73ef0eb40f40e70c9b71c1b085995f08e4'
assert not m['expired'] and m['digest']=='sha256:'+h and m['workflow_run']['id']==r['id'] and m['workflow_run']['head_sha']==r['head_sha']
b=subprocess.check_output(['gh','api',p+'actions/artifacts/14196806624/zip']);assert hashlib.sha256(b).hexdigest()==h
q=json.loads(zipfile.ZipFile(io.BytesIO(b)).read('clock-composition-qualification/result.json'))
assert not q['passed'] and q['sources_unchanged'] and q['derived_sha256']=='45b335d8e543ab7b70afa0d269e6b59b08fd85227420dfe20f4255862c4c7a34'
assert len(q['cases'])==7
for c in q['cases']:
 assert c['trace_rows']==513
 assert c['ideal_mismatch_count']==(495 if c['kind']in ['iverilog-original','iverilog-derived-disabled']else 0)
path=pathlib.Path('out/nba-diagnostic-scope.json');path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(dict(source_head=os.environ['GITHUB_SHA'],native_model_equivalent=False,derived_ideal_composition_passed=True,source_run=r['id'],artifact_sha256=h,full_phy_accepted=False,scope='Explicit supplementary NBA functional experiment. Native composition disagrees; no native/SDF acceptance and no proof that previous whole-chip failure was solely a model issue.'),indent=2))
