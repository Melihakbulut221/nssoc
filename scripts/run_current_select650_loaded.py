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
cfg=source.read(source.ROOT/source.CFG);models=source.acquire_models(cfg['runtime']);source.model_report(models);variant=source.intrinsic_variant(models)
engine=source.NATIVE/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
result=loaded.run_loaded(source,models,variant,engine,target/'model.cir',contract,bound,case)
source.gate();source.save('selected-whole-loaded-summary.json',dict(case=case,partition=n,status=result['status'],all256bits_executed=True,unchanged_original_electrical_gates=True,full_phy_accepted=False,final_timing_complete=False))
