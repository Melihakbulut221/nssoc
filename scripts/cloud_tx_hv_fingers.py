#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route all actual ng10 fingers and prove raw and aggregated native LVS.

A physical building block for the original input driver. No full driver,
extracted electrical, serializer, PHY or chip acceptance is implied.
"""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-hv-fingers'
TOP='nssoc_tx_hv_ng10_v1'
PORTS=['drain','gate','source','sub']

def generate(fault):
    import xml.etree.ElementTree as ET
    native=ROOT/'pdk/libs.tech/klayout/python'
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(native),str(native/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    layers={p.findtext('name')[:-8]:int(p.findtext('source').split('/')[0]) for p in ET.parse(native.parent/'tech/sg13g2.lyp').getroot().iter('properties') if p.findtext('name','').endswith('.drawing')}
    layout=pya.Layout();top=layout.create_cell(TOP)
    def pc(name,params):
        cell=layout.create_cell(name,'SG13_dev',params);assert cell is not None and not cell.is_empty();return cell
    placements=[]
    def place(cell,x,y):
        # DTrans(int, int) selects rotation/mirror, not translation.
        t=pya.DTrans(float(x),float(y))
        b=pya.DBox(0.,0.,1.,2.).transformed(t)
        assert [b.left,b.bottom,b.right,b.top]==[float(x),float(y),float(x)+1.,float(y)+2.]
        top.insert(pya.DCellInstArray(cell.cell_index(),t))
        placements.append(dict(cell=cell.name,x_um=float(x),y_um=float(y),native_transform=str(t)))
        return t
    def box(layer,x1,y1,x2,y2):
        b=pya.DBox(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2));top.shapes(layout.layer(layers[layer],0)).insert(b);return b
    def via(x,y):
        cell=pc('via_stack',dict(b_layer='Metal1',t_layer='Metal2',vn_columns=1,vn_rows=1,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
        center=cell.dbbox().center();place(cell,x-center.x,y-center.y)
    cell=pc('nmosHV',dict(w='10u',l='.45u',ng=10));t=place(cell,30,30)
    active=pya.Region(cell.begin_shapes_rec(layout.layer(layers['Activ'],0))).merged()
    poly=pya.Region(cell.begin_shapes_rec(layout.layer(layers['GatPoly'],0))).merged()
    gates=sorted((active&poly).each(),key=lambda p:p.bbox().left)
    diffusion=sorted(pya.Region(cell.begin_shapes_rec(layout.layer(layers['Metal1'],0))).merged().each(),key=lambda p:p.bbox().left)
    assert len(gates)==10 and len(diffusion)==11
    routes=[]
    for i,p in enumerate(diffusion):
        b=p.bbox().to_dtype(layout.dbu).transformed(t);x=round(b.center().x/.005)*.005
        net='source' if i%2==0 else 'drain';y=27 if net=='source' else 33
        omit=fault=='drain_open' and i==9
        if not omit:box('Metal1',b.left,min(b.bottom,y),b.right,max(b.top,y))
        via(x,y)
        box('Metal2',x-.2,y-.2,54,y+.2)
        routes.append(dict(kind='diffusion',index=i,net=net,x_um=x,bus_y_um=y,connection_present=not omit))
    for i,p in enumerate(gates):
        b=p.bbox().to_dtype(layout.dbu).transformed(t)
        assert abs(b.width()-.45)<1e-9 and abs(b.height()-1)<1e-9
        x=round(b.center().x/.005)*.005;y=35
        box('GatPoly',b.left,b.top-.1,b.right,y+.3)
        box('GatPoly',x-.3,y-.3,x+.3,y+.3)
        omit=fault=='gate_open' and i==9
        if not omit:box('Cont',x-.08,y-.08,x+.08,y+.08)
        box('Metal1',x-.25,y-.25,x+.25,y+.25)
        box('Metal1',x-.25,y-.15,40,y+.15)
        routes.append(dict(kind='gate',index=i,net='gate',x_um=x,bus_y_um=y,connection_present=not omit))
    via(40,35);box('Metal2',39.8,34.8,54,35.2)
    tap=pc('ptap1',dict(w='2u',l='2u'));tt=place(tap,45,20)
    pins=[s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(layers['Metal1'],2))]
    assert len(pins)==1
    center=pins[0].center();via(center.x,center.y)
    box('Metal2',center.x-.2,center.y-.2,54,center.y+.2)
    positions={'drain':33,'source':27,'gate':35,'sub':center.y}
    for n,y in positions.items():
        top.shapes(layout.layer(layers['Metal2'],2)).insert(pya.DBox(52,y-.2,54,y+.2))
        top.shapes(layout.layer(layers['Metal2'],25)).insert(pya.DText(n,53,y))
    if fault=='short':box('Metal2',52.5,27,53.5,33)
    if fault=='offgrid':
        shapes=[s for s in top.each_shape(layout.layer(layers['Metal2'],0)) if s.is_box()];assert shapes
        shapes[0].transform(pya.Trans(1,0))
    directory=OUT/fault;directory.mkdir()
    layout.write(str(directory/'layout.gds'))
    aggregate=['* Original physical HV device plus explicit finite substrate contact', '.subckt '+TOP+' '+' '.join(PORTS),
        'MCORE drain gate source BULK sg13_hv_nmos w=10u l=.45u ng=10 m=1',
        'RTAP sub BULK ptap1 A=4p P=8u','.ends '+TOP,'']
    (directory/'aggregate.cir').write_text('\n'.join(aggregate))
    fingers=['* Uncombined geometry comparison only; never a replacement simulation model','.subckt '+TOP+' '+' '.join(PORTS)]
    fingers += [f'MF{i} drain gate source BULK sg13_hv_nmos w=1u l=.45u ng=1 m=1' for i in range(10)]
    fingers += ['RTAP sub BULK ptap1 A=4p P=8u','.ends '+TOP,'']
    (directory/'fingers.cir').write_text('\n'.join(fingers))
    result=dict(status='GENERATED_UNVERIFIED_NG10_ROUTING',fault=fault,source_geometry=dict(width_um=10,length_um=.45,ng=10),
        routes=routes,placements=placements,ports=positions,bbox_um=str(top.dbbox()),raw_finger_reference_is_not_simulation_substitute=True,
        original_aggregate_reference_preserved=True,finite_contact_to_bulk_added=True,substrate_spreading_qualified=False,
        driver_complete=False,serial_phy_complete=False)
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',choices=['base','gate_open','drain_open','short','offgrid']);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate(args.generate);return
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],steps={},accepted=False,full_driver_complete=False,serial_phy_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        protected={str(Path(__file__).resolve()):sha(Path(__file__).resolve())}
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'fixture.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        from prepare_ihp_drc import validate_lock,verify
        from check_ihp_drc import record_result
        for typ in ('drc','lvs'):
            lock=json.loads((ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json').read_text());validate_lock(lock)
            assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
            for row in lock['files']:
                p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);protected[str(p)]=row['sha256']
        for name in ('base','gate_open','drain_open','short','offgrid'):
            execution=execute([app,'python',Path(__file__).resolve(),'--generate',name],OUT,'generate-'+name)
            r['steps']['generate-'+name]=execution;save();assert execution['returncode']==0
        r['geometry']=json.loads((OUT/'base/result.json').read_text())
        assert len([q for q in r['geometry']['routes'] if q['kind']=='gate' and q['connection_present']])==10
        assert len([q for q in r['geometry']['routes'] if q['kind']=='diffusion' and q['connection_present']])==11
        (OUT/'base/wrong_width.cir').write_text((OUT/'base/aggregate.cir').read_text().replace('w=10u l=.45u','w=9u l=.45u'))
        jobs=[('raw_lvs','base','fingers.cir','deep',False),('aggregate_lvs','base','aggregate.cir','deep',True),
            ('flat_aggregate_lvs','base','aggregate.cir','flat',True),('wrong_width','base','wrong_width.cir','deep',True),
            ('gate_open','gate_open','aggregate.cir','deep',True),('drain_open','drain_open','aggregate.cir','deep',True),
            ('short','short','aggregate.cir','deep',True),('drc','base',None,'deep',False),('offgrid','offgrid',None,'deep',False)]
        verdicts=[]
        for name,geometry,reference,mode,combine in jobs:
            d=OUT/('check-'+name);d.mkdir();gds=OUT/geometry/'layout.gds';drc=reference is None;typ='drc' if drc else 'lvs'
            entry=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc' if drc else 'lvs/sg13g2.lvs')
            options=['input='+str(gds),'topcell='+TOP,'log='+str(d/'deck.log'),'run_mode='+mode]
            options+=['report='+str(d/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False'] if drc else [
                'schematic='+str(OUT/geometry/reference),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),
                'thr=2','no_simplify=true','top_lvl_pins=true','combine_devices='+str(combine).lower()]
            command=[app,'klayout','-b','-zz','-r',entry]
            for option in options:command+=['-rd',option]
            step=dict(execution=execute(command,d,'run'),combine_devices=combine,no_simplify=True);r['steps'][name]=step;save()
            assert step['execution']['returncode']==0
            positive=name in ('raw_lvs','aggregate_lvs','flat_aggregate_lvs','drc')
            if drc:
                step['measurement']=record_result(d,TOP,0,{Path(k):v for k,v in protected.items()})
                verdict=step['measurement']['status'];ok=verdict==('PASS' if positive else 'FAIL') and step['measurement']['category_count']==560
                if not positive:ok=ok and any('metal2_drw_Offgrid' in c for c in step['measurement']['categories'])
            else:
                step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',TOP,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
                audit=json.loads((d/'audit.json').read_text());step['audit']=audit;step['extracted_netlist']=(d/'extracted.cir').read_text();verdict=audit['status']
                ok=verdict==('PASS within comparison scope' if positive else 'FAIL') and step['audit_execution']['returncode']==(0 if positive else 1)
                if positive:
                    census=11 if name=='raw_lvs' else 2
                    tops=[c for c in audit['circuits'] if c['layout']==TOP]
                    ok=ok and len(tops)==1 and all(tops[0][k]==census for k in ('layout_devices_recursive','schematic_devices_recursive')) and not audit['extraction_diagnostics']
                else:ok=ok and 'Deck explicitly reported a mismatch' in audit['reasons']
            step['expected_verdict_observed']=bool(ok);verdicts.append(bool(ok));save();print(name,verdict,'expected',ok,flush=True)
        assert all(sha(Path(p))==v for p,v in protected.items())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        r['status']='PASS_NATIVE_NG10_ROUTING_DRC_RAW_AND_AGGREGATE_LVS_AND_FAULTS_NOT_FULL_DRIVER' if all(verdicts) else 'FAIL_NATIVE_PHYSICAL_GATES'
        save();assert all(verdicts),'Native physical gate failure; all completed comparisons retained'
    except BaseException as e:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(e);raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
