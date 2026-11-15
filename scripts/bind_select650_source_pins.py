import subprocess,json,hashlib,zipfile,io,sys
from pathlib import Path
import pya
import cdr_mos650_metal_rc as archive
import cdr_mos650_geometry as original
out=Path('select650-source-pins');out.mkdir()
archive.NATIVE=Path('select650-pin-native');archive.NATIVE.mkdir();archive.DERIVED=out
cfg=json.loads(Path(archive.CFG).read_text());parent=archive.NATIVE/'parent'
archive.acquire(cfg['view'],parent,lambda n:n.startswith(('native/view/','native/selected/','derived/')))
old=json.loads((parent/'native/view/wire/source-pins.json').read_text())
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43744181108');assert r['conclusion']=='success' and r['head_sha']=='ba72787f258e153e9d4070974b8558c817e6171d' and r['run_attempt']==1
m=api('actions/artifacts/14173825484');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:ba416ff202c6bbd9706952fad3215120573a4c544890ec9eab1fb8d4a1040fc2'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14173825484/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));gds=z.read('candidate650-select-width2.gds');assert hashlib.sha256(gds).hexdigest()=='8c42f6785d0b7ebac0a6d1b8f01d72943828a09ecf89b11f9ca05a3b4e771c77'
gpath=archive.NATIVE/'candidate.gds';gpath.write_bytes(gds)
original.NATIVE=archive.NATIVE/'pdk';original.NATIVE.mkdir();original.DERIVED=out/'pdk-receipt';original.DERIVED.mkdir()
pdk=original.pdk(json.loads(Path(original.CFG).read_text()));source=pdk/'libs.tech/klayout/python';sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
import sg13g2_pycell_lib
metals=(8,10,30,50,67,126,134)
def signature(layout,cell):
 drawing=[]
 for i in layout.layer_indexes():
  info=layout.get_info(i)
  if info.layer in metals and info.datatype in (2,25):continue
  region=pya.Region(cell.begin_shapes_rec(i)).merged()
  if not region.is_empty():drawing.append((info.layer,info.datatype,sorted(p.to_s()for p in region.each())))
 assert drawing
 return hashlib.sha256(json.dumps(sorted(drawing),separators=(',',':')).encode()).hexdigest()
sources={}
for row in old['cells'].values():
 key=(row['cell'].split('$')[0],row['drawing_sha256'])
 if key in sources:assert sources[key]['pins']==row['pins']
 else:sources[key]=row
lib=pya.Layout();regenerated=[]
for length in ['6u','8.6u']:
 c=lib.create_cell('rppd','SG13_dev',dict(w='2u',l=length));assert c is not None
 pins=sorted([layer,[s.box.left,s.box.bottom,s.box.right,s.box.top]]for layer in metals for s in c.each_shape(lib.layer(layer,2))if s.is_box())
 assert len(pins)==2 and all(row[0]==8 for row in pins)
 h=signature(lib,c);row=dict(source='pinned native IHP rppd PCell',cell=c.name,pins=pins,drawing_sha256=h,parameters=dict(w='2u',l=length));key=('rppd',h)
 if key in sources:assert sources[key]['pins']==pins
 sources[key]=row;regenerated.append(row)
g=pya.Layout();g.read(str(gpath));top=g.cell('nssoc_cdr_pd500_resistor_v59');assert top is not None and g.dbu==.001
models={'npn13G2','rppd','ptap1','cmim','nmos'};mapped={};reachable=set();instances=[]
def visit(c):
 reachable.add(c.cell_index());children=list(c.each_inst())
 if not children and c.name.split('$')[0]in models:instances.append(c.name)
 for inst in children:assert not inst.is_regular_array();visit(inst.cell)
visit(top);assert len(instances)==650
for idx in reachable:
 c=g.cell(idx);kind=c.name.split('$')[0]
 if kind not in models or list(c.each_inst())or kind=='cmim':continue
 key=(kind,signature(g,c));assert key in sources,('Unbound native primitive',c.name,key)
 mapped[c.name]=sources[key]
newkeys={('rppd',x['drawing_sha256'])for x in regenerated};hits=[name for name in instances if(name.split('$')[0],signature(g,g.cell(name)))in newkeys]
assert len(hits)==4
(out/'source-pins.json').write_text(json.dumps(dict(status='PASS_SELECT_WIDTH2_SOURCE_PINS_ON_IDENTICAL_NATIVE_DRAWINGS',cells=mapped,target_gds_sha256=hashlib.sha256(gds).hexdigest(),regenerated_resistors=regenerated,changed_resistor_instances=hits,physical_instances=650,fresh_rc=False,full_phy_accepted=False),indent=2))
