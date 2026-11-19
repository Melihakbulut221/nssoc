#!/usr/bin/env python3
"""Parse every electrical violation, including OpenSTA's blank slack column."""
import os,json,hashlib,math
from cloud_core_only_postgrt import ROOT,completed,archive,sha
OUT=ROOT/'hw/soc/out/core-only-complete-electrical-delta'
SECTIONS={'max slew':'design__max_slew_violation__count','max fanout':'design__max_fanout_violation__count','max capacitance':'design__max_cap_violation__count'}
def parse(text):
 result={k:{}for k in SECTIONS};section=None
 for line in text.splitlines():
  if line.strip()in SECTIONS:section=line.strip();continue
  if not section or '(VIOLATED)'not in line:continue
  fields=line.split();assert len(fields)in (4,5)and fields[-1]=='(VIOLATED)',line
  name=fields[0];assert name not in result[section],('duplicate',name)
  limit,actual=map(float,fields[1:3]);reported=float(fields[3])if len(fields)==5 else None
  assert math.isfinite(limit)and math.isfinite(actual)and actual>limit,line
  if reported is not None:assert math.isfinite(reported)and reported<0,line
  result[section][name]=dict(limit=limit,actual=actual,reported_slack=reported,derived_margin=limit-actual)
 return result
def controls():
 fixture='max fanout\nA/X 8 10 -2 (VIOLATED)\nB/X 8 9 (VIOLATED)\n'
 p=parse(fixture);assert len(p['max fanout'])==2 and p['max fanout']['B/X']['reported_slack']is None and p['max fanout']['B/X']['derived_margin']==-1
 for bad in ['max fanout\nA/X 8 (VIOLATED)\n','max fanout\nA/X 8 7 (VIOLATED)\n',fixture+'B/X 8 9 (VIOLATED)\n']:
  try:parse(bad)
  except (AssertionError,ValueError):pass
  else:raise AssertionError('Bad report accepted')
 return dict(blank_slack_retained=True,malformed_row_rejected=True,nonviolation_rejected=True,duplicate_rejected=True)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 run=completed(44530797223,'ca3858b4ed8be455acab8103fb278f90eb38bafa');assert run['run_attempt']==1
 z,m=archive(run,'core-only-resized-electrical-comparison-44530797223');assert m['id']==14534485221 and m['digest']=='sha256:ee1d29007f07d60119aa7aeb9f62996162aff9424828fea44f509adf3895a857'
 r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha']
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 result=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='COMPLETE_PIN_DELTA_VALIDATED_AGAINST_NATIVE_COUNTS_NOT_SIGNOFF',source_artifact=m,controls=controls(),corners={})
 for corner in ['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']:
  parsed={}
  for label in ['load','resized']:
   root=label+'/extraction/2-nssoc-coreonlyextractedsta/'+corner+'/'
   parsed[label]=parse(z.read(root+'checks.rpt').decode());metrics=json.loads(z.read(root+'fresh_metrics.json'))
   for section,key in SECTIONS.items():assert len(parsed[label][section])==metrics[key+'__corner:'+corner],(label,corner,section)
  delta={}
  for section in SECTIONS:
   before,after=parsed['load'][section],parsed['resized'][section]
   delta[section]=dict(before=len(before),after=len(after),removed={p:before[p]for p in sorted(set(before)-set(after))},added={p:after[p]for p in sorted(set(after)-set(before))},blank_slack_before=sum(v['reported_slack']is None for v in before.values()),blank_slack_after=sum(v['reported_slack']is None for v in after.values()))
  result['corners'][corner]=delta
  (OUT/(corner+'.json')).write_text(json.dumps(dict(pins=parsed,delta=delta),indent=2)+'\n')
 result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
