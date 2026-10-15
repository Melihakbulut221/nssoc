#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Assemble the actual three-macro 4:1 CML core, then native transistor LVS/DRC.

This is one physical core on the path to32:1/four lanes, NOT fullPHY: CMOS
frontends, loaded TX, clock/bias generation, mainchip and qualified PEX remain.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from run_cloud_tx_layout_repair import fetch, sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-tree-assembly'
TOP='nssoc_tx_tree4_core_v1'
CHILD_PORTS='ap an bp bn sp sn op on avdd avss sub iref'.split()
MAPS={
 'a':dict(zip(CHILD_PORTS,'d0p d0n d2p d2n sap san ap an avdd avss sub ra'.split(),strict=True)),
 'b':dict(zip(CHILD_PORTS,'d1p d1n d3p d3n sbp sbn bp bn avdd avss sub rb'.split(),strict=True)),
 'f':dict(zip(CHILD_PORTS,'ap an bp bn sp sn mp mn avdd avss sub mr'.split(),strict=True))}
PORTS='d0p d0n d1p d1n d2p d2n d3p d3n sap san sbp sbn sp sn mp mn avdd avss sub ra rb mr'.split()

def flatten_reference(text,tag):
    lines=text.splitlines()
    header=[x.split() for x in lines if x.lower().startswith('.subckt ')]
    assert len(header)==1 and header[0][2:]==CHILD_PORTS
    assert sum(x.lower().startswith('.ends ') for x in lines)==1
    output=[]
    for line in lines:
        if not line.strip() or line.startswith(('*','.')): continue
        row=line.split();kind=row[0][0]
        if kind=='Q': count,model=4,'npn13G2'
        elif row[0].startswith('RPTAP'): count,model=2,'ptap1'
        elif row[0].startswith('RD'): count,model=3,'rppd'
        else: raise ValueError('Unknown native device card: '+row[0])
        assert row[count+1]==model, 'Native model/terminal arity mismatch'
        assert all('=' not in node for node in row[1:count+1])
        row[0]=kind+tag+'_'+row[0][1:]
        row[1:count+1]=[MAPS[tag].get(n,'BULK' if n=='BULK' else tag+'_'+n) for n in row[1:count+1]]
        output.append(' '.join(row))
    assert len(output)==54 and len({x.split()[0] for x in output})==54
    assert sum(x.startswith('Q') for x in output)==19
    return output

def generate(profile):
    assert profile in ('baseline','compact_vertical','compact_m5_supply')
    import xml.etree.ElementTree as ET
    source=ROOT/'pdk/libs.tech/klayout/python'
    sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # native PDK via_stack, no hand-drawn via models
    lyp=source.parent/'tech/sg13g2.lyp'
    layers={p.findtext('name')[:-8]:int(p.findtext('source').split('/')[0]) for p in ET.parse(lyp).getroot().iter('properties') if p.findtext('name','').endswith('.drawing')}
    layout=pya.Layout();layout.dbu=.001;top=layout.create_cell(TOP)
    protected={str(Path(__file__).resolve()):sha(Path(__file__).resolve()),str(lyp):sha(lyp)}
    transformed={};schematic=['* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut','* SPDX-License-Identifier: CERN-OHL-W-2.0','.subckt '+TOP+' '+' '.join(PORTS)]
    children={};placement={}
    for kind,child_top in [('pre','nssoc_tx_mux2_cascade158_layout_v1'),('final','nssoc_tx_mux2_final_drive_v10_layout_v1')]:
        directory=OUT/'inputs'/kind/'layout';data=json.loads((directory/'result.json').read_text())
        for name,digest in data['outputs'].items():
            assert sha(directory/name)==digest;protected[str(directory/name)]=digest
        source_layout=pya.Layout();source_layout.read(str(directory/(child_top+'.gds')))
        child=source_layout.cell(child_top);assert child is not None and source_layout.dbu==layout.dbu
        copied=layout.create_cell('core_'+kind);copied.copy_tree(child)
        # Retain the original native PCell hierarchy for exact terminal anchors.
        # Replace only12macro-level public labels/pins before instantiation.
        for datatype in (2,25):
            shapes=copied.shapes(layout.layer(layers['TopMetal2'],datatype))
            assert sum(1 for _ in shapes.each())==12
            shapes.clear()
        # Independent physical drawing-region equality against each frozen child.
        for idx in source_layout.layer_indexes():
            info=source_layout.get_info(idx)
            if info.datatype!=0:continue
            before=pya.Region(child.begin_shapes_rec(idx)).merged()
            after=pya.Region(copied.begin_shapes_rec(layout.layer(info.layer,info.datatype))).merged()
            assert (before^after).is_empty(), ('Frozen child physical geometry changed',kind,info.layer)
        children[kind]=(copied,data,directory)
    by,fy=(400.,150.) if profile=='baseline' else (330.,112.)
    fx=470. if profile=='compact_m5_supply' else 550.
    for tag,kind,x,y,mirror in [('a','pre',353.985,0.,True),('b','pre',353.985,by,True),('f','final',fx,fy,False)]:
        child,data,directory=children[kind]
        tr=pya.DTrans(2 if mirror else 0,mirror,x,y)
        top.insert(pya.DCellInstArray(child.cell_index(),tr))
        actual={}
        for name,coords in data['ports'].items():
            vals=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',coords)];assert len(vals)==4
            actual[name]=pya.DBox(*vals).transformed(tr)
        transformed[tag]=actual
        placement[tag]=dict(kind=kind,transform=str(tr),bbox_um=str(child.dbbox().transformed(tr)),ports={k:str(v) for k,v in actual.items()})
        schematic.extend(flatten_reference((directory/'schematic.cir').read_text(),tag))
    schematic.append('.ends '+TOP)
    # Native PCell recognition text and hierarchy are deliberately retained.
    routes=[]
    def box(layer,x1,y1,x2,y2):
        top.shapes(layout.layer(layers[layer],0)).insert(pya.DBox(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)))
    def via(x,y,power=False,bottom='TopMetal1'):
        params=dict(b_layer=bottom,t_layer='TopMetal2',vn_columns=2,vn_rows=1,vt1_rows=1,vt2_columns=4 if power else 2,vt2_rows=4 if power else 1)
        if bottom=='Metal5':
            assert power
            params.update(vt1_columns=4,vt1_rows=4)
        c=layout.create_cell('via_stack','SG13_dev',params)
        assert c is not None and not c.is_empty()
        b=c.dbbox();top.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(round((x-b.center().x)/.005)*.005,round((y-b.center().y)/.005)*.005)))
    def center(tag,pin):
        q=transformed[tag][pin].center();return q.x,q.y
    def hstub(tag,pin,x,width,bottom='TopMetal1'):
        px,py=center(tag,pin)
        # Rectangles must cover either direction of travel, including endpoints.
        box('TopMetal2',min(px,x)-width/2,py-width/2,max(px,x)+width/2,py+width/2)
        via(x,py,width>4,bottom);return py
    signal_x=(378.,390.,402.,414.) if profile=='compact_m5_supply' else (370.,382.,408.,420.)
    for (tag,op,ip),x in zip([('a','op','ap'),('a','on','an'),('b','op','bp'),('b','on','bn')],signal_x,strict=True):
        y0=hstub(tag,op,x,4.);y1=hstub('f',ip,x,4.)
        box('TopMetal1',x-2,min(y0,y1)-2,x+2,max(y0,y1)+2)
        routes.append(dict(net=MAPS[tag][op],endpoints=[tag+'.'+op,'f.'+ip],vertical_x_um=x,width_um=4.,length_um=abs(y0-y1)+abs(center(tag,op)[0]-x)+abs(center('f',ip)[0]-x),fault_cut_um=[x-3,(y0+y1)/2-.5,x+3,(y0+y1)/2+.5]))
    # Shared actual power and substrate conductors, all outside macro bodies.
    power_routes=[('avdd',490.,32.),('sub',530.,4.)]
    if profile=='compact_m5_supply':
        # Separate the wide supply stripe from TM1 data channels. W=96um
        # avoids replacing the old32um thick-metal trunk with a narrow M5 wire.
        # Native 4x4via arrays connect M5 through TM1 to TM2 only at x366.
        ys=[hstub(tag,'avdd',366.,32.,'Metal5') for tag in ('a','b','f')]
        box('Metal5',358.,min(ys)-16.,454.,max(ys)+16.)
        routes.append(dict(net='avdd',endpoints=[tag+'.avdd' for tag in ('a','b','f')],
            vertical_x_um=406.,width_um=96.,layer='Metal5',via_x_um=366.,native_via_arrays='4x4 each upper level',em_qualified=False))
        power_routes=[('sub',466.,4.)]
    for net,x,width in power_routes:
        ys=[hstub(tag,net,x,width) for tag in ('a','b','f')]
        box('TopMetal1',x-width/2,min(ys)-width/2,x+width/2,max(ys)+width/2)
        routes.append(dict(net=net,endpoints=[tag+'.'+net for tag in ('a','b','f')],vertical_x_um=x,width_um=width))
    ys=[hstub(tag,'avss',-40.,32.) for tag in ('a','b')]
    ground_x=444. if profile=='compact_m5_supply' else 450.
    yf=hstub('f','avss',ground_x,32.)
    for x,upper in [(-40.,max(ys)),(ground_x,yf)]:
        box('TopMetal1',x-16,-76.,x+16,upper+16);via(x,-60.,True)
    box('TopMetal2',-56.,-76.,ground_x+16.,-44.)
    routes.append(dict(net='avss',endpoints=['a.avss','b.avss','f.avss'],width_um=32.,bottom_bus_y_um=-60.))
    public={}
    for tag,pins in transformed.items():
        for pin,b in pins.items():
            net=MAPS[tag][pin]
            if net in PORTS and net not in public:public[net]=('TopMetal2',b)
    assert set(public)==set(PORTS) and len(routes)==7
    for net,(layer,b) in public.items():
        top.shapes(layout.layer(layers[layer],2)).insert(b)
        top.shapes(layout.layer(layers[layer],25)).insert(pya.DText(net,b.left,b.center().y))
    # Shift the whole exact assembly to a nonnegative LEF origin.
    bounds=top.dbbox();dx=-bounds.left;dy=-bounds.bottom
    top.transform(pya.Trans(round(dx/layout.dbu),round(dy/layout.dbu)))
    public={n:(l,b.transformed(pya.DTrans(dx,dy))) for n,(l,b) in public.items()}
    for row in routes:
        if 'fault_cut_um' in row:
            b=row['fault_cut_um'];row['fault_cut_um']=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
    previous=pya.Layout();previous.read(str(OUT/'verified-flat.gds'))
    old=previous.cell(TOP);assert old is not None and previous.dbu==layout.dbu
    layer_keys={(layout.get_info(i).layer,layout.get_info(i).datatype) for i in layout.layer_indexes()}
    layer_keys|={(previous.get_info(i).layer,previous.get_info(i).datatype) for i in previous.layer_indexes()}
    changed_layers=[]
    for layer,datatype in sorted(layer_keys):
        before=pya.Region(old.begin_shapes_rec(previous.layer(layer,datatype))).merged()
        after=pya.Region(top.begin_shapes_rec(layout.layer(layer,datatype))).merged()
        if not (before^after).is_empty():changed_layers.append([layer,datatype])
    if profile=='baseline':assert not changed_layers, ('Hierarchy representation changed physical geometry',changed_layers)
    else:assert changed_layers, 'An intended physical placement change must not reuse baseline geometry'
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_clock_vco_v6_local_v1 as writer
    writer.TOP=TOP;writer.PORTS=PORTS
    writer.use_direction=lambda n:('POWER','INOUT') if n=='avdd' else ('GROUND','INOUT') if n in ('avss','sub') else ('SIGNAL','OUTPUT' if n in ('mp','mn') else 'INPUT')
    dest=OUT/'layout';dest.mkdir()
    top.write(str(dest/(TOP+'.gds')))
    (dest/'schematic.cir').write_text('\n'.join(schematic)+'\n')
    (dest/(TOP+'.lef')).write_text(writer.lef(pya,layout.dbu,top.dbbox(),public))
    assert len(schematic)==166
    result=dict(status='GENERATED_UNVERIFIED_ACTUAL_4TO1_CORE',inputs=protected,outputs={p.name:sha(p) for p in dest.iterdir()},ports={n:str(b) for n,(l,b) in public.items()},bbox_um=str(top.dbbox()),placement=placement,origin_translation_um=[dx,dy],routes=routes,exact_flat_geometry_preserved=not changed_layers,placement_profile=profile,frozen_child_drawing_regions_equal=True,baseline_geometry_changed_layers=changed_layers,core_devices=81,substrate_contacts=81,total_devices=162,serial_phy_complete=False,main_chip_integrated=False,qualified_pex=False,scope='Actual three native cores plus four differential data wires and shared supplies/substrate. External clocks/bias, CMOS frontends and loaded TX remain outside this core. Requires native DRC/LVS then fresh intermacro RC and loaded waveform gates.')
    (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true')
    p.add_argument('--placement-profile',choices=('baseline','compact_vertical','compact_m5_supply'),default='baseline');args=p.parse_args()
    if args.generate:generate(args.placement_profile);return
    assert os.environ.get('GITHUB_ACTIONS')=='true','CAD executes only on hosted runners'
    spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    out=OUT;out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',placement_profile=args.placement_profile,inputs=spec,serial_phy_complete=False,main_chip_integrated=False,qualified_pex=False)
    def run(command,label):
        log=out/(label+'.log')
        with log.open('w') as stream:code=subprocess.call([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-16000:],flush=True)
            raise RuntimeError((label,code))
    try:
        source=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        archive=out/'restore.tar.gz';fetch(source['receipt']['url'],source['receipt']['sha256'],archive)
        with tarfile.open(archive) as tar:tar.extractall(ROOT,filter='data')
        archive.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        for kind,row in spec['children'].items():
            fetch(row['url'],row['sha256'],archive);assert archive.stat().st_size==row['bytes']
            with tarfile.open(archive) as tar:
                prefix='hw/soc/out/cloud-tx-layout-repair/'
                previous=json.loads(tar.extractfile(prefix+'result.json').read())
                assert previous['status']=='PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
                assert previous['variant']==row['variant'] and previous['circuit_profile']==row['circuit_profile'] and previous['boundary_pin_policy']=='nearest_pair_tight'
                for name in ['layout/result.json','layout/schematic.cir',*['layout/'+n for n in row['generated_outputs'] if n.endswith(('.gds','.lef'))],'verify-physical.py']:
                    raw=tar.extractfile(prefix+name).read();target=out/'inputs'/kind/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                    if Path(name).name in row['generated_outputs']:assert hashlib.sha256(raw).hexdigest()==row['generated_outputs'][Path(name).name]
            archive.unlink()
        old=spec['verified_flat_assembly'];fetch(old['url'],old['sha256'],archive)
        assert archive.stat().st_size==old['bytes']
        with tarfile.open(archive) as tar:
            name='hw/soc/out/cloud-tx-tree-assembly/layout/'+TOP+'.gds'
            data=tar.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==old['outputs'][TOP+'.gds']
            (out/'verified-flat.gds').write_bytes(data)
        archive.unlink()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==source['runtime_sha256']
        run([app,'python',Path(__file__).resolve(),'--generate','--placement-profile',args.placement_profile],'generate')
        generated=json.loads((out/'layout/result.json').read_text());result['layout']=generated
        method=(out/'inputs/pre/verify-physical.py').read_text()
        before='TOP = "nssoc_tx_mux2_cascade158_layout_v1"';assert method.count(before)==1;method=method.replace(before,'TOP = '+repr(TOP))
        before="PORTS = ['ap','an','bp','bn','sp','sn','op','on','avdd','avss','sub','iref']";assert method.count(before)==1;method=method.replace(before,'PORTS = '+repr(PORTS))
        for before,after in [('"QD0 "','"Qf_D0 "'),('"QD1 "','"Qf_D1 "'),('!= 54','!= 162'),('TX_MUX54','TX_TREE162')]:
            assert method.count(before)==1;method=method.replace(before,after)
        old=next(l for l in method.splitlines() if "li=L.layer(134,0);before=pya.Region" in l)
        cut=generated['routes'][0]['fault_cut_um']
        new='    li=L.layer(126,0);before=pya.Region(top.shapes(li));cut=pya.Region(pya.DBox('+','.join(map(str,cut))+').to_itype(L.dbu));after=before-cut;assert before.area()!=after.area();top.shapes(li).clear();top.shapes(li).insert(after)'
        method=method.replace(old,new)
        verification=out/'verify-assembly.py';verification.write_text(method)
        run([sys.executable,verification,'--layout',out/'layout','--out',out/'physical','--app',app],'physical')
        physical=json.loads((out/'physical/result.json').read_text());assert physical['status']=='PASS_NATIVE_PDK_TX_TREE162_DRC_LVS_AND_FAULT_CONTROLS'
        result['physical']={k:v for k,v in physical.items() if k!='inputs'}
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        result['status']='PASS_ACTUAL_TREE162_NATIVE_DRC_LVS_FAULTS_REQUIRES_PARENT_RC_AND_WAVES'
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e))
        if (out/'physical/result.json').exists():result['physical']=json.loads((out/'physical/result.json').read_text())
        raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json'}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
