"""111 selectively delayed feedback branches after combined IO repair."""
import os,json,subprocess,zipfile,hashlib,stat,re
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get('GITHUB_ACTIONS')=='true'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'input-timing';OUT.mkdir()
prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
SOURCE=ROOT/'hw/soc/out/cloud-predecode-postcts';SOURCE.mkdir(parents=True)
def digest(b):return hashlib.sha256(b).hexdigest()
def api(s):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+s]))
r=api('actions/runs/43643048434');assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']=='db35595f13bc3eb63890086789b93e252fbb4cb6'
def archive(i,h,n):
 m=api('actions/artifacts/'+str(i));assert m['workflow_run']['id']==r['id'] and m['workflow_run']['head_sha']==r['head_sha'] and m['digest']=='sha256:'+h and not m['expired']
 p=OUT/n
 with p.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(i)+'/zip'],stdout=f,check=True)
 assert prior.sha(p)==h;return zipfile.ZipFile(p)
safe=archive(14133259949,'f508cef6faf940e32aea7ab50f8ac83e8ce158e2bd3789c86c46633c6ed29c9b','safe.zip')
native=archive(14133777129,'238cba66b6541bffa2407278ced7d453c64286bc5515a1d6e01939781f6f0c98','native.zip')
report=json.loads(safe.read('result.json'));assert report['sources_unchanged'] and report['returncode']==0 and not report['accepted']
assert report['repaired_odb_sha256']=='3f0dea28cbacdfb5c3fdaff22abc9191cc589437c9a2fda4740e7ba5063d87bd'
assert len(native.namelist())==len(set(native.namelist()))
assert {n for n in native.namelist()if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
for i in native.infolist():
 p=prior.relative(i.filename);assert not stat.S_ISLNK(i.external_attr>>16)
 if i.is_dir():continue
 b=native.read(i);expected=digest(safe.read('result.json'))if i.filename=='result.json'else report['outputs'][i.filename];assert digest(b)==expected
 q=SOURCE/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
state=json.loads((SOURCE/report['repaired_state']).read_text());odb=Path(state['odb']);assert prior.sha(odb)==report['repaired_odb_sha256'];state['metrics']={}
# Continue from the exact successful RX training ECO, not the older placement.
eco_run=api('actions/runs/43648980039');assert eco_run['status']=='completed'and eco_run['conclusion']=='success'and eco_run['head_sha']=='95929ee677c79d9bab52f47c28f684eedb91795a'
m=api('actions/artifacts/14135173417');h='31bfe99bd985d6edfd9246d21c511edf2d17f17371d091158bf9299c909f824b'
assert not m['expired']and m['workflow_run']['id']==43648980039 and m['workflow_run']['head_sha']==eco_run['head_sha']and m['digest']=='sha256:'+h
p=OUT/'baseline.zip'
with p.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14135173417/zip'],stdout=f,check=True)
assert prior.sha(p)==h;z=zipfile.ZipFile(p);assert len(z.namelist())==len(set(z.namelist()))
baseline=OUT/'baseline-eco'
for i in z.infolist():
 q=baseline/prior.relative(i.filename);assert not stat.S_ISLNK(i.external_attr>>16)
 if i.is_dir():continue
 q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(i))
state=json.loads((baseline/'1-nssoc-trainingholdeco/state_out.json').read_text())
old_prefix=str(OUT/'run')+'/'
def relocate(v):
 if isinstance(v,str)and v.startswith(old_prefix):return str(baseline/v[len(old_prefix):])
 if isinstance(v,dict):return {k:relocate(x)for k,x in v.items()}
 if isinstance(v,list):return [relocate(x)for x in v]
 return v
state=relocate(state);state['metrics']={};odb=Path(state['odb'])
assert prior.sha(odb)=='de8647caef5c3d38121edeb9d102f53e5406f77371ca161d254459aad58075ca'
initial=OUT/'initial.json';initial.write_text(json.dumps(state))
config=SOURCE/'trial-config.json';cfg=json.loads(config.read_text());assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5.0
app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
# Verify the exact native delay model is a two-port identity buffer.
import base64
model=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v?ref=c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c']))
raw=base64.b64decode(model['content']);assert digest(raw)=='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
module=re.search(r'module sg13g2_dlygate4sd3_1\b.*?endmodule',raw.decode(),re.S)[0]
assert re.search(r'buf\s*\(X, A\);',module) and 'output X;' in module and 'input A;' in module
protected={str(p):prior.sha(p)for p in [odb,config,prior.SOURCE/'prepared/physical.sdc',ROOT/'hw/soc/pnr/input_timing_flow.py',Path(__file__)]}
cmd=[str(app),'python',str(ROOT/'hw/soc/pnr/input_timing_flow.py'),'--flow','InputTiming','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(config)]
(OUT/'run').mkdir()
with (OUT/'native.log').open('w')as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
if code:print((OUT/'native.log').read_text()[-6000:])
assert code==0
assert all(prior.sha(p)==h for p,h in protected.items())
rows={}
for p in (OUT/'run').glob('*/io-*.rpt'):
 text=p.read_text();v=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',text);assert v
 rows[str(p.relative_to(OUT))]={'worst_slack_ns':min(map(float,v)),'reported_paths':len(v),'sha256':prior.sha(p)}
assert len(rows)==906
states=list((OUT/'run').glob('*-nssoc-trainingholdeco/state_out.json'));assert len(states)==1
eco_state=json.loads(states[0].read_text());eco_odb=Path(eco_state['odb']);assert eco_odb.is_file()
assert len(rows)==906
input_closed=all(v['worst_slack_ns']>=0.05 for v in rows.values())
(OUT/'result.json').write_text(json.dumps({'source_run':eco_run['id'],'source_head':eco_run['head_sha'],'source_odb_sha256':prior.sha(odb),'source_unchanged':True,'222_delay_cells_inserted':True,'native_delay_is_identity_buffer':True,'all_io_and_feedback_setup_hold_margin_50ps_passed':input_closed,'candidate_odb_sha256':prior.sha(eco_odb),'reports':rows,'accepted':False,'scope':'111 feedback branches with two delays each; previous40IOs and111through-pins remeasured; original incidence protected, fresh placement RC, no routed or full-chip signoff.'},indent=2))
