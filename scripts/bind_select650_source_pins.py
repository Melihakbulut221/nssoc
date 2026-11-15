import subprocess,json,hashlib,zipfile,io,sys
from pathlib import Path
import pya
import cdr_mos650_metal_rc as archive
import cdr_mos650_geometry as original
out=Path('select650-source-pins');out.mkdir()
archive.NATIVE=Path('select650-pin-native');archive.NATIVE.mkdir();archive.DERIVED=out
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
oldrun=api('actions/runs/43695818962');assert oldrun['conclusion']=='success'and oldrun['head_sha']=='8fc405e96adafb355d85e6da401df25b6ac22bfc'and oldrun['run_attempt']==1
oldmeta=api('actions/artifacts/14153204757');assert oldmeta['workflow_run']['id']==oldrun['id']and oldmeta['digest']=='sha256:e9233feee1c10354794dc7646b73b8fe9247113e3a1c070a8d0295d7c42e208f'and not oldmeta['expired']
oldbytes=subprocess.check_output(['gh','api',P+'actions/artifacts/14153204757/zip']);assert 'sha256:'+hashlib.sha256(oldbytes).hexdigest()==oldmeta['digest']
oldzip=zipfile.ZipFile(io.BytesIO(oldbytes));old=json.loads(oldzip.read('source-pins.json'))
assert old['status']=='PASS_PAIRED650_PRIMITIVE_PINS_REBOUND_AFTER_VERIFIED_BAND_TRANSLATION'and old['target_gds_sha256']=='6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a'
(out/'current-pin-parent.json').write_text(json.dumps(dict(run=oldrun['id'],artifact=oldmeta['id'],archive_sha256=oldmeta['digest'][7:],source_pins_sha256=hashlib.sha256(oldzip.read('source-pins.json')).hexdigest()),indent=2))
r=api('actions/runs/43748270188');assert r['conclusion']=='success' and r['head_sha']=='4a37a0285be11fc7d424daa830887ec7bde5654b' and r['run_attempt']==1
m=api('actions/artifacts/14175765192');assert m['workflow_run']['id']==r['id']and m['digest']=='sha256:a1381011a37b531184deedcca9e57e6bdba3ce18ac9d7a280ff0f00c1747504a'and not m['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14175765192/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==m['digest'];z=zipfile.ZipFile(io.BytesIO(b));gds=z.read('candidate650-select-width2.gds');assert hashlib.sha256(gds).hexdigest()=='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a'
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
