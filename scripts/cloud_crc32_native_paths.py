#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read exact existing packet STA paths and count actual mapped loads; no CAD rerun."""
import hashlib,io,json,os,re,subprocess,tarfile,traceback
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-crc32-native-paths'
REPO='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def asset(a):return subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,
  scope='Read-only exact reported paths and mapped pin fanout. Does not change source netlists, run STA, model parasitics or establish physical sensitivity.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  run=api('actions/runs/39900301089')
  assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='5302210b2f6482f06994dd00f382f462fa5750e9'and run['run_attempt']==1
  raw=asset(667956757);assert sha(raw)=='9f68e111273e3613da23feb8ecc95fbd63b4e6e0390d028f43ae004fe7ee70e8'
  source=json.loads(raw);assert source['sources_unchanged']
  assert source['status']=='COMPLETE_CRC_PARALLEL_PROOF_PORTS_AND_NATIVE_PACKET_COMPARISON_NOT_PHYSICAL_ACCEPTANCE'
  archive=asset(667956964);assert len(archive)==123314626 and sha(archive)=='1bf4f28d081e51b78048908cda1e9675d9a61d7bd8312fe9a683b069467c1f64'
  tf=tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz')
  def read(name):
   ms=[m for m in tf.getmembers()if m.name==name or m.name.endswith('/'+name)]
   assert len(ms)==1 and ms[0].isfile()
   b=tf.extractfile(ms[0]).read();assert sha(b)==source['outputs'][name]
   p=OUT/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
   return b
  r['source']=dict(run=39900301089,summary_sha256=sha(raw),archive_sha256=sha(archive),all_archive_bytes_verified=True)
  r['paths']={}
  for key,spec in source['mapping'].items():
   top,label=key.split('/');directory=top+'-'+label+'-mapped'
   module=json.loads(read(directory+'/mapped.json'))['modules'][top]
   assert len(module['cells'])==spec['cells']
   aliases=spec['aliases'];back={v:k for k,v in aliases.items()}
   assert len(back)==len(module['cells'])and set(aliases)==set(module['cells'])
   loads=defaultdict(list);names=defaultdict(list)
   for cn,c in module['cells'].items():
    for pin,bits in c['connections'].items():
     if c['port_directions'][pin]=='input':
      for b in bits:loads[b].append(aliases[cn]+'/'+pin)
   for n,v in module['netnames'].items():
    for i,b in enumerate(v['bits']):
     if isinstance(b,int):names[b].append(n+('['+str(i)+']'if len(v['bits'])>1 else ''))
   rows={}
   for corner in ['typ','slow','fast']:
    body=read(directory+'/'+corner+'/max.rpt').decode()
    first=body.split('Startpoint:')[1].split('Startpoint:')[0]
    launch=re.match(r'\s*(physical_cell_\d+)',first).group(1)
    capture=re.search(r'Endpoint:\s*(physical_cell_\d+)',first).group(1)
    observed=[]
    pattern=r'^\s*([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+[\^v]\s+(physical_cell_\d+)/(\S+)\s+\((\S+)\)'
    for line in first.splitlines():
     match=re.match(pattern,line)
     if not match:continue
     delay,time,alias,pin,typ=match.groups();cell=module['cells'][back[alias]]
     assert cell['type']==typ and pin in cell['connections']and len(cell['connections'][pin])==1
     bit=cell['connections'][pin][0]
     observed.append(dict(pin=alias+'/'+pin,original_cell=back[alias],type=typ,direction=cell['port_directions'][pin],delay_ns=float(delay),arrival_ns=float(time),net_bit=bit,net_names=names[bit],actual_input_pin_load_count=len(loads[bit]),actual_input_pin_loads=loads[bit]))
    assert observed and any(v['pin']==launch+'/Q'for v in observed)and any(v['pin']==capture+'/D'for v in observed)
    slack=float(re.search(r'([-+]?\d+\.\d+)\s+slack\s+\((?:VIOLATED|MET)\)',first).group(1))
    assert slack==source['timing'][key][corner]['max']['minimum_reported_slack_ns']
    rows[corner]=dict(launch_cell=launch,capture_cell=capture,slack_ns=slack,exact_native_report=first,observed_pins=observed,
      largest_output_stage_delays=sorted([v for v in observed if v['direction']=='output'],key=lambda v:v['delay_ns'],reverse=True)[:4])
   r['paths'][key]=rows;save()
  r.update(status='PASS_EXACT18_NATIVE_MAX_PATHS_MAPPED_PIN_IDENTITIES_AND_FANOUT_NOT_PHYSICAL_ACCEPTANCE',read_only=True,source_native_process_not_restarted=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p.read_bytes())for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
