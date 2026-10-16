#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Shorten unneeded public-pin wire extensions after measured driver RC failure.

Common substrate, explicit finite contacts and original CMOS cell are modeled
in the physical reference. This is not electrical or PHY acceptance.
"""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from decimal import Decimal
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-input-driver-localpins'
TOP='nssoc_tx_input_driver_v7_physical_localpins_v1'
PORTS=['din','dout','avdd','dvdd','avss','sub']
DRIVER_SHA='de22ecc19975aab5b35cf441f0c4b0ee289ae2dae9f1727625b22e2ae595f135'
SOURCES=[dict(run=38866034515,group='tx-hv-fingers',bytes=152865,sha='3dd698fa73de68204da704c9148c6861cdfb3f5e2eeb2299aabc4dfcad530c7f',summary='c7b896892fa001eb427769ce08e449a874bc0e6bbf3de0de7d1c4692be878c49',root='cloud-tx-hv-fingers'),
 dict(run=38863174519,group='tx-driver-geometry',bytes=140672,sha='377fbedfa70ad5101f35ce095a7a19597ad909eee5a645dc7b2f45e758f84374',summary='9b83b5376a1c2768e2fc2c1aeefbcde12378757cbcd46c11ec198e20fa46cee2',root='cloud-tx-driver-geometry')]

def restore(spec):
    stem=f"{spec['group']}-{spec['run']}-1"
    packed=OUT/(stem+'.tar.gz')
    fetch(f"https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{spec['run']}-1-{spec['group']}/{stem}.tar.gz.part0000",spec['sha'],packed)
    assert packed.stat().st_size==spec['bytes'];dest=OUT/'inputs'/spec['group'];dest.mkdir(parents=True)
    with tarfile.open(packed) as tar:
        members=tar.getmembers();assert len(members)==len({m.name for m in members})
        for m in members:
            p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]==spec['root'] and (m.isfile() or m.isdir())
        tar.extractall(dest,filter='data')
    packed.unlink();root=dest/spec['root'];assert sha(root/'result.json')==spec['summary']
    r=json.loads((root/'result.json').read_text());assert all(sha(root/p)==v for p,v in r['outputs'].items())
    return root,r

def generate(fault):
    import xml.etree.ElementTree as ET
    pdk=ROOT/'pdk/libs.tech/klayout/python';sys.dont_write_bytecode=True
    sys.path[:0]=[str(pdk),str(pdk/'pycell4klayout-api/source/python'),str(ROOT/'hw/soc/flow')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    import make_pcie_pump_filter13_v1 as parser
    hvroot=OUT/'inputs/tx-hv-fingers/cloud-tx-hv-fingers'
    stdroot=OUT/'inputs/tx-driver-geometry/cloud-tx-driver-geometry'
    assert sha(hvroot/'base/layout.gds')=='d84cfd74705b832370fb91ca9e6c00096316a7c0a0b430a350662883af8738bb'
    driver=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc';assert sha(driver)==DRIVER_SHA
    texts={'driver':driver.read_text(),'buffer':(stdroot/'native/buf16.spice').read_text()}
    parser.MODELS.update(sg13_lv_nmos=4,sg13_lv_pmos=4)
    rows,wires=parser.expand(parser.definitions(texts),['nssoc_tx_cmos_hv_resistive_input_v7','xdriver',PORTS])
    assert not wires and len(rows)==12
    for row in rows:row['nets']=[n.removeprefix('xdriver.') for n in row['nets']]
    hv=[r for r in rows if r['model']=='sg13_hv_nmos'];lv=[r for r in rows if r['model'].startswith('sg13_lv_')];res=[r for r in rows if r['model']=='rppd']
    assert len(hv)==len(lv)==len(res)==4
    assert all(r['params']==dict(w='10u',l='.45u',ng='10') and r['nets']==['sink','drv','avss','sub'] for r in hv)
    layout=pya.Layout();layout.read(str(stdroot/'upstream/gds/sg13g2_stdcell.gds'));layout.read(str(hvroot/'base/layout.gds'))
    hvcell=layout.cell('nssoc_tx_hv_ng10_v1');buf=layout.cell('sg13g2_buf_16');assert hvcell is not None and buf is not None
    # Remove only imported port text, preserving pin shapes, every drawing layer and device-recognition label.
    layers={p.findtext('name')[:-8]:int(p.findtext('source').split('/')[0]) for p in ET.parse(pdk.parent/'tech/sg13g2.lyp').getroot().iter('properties') if p.findtext('name','').endswith('.drawing')}
    def drawing_digest(cell):
        result={}
        for index in layout.layer_indexes():
            info=layout.get_info(index)
            if info.datatype==25 or (cell.name==buf.name and info.layer==layers['Substrate']):continue
            region=pya.Region(cell.begin_shapes_rec(index)).merged()
            if not region.is_empty():result[str(info)]=[str(p) for p in region.each()]
        return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    before={c.name:drawing_digest(c) for c in (hvcell,buf)}
    for cell in layout.each_cell():
        for index in layout.layer_indexes():
            if layout.get_info(index).datatype==25:cell.shapes(index).clear()
    assert before=={c.name:drawing_digest(c) for c in (hvcell,buf)}
    top=layout.create_cell(TOP)
    placements=[];connections={};routes=[];taprefs=[]
    def pc(name,params):
        c=layout.create_cell(name,'SG13_dev',params);assert c is not None and not c.is_empty();return c
    def place(cell,x,y):
        t=pya.DTrans(float(x),float(y));b=pya.DBox(0.,0.,1.,2.).transformed(t)
        assert [b.left,b.bottom,b.right,b.top]==[float(x),float(y),float(x)+1.,float(y)+2.]
        top.insert(pya.DCellInstArray(cell.cell_index(),t));placements.append(dict(cell=cell.name,x_um=x,y_um=y,native_transform=str(t)));return t
    def box(layer,x1,y1,x2,y2):
        b=pya.DBox(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2));top.shapes(layout.layer(layers[layer],0)).insert(b);return b
    def via(lo,hi,x,y):
        assert 1<=lo<hi<=5
        if lo==1 and hi>2:
            via(1,2,x,y);via(2,hi,x,y);return
        # Keep dense native Metal1 cell-pin accesses unchanged. Higher layer
        # transitions receive actual2x2 cuts and the native PCell enclosures.
        count=1 if lo==1 else 2
        c=pc('via_stack',dict(b_layer='Metal'+str(lo),t_layer='Metal'+str(hi),vn_columns=count,vn_rows=count,vt1_columns=count,vt1_rows=count,vt2_columns=count,vt2_rows=count))
        q=c.dbbox().center();place(c,x-q.x,y-q.y)
    def escape(net,x,y,lane,lo=2,omit=False):
        via(lo,3,x,y)
        if not omit:box('Metal3',x-.6,y-.6,lane+.6,y+.6)
        via(3,4,lane,y);connections.setdefault(net,[]).append((lane,y))
        routes.append(dict(net=net,source_um=[x,y],lane_um=lane,connection_present=not omit))
    for i in range(4):
        dx=24*i;place(hvcell,dx,0)
        for port,net,y,lane in [('sub','sub',21,60),('source','avss',27,64),('drain','sink',33,68),('gate','drv',35,72)]:
            escape(net,dx+53,y,dx+lane,omit=fault=='hv_gate_open' and i==3 and port=='gate')
        taprefs.append(f'RHV_TAP{i} sub BULK ptap1 A=4p P=8u')
    bt=place(buf,144,30)
    # Derive the two intrinsic ties from original material geometry before LVS.
    # These are not inferred from an extracted netlist or tuned to a verdict.
    def native_region(layer):return pya.Region(buf.begin_shapes_rec(layout.layer(layers[layer],0))).merged()
    activ=native_region('Activ');psd=native_region('pSD');well=native_region('NWell');poly=native_region('GatPoly')
    ties={'ntap1':((activ&well)-psd-poly).merged(),'ptap1':((activ&psd)-well-poly).merged()}
    intrinsic_ties={}
    for model,region in ties.items():
        polygons=list(region.each());assert len(polygons)==1
        polygon=polygons[0];area=polygon.area()*layout.dbu**2;perimeter=polygon.perimeter()*layout.dbu
        assert area>0 and perimeter>0
        intrinsic_ties[model]=dict(area_um2=area,perimeter_um=perimeter,polygon_dbu=str(polygon),
            derivation='Activ intersect NWell minus pSD and GatPoly' if model=='ntap1' else 'Activ intersect pSD minus NWell and GatPoly')
        tie='dvdd' if model=='ntap1' else 'avss';bulk='NWELL' if model=='ntap1' else 'BULK'
        taprefs.append(f'RBUF_EMBEDDED_{model} {tie} {bulk} {model} A={area:.12g}p P={perimeter:.12g}u')
        if model=='ptap1' and fault!='missing_body_marker':
            # Use the same native Substrate/sub! recognition convention as ptap1.
            # No implant, active, contact, gate or metal geometry is changed.
            # The locked native deck extracts taps cell-locally in deep mode.
            # Keep the recognition marker in the same cell as its actual tie.
            marker=polygon.bbox().to_dtype(layout.dbu)
            assert pya.Region(buf.begin_shapes_rec(layout.layer(layers['Substrate'],0))).is_empty()
            buf.shapes(layout.layer(layers['Substrate'],0)).insert(marker)
            q=marker.center()
            buf.shapes(layout.layer(layers['TEXT'],0)).insert(pya.DText('sub!',q.x,q.y))
            buf.shapes(layout.layer(layers['Substrate'],0)).insert(pya.DText('sub!',q.x,q.y))
    # Chosen access points are inside the original pinned LEF conductor rectangles.
    pins=[('drv',146.,31.68,38.,164),('gate',154.85,31.68,40.,168),('dvdd',144.4,33.78,42.,172),('avss',150.,30.,44.,176)]
    for net,x,y,escape_y,lane in pins:
        native_metal=pya.Region(buf.begin_shapes_rec(layout.layer(layers['Metal1'],0))).transformed(bt.to_itype(layout.dbu))
        access=pya.Region(pya.DBox(x-.13,y-.13,x+.13,y+.13).to_itype(layout.dbu))
        assert (access-native_metal).is_empty(),('Buffer pin is outside native conductor',net)
        via(1,2,x,y);box('Metal2',x-.2,y-.2,x+.2,escape_y+.2);escape(net,x,escape_y,lane)
    nwell=pya.Region(buf.begin_shapes_rec(layout.layer(layers['NWell'],0))).bbox().to_dtype(layout.dbu).transformed(bt)
    if fault!='missing_well_tap':
        nt=pc('ntap1',dict(w='2u',l='2u'));ntt=place(nt,158,32);nb=nt.dbbox().transformed(ntt)
        box('NWell',min(nwell.left,nb.left),min(nwell.bottom,nb.bottom),max(nwell.right,nb.right),max(nwell.top,nb.top))
        pinboxes=[s.dbbox().transformed(ntt) for s in nt.each_shape(layout.layer(layers['Metal1'],2))];assert len(pinboxes)==2
        q=min(pinboxes,key=lambda b:b.area()).center();via(1,2,q.x,q.y);box('Metal2',q.x-.2,q.y-.2,q.x+.2,46.2);escape('dvdd',q.x,46,180)
    taprefs.append('RBUF_NTAP dvdd NWELL ntap1 A=4p P=8u')
    def ptap(name,x,y,lane):
        c=pc('ptap1',dict(w='2u',l='2u'));t=place(c,x,y)
        ps=[s.dbbox().transformed(t) for s in c.each_shape(layout.layer(layers['Metal1'],2))];assert len(ps)==1
        q=ps[0].center();escape('sub',q.x,q.y,lane,lo=1);taprefs.append(name+' sub BULK ptap1 A=4p P=8u')
    ptap('RBUF_PTAP',158,24,184)
    for i,row in enumerate(res):
        x=196+28*i;c=pc('rppd',{k:row['params'][k] for k in ('w','l')});t=place(c,x,30)
        ps=sorted([s.dbbox().transformed(t) for s in c.each_shape(layout.layer(layers['Metal1'],2))],key=lambda b:b.center().y);assert len(ps)==2
        for k,pin in enumerate(ps):
            q=pin.center();escape(row['nets'][k],q.x,q.y,x+17+4*k,lo=1,omit=fault=='input_open' and i==0 and k==0)
        ptap('RRES_PTAP'+str(i),x+10,20,x+25)
    netorder=['drv','gate','sink','din','dout','dvdd','avdd','avss','sub'];assert set(connections)==set(netorder)
    port_boxes={};ys={};rail_spans={}
    for i,net in enumerate(netorder):
        y=60+7*i;ys[net]=y;half=3 if net in ('dvdd','avdd','avss','sub') else 1.2
        points=connections[net]
        for x,sy in points:
            box('Metal4',x-1.,sy-.6,x+1.,y+.6);via(4,5,x,y)
        # Public pins terminate near the first actual conductor access. The old
        # x=0 rule added long unloaded extensions, including the sole avdd/din
        # connections. Keep every actual terminal connection and native device.
        left=min(x for x,sy in points)-(3 if net in PORTS else 1)
        right=max(x for x,sy in points)+(3 if net in PORTS else 1)
        assert right-left>=4 if net in PORTS else right>left
        rail_spans[net]=[left,right]
        box('Metal5',left,y-half,right,y+half)
        if net in PORTS:
            b=pya.DBox(left,y-half,left+4,y+half);top.shapes(layout.layer(layers['Metal5'],2)).insert(b)
            top.shapes(layout.layer(layers['Metal5'],25)).insert(pya.DText(net,left+2,float(y)));port_boxes[net]=str(b)
    if fault=='body_short':
        left=max(rail_spans['avss'][0],rail_spans['sub'][0]);right=min(rail_spans['avss'][1],rail_spans['sub'][1])
        assert right-left>2
        box('Metal5',left+.5,ys['avss'],left+1.5,ys['sub'])
    if fault=='offgrid':
        s=next(s for s in top.each_shape(layout.layer(layers['Metal3'],0)) if s.is_box());s.transform(pya.Trans(1,0))
    assert set(port_boxes)==set(PORTS) and len(taprefs)==12
    assert before=={c.name:drawing_digest(c) for c in (hvcell,buf)}
    d=OUT/fault;d.mkdir();layout.write(str(d/'layout.gds'))
    mapping=[];aggregate=['* Physical common substrate and explicit finite contacts','.subckt '+TOP+' '+' '.join(PORTS)]
    raw=aggregate.copy();mos_fingers=0
    for i,row in enumerate(rows):
        n=row['nets'];p=row['params'];model=row['model']
        if model=='rppd':
            line=f'RCORE{i} '+ ' '.join(n[:2]+['BULK'])+f" rppd w={p['w']} l={p['l']} b=0 m=1";aggregate.append(line);raw.append(line)
            mapping.append(dict(path=row['path'],original_body=n[2],physical_body='BULK'));continue
        body='NWELL' if model.endswith('pmos') else 'BULK'
        mapping.append(dict(path=row['path'],original_body=n[3],physical_body=body))
        params=dict(p);params.setdefault('m','1');assert params['m']=='1';ng=int(params['ng'])
        aggregate.append(f'MCORE{i} '+' '.join(n[:3]+[body])+' '+model+' '+' '.join(k+'='+v for k,v in params.items()))
        assert p['w'].endswith('u');width=Decimal(p['w'][:-1])/ng
        for f in range(ng):raw.append(f'MCORE{i}F{f} '+' '.join(n[:3]+[body])+f' {model} w={width}u l='+p['l']+' ng=1 m=1')
        mos_fingers+=ng
    assert mos_fingers==84
    for text,name in [(aggregate,'aggregate.cir'),(raw,'raw.cir')]:
        text+=taprefs+['.ends '+TOP,''];(d/name).write_text('\n'.join(text))
    result=dict(status='GENERATED_UNVERIFIED_FULL_DRIVER',routing_profile='compact_placement_local_public_pins',routing_width_um=dict(Metal3=1.2,Metal4=2.0,Metal5_signal=2.4,Metal5_power=6.0),upper_vias=dict(columns=2,rows=2),placement_pitch_um=dict(hv=24,resistor=28,spine=7),spine_start_y_um=60,public_pin_policy='near_first_actual_contact_without_x0_extension',rail_spans_um=rail_spans,external_chip_connections_not_yet_routed=True,metal1_access_changed=False,fault=fault,original_source_sha256=DRIVER_SHA,original_core_rows=rows,
        core_devices=12,raw_mos_fingers=84,finite_taps=12,explicit_added_taps=10,intrinsic_buf_ties=intrinsic_ties,raw_reference_devices=100,aggregate_reference_devices_before_combination=24,
        substrate_mapping=mapping,common_substrate_model_qualified=False,original_junction_parameters_retained_in_aggregate_reference=True,
        raw_reference_not_simulation_substitute=True,imported_material_and_pin_geometry_unchanged=before,buffer_substrate_annotation='cell-local Substrate rectangle and sub! labels, absent only in missing_body_marker fault',placements=placements,routes=routes,ports=port_boxes,
        full_driver_accepted=False,qualified_pex=False,serial_phy_complete=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',choices=['base','hv_gate_open','input_open','missing_well_tap','missing_body_marker','body_short','offgrid']);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate(args.generate);return
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],routing_profile='compact_placement_local_public_pins',failed_parent_run=38892907391,wire_metrics_run=38892907583,rejected_wider_supply_run=38901377382,steps={},accepted=False,serial_phy_complete=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        protected={str(Path(__file__).resolve()):sha(Path(__file__).resolve()),str(ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'):DRIVER_SHA}
        for spec in SOURCES:
            root,prior=restore(spec)
            assert prior['status'].startswith('PASS_NATIVE_')
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        from prepare_ihp_drc import validate_lock,verify
        from check_ihp_drc import record_result
        for typ in ('drc','lvs'):
            lock=json.loads((ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json').read_text());validate_lock(lock);assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
            for row in lock['files']:
                p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);protected[str(p)]=row['sha256']
        for name in ('base','hv_gate_open','input_open','missing_well_tap','missing_body_marker','body_short','offgrid'):
            x=execute([app,'python',Path(__file__).resolve(),'--generate',name],OUT,'generate-'+name);r['steps']['generate-'+name]=x;save()
            if x['returncode']:
                print((OUT/('generate-'+name+'.log')).read_text(errors='replace')[-12000:]);raise RuntimeError('Native assembly failed: '+name)
        r['geometry']=json.loads((OUT/'base/result.json').read_text())
        text=(OUT/'base/aggregate.cir').read_text();assert text.count('w=10u l=.45u ng=10 m=1')==4
        (OUT/'base/wrong_width.cir').write_text(text.replace('w=10u l=.45u ng=10 m=1','w=9u l=.45u ng=10 m=1',1))
        jobs=[('raw_lvs','base','raw.cir','deep',False),('raw_flat_lvs','base','raw.cir','flat',False),
            ('aggregate_lvs','base','aggregate.cir','deep',True),('aggregate_flat_lvs','base','aggregate.cir','flat',True),
            ('wrong_width','base','wrong_width.cir','deep',True),('hv_gate_open','hv_gate_open','aggregate.cir','deep',True),
            ('input_open','input_open','aggregate.cir','deep',True),('missing_well_tap','missing_well_tap','aggregate.cir','deep',True),
            ('missing_body_marker','missing_body_marker','aggregate.cir','deep',True),('body_short','body_short','aggregate.cir','deep',True),('drc','base',None,'deep',False),('offgrid','offgrid',None,'deep',False)]
        verdicts=[]
        for name,geometry,reference,mode,combine in jobs:
            d=OUT/('check-'+name);d.mkdir();drc=reference is None;typ='drc' if drc else 'lvs'
            entry=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc' if drc else 'lvs/sg13g2.lvs')
            options=['input='+str(OUT/geometry/'layout.gds'),'topcell='+TOP,'log='+str(d/'deck.log'),'run_mode='+mode]
            options+=['report='+str(d/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False'] if drc else ['schematic='+str(OUT/geometry/reference),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),'thr=2','no_simplify=true','top_lvl_pins=true','combine_devices='+str(combine).lower()]
            command=[app,'klayout','-b','-zz','-r',entry]
            for option in options:command+=['-rd',option]
            step=dict(execution=execute(command,d,'run'),combine_devices=combine,no_simplify=True);r['steps'][name]=step;save();assert step['execution']['returncode']==0
            positive=name in ('raw_lvs','raw_flat_lvs','aggregate_lvs','aggregate_flat_lvs','drc')
            if drc:
                step['measurement']=record_result(d,TOP,0,{Path(k):v for k,v in protected.items()});verdict=step['measurement']['status']
                ok=verdict==('PASS' if positive else 'FAIL') and step['measurement']['category_count']==560
                if not positive:ok=ok and any('metal3_drw_Offgrid' in c for c in step['measurement']['categories'])
                import xml.etree.ElementTree as ET
                step['marker_items']=[ET.tostring(i,encoding='unicode') for i in ET.parse(d/'drc.lyrdb').getroot().findall('.//items/item')]
            else:
                step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',TOP,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
                audit=json.loads((d/'audit.json').read_text());step['audit']=audit;step['extracted_netlist']=(d/'extracted.cir').read_text();verdict=audit['status']
                ok=verdict==('PASS within comparison scope' if positive else 'FAIL') and step['audit_execution']['returncode']==(0 if positive else 1)
                if positive:
                    tops=[c for c in audit['circuits'] if c['layout']==TOP];ok=ok and len(tops)==1 and not audit['extraction_diagnostics']
                    if not combine:ok=ok and all(tops[0][k]==100 for k in ('layout_devices_recursive','schematic_devices_recursive'))
                else:ok=ok and 'Deck explicitly reported a mismatch' in audit['reasons']
            step['expected_verdict_observed']=bool(ok);verdicts.append(bool(ok));save();print(name,verdict,'expected',ok,flush=True)
        assert all(sha(Path(p))==v for p,v in protected.items()) and all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        r['status']='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE' if all(verdicts) else 'FAIL_FULL_DRIVER_NATIVE_PHYSICAL_GATES'
        save();assert all(verdicts),'Native full-driver failures preserved'
    except BaseException as e:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(e);raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
