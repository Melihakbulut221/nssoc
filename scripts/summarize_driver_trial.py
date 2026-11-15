import os,json,subprocess,hashlib,io,zipfile,pathlib,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43776325443');assert r['head_sha']=='50475641846a50fcbb919ff9e218208079515008' and r['conclusion']=='success' and r['run_attempt']==1
m=api('actions/artifacts/14186344549');h='e6ef8008841e9d18436cb75f79326f3620b230b60a3b8b39df691d2f3a0e460e';assert m['workflow_run']['id']==r['id'] and m['digest']=='sha256:'+h and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14186344549/zip']);assert hashlib.sha256(b).hexdigest()==h;z=zipfile.ZipFile(io.BytesIO(b));d=json.loads(z.read('result.json'))
assert d['source_head']==r['head_sha'] and d['sources_unchanged'] and d['returncode']==0
for n in z.namelist():
 if n!='result.json':assert hashlib.sha256(z.read(n)).hexdigest()==d['outputs'][n],n
out=pathlib.Path('diagnosis');out.mkdir();summary={k:v for k,v in d.items()if k!='outputs'};summary['source_artifact']=m['id'];summary['source_archive_sha256']=h;summary['result_sha256']=hashlib.sha256(z.read('result.json')).hexdigest();summary['paths']={}
targets=['$auto$ff.cc:337:slice$183526','$auto$ff.cc:337:slice$172492','$auto$ff.cc:337:slice$172502','eth_txd_o[5]','eth_txd_o[2]','pcie_initialized_o']
summary['paired_paths']={};summary['scope']='Diagnostic path pairing only. Not a promise that arbitrary inserted delay is feasible across corners.'
for n in z.namelist():
 if not n.endswith(('/max.rpt','/min.rpt')):continue
 paths=[s for s in re.split(r'(?=Startpoint:)',z.read(n).decode())if s.startswith('Startpoint:')]
 rows=[]
 for target in targets:
  found=[v for v in paths if re.search(r'^Endpoint: '+re.escape(target)+r'(?:\s|$)',v,re.M)]
  for v in found:
   slack=re.search(r'([-+0-9.]+)\s+slack \((?:MET|VIOLATED)\)',v);assert slack
   rows.append({'endpoint':target,'startpoint':v.splitlines()[0],'slack_ns':float(slack[1]),'path':v})
 summary['paired_paths'][n]=rows
(out/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:[{a:b for a,b in row.items()if a!='path'}for row in v]for k,v in summary['paired_paths'].items()}))
