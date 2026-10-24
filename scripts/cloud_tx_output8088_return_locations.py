#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind dominant measured TX AVSS resistor segments to native extraction coordinates."""
import hashlib,io,json,os,shlex,subprocess,tarfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-output8088-return-locations'
REPO='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def asset(a,h):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
 assert sha(b)==h
 return b
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  raw=asset(669588301,'7cebca01d733cfa997b738974911e920126ed7b3ce16883c7bba7ed74a10187a');sensitivity=json.loads(raw)
  assert sensitivity['status']=='COMPLETE_ORIGINAL_AVSS_DC_SENSITIVITY_NOT_PHYSICAL_REPAIR'
  p=asset(668046881,'090b5d6939018d228dcb2fc0b6c34e2c6f4fa9dcb43c2a4bbd5c566cfa1d4e22');report=json.loads(p)
  assert report['source_head']=='505cb0f89c61d3276856ab8f095dc5e0c1fc5a0f'
  packed=asset(668047039,'6671d835ed9cee45d39391191085d8e00b9ad2e32595bb48d490be9100c7b50f')
  assert len(packed)==79164107
  stem='precise/rc01/full_tx_output8088_power128return64_wires'
  wanted={stem+'.res.ext',stem+'.ext',stem+'.nodes','precise/rc01/wires.spice'}
  found={};seen=set();embedded=False
  with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz')as tar:
   for item in tar:
    q=Path(item.name);assert not q.is_absolute()and '..'not in q.parts and item.name not in seen
    seen.add(item.name);assert item.isdir()or item.isfile()
    if not item.isfile():continue
    name=str(Path(*q.parts[1:]))
    if name in wanted or name=='result.json':
     b=tar.extractfile(item).read()
     if name=='result.json':assert b==p;embedded=True
     else:assert sha(b)==report['outputs'][name];found[name]=b
  assert embedded and set(found)==wanted
  r['verified_sources']=dict(sensitivity_run=39980682925,sensitivity_sha256=sha(raw),
   precision_run=39903139948,precision_summary_sha256=sha(p),precision_archive_sha256=sha(packed),
   files={name:sha(b)for name,b in found.items()})
  edges={}
  for t in sensitivity['exact_avss_dc_resistance']['targets']:
   for e in t['dominant_unit_injection_segments']:
    key=e['name']
    if key in edges:assert edges[key]['original_extractor_nodes']==e['original_extractor_nodes']
    edges[key]=e
  wires={}
  for line in found['precise/rc01/wires.spice'].decode().splitlines():
   f=line.split()
   if f and f[0].lower()in edges:
    assert len(f)==4 and f[0].lower()not in wires
    e=edges[f[0].lower()]
    assert f[1:3]==e['original_extractor_nodes'] and float(f[3])==e['resistance_ohm'],'Wrong native segment identity'
    wires[f[0].lower()]=f
  assert set(wires)==set(edges)
  wanted_nodes={n for e in edges.values()for n in e['original_extractor_nodes']}
  records={n:[]for n in wanted_nodes};scales={}
  for path,b in found.items():
   if not path.endswith(('.ext','.nodes')):continue
   for ordinal,line in enumerate(b.decode().splitlines(),1):
    if not line or line.startswith('#'):continue
    f=shlex.split(line)
    if not f:continue
    if f[0]=='scale':scales.setdefault(path,[]).append(f)
    if f[0]in ('rnode','node','port')and len(f)>1 and f[1]in records:
     records[f[1]].append(dict(source_file=path,line=ordinal,fields=f))
  assert scales[stem+'.res.ext']==scales[stem+'.ext']==[['scale','1000','1','0.5']]
  assert all(records.values()),'Missing source native coordinate'
  r['dominant_segments']={name:dict(sensitivity=e,native_spice=wires[name],
   endpoint_records={n:records[n]for n in e['original_extractor_nodes']})for name,e in edges.items()}
  r['native_scale_records']=scales
  r['status']='COMPLETE_DOMINANT_AVSS_NATIVE_SEGMENT_BINDING_REQUIRES_PHYSICAL_GEOMETRY_REVIEW'
  r['scope']='Exact original raw extraction records with file/line identities. No geometry edit, inferred units, resistance scaling, new simulation or electrical acceptance.'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:save()
if __name__=='__main__':main()
