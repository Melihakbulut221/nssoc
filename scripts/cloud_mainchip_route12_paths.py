#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read immutable completed route12 timing paths; no native analysis or mutation."""
import collections,hashlib,json,os,re,traceback,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route12-paths'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,scope='Read-only actual completed route12 original-clock nominal-RC path diagnosis. No clock or route changes; sampled report paths are not an all-endpoint census.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  run=api('actions/runs/39904823953')
  assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='8214789ad779515f719670a873136842cd50f963'
  pin=json.loads((ROOT/'docs/evidence/mainchip-route12-postroute-open-gates-20261023.json').read_text())
  assert pin['run']==39904823953 and pin['summary_sha256']=='7492dd5d5719f1dd2a7ab15f997eeff70a869f9287ef92c3c6dfa07bad292fb5'
  rel=api('releases/tags/cloud-results-39904823953-1-mainchip-repair-deep-postroute')
  a=next(a for a in rel['assets']if a['name'].endswith('.summary.json'))
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
  assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256']
  source=json.loads(raw);assert source['status']=='COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES'and source['sources_unchanged']
  names=[n for n in source['outputs']if n.startswith('run/4-nssoc-onehotroutedsta/')and n.endswith(('.rpt','.tcl','.json','COMMANDS'))and not n.endswith('.process_stats.json')]
  names+=['run/1-openroad-checkantennas/reports/antenna.rpt','run/1-openroad-checkantennas/reports/antenna_summary.rpt','trial-config.json','initial-state.json']
  assert all(n in source['outputs']for n in names)
  reports.OUT=OUT
  original,proof=reports.restore_report('mainchip-repair-deep-postroute',39904823953,pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
  assert original==source
  r['source']=proof;r['measurements']=source['measurements'];r['corners']={}
  for corner,spec in source['measurements'].items():
   folder=OUT/'source'/spec['directory'];row={}
   for mode in ['max','min']:
    text=(folder/(mode+'.rpt')).read_text()
    blocks=re.split(r'(?m)(?=^Startpoint:)',text)
    parsed=[]
    for block in blocks:
     if not block.startswith('Startpoint:'):continue
     fields={}
     for label in ['Startpoint','Endpoint','Path Group','Path Type']:
      hit=re.search(r'(?m)^'+label+r':\s*(.+)$',block);assert hit,(corner,mode,label)
      fields[label.lower().replace(' ','_')]=hit.group(1).strip()
     hit=re.search(r'(?m)^\s*([-+]?\d+(?:\.\d+)?)\s+slack\s+\((VIOLATED|MET)\)',block)
     assert hit,(corner,mode,'slack')
     fields['slack_ns']=float(hit.group(1));fields['slack_status']=hit.group(2)
     fields['exact_report']=block
     parsed.append(fields)
    assert parsed,(corner,mode)
    metric=spec['metrics']['timing__'+('setup'if mode=='max'else'hold')+'__ws__corner:'+corner]
    worst=min(p['slack_ns']for p in parsed)
    assert abs(worst-metric)<.001,(corner,mode,worst,metric)
    groups=collections.defaultdict(list)
    for p in parsed:groups[p['path_group']].append(p)
    row[mode]=dict(reported_paths=len(parsed),violated_reported_paths=sum(p['slack_ns']<0 for p in parsed),worst_reported_slack_ns=worst,
      groups={g:dict(reported_paths=len(v),violated=sum(x['slack_ns']<0 for x in v),worst_slack_ns=min(x['slack_ns']for x in v))for g,v in groups.items()},
      worst_paths=sorted(parsed,key=lambda x:x['slack_ns'])[:5])
   r['corners'][corner]=row;save()
  r.update(status='PASS_EXACT_COMPLETED_ROUTE12_PATH_DIAGNOSIS_NOT_TIMING_ACCEPTANCE',sources_unchanged=all(sha(OUT/'source'/n)==source['outputs'][n]for n in names),
   native_process_not_restarted=True)
  assert r['sources_unchanged']
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
