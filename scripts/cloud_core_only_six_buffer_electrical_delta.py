#!/usr/bin/env python3
"""Source-bound complete pin delta after six-buffer isolation and antenna repair."""
import os,json,hashlib
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from cloud_core_only_complete_electrical_delta import parse,controls,SECTIONS
OUT=ROOT/'hw/soc/out/core-only-six-buffer-electrical-delta'
SOURCES=[('before',44528360188,'0d69398e384b2e88b14cab7e025f9fc29eceeed0','core-only-load-resize-antenna-extraction',14533133820,'40ef5c20cacb5ec9e175e20cc7022fdeda0092768253242ebef14f634334f5a4'),('after',44550131521,'1aa4f5288de36c472ea5ce9548bffa0c703ee623','core-only-regression-antenna-extraction',14542543395,'7eb3ec71a5435393eb626b14d2a3c190a21a935e169730413fd5662d11ca44f1')]
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 result=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='COMPLETE_PIN_DELTA_VALIDATED_AGAINST_NATIVE_COUNTS_NOT_SIGNOFF',controls=controls(),sources={},corners={})
 parsed={}
 for label,rid,head,name,aid,digest in SOURCES:
  rr=completed(rid,head);assert rr['run_attempt']==1
  z,m=archive(rr,name+'-'+str(rid));assert m['id']==aid and m['digest']=='sha256:'+digest
  r=json.loads(z.read('result.json'));assert r['source_head']==head and r['sources_unchanged'] and not r['accepted']
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
  for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  result['sources'][label]=dict(run=rid,head=head,artifact=m,views=r['fresh_view_binding'],fresh_corners=r['fresh_corners'])
  parsed[label]={}
  for corner in r['fresh_corners']:
   root='extraction/2-nssoc-coreonlyextractedsta/'+corner+'/'
   parsed[label][corner]=parse(z.read(root+'checks.rpt').decode());metrics=json.loads(z.read(root+'fresh_metrics.json'))
   assert metrics==r['fresh_corners'][corner]['metrics']
   for section,key in SECTIONS.items():assert len(parsed[label][corner][section])==metrics[key+'__corner:'+corner],(label,corner,section)
  del z
 assert result['sources']['before']['views']['sdc_sha256']==result['sources']['after']['views']['sdc_sha256']=='f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1'
 assert result['sources']['after']['views']['odb_sha256']=='bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc'
 for corner in parsed['after']:
  delta={}
  for section in SECTIONS:
   before,after=parsed['before'][corner][section],parsed['after'][corner][section]
   delta[section]=dict(before=len(before),after=len(after),removed={p:before[p]for p in sorted(set(before)-set(after))},added={p:after[p]for p in sorted(set(after)-set(before))},worst_remaining=sorted([dict(pin=p,**v)for p,v in after.items()],key=lambda v:v['derived_margin'])[:30])
  result['corners'][corner]=delta
  (OUT/(corner+'.json')).write_text(json.dumps(dict(before=parsed['before'][corner],after=parsed['after'][corner],delta=delta),indent=2)+'\n')
 result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
