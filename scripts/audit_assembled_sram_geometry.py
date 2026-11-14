# SPDX-License-Identifier: Apache-2.0
"""Read back actual assembled SRAM cells; no geometry-derived schematic."""
import pathlib,hashlib,json,tarfile,zipfile,collections
import klayout.db as db
from namespace_sram_macro import geometry
P=pathlib.Path
with P('native.zip').open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='bb1421b73653582fb56f11abedf90d66153e4d5919ef761a1d8a685b12d08d31'
z=zipfile.ZipFile('native.zip');assert z.namelist()==['streamout-native.tgz']
chip_hash='c6c7df7f7fe7d23c03847ffa49bb547423ff89b7dc9266a47effa495efea077d';library_hash='fb6925729c25f70eba48d6feb15daba92e586befe0bf12827e2cc2cc3f76b86a';found={}
with z.open('streamout-native.tgz') as stream,tarfile.open(fileobj=stream,mode='r|gz') as t:
 for m in t:
  if not m.isfile() or not m.name.endswith('.gds'):continue
  raw=t.extractfile(m).read();digest=hashlib.sha256(raw).hexdigest()
  if digest in [chip_hash,library_hash]:
   tag='chip' if digest==chip_hash else 'library'
   if tag not in found:P(tag+'.gds').write_bytes(raw)
   found.setdefault(tag,[]).append(m.name)
assert set(found)=={'chip','library'}
chip=db.Layout();chip.read('chip.gds');library=db.Layout();library.read('library.gds');expected=geometry(library);names=set(expected['cells'])
class Subset:
 def __init__(self,layout,selected):self.layout=layout;self.selected=selected
 def __getattr__(self,name):return getattr(self.layout,name)
 def each_cell(self):return (c for c in self.layout.each_cell() if c.name in self.selected)
actual=geometry(Subset(chip,names));missing=sorted(names-set(actual['cells']));different=sorted(n for n in names&actual['cells'].keys() if actual['cells'][n]!=expected['cells'][n])
top=chip.cell('soc_top');assert top is not None
counts=collections.Counter()
for i in top.each_inst():
 count=i.na*i.nb if i.is_regular_array() else 1
 counts[chip.cell(i.cell_index).name]+=count
macros={'RM_IHPSG13_2P_256x16_c2_bm_bist':16,'RM_IHPSG13_1P_2048x64_c2_bm_bist':4}
r={'status':'ASSEMBLED_SRAM_GEOMETRY_READBACK','source_run':43599532225,'chip_gds_sha256':chip_hash,'library_gds_sha256':library_hash,'expected_macro_library_cells':len(names),'missing_cells':missing,'different_cells':different,'same_grid':actual['dbu']==expected['dbu'],'macro_instance_counts':{n:counts[n] for n in macros},'expected_macro_instance_counts':macros,'all_direct_top_instances':sum(counts.values()),'macro_geometry_and_instances_preserved':not missing and not different and actual['dbu']==expected['dbu'] and all(counts[n]==v for n,v in macros.items()),'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Exact local cell shapes, labels, hierarchical instance transforms/arrays and expected macro multiplicities in the actually assembled GDS. Does not prove main-chip wiring equivalence, timing, DRC, complete PHY or manufacturing readiness.'}
P('out').mkdir();P('out/assembled-sram-readback.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['macro_geometry_and_instances_preserved']
