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
proof=archive(43749998803,'c6cbea424e531f0fdacd95739860db9280e85fe6',14175753278,'d28e28bbddb9dff88e55006ef9ea9aca9e02b7f1796941bf3c544d4c3f6f6707')
gateproof=json.loads(proof.read('result.json'));assert gateproof['status']=='PASS_EXACT_CURRENT_GATE_GEOMETRY_AND_NATIVE_IDENTITY'and all(gateproof['checks'].values())
ids=archive(43748580179,'4602a2710cea2b2322cb035750dad9738d9583f4',14175207602,'0e41bbf406fb1518a17ee41e49814758ebd32ad9fc880e5adaaa864ae00630bc')
identity=json.loads(ids.read('lvs_flat-identity.json'))
wire=archive(43748923684,'e7aef3e3e4b3d7b2c93190649d0981cdee1b9bd5',14175890238,'5495ebccb905ede137d893a1d8a43b448dc988b370c0c58cdd03307ff2b63e4a')
fixture=dict(devices=source.current_cases(identity,json.loads(wire.read('gate-poly-access.json'))))
rc=archive(43749558120,'9ca8ae6070b11a67626f0aa611c8a3e9a3905e71',14175583524,'54b260a566ebf0c98103559ec7a24dedd6a7a29d8b7cb4d41b89f54412351c8a')
result=json.loads(rc.read('derived/result.json'));assert result['status']=='PASS_CURRENT650_MIM_AWARE_TWO_ORDER_RC_AND22_FAULTS_EACH_REQUIRES_FULL_COMPOSITION'and result['actual_resistors']==28458 and result['actual_capacitors']==18384 and result['both_native_orders_verified']
anchors=json.loads(rc.read('native/mim-precise/wire/anchors08.json'));metal=rc.read('native/mim-precise/wire/rc03/wires.spice').decode()
measure=json.loads(rc.read('derived/precise-mim-result.json'))['result'];assert hashlib.sha256(metal.encode()).hexdigest()==measure['native_spice']['sha256'];capture=measure['capture']
reduction=source.NATIVE/'gate-reduction';reduction.mkdir();source.new_reduction(reduction)
cfg=source.read(source.ROOT/source.CFG);magic=source.NATIVE/'magic';magic.mkdir();source.acquire(cfg['magic'],magic,lambda n:n in cfg['magic']['selected'])
legacy=source.read(magic/'binding/binding.json');oldlegacy=copy.deepcopy(legacy);changes=[]
for pair in identity['pairs']:
 origin=pair['original_source']
 if origin['model']!='rppd' or origin['layout_parameters']['w']!=2:continue
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
