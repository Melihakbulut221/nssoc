#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual pad wrapper around frozen clocked bank v4, with explicit shared substrate return."""
import argparse
import json
from pathlib import Path
import sys

import make_pcie_clocked_bank_v4 as bank
from make_pcie_pad_boundary import reference as pad_reference
from make_pcie_sampler_cell import sha

TOP = 'nssoc_pcie_padded_clocked_bank4_v1'
WIDTH, HEIGHT = 2940.0, 3440.0
PORTS = (*bank.PORTS, 'ESD_VDD', 'ESD_RETURN')
LAYERS = dict(Metal1=8,Metal2=10,Metal3=30,Metal4=50,Metal5=67,TopMetal1=126,TopMetal2=134)
PARENTS = {
 'bank': dict(top=bank.TOP,gds='35457f4919f211f8aab1b73a53db5357b1ee3de895961b366c1b92f0d7c315a3',result='04ccbfdcd75ca3c8c7ae7c12eb2f7dbeb02f87c9ed7a364eb4ee8b5cf409c35e',schematic='8655c38f1f48ec26e11e817a670f2f3addacefc214bd98858939d0fb706ebd96',check='e2396d6a28c19ab6744005e5361d69e3b4f48c84d07f58078f4b32cddb58f73a'),
 'pad': dict(top='nssoc_pcie_pad_boundary',gds='2c504a7930ebf78a12d2d29747d71dc779759774cea607feaf661f04b8ac318e',result='1798c472301e334c4db90a6a8fea8792697eae3c4624e27855ce4b764a53e6ee',schematic='5fdd71b2c2523fafab0e149b6db3b30e30c491fab35a5f307094a48cb7e093f3',check='ecb9395de1620837b2a6416562d0373180707d1ba67283990393c43ac79c4ec4')}


def serial_net(lane,kind,pol):
    if lane not in range(4) or kind not in ('TX','RX') or pol not in ('P','N'):
        raise ValueError('Unknown serial terminal')
    return f'L{lane}_{kind}_'+('OUT' if kind=='TX' else 'IN')+pol


SERIAL = tuple(serial_net(i,k,p) for i in range(4) for k in ('TX','RX') for p in 'PN')


def reference(text):
    if __import__('hashlib').sha256(text.encode()).hexdigest()!=PARENTS['bank']['schematic']:
        raise ValueError('Exact frozen bank reference required')
    lines=['* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut','* SPDX-License-Identifier: CERN-OHL-W-2.0',
           '* ESD_RETURN is the actual shared substrate; finite SUB contacts remain, additional native ESD substrate paths are present.',
           '.subckt '+TOP+' '+' '.join(PORTS)]
    for line in text.splitlines():
        if line and line[0] in 'QRCM':
            # Only the new explicitly exposed shared-body net is renamed.
            lines.append(' '.join('ESD_RETURN' if x=='BULK' else x for x in line.split()))
    if len(lines)!=323:
        raise ValueError('Frozen319-device bank body changed')
    for i in range(4):
        for k in ('TX','RX'):
            for line in pad_reference().splitlines():
                if line.startswith('D'):
                    f=line.split();f[0]=f'D{i}{k}_'+f[0][1:];f[1]='ESD_VDD';f[2]=serial_net(i,k,f[2][-1]);f[3]='ESD_RETURN'
                    lines.append(' '.join(f))
    return '\n'.join(lines+['.ends '+TOP,''])


def use_direction(name):
    if name=='ESD_VDD':return 'POWER','INOUT'
    if name=='ESD_RETURN':return 'GROUND','INOUT'
    return bank.use_direction(name)


def lef(pya,dbu,ports):
    if set(ports)!=set(PORTS):raise ValueError('All56wrapper ports required')
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','MACRO '+TOP,'  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {WIDTH:.3f} BY {HEIGHT:.3f} ;']
    for n,(m,b) in ports.items():
        use,direction=use_direction(n)
        lines+=['  PIN '+n,'    DIRECTION '+direction+' ;','    USE '+use+' ;','    PORT','      LAYER '+m+' ;',f'      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;','    END','  END '+n]
    lines+=['  OBS']
    for m in LAYERS:
        region=pya.Region(pya.DBox(0,0,WIDTH,HEIGHT).to_itype(dbu))
        for layer,b in ports.values():
            if layer==m:region-=pya.Region(b.to_itype(dbu))
        lines+=['    LAYER '+m+' ;']
        for polygon in region.decompose_trapezoids_to_region().each():
            if polygon.area()!=polygon.bbox().area():raise ValueError('Nonrectangular obstruction')
            b=polygon.bbox().to_dtype(dbu);lines+=[f'      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;']
    return '\n'.join(lines+['  END','END '+TOP,'END LIBRARY',''])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('pdk','bank','bank-check','pad','pad-check','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[3];out=a.out.resolve();pdk=a.pdk.resolve()
    if out.exists() or not(out.is_relative_to(root/'hw/soc/out') or out.is_relative_to('/dev/shm') and out.name.startswith('nssoc-padded-clocked-')):p.error('Fresh bounded directory required')
    folders={'bank':a.bank.resolve(),'pad':a.pad.resolve()};pins={};records={}
    for label,folder in folders.items():
        contract=PARENTS[label]
        for name,key in ((contract['top']+'.gds','gds'),('result.json','result'),('schematic.cir','schematic')):
            path=folder/name
            if sha(path)!=contract[key]:raise ValueError('Exact positive parent changed: '+str(path))
            pins[str(path)]=contract[key]
        records[label]=json.loads((folder/'result.json').read_text())
        for path,h in records[label]['input_sha256'].items():
            if sha(path)!=h:raise ValueError('Frozen parent dependency changed')
            pins[path]=h
        check=a.bank_check.resolve() if label=='bank' else a.pad_check.resolve()
        if sha(check/'result.json')!=contract['check']:raise ValueError('Exact completed parent validation changed')
        pins[str(check/'result.json')]=contract['check']
    source=pdk/'libs.tech/klayout/python'
    for path in [Path(__file__).resolve(),Path(bank.__file__).resolve(),root/'hw/soc/flow/make_pcie_pad_boundary.py',root/'hw/soc/flow/make_pcie_sampler_cell.py',pdk/'libs.tech/ngspice/models/sg13g2_esd.lib',*source.rglob('*.py'),*source.rglob('*.json')]:pins[str(path)]=sha(path)
    sys.dont_write_bytecode=True;sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    l=pya.Layout();top=l.create_cell(TOP);cells={};native_layouts=[];copies={};placements=[];routes=[];vias=[];ports={};connections=[]
    for label,folder in folders.items():
        native=pya.Layout();native.read(str(folder/(PARENTS[label]['top']+'.gds')));old=native.cell(PARENTS[label]['top'])
        copied=l.create_cell('padded_clocked_'+label);copied.copy_tree(old);layers=[]
        for info in set(l.layer_infos())|set(native.layer_infos()):
            if info.datatype in (2,25):copied.shapes(l.layer(info)).clear();continue
            before=pya.Region(old.begin_shapes_rec(native.layer(info)));after=pya.Region(copied.begin_shapes_rec(l.layer(info)))
            if not(before^after).is_empty():raise ValueError('Original parent geometry changed')
            if not before.is_empty():layers.append(str(info))
        copies[label]=dict(source=str(folder/(PARENTS[label]['top']+'.gds')),unchanged_layers=sorted(layers));cells[label]=copied;native_layouts.append(native)
    def wire(m,x1,y1,x2,y2,w,net):
        if x1!=x2 and y1!=y2:raise ValueError('Manhattan routes only')
        b=pya.DBox(min(x1,x2)-(w/2 if x1==x2 else 0),min(y1,y2)-(w/2 if y1==y2 else 0),max(x1,x2)+(w/2 if x1==x2 else 0),max(y1,y2)+(w/2 if y1==y2 else 0));top.shapes(l.layer(LAYERS[m],0)).insert(b)
        row=dict(net=net,layer=m,rect_um=[b.left,b.bottom,b.right,b.top]);routes.append(row);return row
    def via(bottom,upper,x,y,net):
        c=l.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=upper,vn_columns=1,vn_rows=2,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
        if c is None or c.is_empty():raise ValueError('Native via failed')
        b=c.dbbox();t=pya.DTrans(x-b.center().x,y-b.center().y);top.insert(pya.DCellInstArray(c.cell_index(),t));top.shapes(l.layer(126,0)).insert(pya.DBox(x-1.2,y-1.2,x+1.2,y+1.2));vias.append(dict(net=net,bottom=bottom,top=upper,center_um=[x,y]))
    def pin(n,m,b):
        if n in ports:raise ValueError('Duplicate pin')
        ports[n]=(m,b);top.shapes(l.layer(LAYERS[m],0)).insert(b);top.shapes(l.layer(LAYERS[m],2)).insert(b);top.shapes(l.layer(LAYERS[m],25)).insert(pya.DText(n,pya.DTrans(b.center().x,b.center().y)))
    bt=pya.DTrans(400.0,400.0);top.insert(pya.DCellInstArray(cells['bank'].cell_index(),bt));placements.append(dict(kind='bank',offset_um=[400,400]))
    bp={n:pya.DBox(*r['rect_um']).transformed(bt) for n,r in records['bank']['ports'].items()}
    for n,row in records['bank']['ports'].items():
        b=bp[n];x,y=b.center().x,b.center().y
        if n in SERIAL:continue
        if row['layer']=='TopMetal2':
            wire('TopMetal2',x,y,x,HEIGHT,4,n);pin(n,'TopMetal2',pya.DBox(x-2,HEIGHT-4,x+2,HEIGHT))
        else:
            edge=0 if b.left==400 else WIDTH
            if b.left!=400 and b.right!=2530:raise ValueError('Original boundary moved')
            wire('TopMetal1',x,y,edge,y,2,n);pin(n,'TopMetal1',pya.DBox(0,y-1,2,y+1) if edge==0 else pya.DBox(WIDTH-2,y-1,WIDTH,y+1))
    for index,(lane,kind) in enumerate((i,k) for i in range(4) for k in ('TX','RX')):
        pt=pya.DTrans(500.0+240*index,20.0);top.insert(pya.DCellInstArray(cells['pad'].cell_index(),pt));placements.append(dict(kind='pad',lane=lane,role=kind,offset_um=[500+240*index,20]))
        for pol in 'PN':
            n=serial_net(lane,kind,pol);data=records['pad']['ports']['PAD'+pol];bond=pya.DBox(*data['rectangles_um'][0]).transformed(pt);core=pya.DBox(*data['rectangles_um'][1]).transformed(pt);pin(n,'TopMetal2',bond)
            b=bp[n];bx,by=b.center().x,b.center().y;cx,cy=core.center().x,core.center().y;left=b.left==400
            slot=lane*2+(kind=='RX');channel=80+24*slot if left else 2640+24*slot;bridge=270+8*SERIAL.index(n)
            wire('TopMetal2',cx,cy,cx,bridge,4,n);via('TopMetal1','TopMetal2',cx,bridge,n);row=wire('TopMetal1',cx,bridge,channel,bridge,2.4,n);via('TopMetal1','TopMetal2',channel,bridge,n);wire('TopMetal2',channel,bridge,channel,by,4,n);via('TopMetal1','TopMetal2',channel,by,n);wire('TopMetal1',channel,by,bx,by,2.4,n)
            connections.append(dict(net=n,bank_rect_um=[b.left,b.bottom,b.right,b.top],pad_core_rect_um=[core.left,core.bottom,core.right,core.top],bridge=row,channel_x_um=channel))
    for n,y,x in [('ESD_VDD',200.0,2860.0),('ESD_RETURN',220.0,2890.0)]:
        wire('Metal5',500,y,x,y,4,n);via('Metal5','TopMetal2',x,y,n);wire('TopMetal2',x,y,x,HEIGHT,4,n);pin(n,'TopMetal2',pya.DBox(x-2,HEIGHT-4,x+2,HEIGHT))
    if set(ports)!=set(PORTS) or len(connections)!=16:raise ValueError('Complete wrapper graph missing')
    bbox=top.dbbox()
    if bbox.left<0 or bbox.bottom<0 or bbox.right>WIDTH or bbox.top>HEIGHT:raise ValueError('Geometry outside wrapper outline')
    out.mkdir(parents=True);l.write(str(out/(TOP+'.gds')));(out/(TOP+'.lef')).write_text(lef(pya,l.dbu,ports));(out/'schematic.cir').write_text(reference((folders['bank']/'schematic.cir').read_text()))
    if any(sha(p)!=h for p,h in pins.items()):raise ValueError('Inputs changed during generation')
    record=dict(status='GENERATED_REQUIRES_FULL_NATIVE_VALIDATION',input_sha256=pins,output_sha256={p.name:sha(p) for p in out.iterdir()},ports={n:dict(layer=m,rect_um=[b.left,b.bottom,b.right,b.top]) for n,(m,b) in ports.items()},copies=copies,placements=placements,routes=routes,vias=vias,serial_connections=connections,bbox_um=[0,0,WIDTH,HEIGHT],primitive_counts=dict(**bank.COUNTS,ESD_diodes=32,bondpads=16),substrate_contract='ESD_RETURN exposes actual shared substrate.108 finite SUB contacts retained; ESD structures add real substrate paths. It is not independent ground isolation or unchanged body impedance. No direct AVSS/SUB/supply joins.',esd_qualified=False,qualified_pex=False,main_chip_integrated=False,phy_complete=False)
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
