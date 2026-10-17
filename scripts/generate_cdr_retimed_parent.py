#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route the full16-macro retimed PD/V-I with real interconnect and394devices."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
from cdr_retimed_parent_plan import build,verify,TYPES
TOP='nssoc_cdr_retimed_pd394_layout_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flatten(text,cell,tag,pins):
    cards=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('*'):continue
        if line.startswith('+'):assert cards;cards[-1]+=' '+line[1:]
        else:cards.append(line)
    cells={};current=None
    for line in cards:
        f=line.split();op=f[0].lower()
        if op=='.subckt':
            assert current is None and f[1].lower()not in cells
            current=f[1].lower();cells[current]=dict(ports=f[2:],rows=[])
        elif op=='.ends':assert current is not None;current=None
        else:assert current is not None;cells[current]['rows'].append(f)
    assert current is None
    out=[];census=Counter()
    def visit(name,path,mapping,stack):
        assert name not in stack and set(mapping)=={p.lower()for p in cells[name]['ports']}
        def net(n):return mapping.get(n.lower(),'BULK'if n.lower()=='bulk'else path+'_'+n)
        for f in cells[name]['rows']:
            if f[0][0].lower()=='x':
                target=f[-1].lower();assert target in cells
                visit(target,path+'_'+f[0],dict(zip([p.lower()for p in cells[target]['ports']],[net(n)for n in f[1:-1]],strict=True)),stack+[name]);continue
            kind=f[0][0].lower()
            if kind=='q':count,model=4,'npn13g2'
            elif kind=='r'and f[3].lower()=='ptap1':count,model=2,'ptap1'
            elif kind=='r':count,model=3,'rppd'
            elif kind=='c':count,model=2,'cap_cmim'
            else:raise ValueError(f)
            assert f[count+1].lower()==model
            out.append(' '.join([f[0][0]+path+'_'+f[0][1:],*[net(n)for n in f[1:count+1]],*f[count+1:]]));census[model]+=1
    visit(cell.lower(),tag,{p.lower():n for p,n in pins.items()},[])
    return out,census

def generate(out):
    source=ROOT/'pdk/libs.tech/klayout/python';sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    plan=build();verify(plan);manifest=json.loads((out/'children.json').read_text())
    assert manifest['status']=='ALL_EIGHT_CHILD_SOURCE_PROOFS_BOUND'and set(manifest['children'])==set(TYPES)
    protected={str(p):sha(p)for p in [Path(__file__),ROOT/'scripts/cdr_retimed_parent_plan.py',out/'children.json',*[ROOT/'hw/soc/analog/pcie'/n for n in plan['source_sha256']]]}
    L=pya.Layout();L.dbu=.001;top=L.create_cell(TOP);children={};metadata={};refs={};conservation={}
    metals=(8,10,30,50,67,126,134)
    for kind,item in manifest['children'].items():
        directory=out/item['directory'];cellname=TYPES[kind]['top']
        for name,h in item['files'].items():
            p=out/name;assert sha(p)==h;protected[str(p)]=h
        data=json.loads((directory/'result.json').read_text());old=pya.Layout();old.read(str(directory/(cellname+'.gds')))
        child=old.cell(cellname);assert child is not None and old.dbu==L.dbu
        copied=L.create_cell('pd_child_'+kind);copied.copy_tree(child)
        for c in list(L.each_cell()):
            if c.cell_index()==top.cell_index():continue
            for layer in metals:
                for dt in (2,25):c.shapes(L.layer(layer,dt)).clear()
        checked=0
        for li in old.layer_indexes():
            info=old.get_info(li)
            if info.layer in metals and info.datatype in (2,25):continue
            assert (pya.Region(child.begin_shapes_rec(li))^pya.Region(copied.begin_shapes_rec(L.layer(info)))).is_empty()
            checked+=1
        assert copied.dbbox().left==copied.dbbox().bottom==0
        conservation[kind]=dict(all_non_port_annotation_layers_equal=True,checked_layers=checked,source_gds_sha256=sha(directory/(cellname+'.gds')))
        children[kind]=copied;metadata[kind]=data;refs[kind]=(directory/'schematic.cir').read_text()
    def box(layer,b):top.shapes(L.layer(layer,0)).insert(b)
    def wire(layer,a,b,width):
        assert a[0]==b[0]or a[1]==b[1]
        q=pya.DBox(min(a[0],b[0])-width/2,min(a[1],b[1])-width/2,max(a[0],b[0])+width/2,max(a[1],b[1])+width/2)
        box(layer,q);return q
    def via(x,y,bottom=126):
        name={67:'Metal5',126:'TopMetal1'}[bottom]
        c=L.create_cell('via_stack','SG13_dev',dict(b_layer=name,t_layer='TopMetal2',vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=1,vt2_rows=1))
        assert c is not None and not c.is_empty();b=c.dbbox()
        top.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(round((x-b.center().x)/.005)*.005,round((y-b.center().y)/.005)*.005)))
    buses={};cursor=8
    for net in plan['nets']:
        width=64. if net in ('avdd','avss','sub')else 3.2
        buses[net]=dict(x=cursor+width/2,width=width,ys=[]);cursor+=width+8
    origin_x=cursor+40;origin_y=240.;placements={};routes=[];reference=[];census=Counter()
    def connect(net,y,end_x,tag,pin):
        bus=buses[net];x=bus['x'];extent=24 if bus['width']==64 else 0
        q=wire(134,(x-extent,y),(end_x,y),3.2)
        for vx in ([x+d for d in (-24,-16,-8,0,8,16,24)]if extent else[x]):via(vx,y)
        bus['ys'].append(y);routes.append(dict(net=net,tag=tag,pin=pin,layer=134,box_um=str(q)))
    for node in plan['nodes']:
        kind,tag=node['kind'],node['tag'];c=children[kind];data=metadata[kind];w,h=c.dbbox().width(),c.dbbox().height()
        tr=pya.DTrans(origin_x,origin_y);top.insert(pya.DCellInstArray(c.cell_index(),tr))
        assert set(data['ports'])==set(node['pins'])
        right_count=0;physical_ports={}
        for pin,raw in data['ports'].items():
            b=pya.DBox(*raw['rect_um'])if isinstance(raw,dict)else pya.DBox(*map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
            assert b.left>=0 and b.right<=w+.001 and b.bottom>=0 and b.top<=h+.001
            p=b.transformed(tr);net=node['pins'][pin];px,py=p.center().x,p.center().y;layer=TYPES[kind]['layer'];physical_ports[pin]=str(p)
            if b.left<=.001:
                access=origin_x-6
                wire(layer,(access,py),(px,py),1.2 if layer==67 else 3.2)
                if layer==67:via(access,py,67)
                connect(net,py,access,tag,pin)
            else:
                assert abs(b.right-w)<.001, 'Only actual edge pins can use the external routing channel'
                assert (kind=='sampler' and pin in ('QP','QN') and layer==67) or (kind=='xor' and pin in ('ep','en','iref') and layer==134), 'Unexpected right-edge interface'
                access=origin_x+w+12+right_count*8;ey=origin_y+h+16+right_count*8;right_count+=1
                wire(layer,(px,py),(access,py),1.2 if layer==67 else 3.2);via(access,py,67 if layer==67 else 126)
                wire(126,(access,py),(access,ey),3.2);via(access,ey)
                connect(net,ey,access,tag,pin)
        rows,counts=flatten(refs[kind],TYPES[kind]['top'],tag,node['pins']);assert len(rows)==TYPES[kind]['devices']
        reference+=rows;census.update(counts);placements[tag]=dict(kind=kind,bbox_um=str(c.dbbox().transformed(tr)),ports=physical_ports)
        origin_y+=h+max(80,32+right_count*8)
    assert len(placements)==16 and len(reference)==394 and dict(census)==plan['primitive_census']
    public={}
    for index,net in enumerate(plan['ports']):
        y=1.6+index*8;bus=buses[net];x=bus['x'];extent=24 if bus['width']==64 else 0
        wire(134,(1.6,y),(x+extent,y),3.2)
        for vx in ([x+d for d in (-24,-16,-8,0,8,16,24)]if extent else[x]):via(vx,y)
        bus['ys'].append(y);b=pya.DBox(0,y-1.6,2.4,y+1.6)
        top.shapes(L.layer(134,2)).insert(b);top.shapes(L.layer(134,25)).insert(pya.DText(net,1.2,y));public[net]=('TopMetal2',b)
    for net,bus in buses.items():
        assert bus['ys'];wire(126,(bus['x'],min(bus['ys'])),(bus['x'],max(bus['ys'])),bus['width'])
    # No drawing geometry inside any child is edited during routing.
    assert all(sha(Path(p))==v for p,v in protected.items());verify(plan)
    assert top.dbbox().left==top.dbbox().bottom==0, 'No post-routing transform may invalidate recorded coordinates'
    dest=out/'layout';dest.mkdir()
    opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
    (dest/'schematic.cir').write_text('* Frozen native PD source mapped to real physical leaves\n.subckt '+TOP+' '+' '.join(plan['ports'])+'\n'+'\n'.join(reference)+'\n.ends '+TOP+'\n')
    sys.path.insert(0,str(ROOT/'hw/soc/flow'));import make_pcie_clock_vco_v6_local_v1 as writer
    writer.TOP=TOP;writer.PORTS=plan['ports'];writer.use_direction=lambda n:('POWER','INOUT')if n=='avdd'else('GROUND','INOUT')if n in ('avss','sub')else('SIGNAL','OUTPUT'if n in ('xp','xn','yp','yn','vip','vin')else'INPUT')
    (dest/(TOP+'.lef')).write_text(writer.lef(pya,L.dbu,top.dbbox(),public))
    protected[str(ROOT/'hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py')]=sha(ROOT/'hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py')
    record=dict(status='GENERATED_COMPLETE_PD394_REQUIRES_NATIVE_PHYSICAL_AND_RC',inputs=protected,ports={n:str(b)for n,(_,b)in public.items()},bbox_um=str(top.dbbox()),placements=placements,routes=routes,primitive_census=dict(census),source_plan=plan,child_geometry_conservation=conservation,full_phy_accepted=False,closed_loop=False,qualified_pex=False,main_chip_integrated=False)
    record['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()};(dest/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],bbox_um=record['bbox_um'],devices=len(reference))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
