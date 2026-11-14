# SPDX-License-Identifier: Apache-2.0
"""Bound vendor SRAM LVS diagnostic. Native data remains on cloud runner."""
import hashlib,json,os,pathlib,subprocess,sys,tarfile,time,shutil
P=pathlib.Path
case=sys.argv[1];assert case in ('sp','dp')
mode=sys.argv[2];assert mode in ('deep','flat')
top={'sp':'RM_IHPSG13_1P_2048x64_c2_bm_bist','dp':'RM_IHPSG13_2P_256x16_c2_bm_bist'}[case]
pins={'sp':('48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00','734647f8383209c7e08fc8e66a2914a3acaa33e1848b9ff33b6a4a2ed3c2ec61'),'dp':('420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b','1b307d5bd84ba57087717c1d1e631959352c6d20a27167b3ed08f637e3d312a8')}[case]
out=P('out');native=out/'native';derived=out/'derived'
native.mkdir(parents=True);derived.mkdir()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
r={'status':'PREPARING','top':top,'run_id':os.environ.get('GITHUB_RUN_ID'),'source_sha':os.environ.get('GITHUB_SHA'),'current_vendor_macro_lvs_passed':False,'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Experimental strict metal1/LVSRES class interpretation with native negative controls. Frozen geometry and CDL unchanged. Original PDK deck otherwise unchanged; not production qualification.'}
rc=2
try:
 assert sha(P('pkg.tgz'))=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 with tarfile.open('pkg.tgz','r:gz') as t:
  cs=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/input-contract.json')];assert len(cs)==1
  c=json.loads(t.extractfile(cs[0]).read());prefix=str(P(cs[0].name).parent)+'/files/';restored={}
  for name,info in c['input_files'].items():
   if '/libs.tech/klayout/' not in name and not (name.endswith('/'+top+'.gds') or name.endswith('/'+top+'.cdl')):continue
   rel=P(name);assert not rel.is_absolute() and '..' not in rel.parts
   data=t.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==info['sha256']
   dest=native/'inputs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);restored[name]=info['sha256']
 (native/'restored-inputs.json').write_text(json.dumps(restored,indent=2))
 def unique(suffix):
  paths=[native/'inputs'/n for n in restored if n.endswith(suffix)];assert len(paths)==1;return paths[0].resolve()
 gds=unique('/'+top+'.gds');cdl=unique('/'+top+'.cdl');deck=unique('/lvs/sg13g2.lvs')
 assert (sha(gds),sha(cdl))==pins
 assert sha(P('/tmp/klayout.deb'))=='0bb6b913fd6a32581d50b08be744b522a2a477baa1ed7e253c97cc18ce248a24'
 app=P(shutil.which('klayout')).resolve()
 version=subprocess.check_output([str(app),'-b','-v'],text=True).strip();assert version=='KLayout 0.30.13',version
 r['klayout_version']=version;r['runtime_package_sha256']=sha(P('/tmp/klayout.deb'))
 r.update(gds_sha256=sha(gds),cdl_sha256=sha(cdl),deck_sha256=sha(deck),restored_inputs_sha256=sha(native/'restored-inputs.json'),runtime_sha256=sha(app))
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None);env['APPIMAGE_EXTRACT_AND_RUN']='1';env['QT_QPA_PLATFORM']='offscreen'
 switches=dict(input=gds,schematic=cdl,topcell=top,report=(native/'lvs.lvsdb').resolve(),log=(native/'deck.log').resolve(),target_netlist=(native/'extracted.cir').resolve(),run_mode=mode,no_simplify='true',no_series_res='true',no_parallel_res='true',combine_devices='true',allow_unmatched_ports='false',purge='false',purge_nets='false',top_lvl_pins='false',net_only='false',verbose='false')
 r['normalization']='Native combine_devices on both extracted and original reference; no simplify/purge, no parameter tolerances added, no reference or layout edits.'
 r['switches']={k:str(v) for k,v in switches.items()};cmd=[str(app),'-b','-zz','-r',str(deck)]
 for k,v in switches.items():cmd+=['-rd',f'{k}={v}']

 # Apply only the exact two-line RES2 switch fix proven by native Ruby controls.
 import zipfile,io
 control_blob=P('merge-controls.zip').read_bytes()
 assert hashlib.sha256(control_blob).hexdigest()=='b58b9142d77cb2f5b429ea23df5854b5e65f5bb19158561d635f9be9872214da'
 control=json.loads(zipfile.ZipFile(io.BytesIO(control_blob)).read('merge-switch-controls.json'))
 assert control['status']=='PASS_ISOLATED_MERGE_SWITCH_CONTROLS' and len(control['cases'])==16
 assert control['source_sha']=='e8c09d6041199f1b57b2f7122621909ac9a5ec58'
 devices=deck.parent/'rule_decks/custom_devices.lvs'
 assert sha(devices)==control['original_custom_devices_sha256']
 before_source=devices.read_text();old_class=control['original_RES2_source'];new_class=control['candidate_RES2_source']
 assert before_source.count(old_class)==1
 assert new_class==old_class.replace('    super\n','    super\n    self.supports_serial_combination = SERIES_RES\n    self.supports_parallel_combination = PARALLEL_RES\n')
 devices.write_text(before_source.replace(old_class,new_class))
 r['resistor_merge_switch_fix']={'control_run':43553545114,'control_artifact_sha256':hashlib.sha256(control_blob).hexdigest(),'before_sha256':hashlib.sha256(before_source.encode()).hexdigest(),'after_sha256':sha(devices),'scope':'Honor requested serial/parallel disable switches during native combine_devices; MOS combination unchanged; no SRAM geometry/CDL/tolerance changes.'}

 # Scoped metal1 model interpretation controls; original geometry/CDL stay unchanged.
 import re
 cell='RSC_IHPSG13_CDLYX1_DUMMY'
 blocks=re.findall(r'(?ims)^\.subckt\s+'+re.escape(cell)+r'\b.*?^\.ends[^\n]*',cdl.read_text())
 assert len(blocks)==1
 reference=blocks[0]+'\n'
 resistor_lines=[line for line in reference.splitlines() if re.search(r'(?i)\blvsres\b',line)]
 assert len(resistor_lines)==1
 resistor=resistor_lines[0]
 assert re.search(r'(?i)\bw\s*=\s*2\.6e-07\b',resistor)
 assert re.search(r'(?i)\bl\s*=\s*6e-07\b',resistor)
 reader=deck.parent/'rule_decks/custom_reader.lvs'
 extraction=deck.parent/'rule_decks/res_extraction.lvs'
 reader_before=reader.read_text();extraction_before=extraction.read_text()
 reader_needle="    elsif num_nets == 2 && model.downcase.include?('tap')"
 assert reader_before.count(reader_needle)==1
 extraction_needle="resistor('res_metal1', 1.0, RES2)"
 assert extraction_before.count(extraction_needle)==1
 variants={'original':reference,
  'wrong_width':reference.replace(resistor,re.sub(r'(?i)(\bw\s*=\s*)\S+',lambda m:m[1]+'2.8e-07',resistor)),
  'wrong_length':reference.replace(resistor,re.sub(r'(?i)(\bl\s*=\s*)\S+',lambda m:m[1]+'7e-07',resistor))}
 tokens=resistor.split();assert tokens[0][0].upper()=='R';tokens[1]='NSSOC_FAULT_OPEN'
 variants['open']=reference.replace(resistor,' '.join(tokens))
 controls=[]
 def control(label,text,expected):
  target=native/('control-'+label);target.mkdir()
  reference_path=(target/'reference.cdl').resolve();reference_path.write_text(text)
  overrides={'schematic':reference_path,'topcell':cell,'top_lvl_pins':'true','report':(target/'lvs.lvsdb').resolve(),'log':(target/'deck.log').resolve(),'target_netlist':(target/'extracted.cir').resolve()}
  command=[str(app),'-b','-zz','-r',str(deck)]
  for k,v in {**switches,**overrides}.items():command+=['-rd',f'{k}={v}']
  with (target/'run.log').open('w') as f:proc=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert proc.returncode==0, 'Control extraction failed: '+label
  audit_path=target/'audit.json'
  proc=subprocess.run([sys.executable,'hw/soc/flow/audit_klayout_lvs.py',str(target/'lvs.lvsdb'),'--top',cell,'--deck-log',str(target/'deck.log'),'--output',str(audit_path)],env=env,capture_output=True,text=True,timeout=120)
  assert audit_path.exists(), 'Missing control comparison: '+label
  report=json.loads(audit_path.read_text())
  assert not report['extraction_diagnostics'], 'Control extraction diagnostics: '+label
  assert len(report['circuits'])==1 and report['circuits'][0]['layout_devices_recursive']==3 and report['circuits'][0]['schematic_devices_recursive']==3
  full_leaf_lvs_passed=proc.returncode==0 and not report['reasons']
  import klayout.db as kdb
  database=kdb.LayoutVsSchematic();database.read(str(target/'lvs.lvsdb'))
  pairs=list(database.xref().each_circuit_pair());assert len(pairs)==1
  pair=pairs[0]
  def field(obj,name):
   value=getattr(obj,name);return value() if callable(value) else value
  assert {field(pin,'name') for pin in pair.first().each_pin()}=={'A','Z'}
  assert {field(pin,'name') for pin in pair.second().each_pin()}=={'A','Z','VDD','VSS'}
  net_pairs=[{'layout':field(n.first(),'name') if n.first() else None,'reference':field(n.second(),'name') if n.second() else None,'status':str(n.status())} for n in database.xref().each_net_pair(pair)]
  signal_ports_match=all(sum(n['layout']==port and n['reference']==port and n['status']=='Match' for n in net_pairs)==1 for port in ('A','Z'))
  graph_match=report['circuits'][0]['status']=='Match'
  passed=graph_match and signal_ports_match
  controls.append({'label':label,'expected_graph_and_signal_ports_match':expected,'device_graph_match':graph_match,'signal_ports_match':signal_ports_match,'graph_and_signal_ports_match':passed,'net_pairs':net_pairs,'full_leaf_lvs_passed':full_leaf_lvs_passed,'audit':report,'reference_sha256':sha(reference_path)})
  (derived/'metal1-mapping-controls.json').write_text(json.dumps({'scope':'DEVICE GRAPH AND EXACT A/Z SIGNAL PORT CONTROLS ONLY: original leaf has A/Z ports while reference also declares VDD/VSS. Full leaf LVS verdict remains separately recorded and is not waived. No geometry, dimension, connection, or full-macro acceptance changes.','controls':controls,'production_accepted':False},indent=2))
  assert passed==expected, 'Unexpected control verdict: '+label
 control('unmapped-original',reference,False)
 reader.write_text(reader_before.replace(reader_needle,"    elsif num_nets == 2 && model.downcase == 'lvsres'\n      RES2.new\n"+reader_needle))
 extraction.write_text(extraction_before.replace(extraction_needle,"resistor('lvsres', 1.0, RES2)"))
 r['experimental_mapping']={'scope':'Only extracted metal1 class name mapped to lvsres; reference lvsres uses existing RES2 W/L comparison policy; no circuit or dimension edits; no net aliases','reader_before_sha256':hashlib.sha256(reader_before.encode()).hexdigest(),'reader_after_sha256':sha(reader),'extraction_before_sha256':hashlib.sha256(extraction_before.encode()).hexdigest(),'extraction_after_sha256':sha(extraction),'production_accepted':False}
 for label,text in variants.items():control('mapped-'+label,text,label=='original')
 r['metal1_device_graph_and_signal_port_controls_passed']=True
 r['leaf_full_lvs_accepted']=False
 r['control_scope']='Model class interpretation and exact A/Z signal-port mapping only. Full leaf VDD/VSS failures remain recorded, not accepted. Full macro is audited with unchanged port/error acceptance rules.'



 # Versioned engineering reference candidate. Original CDL/GDS remain immutable.
 assert case=='sp' and mode=='deep'
 mapping_blob=P('bitcell-mapping.zip').read_bytes()
 assert hashlib.sha256(mapping_blob).hexdigest()=='9ef327edaad1aaa5c6d605e127c36c8fb658d464a9da3836cf6f47b5503314e2'
 mapping=json.loads(zipfile.ZipFile(io.BytesIO(mapping_blob)).read('bitcell-endpoint-diagnosis.json'))
 assert mapping['source']=='daf24ca240958f2ed85099b48f72bb0b44904487' and mapping['all_three_uniquely_anchored']
 layer_map={}
 for row in mapping['mapping']:
  assert row['unique_external_endpoint_match'] and len(row['candidate_layout_classes_and_dimensions'])==1
  v=row['candidate_layout_classes_and_dimensions'][0]
  assert abs(v['L']-.6)<1e-12 and abs(v['W']-.2)<1e-12
  layer_map['R'+row['reference_name']]=v['class']
 assert layer_map=={'R0':'res_metal2','R1':'res_metal2','R2':'res_metal3'}
 original_cdl=cdl.read_text();candidate=original_cdl;changes=[];reversible=[]
 specs=[('RM_IHPSG13_2048x64_c2_1P_BITKIT_CELL',layer_map,'2e-07'),('RSC_IHPSG13_MET2RES',{'R0':'res_metal2'},'2.6e-07'),('RSC_IHPSG13_MET3RES',{'R0':'res_metal3'},'2.6e-07')]
 for cell_name,layers,width in specs:
  blocks=re.findall(r'(?ims)^\.subckt\s+'+re.escape(cell_name)+r'\b.*?^\.ends[^\n]*',candidate)
  assert len(blocks)==1,cell_name
  before=blocks[0];after=before;seen=set()
  for match in re.finditer(r'(?m)^[Rr][^\n]*(?:\n\+[^\n]*)*',before):
   line=match.group(0);name=line.split()[0].upper();assert name in layers and name not in seen;seen.add(name)
   assert len(re.findall(r'(?i)\blvsres\b',line))==1
   assert re.search(r'(?i)\bw\s*=\s*2\.6e-07\b',line) and re.search(r'(?i)\bl\s*=\s*6e-07\b',line)
   revised=re.sub(r'(?i)\blvsres\b',layers[name],line)
   revised=re.sub(r'(?i)(\bw\s*=\s*)2\.6e-07\b',lambda m:m[1]+width,revised)
   # Explicitly prove restoration: only model identity and W token changed.
   restored=re.sub(r'(?i)\b'+layers[name]+r'\b','LVSRES',revised)
   restored=re.sub(r'(?i)(\bw\s*=\s*)'+re.escape(width)+r'\b',lambda m:m[1]+'2.6e-07',restored)
   assert restored.lower()==line.lower()
   assert after.count(line)==1;after=after.replace(line,revised)
   changes.append({'cell':cell_name,'resistor':name,'before_class':'LVSRES','after_class':layers[name],'before_width_m':2.6e-7,'after_width_m':float(width),'length_m':6e-7,'terminal_tokens_unchanged':line.split()[1:3]==revised.split()[1:3]})
  assert seen==set(layers)
  assert candidate.count(before)==1;candidate=candidate.replace(before,after);reversible.append((before,after))
 restored=candidate
 for before,after in reversed(reversible):
  assert restored.count(after)==1;restored=restored.replace(after,before)
 assert restored==original_cdl and len(changes)==5 and all(x['terminal_tokens_unchanged'] for x in changes)
 candidate_path=(native/'engineering-reference-v1.cdl').resolve();candidate_path.write_text(candidate)
 reader_current=reader.read_text();target="    elsif num_nets == 2 && model.downcase == 'lvsres'\n      RES2.new\n"
 assert reader_current.count(target)==1
 reader.write_text(reader_current.replace(target,"    elsif num_nets == 2 && ['lvsres', 'res_metal2', 'res_metal3'].include?(model.downcase)\n      RES2.new\n"))
 # Distinct model names retained; RES2 compares strict dimensions and disables merging.
 switches['schematic']=candidate_path
 cmd=[str(app),'-b','-zz','-r',str(deck)]
 for k,v in switches.items():cmd+=['-rd',f'{k}={v}']
 r['scope']='Engineering reference candidate v1, NOT original vendor acceptance: five R statements in three cells change only independently diagnosed model/W tokens. Geometry, all terminal connections, other devices, strict ports and dimensions unchanged. Full macro comparison includes original well/tap context. No body aliases. Negative layer/width/open controls and vendor qualification remain pending.'
 r['normalization']='Strict unmerged RES2 and original SP hierarchy; candidate reference explicitly different from immutable original CDL.'
 r['switches']={k:str(v) for k,v in switches.items()}
 r['engineering_reference']={'original_sha256':sha(cdl),'candidate_sha256':sha(candidate_path),'changes':changes,'mapping_run':43564703460,'mapping_artifact':14101134348,'reader_sha256':sha(reader),'all_other_reference_text_unchanged':True,'geometry_unchanged':sha(gds)==pins[0],'negative_controls_complete':False,'vendor_approved':False}
 (derived/'engineering-reference-change.json').write_text(json.dumps(r['engineering_reference'],indent=2))

 # SP starts with original hierarchy: no DP-specific flatten targets/counts.
 r['hierarchy_normalization']='Six SP-specific unmatched boundaries flattened identically on both sides; all1211120 primitives retained; no purge/body aliases.'
 def inventory(text):
  import collections
  logical=[]
  for line in text.splitlines():
   line=line.strip()
   if not line or line.startswith('*'):continue
   if line.startswith('+'):
    assert logical;logical[-1]+=' '+line[1:].strip()
   else:logical.append(line)
  cells={};current=None
  for line in logical:
   tok=line.split();tag=tok[0].lower()
   if tag=='.subckt':
    current=tok[1].casefold();assert current not in cells
    cells[current]={'devices':collections.Counter(),'children':collections.Counter()}
   elif tag=='.ends':current=None
   elif current is not None and not tag.startswith('.'):
    if tag.startswith('x'):
     assert '=' not in line,'Parameterized hierarchy needs explicit count parser'
     cells[current]['children'][tok[-1].casefold()]+=1
    else:
     assert tag[0] in 'mrcqd','Unexpected primitive type: '+tag
     cells[current]['devices'][tag[0]]+=1
  assert current is None
  cache={}
  def count(name,active):
   assert name in cells and name not in active
   if name in cache:return cache[name].copy()
   total=cells[name]['devices'].copy()
   for child,n in cells[name]['children'].items():
    for kind,value in count(child,active|{name}).items():total[kind]+=n*value
   cache[name]=total;return total.copy()
  return {'expanded_primitive_counts_before_native_combination':dict(count(top.casefold(),set())),'defined_cells':len(cells)}
 before_inventory=inventory(original_cdl);after_inventory=inventory(candidate)
 assert before_inventory==after_inventory and sum(before_inventory['expanded_primitive_counts_before_native_combination'].values())>0
 r['reference_primitive_inventory']=before_inventory
 (derived/'reference-inventory.json').write_text(json.dumps({'original':before_inventory,'candidate':after_inventory,'all_counts_preserved':True,'scope':'CDL source inventory before native MOS combination; not physical connectivity or LVS acceptance'},indent=2))
 # Normalize only the six remaining hierarchy boundaries after all model controls.
 deck_before=deck.read_text()
 anchor='\n# PURGE\nnetlist.purge if PURGE\n'
 assert deck_before.count(anchor)==1
 flatten_ruby='\n# Experimental representation normalization only: preserve every primitive.\nrequire \'json\'\ndef nssoc_device_count(circuit, cache = {}, active = [])\n  raise \'Missing circuit\' unless circuit\n  name = circuit.name\n  raise \'Recursive hierarchy\' if active.include?(name)\n  return cache[name] if cache.key?(name)\n  total = circuit.each_device.to_a.size\n  circuit.each_subcircuit { |sub| total += nssoc_device_count(sub.circuit_ref, cache, active + [name]) }\n  cache[name] = total\nend\nnssoc_names = %w[RSC_IHPSG13_CBUFX8 RSC_IHPSG13_CINVX2 RSC_IHPSG13_CINVX8 RSC_IHPSG13_FILLCAP4 RSC_IHPSG13_FILLCAP8 RSC_IHPSG13_WLDRVX8]\nnssoc_rows = []\n[[\'layout\', netlist], [\'reference\', schematic]].each do |label, nl|\n  tops = nl.each_circuit.select { |c| c.name.downcase == $topcell.downcase }\n  raise \'Top identity mismatch\' unless tops.size == 1\n  top_circuit = tops[0]\n  before = nssoc_device_count(top_circuit)\n  raise \'Unexpected frozen SP primitive count\' unless before == 1211120\n  selected = nssoc_names.map do |name|\n    matches = nl.each_circuit.select { |c| c.name.downcase == name.downcase }\n    raise "Missing/ambiguous flatten target #{name}" unless matches.size == 1\n    matches[0]\n  end\n  nl.flatten_circuits(selected)\n  after = nssoc_device_count(top_circuit)\n  raise \'Flattening changed recursive primitive count\' unless before == after\n  nssoc_rows << {\'side\'=>label,\'before\'=>before,\'after\'=>after,\'flattened_circuits\'=>nssoc_names}\nend\nFile.write($nssoc_flatten_report, JSON.pretty_generate({\'scope\'=>\'Selective hierarchy normalization only; no primitive exclusion, circuit edits or acceptance waiver\',\'rows\'=>nssoc_rows,\'production_accepted\'=>false}))\n'
 deck.write_text(deck_before.replace(anchor,flatten_ruby+anchor))
 r['selective_flatten_deck_sha256']=sha(deck)
 r['selective_flatten_scope']='Six named remaining cells, both sides; recursive primitive counts must remain 1211120. Engineering reference changes separately recorded; no geometry, primitive exclusion, net alias, dimensional tolerance or final port acceptance changes.'
 cmd+=['-rd','nssoc_flatten_report='+str((derived/'selective-flatten.json').resolve())]

 (native/'command.json').write_text(json.dumps(cmd));start=time.monotonic()
 with (native/'run.log').open('w') as f:
  p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=18000)
 r['extraction_returncode']=p.returncode;r['elapsed_seconds']=time.monotonic()-start
 if p.returncode!=0:raise RuntimeError('KLayout execution failed; native log retained in cloud')
 audit=[sys.executable,'hw/soc/flow/audit_klayout_lvs.py',str(native/'lvs.lvsdb'),'--top',top,'--deck-log',str(native/'deck.log'),'--output',str(derived/'audit.json')]
 with (native/'audit.log').open('w') as f:a=subprocess.run(audit,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 r['audit_returncode']=a.returncode
 if not (derived/'audit.json').exists():raise RuntimeError('Independent result audit failed to produce report')
 report=json.loads((derived/'audit.json').read_text());passed=(a.returncode==0 and report['status']=='PASS within comparison scope' and not report['reasons'])
 r['engineering_candidate_comparison_passed']=passed;r['current_vendor_macro_lvs_passed']=False;r['status']='PASS_ENGINEERING_REFERENCE_COMPARISON_ONLY_NOT_QUALIFIED' if passed else 'FAIL_ENGINEERING_REFERENCE_COMPARISON';rc=0 if passed else 1
except Exception as e:r['status']='ERROR_OR_INCOMPLETE_LVS';r['error']=type(e).__name__+': '+str(e)
finally:
 r['native_outputs']={str(p.relative_to(native)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in native.iterdir() if p.is_file()}
 (derived/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));sys.exit(rc)
