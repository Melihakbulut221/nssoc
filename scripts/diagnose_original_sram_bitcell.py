# SPDX-License-Identifier: Apache-2.0
"""Bound vendor SRAM LVS diagnostic. Native data remains on cloud runner."""
import hashlib,json,os,pathlib,subprocess,sys,tarfile,time,shutil
P=pathlib.Path
case='dp'
mode='deep'
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


 import re
 cell='RM_IHPSG13_2P_BITKIT_CELL';original_name='RM_IHPSG13_256x16_c2_2P_BITKIT_CELL'
 blocks=re.findall(r'(?ims)^\.subckt\s+'+re.escape(original_name)+r'\b.*?^\.ends[^\n]*',cdl.read_text());assert len(blocks)==1
 original=blocks[0]+'\n'
 reference=re.sub(r'(?i)\b'+re.escape(original_name)+r'\b',cell,original)
 assert reference.replace(cell,original_name)==original,'Only explicit subcircuit top-name translation permitted'
 elements=[x.strip() for x in original.splitlines() if x.strip() and not x.lstrip().startswith(('*','.','+'))]
 assert sum(x[0].upper()=='R' for x in elements)==6 and sum(x[0].upper()=='M' for x in elements)==8 and len(elements)==14
 reference_path=(native/'bitcell-original.cdl').resolve();reference_path.write_text(reference)
 reader=deck.parent/'rule_decks/custom_reader.lvs';source=reader.read_text()
 needle="    elsif num_nets == 2 && model.downcase.include?('tap')";assert source.count(needle)==1
 reader.write_text(source.replace(needle,"    elsif num_nets == 2 && model.downcase == 'lvsres'\n      RES2.new\n"+needle))
 switches.update(schematic=reference_path,topcell=cell,top_lvl_pins='true')
 command=[str(app),'-b','-zz','-r',str(deck)]
 for k,v in switches.items():command+=['-rd',f'{k}={v}']
 r.update(scope='Original isolated bitcell diagnostic: explicit top-name translation only, strict unmerged resistor dimensions and ports; no class/layer/width correction, no geometry changes. Not LVS acceptance.',original_reference_cell=original_name,physical_cell=cell,reference_sha256=sha(reference_path),reader_sha256=sha(reader))
 with (native/'run.log').open('w') as f:proc=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert proc.returncode==0,'Native extraction execution failed'
 audit_path=derived/'audit.json'
 audit=subprocess.run([sys.executable,'hw/soc/flow/audit_klayout_lvs.py',str(native/'lvs.lvsdb'),'--top',cell,'--deck-log',str(native/'deck.log'),'--output',str(audit_path)],env=env,capture_output=True,text=True,timeout=120)
 report=json.loads(audit_path.read_text());assert not report['extraction_diagnostics'];r['audit']=report
 import klayout.db as kdb
 db=kdb.LayoutVsSchematic();db.read(str(native/'lvs.lvsdb'));xref=db.xref()
 pairs=[p for p in xref.each_circuit_pair() if p.first() and p.first().name==cell];assert len(pairs)==1;pair=pairs[0]
 def field(o,n):
  v=getattr(o,n);return v() if callable(v) else v
 def device(d):
  if d is None:return None
  cls=field(d,'device_class')
  return {'name':field(d,'name'),'class':field(cls,'name'),'parameters':{field(p,'name'):d.parameter(field(p,'id')) for p in field(cls,'parameter_definitions')}}
 r['device_pairs']=[{'status':str(p.status()),'layout':device(p.first()),'reference':device(p.second())} for p in xref.each_device_pair(pair)]
 r['port_names']={label:[field(p,'name') for p in c.each_pin()] for label,c in [('layout',pair.first()),('reference',pair.second())]}
 r['status']='DIAGNOSTIC_COMPLETE_NOT_LVS_ACCEPTANCE';rc=0
except Exception as e:r['status']='ERROR_OR_INCOMPLETE_DIAGNOSTIC';r['error']=type(e).__name__+': '+str(e)
finally:
 r['native_outputs']={str(p.relative_to(native)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in native.iterdir() if p.is_file()}
 (derived/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k in ['status','error']}));sys.exit(rc)
