"""Read-only passive resistance comparison; no electrical acceptance."""
import os,pathlib,json,subprocess,zipfile,hashlib
import cdr_shared_resistance as measure
assert os.environ.get('GITHUB_ACTIONS')=='true'
ROOT=pathlib.Path.cwd();OUT=ROOT/'resistance-comparison';OUT.mkdir(exist_ok=False)
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def digest(p):
 with pathlib.Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
specs=[
 dict(label='before',run=43655950942,head='ae914da1b8791477927d34ac8c8b50c060d2921a',id=14138785042,sha256='dbbaaa2f8d2dfeb5267bc08165541dd2587d74c9eb34f6010183513bd5ab2ae8'),
 dict(label='after',run=43681301520,head='a81e8c3d4f38a9f836e710dce22085e6de39b97c',id=14148810524,sha256='ee54cfd52b54b7ce963449a839280b0f31a68ddb152aa2b95dee061cd5f6434d')]
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,full_phy_accepted=False,inputs=specs)
try:
 data={}
 for spec in specs:
  run=api('actions/runs/'+str(spec['run']));assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==spec['head']and run['run_attempt']==1
  meta=api('actions/artifacts/'+str(spec['id']))
  assert not meta['expired']and meta['workflow_run']['id']==spec['run']and meta['workflow_run']['head_sha']==spec['head']and meta['digest']=='sha256:'+spec['sha256']
  p=ROOT/(spec['label']+'.zip')
  with p.open('xb')as f:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(spec['id'])+'/zip'],stdout=f,check=True)
  assert digest(p)==spec['sha256']
  with zipfile.ZipFile(p)as z:
   prefix='mos650-metal-rc/native/mim-precise/wire/'
   text=z.read(prefix+'rc03/wires.spice').decode();anchors=json.loads(z.read(prefix+'anchors08.json'))
   report=json.loads(z.read('mos650-metal-rc/derived/precise-mim-result.json'))
   assert hashlib.sha256(text.encode()).hexdigest()==report['result']['native_spice']['sha256']
   data[spec['label']]=(text,anchors)
 r['measurement']=measure.compare(*data['before'],*data['after']);r['passed']=True
except BaseException as e:r['error']=repr(e);raise
finally:
 r['methods']={f:digest(ROOT/'scripts'/f)for f in ['compare_shared_resistance.py','cdr_shared_resistance.py','cdr_mos650_spice_syntax.py']}
 (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
