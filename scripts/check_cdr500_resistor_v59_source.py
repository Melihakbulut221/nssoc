#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only controls; no pya, layout rendering or simulator import."""
import copy,hashlib,json,os
from pathlib import Path
import generate_cdr500_resistor_v59 as candidate
ROOT=Path(__file__).resolve().parents[1]
PIN='docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 method=json.loads((ROOT/'scripts/cdr500-resistor-v59-source-methods.json').read_text())
 for n,h in method['protected'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 exact={
  'cd_shunt':dict(kind='sampler_cd',tags=['sc','sd'],names=['DN','DP'],ids=[184,185,222,223],width=4.,old_length=7.4,new_length=5.),
  'ab_hold':dict(kind='sampler',tags=['sa','sb'],names=['S_RN','S_RP'],ids=[191,194,202,205],width=32.,old_length=2.6,new_length=2.),
 }
 assert candidate.ARMS==exact
 pin=json.loads((ROOT/PIN).read_text());source=pin['report']
 assert pin['run']==40096705004 and pin['summary_sha256']==candidate.SUMMARY_SHA
 assert candidate.validate_summary(source)
 faults=[]
 def reject(name,f):
  try:f()
  except (AssertionError,KeyError,ValueError):faults.append(name)
  else:raise AssertionError('Accepted '+name)
 mutations=[
 ('wrong_source',lambda s:s.__setitem__('source_head','0'*40)),
 ('failed_status',lambda s:s.__setitem__('status','FAIL')),
 ('changed_sources',lambda s:s.__setitem__('sources_unchanged',False)),
 ('wrong_gds',lambda s:s['outputs'].__setitem__('parent/layout/'+candidate.OLD+'.gds','0'*64)),
 ('missing_device',lambda s:s['device_locations']['devices'].pop()),
 ('wrong_location_status',lambda s:s['device_locations'].__setitem__('status','UNQUALIFIED')),
 ('wrong_device_count',lambda s:s['strict_wire_graph'].__setitem__('native_device_count',499)),
 ('wrong_terminal_count',lambda s:s['strict_wire_graph'].__setitem__('native_terminal_count',1445)),
 ('wrong_anchor_count',lambda s:s['anchors'].__setitem__('logical_anchor_count',977)),
 ('wrong_public_ports',lambda s:s['anchors'].__setitem__('public_ports',24)),
 ]
 for name,edit in mutations:
  s=copy.deepcopy(source);edit(s);reject(name,lambda s=s:candidate.validate_summary(s))
 for name,field,value in [('wrong_target_model','model','ptap1'),
 ('wrong_target_width','w',4.1),('wrong_target_length','l',7.3),('bent_target','b',1.),
 ('parallel_target','m',2.),('wrong_extracted_poly_spacing','ps',1.)]:
  s=copy.deepcopy(source);d=next(d for d in s['device_locations']['devices']if d['native_id']==184)
  if field=='model':d[field]=value
  else:d['parameters'][field]=value
  reject(name,lambda s=s:candidate.validate_summary(s))
 s=copy.deepcopy(source);d=next(d for d in s['device_locations']['devices']if d['native_id']==184)
 d['terminals'][1]['name']='PLUS0';reject('wrong_native_terminal',lambda:candidate.validate_summary(s))
 s=copy.deepcopy(source);d=next(d for d in s['device_locations']['devices']if d['native_id']==184)
 d['pcell']['transform']='r90 *1 0,0';reject('rotated_target',lambda:candidate.validate_summary(s))
 positives=[]
 for arm,a in exact.items():
  for child in(False,True):
   names=['R'+n for n in a['names']]if child else['R'+t+'_'+n for t in a['tags']for n in a['names']]
   lines=['* exact reference transport fixture\n','.subckt TEST A B BULK\n']
   lines += [n+' A B BULK rppd w='+format(a['width'],'g')+'u l='+format(a['old_length'],'g')+'u b=0 m=1\n'for n in names]
   lines += ['RUNRELATED A B BULK rppd w=4u l=7.4u b=0 m=1\n','.ends TEST\n']
   text=''.join(lines);actual,changed=candidate.reference(text,arm,child)
   expected=''.join(line.replace(' l='+format(a['old_length'],'g')+'u ',' l='+format(a['new_length'],'g')+'u ')if line.split()and line.split()[0]in names else line for line in lines)
   assert actual==expected and changed==sorted(names)
   positives.append(dict(arm=arm,child=child,changed=changed))
   if not child:
    reject(arm+'_missing_reference',lambda text=text,arm=arm:candidate.reference(text.replace(names[0]+' ','RREMOVED ',1),arm))
    reject(arm+'_wrong_reference_width',lambda text=text,arm=arm:candidate.reference(text.replace('w='+format(a['width'],'g')+'u','w=999u',1),arm))
    reject(arm+'_wrong_reference_length',lambda text=text,arm=arm:candidate.reference(text.replace('l='+format(a['old_length'],'g')+'u','l=999u',1),arm))
    reject(arm+'_duplicate_reference',lambda text=text,arm=arm:candidate.reference(text+lines[2],arm))
 assert len(faults)==26 and len(positives)==4
 result=dict(status='PASS_CDR_V59_ISOLATED_SOURCE_CONTROLS',controls=faults,reference_fixtures=positives,
  protected=method['protected'],native_renderer_executed=False,physical_accepted=False,qualified_pex=False,electrical_accepted=False)
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
