import os,json,subprocess,hashlib,zipfile,io,copy
from pathlib import Path
from decimal import Decimal
import cdr_mos650_gate_ac as source
import cdr_mos650_full650 as full
source.NATIVE.mkdir(parents=True);source.DERIVED.mkdir(parents=True)
context=source.gate()
def archive(run,head,aid,digest):
 r=source.api('actions/runs/'+str(run));assert r['conclusion']=='success'and r['head_sha']==head and r['run_attempt']==1
 m=source.api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest and not m['expired']
 b=subprocess.check_output(['gh','api','repos/'+source.REPO+'/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()));return z
proof=archive(43860719107,'88361396125c6e2a9da2536585f99b47212377b5',14223540358,'93168cf1b8d5adc1d716f6d65828f4caac709e6e0587273571ebc194434bf0fa')
gateproof=json.loads(proof.read('result.json'));assert gateproof['status']=='PASS_NOMINAL_PHYSICAL_GATE_PORT_REDUCTION_REQUIRES_FULL_NONLINEAR_AND_METAL_INTEGRATION'
fresh_cases=json.loads(proof.read('current-physical-cases.json'))
assert fresh_cases['source']['native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds']['sha256']=='1337c86e9bf28e68d93d3dcc2c80afc3040ecd7f21b32eb6b149896aa3490e11'
ids=archive(43858886164,'556dd5c9bc992e3df924039bf04c731d49e2b98e',14223215265,'3c3e4373bbddf712150e445cacc58e0e6ffd4cc169c95eb691065cdedb6c0bbf')
identity=json.loads(ids.read('lvs_flat-identity.json'))
wire=archive(43859272466,'02362d83177e828b9b422255423d6bb76b716029',14222347687,'f8c9d6ef41e7656ad7a8b03dce1fe7865de10441813b31811533008aa30f8c9c')
fixture=dict(devices=source.current_cases(identity,json.loads(wire.read('gate-poly-access.json'))))
assert fixture['devices']==fresh_cases['devices'], 'fresh geometry exact gate cases'
for member, raw in [('derived/lvs_flat-identity.json',ids.read('lvs_flat-identity.json')),('derived/gate-poly-access.json',wire.read('gate-poly-access.json'))]:
 assert fresh_cases['source'][member]==dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()), 'fresh gate source identity'
rc=archive(43864620012,'f3b8afa8ececf5663127ebe8643910aed4013ee7',14225206115,'82cd73377b84233e6a11abc654e2b43ce1331b1515dec7da2d24eef8128ed699')
result=json.loads(rc.read('derived/result.json'));assert result['status']=='PASS_CURRENT650_MIM_AWARE_TWO_ORDER_RC_AND22_FAULTS_EACH_REQUIRES_FULL_COMPOSITION'and result['actual_resistors']==28458 and result['actual_capacitors']==18384 and result['both_native_orders_verified']
anchors=json.loads(rc.read('native/mim-precise/wire/anchors08.json'));metal=rc.read('native/mim-precise/wire/rc03/wires.spice').decode()
measure=json.loads(rc.read('derived/precise-mim-result.json'))['result'];assert hashlib.sha256(metal.encode()).hexdigest()==measure['native_spice']['sha256'];capture=measure['capture']
reduction=source.NATIVE/'gate-reduction';reduction.mkdir();source.new_reduction(reduction)
cfg=source.read(source.ROOT/source.CFG);magic=source.NATIVE/'magic';magic.mkdir();source.acquire(cfg['magic'],magic,lambda n:n in cfg['magic']['selected'])
legacy=source.read(magic/'binding/binding.json');oldlegacy=copy.deepcopy(legacy);changes=[]
for pair in identity['pairs']:
 origin=pair['original_source']
 if origin['model']!='rppd' or origin['origin_native_id']not in (234,235,236,237):continue
 approved={234:('DQP','USP',6.0),235:('USP','AVSS',8.6),236:('DQN','USN',6.0),237:('USN','AVSS',8.6)}
 plus,minus,length=approved[origin['origin_native_id']]
 assert origin['terminals']==dict(RPPD_1=plus,RPPD_2=minus,RPPD_SUB='BULK')and origin['layout_parameters']['l']==length and origin['layout_parameters']['w']==2
 old=next(d for d in legacy['devices']if d['native_id']==origin['origin_native_id'])
 # Only the four independently LVS-qualified width edits may change canonical cards.
 assert pair['layout']['parameters']['w']==2 and old['model']=='rppd'and old['instance']==origin['loaded_instance']
 assert Decimal(old['native_parameters']['w'])==1 and full.parser.number(old['parameters']['w'])==Decimal('1e-6')
 old['native_parameters']['w']='2';old['parameters']['w']='2u';changes.append(dict(native_id=pair['layout']['id'],origin_native_id=origin['origin_native_id'],instance=old['instance']))
assert len(changes)==4 and len({x['origin_native_id']for x in changes})==4
source.save('current-physical-cases.json',fixture);source.save('canonical-width-edits.json',dict(changes=changes,independent_native_LVS_reference=True,full_phy_accepted=False))
composed=[]
for n in (1,2,4,8,16):
 parts=[]
 for gi in range(50):
  folder=reduction/f'native/reduction-g{gi}-n{n}'
  parts.append((source.read(folder/'ports-and-matrices.json'),(folder/'reduced-positive-resistors.cir').read_text()))
 text,contract=full.assemble(identity,anchors,legacy,metal,capture,parts,fixture,n)
 bound=full.probes(contract);target=source.NATIVE/f'composition-n{n}';target.mkdir()
 for name,value in [('contract.json',contract),('probes.json',bound)]:(target/name).write_bytes(source.enc(value))
 (target/'model.cir').write_text(text)
 composed.append(dict(partition=n,model=source.pin(target/'model.cir'),contract=source.pin(target/'contract.json'),probes=source.pin(target/'probes.json')))
 if n==1:
  controls=[]
  for label,oldcards,cap,red in [('old resistor width',oldlegacy,capture,parts),('missing MIM',legacy,dict(capture,native_mim_devices=capture['native_mim_devices'][:-1]),parts),('wrong gate contact point',legacy,capture,copy.deepcopy(parts))]:
   if label=='wrong gate contact point':red[0][0]['actual_reference_contact']['physical_anchor']['point_dbu'][0]+=5
   try:full.assemble(identity,anchors,oldcards,metal,cap,red,fixture,n)
   except ValueError as error:controls.append(dict(case=label,rejected=True,reason=str(error)))
   else:raise AssertionError('accepted corruption '+label)
  source.save('composition-controls.json',dict(cases=controls));assert len(controls)==3
source.gate();source.save('result.json',dict(status='PASS_CURRENT_WIDTH2_FULL650_COMPOSITION_REQUIRES_LOADED_ELECTRICAL',context=context,physical_devices=650,physical_terminals=2046,physical_gate_contacts=200,metal_R=28458,metal_C=18384,native_MIM=7,partitions=composed,gate_geometry_binding=gateproof,full_loaded_simulation_passed=False,full_phy_accepted=False,full_pex_qualified=False))
