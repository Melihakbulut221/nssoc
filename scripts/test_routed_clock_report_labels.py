# SPDX-License-Identifier: Apache-2.0
"""Execute upstream report labels with all virtual/propagated truth states."""
import ast,base64,hashlib,json,pathlib,subprocess
path=pathlib.Path('hw/soc/pnr/replay_onehot_routed_extraction_flow.py')
module=ast.parse(path.read_text());func=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='correct_clock_report_labels')
ns={};exec(compile(ast.Module(body=[func],type_ignores=[]),str(path),'exec'),ns);fix=ns['correct_clock_report_labels']
d=json.loads(subprocess.check_output(['gh','api','repos/librelane/librelane/contents/librelane/scripts/openroad/sta/corner.tcl?ref=3.0.5'],timeout=60));text=base64.b64decode(d['content']).decode();digest=hashlib.sha256(text.encode()).hexdigest()
assert digest=='e0096884c1929ed80506366ecc3e809c78c8493180e366fc095e2b09f5c36f53'
patched=fix(text);old='    if { [get_property $clock is_propagated] } {\n        set is_virtual "yes"\n    }';new=old.replace('set is_virtual','set is_propagated');assert patched.replace(new,old)==text
start='foreach clock [all_clocks] {\n    set source_names';end='    puts "Period: [get_property $clock period]"'
def block(t):
 assert t.count(start)==1 and t.count(end)==1
 return t[t.index(start):t.index(end)+len(end)]+'\n}\n'
def output(t,v,p):
 pre='set virtual '+str(v)+'\nset propagated '+str(p)+'\n'
 pre+='proc all_clocks {} {return test_clock}\nproc get_property {obj prop} {\n global virtual propagated\n switch -- $prop {sources {return cp} full_name {return cp} is_generated {return 0} is_virtual {return $virtual} is_propagated {return $propagated} name {return test_clock} period {return 4} default {error "Unexpected property"}}\n}\n'
 result=subprocess.run(['tclsh'],input=pre+block(t),text=True,capture_output=True,check=True,timeout=10)
 return dict(line.split(': ',1) for line in result.stdout.splitlines() if ': ' in line)
rows=[];original_failures=0
for v in [0,1]:
 for p in [0,1]:
  expected={'Virtual':'yes' if v else 'no','Propagated':'yes' if p else 'no'}
  oldrow=output(text,v,p);row=output(patched,v,p)
  assert all(row[k]==val for k,val in expected.items());original_failures+=int(any(oldrow[k]!=val for k,val in expected.items()))
  rows.append({'virtual':v,'propagated':p,'original':oldrow,'corrected':row})
assert original_failures==2
rejected=[]
for name,bad in [('missing',text.replace(old,'')),('duplicate',text+'\n'+old)]:
 try:fix(bad)
 except AssertionError:rejected.append(name)
assert rejected==['missing','duplicate']
r={'status':'PASS_REPORT_LABEL_CONTROLS','upstream_sha256':digest,'only_print_variable_assignment_changed':True,'truth_table':rows,'original_cases_failing':original_failures,'invalid_anchor_controls':rejected,'timing_acceptance':False,'scope':'Report presentation correction only. Does not change clocks, constraints, propagation, SPEF, path delays or acceptance.'}
pathlib.Path('out').mkdir();pathlib.Path('out/report-label-controls.json').write_text(json.dumps(r,indent=2));print(r['status'])
