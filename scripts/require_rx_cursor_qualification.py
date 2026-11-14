"""Require exact completed real RX proof and traffic evidence before CAD."""
import subprocess,json,hashlib,zipfile,io,pathlib,os,time
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_bytes();digest=hashlib.sha256(source).hexdigest()
assert digest=='6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0'
out=pathlib.Path('out');out.mkdir(exist_ok=True);results=[]
for run,head,name,kind,count in [(43646311455,'d93e575991c560ec910925eee630f6555af26d81','rx-cursor-formal-43646311455','formal',4),(43646430563,'a5084f973055411c1891033fadf040b9055c9dfd','rx-cursor-traffic-43646430563','traffic',16)]:
 r=api(f'actions/runs/{run}');assert r['head_sha']==head
 # Select exact immutable producer job, not the first run's unrelated failed traffic job.
 deadline=time.monotonic()+2700
 while True:
  jobs=api(f'actions/runs/{run}/jobs')['jobs'];selected=[j for j in jobs if j['name']==f'qualify ({kind})'];assert len(selected)==1
  if selected[0]['status']=='completed':break
  assert selected[0]['id']==({'formal':132604800997,'traffic':132605179099}[kind])
  assert time.monotonic()<deadline,('qualification still pending; no CAD started',run)
  print('Waiting for exact qualification job',run,kind,selected[0]['status'],flush=True)
  time.sleep(45)
 assert selected[0]['status']=='completed'and selected[0]['conclusion']=='success',('qualification not completed successfully',run,selected[0]['status'],selected[0]['conclusion'])
 artifacts=api(f'actions/runs/{run}/artifacts')['artifacts'];selected_artifacts=[x for x in artifacts if x['name']==name and not x['expired']];assert len(selected_artifacts)==1
 art=selected_artifacts[0];assert art['workflow_run']['head_sha']==head
 b=subprocess.check_output(['gh','api',P+f"actions/artifacts/{art['id']}/zip"]);sha=hashlib.sha256(b).hexdigest();assert art['digest']=='sha256:'+sha
 assert art['workflow_run']['id']==run
 assert selected[0]['id']==({'formal':132604800997,'traffic':132605179099}[kind])
 z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist()if n.endswith('result.json')];assert len(names)==1
 result=json.loads(z.read(names[0]));assert result['source_sha256']==digest and len(result['cases'])==count
 assert len(z.namelist())==len(set(z.namelist()))
 for case in result['cases']:
  if kind=='formal':
   suffix=f"dw{case['dw']}-s{case['slots']}-"+('mutant'if case['mutation']else'positive')+'.log'
  else:
   suffix=('mutant/'if case['mutation']else'positive/')+case['case']+'.log'
  matches=[n for n in z.namelist()if n==suffix or n.endswith('/'+suffix)]
  assert len(matches)==1 and hashlib.sha256(z.read(matches[0])).hexdigest()==case['log_sha256']
 assert sum(c['mutation']for c in result['cases'])==count//2
 assert all(c['mutation_rejected']if c['mutation']else c['proven'if kind=='formal'else'passed']for c in result['cases'])
 assert result['status']==('TWO_FULL_MODULE_PROOFS_AND_TWO_MUTATIONS_COMPLETE_NOT_PHYSICAL_SIGNOFF'if kind=='formal'else'EIGHT_TRAFFIC_PASSES_AND_EIGHT_MUTATION_REJECTIONS_NOT_SIGNOFF')
 results.append({'run':run,'source_head':head,'job_id':selected[0]['id'],'artifact_id':art['id'],'artifact_sha256':sha,'result':result})
(out/'rx-qualification-gate.json').write_text(json.dumps({'source_sha256':digest,'qualified_inputs':results,'physical_acceptance':False},indent=2))
