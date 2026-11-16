import os,subprocess,json,hashlib,zipfile,io
from pathlib import Path
import cdr_mos650_gate_ac as source
import cdr_mos650_full650 as full
import cdr_mos650_clock_buffer_loaded as loaded
source.NATIVE.mkdir(parents=True);source.DERIVED.mkdir(parents=True);context=source.gate()
r=source.api('actions/runs/43750397504');assert r['conclusion']=='success'and r['head_sha']=='9e0a97f52829c8b7724076559fb67966640c411e'and r['run_attempt']==1
m=source.api('actions/artifacts/14176147111');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:6233dc9e8514c834d50cbe5f0350fcfc6ce13e4cebc1060b1a0cf8634a059957'and not m['expired']
b=subprocess.check_output(['gh','api','repos/'+source.REPO+'/actions/artifacts/14176147111/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b))
proof=json.loads(z.read('derived/result.json'));assert proof['status']=='PASS_CURRENT_WIDTH2_FULL650_COMPOSITION_REQUIRES_LOADED_ELECTRICAL'and proof['metal_R']==28458 and proof['metal_C']==18384 and proof['native_MIM']==7
controls=json.loads(z.read('derived/composition-controls.json'));assert len(controls['cases'])==3 and all(x['rejected']for x in controls['cases'])
n=int(os.environ['GATE_PARTITION']);case=os.environ['LOADED_CASE'];assert n==1 and case=='nominal_late'
record=next(x for x in proof['partitions']if x['partition']==n);target=source.NATIVE/'composition-n1';target.mkdir()
for leaf,key in [('model.cir','model'),('contract.json','contract'),('probes.json','probes')]:
 data=z.read('native/composition-n1/'+leaf);p=target/leaf;p.write_bytes(data);assert source.pin(p)==record[key]
assert record['model']['sha256']=='7aa759f68d570eb0bbbecef16dea6f9d7877c558fd3b53c2fcd892a841c39072'
contract=source.read(target/'contract.json');bound=source.read(target/'probes.json');assert full.probes(contract)==bound
source.save('loaded-source-binding.json',dict(context=context,composition_run=r['id'],artifact=m['id'],archive_sha256=m['digest'][7:],selected_partition=record,physical_devices=650,source_gds_sha256='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a',full_phy_accepted=False))
fixture_bytes=z.read('derived/current-physical-cases.json');fixture=json.loads(fixture_bytes)
mos={d['native_id']:d['native_parameters']for d in contract['devices']if d['model']=='sg13_lv_nmos'}
assert len(mos)==len(fixture['devices'])==200 and {d['native_id']:d['parameters']for d in fixture['devices']}==mos
(source.DERIVED/'current-physical-cases.json').write_bytes(fixture_bytes)
cfg=source.read(source.ROOT/source.CFG);models=source.acquire_models(cfg['runtime']);source.model_report(models);variant=source.intrinsic_variant(models)
engine=source.NATIVE/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
# Exploratory resistor sizing only: baseline physical RC is retained, so this
# is NOT an extracted model of a changed layout and cannot qualify physical PHY.
import copy
candidate_contract=copy.deepcopy(contract);text=(target/'model.cir').read_text();changes=[]
approved={377:(6.,2.),378:(8.6,2.),379:(6.,2.),380:(8.6,2.),381:(3.6,1.),382:(21.6,1.),383:(3.6,1.),384:(21.6,1.),400:(3.6,1.),401:(21.6,1.),402:(3.6,1.),403:(21.6,1.)}
for d in candidate_contract['devices']:
 if d['native_id']not in approved:continue
 length,width=approved[d['native_id']];assert d['model']=='rppd'and d['native_parameters']['l']==length and d['native_parameters']['w']==width
 assert len(d['instances'])==1
 inst=d['instances'][0];old=inst['parameters']['l'];assert float(old.removesuffix('u'))==length
 new_length=length*width/4.;new=format(new_length,'.12g')+'u'
 assert new_length>=.9 and new_length<length
 lines=text.splitlines();hits=[i for i,line in enumerate(lines)if line.split()and line.split()[0]==inst['name']];assert len(hits)==1
 tokens=lines[hits[0]].split();assert tokens.count('l='+old)==1;tokens[tokens.index('l='+old)]='l='+new;lines[hits[0]]=' '.join(tokens);text='\n'.join(lines)+'\n'
 inst['parameters']['l']=new;d['native_parameters']['l']=new_length;changes.append(dict(native_id=d['native_id'],width_um=width,old_length_um=length,new_length_um=new_length,nominal_l_over_w=new_length/width))
assert len(changes)==12
# Controlled native-MIM compensation experiment: retain original3200ohm clock bias
# and shortened-resistor baseline. Double both plate dimensions of six existing
# feed-forward capacitors; no ideal capacitors or extra devices. Metal RC remains
# OLD, so this exploratory model is explicitly not geometry-matched or signoff.
clock=source.ROOT/'scripts/cdr_cascode_clock_buffer_candidate.inc'
assert source.pin(clock)['sha256']=='9fe065eb58122f85d484dbb5977585b550403c15afd5a7f44167c40b2e78b77d'
cap_changes=[]
expected_caps={423:('dqp','usp'),424:('dqn','usn'),425:('aqp','uap'),426:('aqn','uan'),427:('cqp','ucp'),428:('cqn','ucn')}
for d in candidate_contract['devices']:
 if d['native_id']not in expected_caps:continue
 assert d['model']=='cap_cmim' and len(d['instances'])==1
 assert (d['logical_terminals']['MIM_TOP'],d['logical_terminals']['MIM_BTM'])==expected_caps[d['native_id']]
 inst=d['instances'][0];before=copy.deepcopy(d['native_parameters']);old_parameters=copy.deepcopy(inst['parameters'])
 lines=text.splitlines();hits=[i for i,line in enumerate(lines)if line.split()and line.split()[0]==inst['name']];assert len(hits)==1
 tokens=lines[hits[0]].split()
 for axis in ['l','w']:
  old=inst['parameters'][axis];value=float(old.removesuffix('u'));assert abs(value-before[axis])<1e-9
  new=format(value*2,'.12g')+'u';assert tokens.count(axis+'='+old)==1
  tokens[tokens.index(axis+'='+old)]=axis+'='+new;inst['parameters'][axis]=new;d['native_parameters'][axis]=value*2
 d['native_parameters']['A']=before['A']*4;d['native_parameters']['P']=before['P']*2
 lines[hits[0]]=' '.join(tokens);text='\n'.join(lines)+'\n'
 cap_changes.append(dict(native_id=d['native_id'],logical_terminals=d['logical_terminals'],old_parameters=old_parameters,new_parameters=copy.deepcopy(inst['parameters']),native_before=before,native_after=copy.deepcopy(d['native_parameters'])))
assert len(cap_changes)==6 and len(candidate_contract['devices'])==650
source.save('divider-mim-area4-experiment.json',dict(baseline_run=43776904300,changes=cap_changes,clock=source.pin(clock),native_device_count=650,native_mim_count=7,physical_geometry_matches=False,full_phy_accepted=False,unchanged_original_electrical_gates=True,scope='Existing six native MIM feed-forward plates get4x area/2x perimeter relative to shortened-resistor3200ohm baseline. OLD metal RC and original substrate model; not extracted candidate or layout acceptance.'))
candidate_contract['physical_geometry_matches']=False
candidate_contract['scope']='Exploratory twelve shortened divider resistors plus six existing native MIM plate dimensions doubled, using OLD baseline metal/gate RC. Not a physically extracted candidate, not layout or PHY acceptance.'
candidate=target/'candidate-model.cir';candidate.write_text(text)
(target/'candidate-contract.json').write_bytes(source.enc(candidate_contract))
source.save('divider-short-length-experiment.json',dict(changes=changes,baseline_model_sha256=source.pin(target/'model.cir'),candidate_model=source.pin(candidate),physical_geometry_matches=False,full_phy_accepted=False,scope=candidate_contract['scope']))
bound=full.probes(candidate_contract)
result=loaded.run_loaded(source,models,variant,engine,candidate,candidate_contract,bound,case)
source.gate();source.save('selected-whole-loaded-summary.json',dict(case=case,partition=n,status=result['status'],all256bits_executed=True,unchanged_original_electrical_gates=True,full_phy_accepted=False,final_timing_complete=False))
