#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read native failed parent geometry; never modifies the candidate."""
import argparse,hashlib,json
from pathlib import Path
TOP='nssoc_cdr_pd476_follower_v23'
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
 root=a.root.resolve();gds=root/'layout'/(TOP+'.gds')
 before=hashlib.sha256(gds.read_bytes()).hexdigest()
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);li=L.layer(50,0)
 assert L.dbu==.001 and T is not None
 zones=[(1156.98,1158.205),(1159.405,1160.63),(1191.38,1192.605),(1193.805,1195.03)]
 rows=[]
 for y in (290.565,1480.085):
  for x1,x2 in zones:
   box=pya.Box(round((x1-1)*1000),round((y-1)*1000),round((x2+1)*1000),round((y+1.2)*1000))
   it=T.begin_shapes_rec_touching(li,box);shapes=[]
   while not it.at_end():
    s=it.shape()
    if not s.is_text():
     poly=s.polygon.transformed(it.trans())
     clipped=pya.Region(poly)&pya.Region(box)
     if not clipped.is_empty():
      shapes.append(dict(owner=it.cell().name,transform=str(it.trans()),bbox=str(poly.bbox()),
       original_polygon=str(poly),clipped=str(clipped)))
    it.next()
   assert shapes
   rows.append(dict(marker_um=[x1,y,x2,y+.04],shapes=shapes))
 assert hashlib.sha256(gds.read_bytes()).hexdigest()==before
 result=dict(status='READ_ONLY_NATIVE_M4_GEOMETRY_DIAGNOSIS',source_gds_sha256=before,rows=rows,
  full_phy_accepted=False,geometry_modified=False)
 (root/'metal4-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()

