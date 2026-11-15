import subprocess,json,hashlib,zipfile,io,shutil
from pathlib import Path
import cdr_mos650_geometry as source
P='repos/Melihakbulut221/nssoc/'
def api(x):return json.loads(subprocess.check_output(['gh','api',P+x]))
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
run=api('actions/runs/43740622508')
assert run['conclusion']=='success' and run['head_sha']=='6e6b9e41a75b8202f7c542f08d46e502feda6856' and run['run_attempt']==1
meta=api('actions/artifacts/14171769619')
assert meta['digest']=='sha256:56d5473fc33b95f28a320fc5b31bac9d07ad9989662f66335023a55b723f42e2' and not meta['expired'] and meta['workflow_run']['id']==run['id']
data=subprocess.check_output(['gh','api',P+'actions/artifacts/14171769619/zip'])
assert hashlib.sha256(data).hexdigest()==meta['digest'][7:]
z=zipfile.ZipFile(io.BytesIO(data));receipt=json.loads(z.read('acquisition.json'))
out=Path('select-variant-evidence');out.mkdir()
for n,record in receipt['selected'].items():
 b=z.read(n);assert len(b)==record['bytes'] and hashlib.sha256(b).hexdigest()==record['sha256']
 dest=out/'original'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
source.NATIVE=Path('select-pdk-runtime');source.NATIVE.mkdir()
source.DERIVED=out/'runtime-receipt';source.DERIVED.mkdir()
pdk=source.pdk(json.loads(Path(source.CFG).read_bytes()))
for width,label in [('1u','baseline'),('2u','rwidth2')]:
 target=Path('hw/soc/out')/('select-width-'+label)
 target.parent.mkdir(parents=True,exist_ok=True)
 command=['python3','-B','hw/soc/flow/make_pcie_cdr_feedforward_width_trial.py','--pdk',str(pdk),'--out',str(target),'--kind','select','--select-resistor-width',width]
 with (out/(label+'.log')).open('w')as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 shutil.copytree(target,out/label)
import pya
original=pya.Layout();original.read(str(out/'original/layout/nssoc_cdr_select_feedforward_layout_v1.gds'))
baseline=pya.Layout();baseline.read(str(out/'baseline/nssoc_cdr_select_feedforward_layout_v1.gds'))
assert original.dbu==baseline.dbu
ot=original.top_cell();bt=baseline.top_cell()
assert ot.name==bt.name and ot.bbox()==bt.bbox()
layers=set((i.layer,i.datatype)for i in original.layer_infos())|set((i.layer,i.datatype)for i in baseline.layer_infos())
for layer,datatype in sorted(layers):
 left=pya.Region(ot.begin_shapes_rec(original.layer(layer,datatype))).merged()
 right=pya.Region(bt.begin_shapes_rec(baseline.layer(layer,datatype))).merged()
 assert (left^right).is_empty(),(layer,datatype)
assert (out/'original/layout/schematic.cir').read_bytes()==(out/'baseline/schematic.cir').read_bytes()
assert (out/'original/layout/nssoc_cdr_select_feedforward_layout_v1.lef').read_bytes()==(out/'baseline/nssoc_cdr_select_feedforward_layout_v1.lef').read_bytes()
br=json.loads((out/'baseline/result.json').read_bytes());vr=json.loads((out/'rwidth2/result.json').read_bytes())
assert br['ports']==vr['ports'] and br['bbox_um']==vr['bbox_um']
assert len(vr['core_devices'])==6 and vr['substrate_contacts']==6
for old,new in zip(br['core_devices'],vr['core_devices'],strict=True):
 assert old['model']==new['model'] and old['nets']==new['nets'] and old['placement_um']==new['placement_um']
 want=dict(old['params'])
 if old['model']=='rppd':want['w']='2u'
 assert new['params']==want
for name in ['drc_pass','lvs_pass','pex_qualified','main_chip_integrated','serial_phy_complete']:assert vr[name]is False
(out/'comparison.json').write_text(json.dumps(dict(status='PASS_BASELINE_GEOMETRY_REPLAY_AND_CANDIDATE_GENERATION',accepted=False,full_phy_accepted=False,baseline_full_region_equal=True,baseline_schematic_lef_equal=True,candidate_resistors=4,candidate_width_um=2,original_width_um=1,ports_bbox_preserved=True,scope='Physical primitive width experiment only. Candidate needs DRC/LVS, new RC, loaded timing and current checks before integration.',files={str(f.relative_to(out)):sha(f)for f in out.rglob('*')if f.is_file()}),indent=2))
