# SPDX-License-Identifier: Apache-2.0
"""Add short Metal2 power straps, each tied by one Via1 to a standard-cell rail.

Run with KLayout's Python on a filled GDS. Every strap is a vertical Metal2
rectangle centred on a Metal1 row rail, with one Via1 at its centre inside the
rail. It touches no other conductor, so it carries the rail's own net and
cannot short anything. Clearances: 0.25 um to drawn Metal2 (above Mn.b 0.21),
0.42 um to Metal2 fill (MFil.c), 0.22 um between Via1 (V1.b), 0.05 um Metal1
enclosure of the Via1, 2 um from the vendor SRAM macros. The straps go into a
new cell; no existing shape changes.
"""
import json,sys,time
import klayout.db as db
src,dst,report=sys.argv[1:4]
W,H,PITCH=0.28,3.2,0.55            # strap width, height, centre pitch (um)
SP_M2,SP_FILL,SP_V1,ENC,VIA=0.25,0.42,0.22,0.05,0.19
t0=time.time();l=db.Layout();l.read(src);top=l.top_cell();u=l.dbu;um=lambda x:int(round(x/u))
R=lambda ly,dt:db.Region(top.begin_shapes_rec(l.layer(ly,dt)))
m2=R(10,0)+R(10,2);m2.merge();fill=R(10,22);v1=R(19,0);m1=R(8,0);m1.merge()
macros=db.Region()
for inst in top.each_inst():
    if inst.cell.name.startswith('RM_IHPSG13'):macros.insert(inst.bbox().enlarged(um(2.0),um(2.0)))
rows=set()
for p in R(189,4).each():
    b=p.bbox()
    if abs(b.height()*u-3.78)<0.01:rows.add(b.bottom);rows.add(b.top)
print('loaded %.0fs rows %d macros %d'%(time.time()-t0,len(rows),macros.count()),flush=True)
# Feasible strap centres: Minkowski-expand every obstacle by the strap half size plus its clearance.
hx,hy=um(W/2),um(H/2)
obst=m2.sized(um(SP_M2)+hx,um(SP_M2)+hy)+fill.sized(um(SP_FILL)+hx,um(SP_FILL)+hy)+macros.sized(hx,hy)
obst+=v1.sized(um(SP_V1+VIA/2))
obst.merge()
viaok=m1.sized(-um(ENC+VIA/2));viaok.merge()
print('obstacles %.0fs'%(time.time()-t0),flush=True)
bb=top.bbox();straps=[];vias=[]
for y in sorted(rows):
    line=db.Region(db.Box(bb.left,y-1,bb.right,y+1))
    ok=(line&viaok)-obst
    last=None
    # The centre pitch holds along the whole rail, across interval boundaries.
    for b in sorted((p.bbox() for p in ok.merged().each()),key=lambda b:b.left):
        x=b.left if last is None else max(b.left,last+um(PITCH))
        while x<=b.right:
            straps.append(db.Box(x-hx,y-hy,x+hx,y+hy));h=um(VIA/2);vias.append(db.Box(x-h,y-h,x+h,y+h));last=x;x+=um(PITCH)
cell=l.create_cell('NS_M2_PG_STRAPS')
for b in straps:cell.shapes(l.layer(10,0)).insert(b)
for b in vias:cell.shapes(l.layer(19,0)).insert(b)
top.insert(db.CellInstArray(cell.cell_index(),db.Trans()))
check=db.Region()
for b in straps:check.insert(b)
assert check.merged().count()==len(straps),'straps touch'
assert check.space_check(um(SP_M2)).is_empty(),'straps closer than the Metal2 clearance'
assert (check&(m2+fill)).is_empty(),'strap overlaps existing Metal2'
die=bb.width()*bb.height()*u*u;add=len(straps)*W*H
r=dict(straps=len(straps),added_m2_um2=add,die_um2=die,added_percent=add/die*100,
       m2_before_percent=(m2+fill).merged().area()*u*u/die*100,seconds=time.time()-t0)
json.dump(r,open(report,'w'),indent=1);print(json.dumps(r),flush=True)
l.write(dst)
