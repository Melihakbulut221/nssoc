# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Synthetic OP/log fixtures check zero-HBT startup classification; no solver."""
from pathlib import Path
import json,resource,sys
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_pump13_02 as m
D=B/'startup-controls01'
def main():
 assert not D.exists();D.mkdir();cases=[];c,rows,_=m.config();expected=m.n.vectors(rows,c['extra_vectors']);names=m.stream.previous.data_names(expected)
 for label,diagnostic in [('positive',None),('warning','Strict clean native diagnostics'),('fabricated_HBT','Exact zero HBT/OFF census'),('nonzero_OP','Exact finite zero-source OP'),('missing_OP_column','')]:
  out=D/label;out.mkdir();values=np.zeros(len(names));columns=list(names)
  log='ngspice-47 done\n'
  if label=='warning':log='Warning: synthetic failure\n'+log
  if label=='fabricated_HBT':log='NSSOC_NATIVE_FLAG_BEGIN q.fake\n device q.fake\n off 1\nNSSOC_NATIVE_FLAG_END\n'+log
  if label=='nonzero_OP':values[0]=1e-6
  if label=='missing_OP_column':columns.pop();values=values[:-1]
  header=f'Title: Explicit synthetic13 zero OP\nDate: fixed\nPlotname: Operating Point\nFlags: real\nNo. Variables: {len(columns)}\nNo. Points: 1\nVariables:\n'
  for i,name in enumerate(columns):header+=f'{i}\t{name}\t'+('current'if name.startswith('i(')else'voltage')+'\n'
  (out/'op.raw').write_bytes(header.encode()+b'Binary:\n'+values.astype('<f8').tobytes());(out/'run.log').write_text(log)
  try:r=m.startup_proof(out,dict(devices=rows,config=c))
  except (AssertionError,ValueError) as e:assert diagnostic is not None and diagnostic in str(e),(label,repr(e))
  else:assert diagnostic is None and r==dict(zero_source_op=True,native_off_flags=[],clean_diagnostics=True)
  cases.append(dict(case=label,passed=True,diagnostic=diagnostic,fixtures={p.name:m.pin(p)for p in out.iterdir()}))
 result=dict(status='PASS_SYNTHETIC13_ZERO_HBT_STARTUP_CLASSIFICATION_CONTROLS',cases=len(cases),outcomes=cases,method=m.pin(__file__),producer=m.pin(m.__file__),native_or_solver_executed=False,scope='Synthetic byte/log fixtures exercise exact startup parser. No actual device operating point or simulator success is claimed; zero HBT census is required rather than fabricated64 flags.')
 (D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(cases))))
if __name__=='__main__':main()
