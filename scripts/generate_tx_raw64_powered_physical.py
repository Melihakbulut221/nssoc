#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Add real four-net power/body distribution and the complete8074-device reference."""
import json,re,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_full32_raw64_handoff_candidate_v1'
def main(out):
 import pya
 pd=ROOT/'pdk/libs.tech/klayout/python';sys.path[:0]=[str(pd),str(pd/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 source=out/'source';report=json.loads((source/'handoff-result.json').read_text())
 assert report['routed_count']==64 and report['blocked_count']==0
 src=source/'candidate/handoffs.gds';assert sha(src)=='b1349b9209f5bde68219ac9ad03f925df84ea68646c598962dc251da68dcf02a'
 L=pya.Layout();L.read(str(src));T=L.cell(TOP);assert T is not None and L.dbu==.001
 def regs(l,t):
  return {(l.get_info(i).layer,l.get_info(i).datatype):pya.Region(t.begin_shapes_rec(i)).merged()
   for i in l.layer_indexes()if not pya.Region(t.begin_shapes_rec(i)).is_empty()}
 before=regs(L,T);metals=(67,126,134)
 flat={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in metals}
 cm=json.loads((source/'core/layout/result.json').read_text())
 def box(s):
  a=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)));assert len(a)==4
  return pya.DBox(*a).to_itype(L.dbu)
 cp={n:box(v).transformed(pya.Trans(600000,0))for n,v in cm['ports'].items()}
 def comp(m,p):
  q=list(flat[m].interacting(pya.Region(p)).each());assert len(q)==1,('Ambiguous pin',m,str(p))
  r=pya.Region(q[0]);assert(pya.Region(p)-r).is_empty();return r
 def wire(x0,y0,x1,y1,h=1600):
  assert x0==x1 or y0==y1
  return pya.Region(pya.Box(min(x0,x1)-h,min(y0,y1)-h,max(x0,x1)+h,max(y0,y1)+h))
 def via(bottom,top,x,y):
  c=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=top,vn_columns=1,vn_rows=1,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
  assert c is not None and not c.is_empty()
  cut=133 if top=='TopMetal2'else 125;q=pya.Region(c.begin_shapes_rec(L.layer(cut,0))).bbox().center()
  tr=pya.Trans(x-q.x,y-q.y);r=regs(L,c)
  assert all(dt==0 for _,dt in r)
  return {m:a.transformed(tr)for(m,dt),a in r.items()}
 added={};prior={m:pya.Region()for m in metals};proof=[];clearance=1645;external_dvdd=None
 for n,x in [('sub',10000),('avss',30000),('avdd',50000),('dvdd',70000)]:
  pins=[pya.Box.from_s(r['pins_dbu'][n])for r in report['placements']]
  allowed={67:pya.Region(),126:pya.Region(),134:pya.Region()}
  for p in pins:allowed[67]+=comp(67,p)
  ys=[p.center().y for p in pins]
  if n!='dvdd':
   end=cp[n].center();allowed[134]=comp(134,cp[n])
  else:end=pya.Point(120000,303890);external_dvdd=pya.Box(end.x-3000,end.y-3000,end.x+3000,end.y+3000)
  candidate={67:pya.Region(),126:wire(x,min([end.y,*ys]),x,max([end.y,*ys]),3000),134:wire(x,end.y,end.x,end.y,3000)}
  def addvia(bottom,top,qx,qy):
   for m,r in via(bottom,top,qx,qy).items():candidate[m]=candidate.get(m,pya.Region())+r
  for p in pins:
   q=p.center();candidate[67]+=wire(x,q.y,q.x,q.y)
   addvia('Metal5','TopMetal1',x,q.y)
  addvia('TopMetal1','TopMetal2',x,end.y)
  if n=='dvdd':candidate[134]+=pya.Region(external_dvdd)
  collisions={}
  for m in metals:
   bad=candidate[m].sized(clearance)&((flat[m]-allowed[m])+prior[m])
   if not bad.is_empty():collisions[str(m)]=dict(bbox_dbu=str(bad.bbox()),area_dbu2=bad.area(),polygons=[str(p)for p in list(bad.each())[:12]])
  (out/'power-obstructions.json').write_text(json.dumps(dict(net=n,collisions=collisions),indent=2)+'\n')
  assert not collisions,('Power route intersects foreign native metal',n,collisions)
  for m,r in candidate.items():
   T.shapes(L.layer(m,0)).insert(r);added[m]=added.get(m,pya.Region())+r
  for m in metals:prior[m]+=candidate[m]
  proof.append(dict(net=n,trunk_x_dbu=x,driver_terminals=len(pins),native_vias=65,core_connected=n!='dvdd',external_pin_dbu=str(cp[n]if n!='dvdd'else external_dvdd)))
 # Explicit parent external labels:64 CMOS inputs,98 remaining core pins, plusDVDD.
 data={f'd{i}{p}'for i in range(32)for p in('p','n')}
 ports={n:(134,p)for n,p in cp.items()if n not in data};assert len(ports)==98
 for r in report['placements']:ports[r['net']+'0']=(67,pya.Box.from_s(r['pins_dbu']['din']))
 ports['dvdd']=(134,external_dvdd);assert len(ports)==163
 for n,(m,p)in ports.items():
  T.shapes(L.layer(m,2)).insert(p);q=p.center();T.shapes(L.layer(m,25)).insert(pya.Text(n,q.x,q.y))
 dest=out/'layout';dest.mkdir();L.write(str(dest/'layout.gds'))
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP)
 actual=regs(R,U);expected={k:v.dup()for k,v in before.items()}
 for m,r in added.items():expected[(m,0)]=expected.get((m,0),pya.Region())+r
 for n,(m,p)in ports.items():expected[(m,2)]=expected.get((m,2),pya.Region())+pya.Region(p)
 assert expected.keys()==actual.keys()
 for k in expected:assert(expected[k]^actual[k]).is_empty(),('Unexpected serialized material',k)
 labels={}
 for m in (67,134):
  for s in U.shapes(R.layer(m,25)).each():
   if s.is_text():
    assert s.text.string not in labels
    labels[s.text.string]=(m,s.text.trans.disp)
 assert set(labels)==set(ports)
 for n,(m,p)in ports.items():assert labels[n][0]==m and p.contains(labels[n][1])
 core=(source/'core/layout/schematic.cir').read_text().splitlines()
 drv=(source/'driver/inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins/base/raw.cir').read_text().splitlines()
 cc=[s for s in core if s and s[0]in 'QRM'];dc=[s for s in drv if s and s[0]in 'QRM']
 assert len(cc)==1674 and len(dc)==100
 original_ports=next(s.split()[2:]for s in core if s.startswith('.subckt'))
 assert len(original_ports)==162 and set(original_ports)==set(cp)
 refs=['* Native8074 reference; common physical substrate BULK; distinct per-driver wells.',
  '.subckt '+TOP+' '+' '.join([n+'0'if n in data else n for n in original_ports]+['dvdd']),*cc]
 mapping=[]
 for row in sorted(report['placements'],key=lambda r:r['net']):
  n=row['net'];mp=dict(din=n+'0',dout=n,avdd='avdd',avss='avss',sub='sub',dvdd='dvdd',BULK='BULK')
  for line in dc:
   a=line.split();count=4 if a[0][0]in 'QM'else 2 if a[3]in ('ptap1','ntap1')else 3
   assert a[count+1]in ('sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos','rppd','ptap1','ntap1')
   a[0]=a[0][0]+'driver_'+n+'_'+a[0][1:]
   a[1:count+1]=[mp.get(v,'driver_'+n+'_'+v)for v in a[1:count+1]]
   refs.append(' '.join(a))
  mapping.append(dict(instance=n,public_mapping=mp,body_policy='BULK common, all internal NWELL names unique per driver'))
 refs+=['.ends '+TOP,''];text='\n'.join(refs)
 (dest/'schematic.cir').write_text(text)
 assert sum(s.startswith(('Q','R','M'))for s in refs)==8074
 faults=out/'faults';faults.mkdir()
 # Real parent metal open, with original native cells untouched.
 li=L.layer(134,0);saved=pya.Region(T.shapes(li));y=cp['d0p'].center().y
 cut=pya.Region(pya.Box(499000,y-3000,501000,y+3000));assert not(saved&cut).is_empty()
 T.shapes(li).clear();T.shapes(li).insert(saved-cut);L.write(str(faults/'handoff_open.gds'))
 T.shapes(li).clear();T.shapes(li).insert(saved)
 li=L.layer(126,0);saved=pya.Region(T.shapes(li));short=wire(10000,400000,30000,400000)
 T.shapes(li).insert(short);L.write(str(faults/'body_supply_short.gds'))
 T.shapes(li).clear();T.shapes(li).insert(saved)
 # Wrong native MOS width in reference: all layout geometry remains unchanged.
 wrong=text.replace('sg13_hv_nmos w=1u l=.45u','sg13_hv_nmos w=0.9u l=.45u',1)
 assert wrong!=text
 (faults/'wrong_width.cir').write_text(wrong)
 li=L.layer(67,0);shape=next(s for s in T.shapes(li).each()if not s.is_text())
 shape.transform(pya.Trans(1,0));L.write(str(faults/'offgrid.gds'));shape.transform(pya.Trans(-1,0))
 result=dict(status='GENERATED_POWERED_RAW64_CORE8074_REQUIRES_NATIVE_DRC_LVS_AND_FRESH_RC',
  source_gds_sha256=sha(src),power_routes=proof,external_ports={n:dict(layer=m,box_dbu=str(p))for n,(m,p)in ports.items()},
  reference_devices=8074,reference_mapping=mapping,native_material_preserved=True,serialized_geometry_verified=True,
  main_chip_integrated=False,full_phy_accepted=False,qualified_pex=False,electrical_accepted=False,
  outputs={str(p.relative_to(out)):sha(p)for folder in(dest,faults)for p in folder.iterdir()})
 (out/'power-result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
