"""Read-only exact CRC postCTS input timing diagnosis; no timing waiver or ECO."""
import os,json,subprocess,zipfile,hashlib,stat,re
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get('GITHUB_ACTIONS')=='true'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'input-timing';OUT.mkdir()
prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
SOURCE=ROOT/'hw/soc/out/cloud-predecode-postcts';SOURCE.mkdir(parents=True)
def digest(b):return hashlib.sha256(b).hexdigest()
def api(s):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+s]))
r=api('actions/runs/43639975405');assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']=='b6dfa2a1429d837d7f4d5e479897cf95dac06f87'
def archive(i,h,n):
 m=api('actions/artifacts/'+str(i));assert m['workflow_run']['id']==r['id'] and m['workflow_run']['head_sha']==r['head_sha'] and m['digest']=='sha256:'+h and not m['expired']
 p=OUT/n
 with p.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(i)+'/zip'],stdout=f,check=True)
 assert prior.sha(p)==h;return zipfile.ZipFile(p)
safe=archive(14132078627,'0ed233f5323f5cd384752bb90205d8ecfe989da42d936701151ea37183815c01','safe.zip')
native=archive(14131978922,'f6dff8733fb34fdc4d9e5bb58a73a61390c8341ecaf7edbd0980a0cbdb4a8021','native.zip')
report=json.loads(safe.read('result.json'));assert report['sources_unchanged'] and report['returncode']==0 and not report['accepted']
assert report['repaired_odb_sha256']=='568dfa2f110b6813d316087b6249340bedd4c831b95bf13d6224014b49c6afb1'
assert len(native.namelist())==len(set(native.namelist()))
assert {n for n in native.namelist()if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
for i in native.infolist():
 p=prior.relative(i.filename);assert not stat.S_ISLNK(i.external_attr>>16)
 if i.is_dir():continue
 b=native.read(i);expected=digest(safe.read('result.json'))if i.filename=='result.json'else report['outputs'][i.filename];assert digest(b)==expected
 q=SOURCE/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
state=json.loads((SOURCE/report['repaired_state']).read_text());odb=Path(state['odb']);assert prior.sha(odb)==report['repaired_odb_sha256'];state['metrics']={}
initial=OUT/'initial.json';initial.write_text(json.dumps(state))
config=SOURCE/'trial-config.json';cfg=json.loads(config.read_text());assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5.0
app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
protected={str(p):prior.sha(p)for p in [odb,config,prior.SOURCE/'prepared/physical.sdc',ROOT/'hw/soc/pnr/input_timing_flow.py',Path(__file__)]}
cmd=[str(app),'python',str(ROOT/'hw/soc/pnr/input_timing_flow.py'),'--flow','InputTiming','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(config)]
(OUT/'run').mkdir()
with (OUT/'native.log').open('w')as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
if code:print((OUT/'native.log').read_text()[-6000:])
assert code==0
assert all(prior.sha(p)==h for p,h in protected.items())
rows={}
for p in (OUT/'run').glob('*/training-*.rpt'):
 text=p.read_text();v=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',text);assert v
 rows[str(p.relative_to(OUT))]={'worst_slack_ns':min(map(float,v)),'reported_paths':len(v),'sha256':prior.sha(p)}
assert len(rows)==6
(OUT/'result.json').write_text(json.dumps({'source_run':r['id'],'source_head':r['head_sha'],'source_odb_sha256':report['repaired_odb_sha256'],'source_unchanged':True,'reports':rows,'accepted':False,'scope':'Exact CRC repaired placement-estimated input setup/hold diagnosis only; no ECO, no routed or full-chip signoff.'},indent=2))
