#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict whole PLL845 native R/C point/value audit with preserved original gates."""
import difflib,hashlib,importlib.util,io,json,os,re,subprocess,sys,tokenize
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import compare_cloud_routed_endpoints as reports
import audit_pll845_mim_intrinsic as intrinsic
from cloud_cdr_v4_rc import NONBRIDGE_SELECTOR
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-raw-audit'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,
  full_phy_accepted=False,raw_rc_audit_passed=False,accepted=False,native_CAD_repeated=False,
  controller_sha256=sha(Path(__file__)),intrinsic_helper_sha256=sha(Path(intrinsic.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(cmd,label):
  path=OUT/(label+'.log')
  with path.open('w')as stream:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(path)));save()
  if code:print(path.read_text(errors='replace')[-14000:],flush=True)
  assert code==0,(label,code)
 save()
 try:
  review,rproof=reports.restore_report('pll-rhi120-c8-rc-review',39917135843,
   'f616d64ac2de5d166b478374fdf52326c2c4bc4b01b6091c0b8908e0ad332985',
   'f04c1497a7e3fe16166a26c1ac896d60ec69f91b124987ca73c705d1fc2c1064',OUT/'review',['mim-comparison.json'])
  assert review['status']=='PASS_PLL845_PRESERVED_NATIVE_CAPTURE_AND10_CONTROL_FAMILIES_REQUIRES_RAW_RC_AUDIT'
  assert review['source_head']=='eb2036566d63070e411171600f8501ddac59dba8'and review['sources_unchanged']
  assert len(review['capture_controls'])==8 and all(x['rejected']for x in review['capture_controls'])
  assert len(review['dimension_controls'])==2 and all(x['rejected']and x['actual_source_device_cases']==26 for x in review['dimension_controls'])
  assert review['intrinsic_capture_binding']['all_mim_identities_unique']
  r['capture_review_source']=rproof
  names=['wire/anchors08.json','source/source/native-mim-geometry.json','native-inputs.json',
   'wire/rc03/wires.spice','wire/rc03/baseline.spice','wire/rc03/pump_wires.ext',
   'wire/rc03/pump_wires.res.ext','wire/rc03/native.log','wire/rc03/result.json',
   'wire/run-rc01.py','wire/native05/wires.gds']
  prior,proof=reports.restore_report('pll-rhi120-c8-rc',39916625651,
   'c13eb417f3c9a8cfe4dc2260dd58233f171a410314209f5a2952643c1e3d57fd',
   'c55f4dd64cff7b31647a343036ec4d62f8c7324463b8c591d6dfddea8cad7b18',OUT/'capture',names)
  assert proof['summary_sha256']==review['capture_source']['summary_sha256']and proof['run']==review['capture_source']['run']
  assert prior['capture']['returncode']==0 and prior['native_inputs']['physical_points']==1604
  r['capture_source']=proof;save()
  B=OUT/'capture/wire';P=B/'rc03';anchors=json.loads((B/'anchors08.json').read_text())
  assert anchors['logical_anchor_count']==1877 and anchors['physical_anchor_count']==1604
  methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
  meta=methods['audit-rc48.py'];text=meta['text'];assert hashlib.sha256(text.encode()).hexdigest()==meta['sha256'];edits=[]
  def replace(before,after):
   nonlocal text
   assert text.count(before)==1,(before,text.count(before));text=text.replace(before,after);edits.append(dict(before=before,after=after))
  replace('original_devices=54','original_devices=845')
  number_map={'12':'17','17':'235','18':'236','112':'1604','154':'2737','54':'819','100':'1860'}
  tokens=[];counts=Counter()
  for tok in tokenize.generate_tokens(io.StringIO(text).readline):
   if tok.type==tokenize.NUMBER and tok.string in number_map:
    counts[tok.string]+=1;tok=tok._replace(string=number_map[tok.string])
   tokens.append(tok)
  assert set(counts)==set(number_map)
  text=tokenize.untokenize(tokens);edits.append(dict(numeric_census_changes=dict(counts),mapping=number_map))
  replace("==['18']","==['236']");replace("==['17']","==['235']")
  replace("anchors['dispositions']","anchors['counts']['dispositions']")
  replace("dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1860,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=819)",
   "dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1860,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING=819,RETAINED_SHARED_INTRINSIC_DIFFUSION_NO_METAL_OR_DIFFUSION_R=58)")
  replace('logical=f"T{r[\'device\']:03d}_{r[\'terminal\']}"',"logical=r['reference_label']")
  replace('shared_diffusion_terminals=0','shared_diffusion_terminals=58')
  replace('import networkx as nx','import networkx as nx\nsys.path.insert(0,str(Path.cwd()/"scripts"))\nfrom audit_pll845_mim_intrinsic import validate_mim')
  replace("require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')",
   "require(not before['resistors'],'Unexpected baseline resistor insertion')")
  replace("require(native_r==export_r,'Native/export resistor topology/value differs')",
   "require(native_r==export_r,'Native/export resistor topology/value differs')\n mim_proof=validate_mim(rows,rep,before,after,original,owners,anchors)")
  replace('original_devices=845,','native_mim_intrinsic=mim_proof,original_devices=845,')
  target=B/'audit-rc48.py';assert not target.exists();target.write_text(text)
  r['auditor_adaptation']=dict(original_sha256=meta['sha256'],adapted_sha256=sha(target),edits=edits)
  meta=methods['mutations48.py'];text=meta['text'];assert hashlib.sha256(text.encode()).hexdigest()==meta['sha256'];changes=[]
  def mutate(before,after):
   nonlocal text
   assert text.count(before)==1,(before,text.count(before));text=text.replace(before,after);changes.append(dict(before=before,after=after))
  choose="fault_a=a['anchors'][0]['label'];fault_b=next(x['label']for x in a['anchors']if x['wire_component']!=a['anchors'][0]['wire_component'])\n"
  mutate('cases=[\n',NONBRIDGE_SELECTOR+choose+'cases=[\n')
  mutate(r"re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)",'dropped_text')
  mutate("text.replace('.ends','R_EXTRA P_cp P_cn 1\\n.ends')","text.replace('.ends',f'R_EXTRA {fault_a} {fault_b} 1\\n.ends')")
  # Body identity checks now include the same819 retained body/well rows.
  count=text.count('RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE');assert count==2
  text=text.replace('RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE','RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING')
  changes.append(dict(before='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',after='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING',count=count))
  mutate("x['dispositions']","x['counts']['dispositions']")
  mutations=B/'mutations48.py';assert not mutations.exists();mutations.write_text(text)
  r['wire_mutation_adaptation']=dict(original_sha256=meta['sha256'],adapted_sha256=sha(mutations),edits=changes)
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
  raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
  raw.parent.mkdir(parents=True,exist_ok=True);fetch(spec['raw_parser']['url'],spec['raw_parser']['sha256'],raw);save()
  run([sys.executable,target,P,B/'anchors08.json',B/'audit.json'],'strict-whole-pll-native-RC')
  r['audit']=json.loads((B/'audit.json').read_text());save()
  assert r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
  assert r['audit']['actual_exported_resistors']==3380 and r['audit']['actual_exported_capacitors']==5104
  assert r['audit']['native_mim_intrinsic']['devices']==26
  run([sys.executable,mutations],'thirteen-raw-wire-corruptions')
  r['wire_controls']=json.loads((B/'native-mutations01.json').read_text());save()
  assert len(r['wire_controls']['cases'])==13
  ms=importlib.util.spec_from_file_location('pll_strict',target)
  module=importlib.util.module_from_spec(ms);ms.loader.exec_module(module)
  texts={n:(P/n).read_text()for n in ('wires.spice','baseline.spice','pump_wires.ext','pump_wires.res.ext')}
  original_rows=texts['wires.spice'].splitlines();idx=next(i for i,x in enumerate(original_rows)if x.startswith('X'));x=original_rows[idx].split();cases=[]
  def spice_case(name,change):
   lines=original_rows.copy();fields=x.copy();change(fields)
   if fields:lines[idx]=' '.join(fields)
   else:del lines[idx]
   cases.append((name,'wires.spice','\n'.join(lines)+'\n'))
  spice_case('missing_export_mim',lambda f:f.clear())
  spice_case('wrong_export_model',lambda f:f.__setitem__(3,'cap_rfcmim'))
  spice_case('wrong_export_width',lambda f:f.__setitem__(next(i for i,t in enumerate(f)if t.startswith('w=')),'w=999u'))
  spice_case('swapped_export_plates',lambda f:f.__setitem__(slice(1,3),list(reversed(f[1:3]))))
  for name,filename,transform in [
   ('missing_source_device','pump_wires.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
   ('wrong_source_dimension','pump_wires.ext',lambda t:re.sub(r'^(device .*? w=)\S+',r'\g<1>999999',t,count=1,flags=re.M)),
   ('missing_replacement_device','pump_wires.res.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
   ('shifted_replacement_location','pump_wires.res.ext',lambda t:re.sub(r'^(device csubckt cap_cmim )\d+',r'\g<1>1',t,count=1,flags=re.M)),
   ('wrong_parameter_declaration','pump_wires.ext',lambda t:t.replace('parameters cap_cmim w=w l=l','parameters cap_cmim w=l l=w',1))]:
   cases.append((name,filename,transform(texts[filename])))
  read_text=Path.read_text;r['intrinsic_controls']=[]
  for name,filename,changed in cases:
   assert changed!=texts[filename]
   def changed_read(path,*args,**kwargs):return changed if path==P/filename else read_text(path,*args,**kwargs)
   with patch.object(Path,'read_text',changed_read):
    try:module.audit(P,anchors)
    except ValueError as e:reason=str(e)
    else:raise AssertionError('Accepted '+name)
   assert 'MIM'in reason,(name,reason)
   r['intrinsic_controls'].append(dict(name=name,rejected=True,reason=reason,sha256=hashlib.sha256(changed.encode()).hexdigest(),
    diff=''.join(difflib.unified_diff(texts[filename].splitlines(True),changed.splitlines(True)))))
  assert len(r['intrinsic_controls'])==9
  assert all(sha(OUT/'capture'/n)==prior['outputs'][n]for n in names)
  assert sha(target)==r['auditor_adaptation']['adapted_sha256']and sha(mutations)==r['wire_mutation_adaptation']['adapted_sha256']
  assert sha(Path(intrinsic.__file__))==r['intrinsic_helper_sha256']and sha(Path(__file__))==r['controller_sha256']
  assert sha(raw)==spec['raw_parser']['sha256']
  r.update(status='PASS_PLL845_WHOLE_RAW_RC_AND22_CONTROLS_REQUIRES_INTRINSIC_COMPOSITION_AND_LOADED_WAVES',sources_unchanged=True,raw_rc_audit_passed=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
