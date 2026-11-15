"""Require exact completed real RX proof and traffic evidence before CAD."""
import subprocess,json,hashlib,zipfile,io,pathlib,os,time,base64
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_bytes();digest=hashlib.sha256(source).hexdigest()
assert digest=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
legacy_raw=base64.b64decode(api('contents/hw/soc/rtl/pcie/soc_pcie_rx_credit.v?ref=7b3d47cd6bd0666f035f6c231f5edefb705ca1c6')['content']);legacy=legacy_raw.decode()
legacy_hash=hashlib.sha256(legacy_raw).hexdigest();assert legacy_hash=='2a345ba4082873f73fd8f308880a1f8d29651e24c12bbeaf9ac20b8f4082636e'
text=source.decode();start=text.index('`ifdef SOC_PCIE_RX_DLLP_LAST_COMPARE');end=text.index('`endif',start)+len('`endif');block=text[start:end]
prefix=text[:start];suffix=text[end:];assert legacy.startswith(prefix) and legacy.endswith(suffix)
assert legacy[len(prefix):len(legacy)-len(suffix)].strip()==block.split('`else',1)[1].rsplit('`endif',1)[0].strip()
out=pathlib.Path('out');out.mkdir(exist_ok=True);results=[]
for run,head,name,kind,count in [(43659882138,'7b3d47cd6bd0666f035f6c231f5edefb705ca1c6','rx-cursor-formal-43659882138','formal',4),(43659882138,'7b3d47cd6bd0666f035f6c231f5edefb705ca1c6','rx-cursor-traffic-43659882138','traffic',16),(43707359187,'d7719ea5449f3c61102f9a633692beaa19aa66be','rx-dllp-full-formal-43707359187','formal',4),(43707359187,'d7719ea5449f3c61102f9a633692beaa19aa66be','rx-dllp-full-traffic-43707359187','traffic',16)]:
 r=api(f'actions/runs/{run}');assert r['head_sha']==head
 # Select exact immutable producer job, not the first run's unrelated failed traffic job.
 deadline=time.monotonic()+2700
 while True:
  jobs=api(f'actions/runs/{run}/jobs')['jobs'];selected=[j for j in jobs if j['name']==(f'qualify ({kind})' if run==43659882138 else kind)];assert len(selected)==1
  if selected[0]['status']=='completed':break
  assert selected[0]['id']==(({'formal':132646601704,'traffic':132646601948} if run==43659882138 else {'formal':132791216269,'traffic':132791216392})[kind])
  assert time.monotonic()<deadline,('qualification still pending; no CAD started',run)
  print('Waiting for exact qualification job',run,kind,selected[0]['status'],flush=True)
  time.sleep(45)
 assert selected[0]['status']=='completed'and selected[0]['conclusion']=='success',('qualification not completed successfully',run,selected[0]['status'],selected[0]['conclusion'])
 artifacts=api(f'actions/runs/{run}/artifacts')['artifacts'];selected_artifacts=[x for x in artifacts if x['name']==name and not x['expired']];assert len(selected_artifacts)==1
 art=selected_artifacts[0];assert art['workflow_run']['head_sha']==head
 b=subprocess.check_output(['gh','api',P+f"actions/artifacts/{art['id']}/zip"]);sha=hashlib.sha256(b).hexdigest();assert art['digest']=='sha256:'+sha
 assert art['workflow_run']['id']==run
 assert selected[0]['id']==(({'formal':132646601704,'traffic':132646601948} if run==43659882138 else {'formal':132791216269,'traffic':132791216392})[kind])
 z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist()if n.endswith('result.json')];assert len(names)==1
 result=json.loads(z.read(names[0]));assert result['source_sha256']==(legacy_hash if run==43659882138 else digest) and len(result['cases'])==count
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
(out/'rx-qualification-gate.json').write_text(json.dumps({'source_sha256':digest,'legacy_source_sha256':legacy_hash,'qualified_inputs':results,'physical_acceptance':False},indent=2))
