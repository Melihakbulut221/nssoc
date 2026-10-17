# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite copied-byte and arithmetic controls; no native interpreter run."""
from pathlib import Path
import copy,hashlib,io,json,resource,sys
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_pump13_02 as m
import force_arithmetic02 as force
import run_sign_controls01 as sign
D=B/'contract-controls02'

def main():
 assert not D.exists();D.mkdir();cases=[]
 def ok(label,**kw):cases.append(dict(case=label,passed=True,**kw))
 def reject(label,call,diagnostic):
  try:call()
  except (AssertionError,ValueError,KeyError) as error:
   assert diagnostic in str(error),(label,repr(error));ok(label,diagnostic=str(error))
  else:raise AssertionError(label+' accepted')
 for current in (1e-6,-1e-6):
  data={'v(vctrl)':np.array([.6]),'i(vctrl)':np.array([current])};sign.verify_sign(data,current);ok('synthetic_sign_'+str(current))
  reject('synthetic_reversed_sign_'+str(current),lambda:sign.verify_sign(data,-current),'Actual independent source current sign')
 reject('synthetic_missing_current',lambda:sign.verify_sign({'v(vctrl)':np.array([.6])},1e-6),'Exact sign-control observations')
 c,rows,_=m.config();expected=m.n.vectors(rows,c['extra_vectors'])
 raw=(B/'finite-controls02/positive.raw').read_bytes();header,_=raw.split(b'Binary:\n',1)
 header+=b'Binary:\n';lines=header.decode().splitlines(True);start=lines.index('Variables:\n')+1
 for mode in ('missing','duplicate','reordered'):
  changed=list(lines)
  if mode=='missing':del changed[start+1]
  elif mode=='duplicate':
   fields=changed[start+2].split();fields[1]=changed[start+1].split()[1];changed[start+2]='\t'.join(fields)+'\n'
  else:changed[start+1],changed[start+2]=changed[start+2],changed[start+1]
  body=''.join(changed).encode();(D/('bad-'+mode+'.raw')).write_bytes(body)
  diagnostic={'missing':'Complete native variable table','duplicate':'Exact source-vector bijection','reordered':'Unique ordered variable IDs'}[mode]
  reject('copied13_header_'+mode,lambda:m.life.tiny.parse_header(io.BytesIO(body),expected),diagnostic)
 def row(kind,value):return dict(kind=kind,mean_a=value,vctrl_v=.6,interval_s=[4e-9,14e-9],port_waveform_sha256='1'*64,noncommand_boundary_sha256='2'*64,sign_control_passed=True)
 loaded=row('570_idle',30e-6);forced=row('13_forced',50e-6);idle=row('13_matched_idle',10e-6)
 def oracle(result):assert abs(result['mean_a']-70e-6)<1e-18 and result['arithmetic_only'] and not result['physical_reachability_qualified'],'Independent replacement-current arithmetic'
 oracle(force.replacement_current(loaded,forced,idle));ok('independent70uA_scalar_replacement')
 zero=copy.deepcopy(forced);zero['mean_a']=idle['mean_a'];r=force.replacement_current(loaded,zero,idle);assert r['mean_a']==loaded['mean_a'];ok('exact_matched_idle_identity')
 for label,term,key,value,diagnostic in [
  ('mismatched_voltage',1,'vctrl_v',.7,'Equal actual clamped voltage'),
  ('mismatched_window',2,'interval_s',[14e-9,24e-9],'Equal integration interval'),
  ('unmatched_idle_wave',2,'port_waveform_sha256','3'*64,'Actual loaded and subtraction-idle'),
  ('wrong_noncommand_boundary',1,'noncommand_boundary_sha256','3'*64,'State replacement preserves'),
  ('unsigned_current',0,'sign_control_passed',False,'Actual sign convention prerequisite'),
  ('wrong_role',0,'kind','13_idle','Exact loaded/state/matched-idle roles')]:
  args=copy.deepcopy([loaded,forced,idle]);args[term][key]=value
  reject(label,lambda:force.replacement_current(*args),diagnostic)
 source=Path(force.__file__).read_text();expression="loaded['mean_a']+(forced['mean_a']-matched_idle['mean_a'])"
 for label,wrong in [('double_filter_count',"loaded['mean_a']+forced['mean_a']"),('wrong_clamp_sign',"-loaded['mean_a']-forced['mean_a']+matched_idle['mean_a']"),('missing570term',"forced['mean_a']-matched_idle['mean_a']")]:
  assert source.count(expression)==1;mutant=source.replace(expression,wrong);(D/(label+'.py')).write_text(mutant);ns={};exec(compile(mutant,label,'exec'),ns)
  reject('actual_arithmetic_mutant_'+label,lambda:oracle(ns['replacement_current'](loaded,forced,idle)),'Independent replacement-current arithmetic')
 result=dict(status='PASS_SYNTHETIC13_SIGN_OBSERVATION_AND_MATCHED_REPLACEMENT_ARITHMETIC_CONTROLS',cases=len(cases),outcomes=cases,
             inputs={str(p):m.pin(p)for p in [Path(__file__),Path(m.__file__),Path(force.__file__),Path(sign.__file__),B/'finite-controls02/positive.raw']},
             native_or_solver_executed=False,actual_sign_control_completed=False,scope='Synthetic sign-checker tests and real copied finite13 headers, explicit scalar matched-boundary fixtures plus executed expression mutants. No physical waveform matching or pump-current inference.')
 (D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(cases))))
if __name__=='__main__':main()
