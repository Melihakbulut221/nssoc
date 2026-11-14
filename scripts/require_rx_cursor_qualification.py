"""Require exact completed real RX proof and traffic evidence before CAD."""
import subprocess,json,hashlib,zipfile,io,pathlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_bytes();digest=hashlib.sha256(source).hexdigest()
assert digest=='c16d14cb42d27d261ec7aca5a303f9c3b63e24da6ce651b1a504fe3e56f658ec'
out=pathlib.Path('out');out.mkdir(exist_ok=True);results=[]
for run,head,name,kind,count in [(43637249034,'2eed5ba2ffa16553d9bdaa79856eceb4e3519139','rx-cursor-formal-43637249034','formal',4),(43637085427,'c5becaa11a0274839f798a47890dd021fb78d0cf','rx-cursor-traffic-43637085427','traffic',16)]:
 r=api(f'actions/runs/{run}');assert r['head_sha']==head
 # Initial formal harness in the traffic run failed separately; require the
 # exact traffic job, never infer failure or success from overall run color.
 jobs=api(f'actions/runs/{run}/jobs')['jobs'];selected=[j for j in jobs if j['name']==f'qualify ({kind})'];assert len(selected)==1
 assert selected[0]['status']=='completed'and selected[0]['conclusion']=='success',('qualification not completed successfully',run,selected[0]['status'],selected[0]['conclusion'])
 artifacts=api(f'actions/runs/{run}/artifacts')['artifacts'];selected_artifacts=[x for x in artifacts if x['name']==name and not x['expired']];assert len(selected_artifacts)==1
 art=selected_artifacts[0];assert art['workflow_run']['head_sha']==head
 b=subprocess.check_output(['gh','api',P+f"actions/artifacts/{art['id']}/zip"]);sha=hashlib.sha256(b).hexdigest();assert art['digest']=='sha256:'+sha
 if kind=='formal':assert art['id']==14129599973 and sha=='dfc322a1d49550d5b4df1b30beb294d9bc3c343eb26bcd3c7209536e1a711223'
 z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist()if n.endswith('result.json')];assert len(names)==1
 result=json.loads(z.read(names[0]));assert result['source_sha256']==digest and len(result['cases'])==count
 assert sum(c['mutation']for c in result['cases'])==count//2
 assert all(c['mutation_rejected']if c['mutation']else c['proven'if kind=='formal'else'passed']for c in result['cases'])
 assert result['status']==('TWO_FULL_MODULE_PROOFS_AND_TWO_MUTATIONS_COMPLETE_NOT_PHYSICAL_SIGNOFF'if kind=='formal'else'EIGHT_TRAFFIC_PASSES_AND_EIGHT_MUTATION_REJECTIONS_NOT_SIGNOFF')
 results.append({'run':run,'source_head':head,'job_id':selected[0]['id'],'artifact_id':art['id'],'artifact_sha256':sha,'result':result})
(out/'rx-qualification-gate.json').write_text(json.dumps({'source_sha256':digest,'qualified_inputs':results,'physical_acceptance':False},indent=2))
