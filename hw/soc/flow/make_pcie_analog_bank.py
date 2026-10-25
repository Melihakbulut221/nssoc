#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real four-lane analog TX/RX hierarchy and metal, not a complete PCIe PHY."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOP = 'nssoc_pcie_analog_bank4'
SUPPLIES = ('AVDD', 'AVSS', 'SUB')
TX_GDS_SHA = 'e94cfeb84b007ae23449de25e2c35fd63720f52ccfd5fa44d8d3a6f4380fa7c2'
TX_RESULT_SHA = '1355131bd7774a16c46e381e8103060a3fce84b6ddc4df05ba35da8c18956dc8'
CELL_PORTS = {'TX': ('INP','INN','OUTP','OUTN','AVDD','AVSS','SUB','IREF'),
              'RX': ('INP','INN','OUTP','OUTN','AVDD','AVSS','SUB','IREF','VCM')}
PORTS = tuple(f'L{i}_{kind}_{pin}' for i in range(4) for kind in ('TX','RX')
              for pin in CELL_PORTS[kind] if pin not in SUPPLIES) + SUPPLIES
WIDTH, HEIGHT, PITCH = 260.0, 1460.0, 180.0


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def mapped_net(lane, kind, net):
    if lane not in range(4) or kind not in CELL_PORTS:
        raise ValueError('Unknown lane/cell')
    return net if net in (*SUPPLIES, 'BULK') else f'L{lane}_{kind}_{net}'


def reference(tx, rx):
    """Literal original device bodies, real common metal nets and substrate."""
    out = ['* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut',
           '* SPDX-License-Identifier: CERN-OHL-W-2.0', '.subckt '+TOP+' '+' '.join(PORTS)]
    counts = {'Q':0,'R':0,'tap':0}
    for lane in range(4):
        for kind, text in (('TX',tx),('RX',rx)):
            lines = [v.split() for v in text.splitlines() if v.strip() and not v.startswith('*')]
            if len(lines) < 3 or lines[0][0].lower() != '.subckt' or tuple(lines[0][2:]) != CELL_PORTS[kind] or lines[-1][0].lower() != '.ends':
                raise ValueError('Primitive source port contract differs')
            for fields in lines[1:-1]:
                typ=fields[0][0].upper(); terminals=4 if typ=='Q' else 2 if fields[3].lower()=='ptap1' else 3
                if typ not in ('Q','R'):
                    raise ValueError('Unsupported primitive reference')
                counts['tap' if terminals==2 else typ]+=1
                out.append(' '.join([f'{typ}{lane}{kind}_{fields[0][1:]}']+
                           [mapped_net(lane,kind,n) for n in fields[1:1+terminals]]+fields[1+terminals:]))
    if counts != {'Q':32,'R':24,'tap':64}:
        raise ValueError('Bank primitive census differs')
    return '\n'.join(out+['.ends '+TOP,''])


def use_direction(name):
    if name == 'AVDD': return 'POWER','INOUT'
    if name in ('AVSS','SUB'): return 'GROUND','INOUT'
    return 'SIGNAL','OUTPUT' if name.endswith(('_OUTP','_OUTN')) else 'INPUT'


def lef(pya, dbu, ports):
    if set(ports)!=set(PORTS): raise ValueError('Incomplete bank ports')
    out=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','MACRO '+TOP,
         '  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {WIDTH:.3f} BY {HEIGHT:.3f} ;']
    for n in PORTS:
        layer,b=ports[n];use,direction=use_direction(n)
        out += ['  PIN '+n,'    DIRECTION '+direction+' ;','    USE '+use+' ;','    PORT',
                '      LAYER '+layer+' ;',f'      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;',
                '    END','  END '+n]
    out+=['  OBS']
    for layer in ('Metal1','Metal2','Metal3','Metal4','Metal5','TopMetal1','TopMetal2'):
        region=pya.Region(pya.DBox(0,0,WIDTH,HEIGHT).to_itype(dbu))
        openings=pya.Region()
        for metal,box in ports.values():
            if metal==layer: openings.insert(box.to_itype(dbu))
        out += ['    LAYER '+layer+' ;']
        for polygon in (region-openings).decompose_trapezoids_to_region().each():
            if polygon.area()!=polygon.bbox().area(): raise ValueError('Nonrectangular obstruction')
            b=polygon.bbox().to_dtype(dbu)
            out += [f'      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;']
    return '\n'.join(out+['  END','END '+TOP,'END LIBRARY',''])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('pdk','tx','rx','out'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();root=Path(__file__).resolve().parents[3];out=a.out.resolve()
    if out.exists() or not (out.is_relative_to(root/'hw/soc/out') or out.is_relative_to(Path('/dev/shm')) and out.name.startswith('nssoc-bank-')):
        ap.error('Fresh project or /dev/shm/nssoc-bank- output required')
    tx=a.tx.resolve();rx=a.rx.resolve();pdk=a.pdk.resolve()
    if sha(tx/'nssoc_tx_cml_layout.gds')!=TX_GDS_SHA or sha(tx/'result.json')!=TX_RESULT_SHA:
        raise ValueError('TX differs from exact independently verified original geometry')
    from make_pcie_rx_cell_v2 import TOP as RX_TOP, CIRCUIT_SHA256, physical_reference
    rx_result=json.loads((rx/'result.json').read_text());tx_result=json.loads((tx/'result.json').read_text())
    if rx_result['source_circuit_sha256']!=CIRCUIT_SHA256:
        raise ValueError('RX source geometry contract differs')
    if (rx/'schematic.cir').read_text()!=physical_reference((root/'hw/soc/analog/pcie/rx_hbt_rsil_v2.spice').read_text()):
        raise ValueError('RX reference differs from frozen circuit')
    pins={str(Path(__file__).resolve()):sha(__file__),str(root/'hw/soc/flow/make_pcie_rx_cell_v2.py'):sha(root/'hw/soc/flow/make_pcie_rx_cell_v2.py')}
    for folder,result in ((tx,tx_result),(rx,rx_result)):
        pins[str(folder/'result.json')]=sha(folder/'result.json')
        for name,expected in result['output_sha256'].items():
            if sha(folder/name)!=expected: raise ValueError('Primitive view changed')
            pins[str(folder/name)]=expected
        for path,expected in result['input_sha256'].items():
            if not Path(path).is_file() or sha(path)!=expected: raise ValueError('Primitive method/source changed')
            pins[path]=expected
    source=pdk/'libs.tech/klayout/python';lyp=source.parent/'tech/sg13g2.lyp'
    for path in [*source.rglob('*.py'),*source.rglob('*.json'),lyp]:pins[str(path)]=sha(path)
    sys.dont_write_bytecode=True;sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- actual native via PCells
    l=pya.Layout();top=l.create_cell(TOP);layers={}
    for prop in ET.parse(lyp).getroot().iter('properties'):
        name=prop.findtext('name','')
        if name.endswith('.drawing'): layers[name[:-8]]=int(prop.findtext('source').split('/')[0])
    cells={};measurements={};source_layouts=[]
    for kind,folder,name in (('TX',tx,'nssoc_tx_cml_layout'),('RX',rx,RX_TOP)):
        native=pya.Layout();native.read(str(folder/(name+'.gds')));c=native.cell(name)
        if c is None:raise ValueError('Missing primitive cell')
        if not pya.Region(c.begin_shapes_rec(native.layer(layers['TopMetal1'],0))).is_empty() or not pya.Region(c.begin_shapes_rec(native.layer(layers['TopMetal2'],0))).is_empty():
            raise ValueError('Primitive occupies reserved bank routing metal')
        labels={}
        boxes=[s.dbbox() for s in c.each_shape(native.layer(layers['Metal5'],2))]
        for s in c.each_shape(native.layer(layers['Metal5'],25)):
            if not s.is_text():raise ValueError('Unexpected primitive label shape')
            n=s.dtext.string;p=s.dtext.trans.disp
            found=[b for b in boxes if b.contains(pya.DPoint(p.x,p.y))]
            if len(found)!=1 or n in labels:raise ValueError('Ambiguous native primitive pin')
            labels[n]=found[0]
        if set(labels)!=set(CELL_PORTS[kind]):raise ValueError('Primitive physical pin inventory differs')
        copied=l.create_cell('bank_'+kind);copied.copy_tree(c)
        # Parent owns port labels; remove only copied primitive top pin/label metadata.
        # All conductive geometry and device PCell hierarchy are retained verbatim.
        for layer in native.layer_infos():
            if layer.datatype in (2,25):copied.shapes(l.layer(layer)).clear()
        measurements[kind]={'bbox_um':[c.dbbox().left,c.dbbox().bottom,c.dbbox().right,c.dbbox().top],
                            'ports':{n:[b.left,b.bottom,b.right,b.top] for n,b in labels.items()}}
        cells[kind]=(copied,labels,c.dbbox());source_layouts.append(native)
    routes=[];ports={};placements=[];vias=[]
    def rect(layer,b):top.shapes(l.layer(layers[layer],0)).insert(b)
    def via(bottom,upper,x,y,net):
        c=l.create_cell('via_stack','SG13_dev',{'b_layer':bottom,'t_layer':upper,'vt1_columns':2,'vt1_rows':1,'vt2_columns':1,'vt2_rows':1})
        if c is None or c.is_empty():raise ValueError('Native bank via failed')
        b=c.dbbox();t=pya.DTrans(x-b.center().x,y-b.center().y)
        top.insert(pya.DCellInstArray(c.cell_index(),t))
        # Actual native two-cut topvia1 metal is only1.26um tall; extend the
        # bank landing to2.4um in both dimensions (TM1 minimum1.64um).
        rect('TopMetal1',pya.DBox(x-1.2,y-1.2,x+1.2,y+1.2))
        vias.append(dict(landing_topmetal1_um=[x-1.2,y-1.2,x+1.2,y+1.2],net=net,bottom=bottom,top=upper,center_um=[x,y],bbox_um=str(b.transformed(t))))
    def pin(net,layer,b):
        if net in ports:raise ValueError('Repeated bank pin')
        ports[net]=(layer,b);rect(layer,b)
        top.shapes(l.layer(layers[layer],2)).insert(b)
        top.shapes(l.layer(layers[layer],25)).insert(pya.DText(net,pya.DTrans(b.center().x,b.center().y)))
    trunks={'AVDD':220.0,'AVSS':232.0,'SUB':244.0}
    for net,x in trunks.items():
        rect('TopMetal2',pya.DBox(x-2,0,x+2,HEIGHT));pin(net,'TopMetal2',pya.DBox(x-2,0,x+2,4))
    for lane in range(4):
        for index,kind in enumerate(('TX','RX')):
            c,pins_local,box=cells[kind];dx=30-box.left;dy=10+(lane*2+index)*PITCH-box.bottom
            t=pya.DTrans(dx,dy);top.insert(pya.DCellInstArray(c.cell_index(),t))
            placements.append(dict(lane=lane,kind=kind,cell=c.name,translation_um=[dx,dy],bbox_um=str(box.transformed(t))))
            for name in CELL_PORTS[kind]:
                b=pins_local[name].transformed(t);x,y=b.center().x,b.center().y;net=mapped_net(lane,kind,name)
                via('Metal5','TopMetal1',x,y,net)
                if name in SUPPLIES:
                    edge=trunks[name];via('TopMetal1','TopMetal2',edge,y,net)
                else:
                    # Same-height differential pins escape toward opposite boundaries.
                    edge=0.0 if name in ('INP','OUTN','IREF') else WIDTH
                    pin(net,'TopMetal1',pya.DBox(0,y-1,2,y+1) if edge==0 else pya.DBox(WIDTH-2,y-1,WIDTH,y+1))
                route=pya.DBox(min(x,edge),y-1,max(x,edge),y+1);rect('TopMetal1',route)
                routes.append(dict(lane=lane,kind=kind,terminal=name,net=net,source_m5_rect_um=[b.left,b.bottom,b.right,b.top],
                                   layer='TopMetal1',route_rect_um=[route.left,route.bottom,route.right,route.top]))
    if set(ports)!=set(PORTS) or top.dbbox()!=pya.DBox(0,0,WIDTH,HEIGHT):raise ValueError('Bank boundary/port inventory differs')
    net=reference((tx/'schematic.cir').read_text(),(rx/'schematic.cir').read_text())
    out.mkdir(parents=True);(out/'schematic.cir').write_text(net);l.write(str(out/(TOP+'.gds')))
    (out/(TOP+'.lef')).write_text(lef(pya,l.dbu,ports))
    if any(sha(path)!=value for path,value in pins.items()):raise ValueError('Bank inputs changed during generation')
    result=dict(status='GENERATED_REQUIRES_BANK_DRC_LVS_AND_PHYSICAL_QUALIFICATION',input_sha256=pins,
                output_sha256={p.name:sha(p) for p in out.iterdir()},ports={n:dict(layer=layer,rect_um=[b.left,b.bottom,b.right,b.top]) for n,(layer,b) in ports.items()},
                primitive_source_measurements=measurements,placements=placements,routes=routes,vias=vias,
                bbox_um=[0,0,WIDTH,HEIGHT],primitive_counts=dict(hbt=32,rsil=24,physical_tap=64),
                klayout_version=pya.__version__,phy_complete=False,main_chip_integrated=False,qualified_pex=False,
                scope='Four actual TX/RX preamplifier lanes with shared routed AVDD/AVSS/SUB and explicit 44 signal/bias pins. No serializer, slicer, CDR, PLL, pad/ESD, package, current or RF qualification, full PHY or main chip integration.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
