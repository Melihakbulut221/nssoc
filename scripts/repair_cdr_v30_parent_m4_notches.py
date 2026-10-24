#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fill eight proven same-component M4 notches; preserve all original geometry."""
import json
from pathlib import Path
def apply(layout,top,layer_map):
 import pya
 assert layout.dbu==.001 and top.name=='nssoc_cdr_pd476_follower_v23'
 evidence=json.loads((Path(__file__).with_name('cdr-v30-parent-m4-diagnosis.json')).read_text())
 assert evidence['run']==39705547543 and evidence['diagnosis']['geometry_modified']is False
 rows=evidence['diagnosis']['rows'];assert len(rows)==8
 li=layout.layer(50,0)
 original=pya.Region(top.shapes(li)).flatten().merged()
 full=pya.Region(top.begin_shapes_rec(li)).flatten().merged()
 # Refuse an unrelated parent or changed offending geometry.
 actual={str(s.polygon)for s in top.shapes(li).each()if not s.is_text()}
 expected={s['original_polygon']for r in rows for s in r['shapes']if s['owner']==top.name}
 assert len(expected)==12 and expected<=actual
 bridges=pya.Region();patches=[]
 for row in rows:
  x1,y1,x2,y2=[round(x*1000)for x in row['marker_um']]
  assert x2-x1==1225 and y2-y1==40
  patch=pya.Region(pya.Box(x1,y1-50,x2,y2+50))
  gap=pya.Region(pya.Box(x1,y1,x2,y2))
  assert ((patch-full)^gap).is_empty(),'Measured gap changed'
  touched=full.interacting(patch).merged()
  assert touched.size()==1,'Patch could merge different conductive components'
  # Both boundaries and side connection must belong to this same component.
  assert (patch-gap-touched).is_empty()
  bridges+=patch
  patches.append(dict(box_dbu=[x1,y1-50,x2,y2+50],added_area_dbu2=gap.area(),
   touched_existing_m4_components=touched.size()))
 bridges.merge()
 changed=(bridges-full).merged()
 assert changed.area()==392000 and changed.size()==8
 after_full=(full+bridges).merged()
 assert after_full.size()==full.size(),'Connected-component count changed'
 # Reject new vertical connections: added metal must not expose an existing via.
 tech=[Path(layer_map)]
 assert tech[0].is_file(),'Missing pinned native layer map'
 import xml.etree.ElementTree as ET
 maps=[]
 for path in tech:
  mapping={prop.findtext('name')[:-8]:prop.findtext('source')
   for prop in ET.parse(path).getroot().iter('properties')
   if prop.findtext('name','').endswith('.drawing')}
  if 'Via3'in mapping and 'Via4'in mapping:maps.append((path,mapping))
 assert maps,'Native layer map lacks adjacent M4 vias'
 via_layers={}
 for name in ('Via3','Via4'):
  mapped={int(m[name].split('/')[0])for _,m in maps}
  assert len(mapped)==1,('Conflicting native via maps',name)
  layer=next(iter(mapped));via_layers[name]=layer
  vias=pya.Region(top.begin_shapes_rec(layout.layer(layer,0))).flatten().merged()
  assert not vias.is_empty()
  assert (changed&vias).is_empty(),'Patch would create a new via connection'
 for polygon in bridges.each():top.shapes(li).insert(polygon)
 written=pya.Region(top.shapes(li)).flatten().merged()
 assert (original-written).is_empty()
 assert ((written-original)-(bridges-original)).is_empty()
 assert ((written-original)^(bridges-original)).is_empty()
 return bridges,dict(status='EIGHT_SAME_COMPONENT_M4_NOTCHES_FILLED_REQUIRES_NATIVE_DRC_LVS',
  patches=patches,added_flat_metal_area_dbu2=changed.area(),original_component_count=full.size(),
  new_component_count=after_full.size(),adjacent_via_layers=via_layers,
  no_new_via_connections=True,all_original_metal_preserved=True,
  all_children_and_other_layers_unchanged=True,physical_validation_passed=False,
  full_phy_accepted=False,qualified_pex=False)

