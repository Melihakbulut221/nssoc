# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay only the preserved failed template command with two extra macro LEFs."""
import sys,json,pathlib,shlex
R=pathlib.Path(__file__).absolute().parents[4]
sys.path[:0]=[str(R/'scripts'),str(R/'hw/soc/pnr')]
import run_npu_eco_physical as f
from npu_eco_template_lefs import append_template_macro_lefs
B=pathlib.Path(__file__).absolute().parent
C=f.common.fresh_directory(B/'template-control04')
old=B/'pair01-original-work/run/18-odb-applydeftemplate'
command=shlex.split((old/'COMMANDS').read_text())
assert command[0]=='openroad' and command[-1].endswith('/12-openroad-generatepdn/soc_top.odb')
original=list(command)
for option,name in [('-metrics','metrics.json'),('--output-odb','soc_top.odb'),('--output-def','soc_top.def')]:
 assert command.count(option)==1
 command[command.index(option)+1]=str(C/name)
cfg=json.loads((B/'pair01-original/config.json').read_text())
macros={n:d['lef'] for n,d in cfg['MACROS'].items()}
command=append_template_macro_lefs(command[:-1],macros)+command[-1:]
runtime=R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
inputs=[pathlib.Path(original[-1]),pathlib.Path(original[original.index('--def-template')+1]),runtime,R/'hw/soc/pnr/alu_physical_geometry.tcl',R/'hw/soc/pnr/npu_eco_template_lefs.py']+[pathlib.Path(s) for a in macros.values() for s in a]
pins={str(p):f.pin(p) for p in inputs}
row={'status':'PREPARING_TEMPLATE_READER_CONTROL','old_command':original,'corrected_command':command,'inputs':pins,'scope':'A parser/import control only, using retained oldPDN ODB. Not a fresh complete physical experiment or timing result.'}
f.common.save(C/'control.json',row)
try:
 row['template_execution']=f.execute([str(runtime),*command],C,row)
 f.require(row['template_execution']['returncode']==0,'Macro-aware template control failed')
 for label in ['source','output']:
  out=C/label;out.mkdir()
  lines=['set ::nssoc_alu_geometry_definitions_only 1','source {'+str(R/'hw/soc/pnr/alu_physical_geometry.tcl')+'}']
  if label=='source':
   lefs=[original[i+1] for i,v in enumerate(original) if v=='--input-lef']+[s for a in macros.values() for s in a]
   lines+=['read_lef {'+s+'}' for s in lefs]
   lines+=['read_def {'+original[original.index('--def-template')+1]+'}']
  else:lines+=['read_db {'+str(C/'soc_top.odb')+'}']
  lines+=['nssoc_alu_geometry {'+str(out)+'}','exit']
  t=out/'geometry.tcl';t.write_text('\n'.join(lines)+'\n')
  rec={};row[label+'_execution']=f.execute([str(runtime),'openroad','-exit',str(t)],out,rec)
  f.require(row[label+'_execution']['returncode']==0,'Native geometry capture failed')
  row[label+'_geometry']=f.physical.geometry_check(out,cfg)
 for name in ['signal-pins.tsv','bounds.tsv','dbu.txt']:
  f.require(row['source_geometry'][name]==row['output_geometry'][name],'Template geometry changed: '+name)
 for p,h in pins.items():f.common.verify_file(pathlib.Path(p),h)
 row.update(status='PASS_NATIVE_MACRO_LEF_TEMPLATE_CONTROL_FIXED32MACROS301PINS',output_views={n:f.pin(C/n) for n in ['soc_top.odb','soc_top.def']},all_input_pins_rechecked=True,whole_chip_timing_accepted=False)
except BaseException as error:
 row.update(status='FAILED_PRESERVED',error=repr(error));raise
finally:
 f.common.save(C/'control.json',row)
