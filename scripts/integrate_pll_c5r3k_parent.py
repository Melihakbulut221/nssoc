#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Integrate the c5r3k child macros into the verified RHI120/C8 PLL845 parent.

Starting point: the passing RHI120/C8 parent GDS and reference (run 39914855175).
Declared changes, and nothing else:
  - pump instance -> nssoc_pump_filter13_c5r3k_v1 (one card: XPSOURCE W8)
  - vco instance  -> nssoc_clock_vco_hbt_v6_c5r3k_v1_layout (six ring loads L4.93)
  - div1 instance only -> nssoc_clock_div4_load3p2_c5r3k_v1_layout (XSP/XSN W16);
    div2 keeps nssoc_clock_div4_load3p2_v2_layout
  - new integrator instance nssoc_pll_vctrl_integrator_c5r3k_v1 at INT_ORIGIN
    with three parent routes (avss, sub, vctrl) built from the parent's own
    via cells and the same stub/pad/strip pattern as the pump port routes.
Every swapped instance keeps its transform, bbox and port boxes; every other
cell and every existing parent shape is unchanged. New parent shapes are
checked against the actual parent geometry before insertion. Never PHY
acceptance.
"""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-c5r3k-parent'
OLDTOP='nssoc_pll845_divider3p2_rhi120_c8_development'
TOP='nssoc_pll849_divider3p2_c5r3k_development'
DEVICES=849
INT='nssoc_pll_vctrl_integrator_c5r3k_v1'
# name -> (old cell, new cell, child key, instance position or None if unique)
SWAPS={'pump':('nssoc_pump_filter13_rhi120_c8_v1','nssoc_pump_filter13_c5r3k_v1','pump',None),
       'vco':('nssoc_clock_vco_hbt_v6_local_v1_layout','nssoc_clock_vco_hbt_v6_c5r3k_v1_layout','vco',None),
       'div1':('nssoc_clock_div4_load3p2_v2_layout','nssoc_clock_div4_load3p2_c5r3k_v1_layout','div1',(1100.0,100.0))}
# Exact expected reference card deltas (old card, new card), lower case.
CARD_DELTAS={
 'pump':[('md4 xloop.xdet.xcp.source xloop.xdet.xcp.pb div_avdd nwell4 sg13_hv_pmos w=6.4u l=2u ng=1 m=1',
          'md4 xloop.xdet.xcp.source xloop.xdet.xcp.pb div_avdd nwell4 sg13_hv_pmos w=8u l=2u ng=1 m=1')],
 'vco':[(f'r{n} avdd {n[1:]} bulk rppd w=8u l=4.4u b=0 m=1',f'r{n} avdd {n[1:]} bulk rppd w=8u l=4.93u b=0 m=1')
        for n in ('rp0','rn0','rp1','rn1','rp2','rn2')],
 'div1':[('rdiv__xfirst__xsp clkp div__xfirst__ckp bulk rppd w=4u l=3.6u b=0 m=1','rdiv__xfirst__xsp clkp div__xfirst__ckp bulk rppd w=16u l=3.6u b=0 m=1'),
         ('rdiv__xfirst__xsn clkn div__xfirst__ckn bulk rppd w=4u l=3.6u b=0 m=1','rdiv__xfirst__xsn clkn div__xfirst__ckn bulk rppd w=16u l=3.6u b=0 m=1')]}
# Integrator placement inside the free area (1022,1495)-(2162,1760) um. Checked
# against the actual parent: between the fb TopMetal1 bus (y<=1490.82) and the
# vctrl TopMetal1 bus (y>=1764.18), right of the avss TopMetal2 strap (x<=1020).
INT_ORIGIN=(1100.0,1550.0)
INT_PORTS={'avss':100.03,'sub':106.03,'vctrl':112.03}   # child port centre y (x=0..2, Metal5)
# Supply ports: lane on the existing TopMetal2 strap of the same net.
SUPPLY_LANES={'avss':980.0,'sub':828.0}
# Signal port: new 2 um TopMetal2 riser joining the existing vctrl TopMetal1 bus.
VCTRL_LANE=1040.0;VCTRL_BUS_Y=1765.0;VCTRL_RISER_TOP=1766.0
SPACE={67:0.5,126:2.0,134:2.0}   # >= native Metal5/TopMetal1/TopMetal2 spacing
VIA_CELLS={'via_stack$2':{(67,0):2,(126,0):1,(125,0):4},'via_stack':{(67,0):2,(126,0):1,(125,0):1},
           'via_stack$1':{(126,0):2,(134,0):1,(133,0):1},'via_stack$3':{(126,0):2,(134,0):1,(133,0):8}}

def route_plan():
    """Boxes (net, layer, x1,y1,x2,y2) and vias (net, cell, x, y) in parent um."""
    X0,Y0=INT_ORIGIN;boxes,vias=[],[]
    for net,lane in SUPPLY_LANES.items():
        y=round(Y0+INT_PORTS[net],3)
        boxes+=[(net,67,X0-5.75,y-.75,X0+1.75,y+.75),(net,126,X0-6.89,y-.82,X0-3.11,y+.82),
                (net,126,lane-2,y-2,X0-3,y+2),(net,126,lane-1.89,y-.82,lane+1.89,y+.82)]
        vias+=[(net,'via_stack$2',X0-5,y),(net,'via_stack$3',lane,y)]
    y=round(Y0+INT_PORTS['vctrl'],3)
    boxes+=[('vctrl',67,X0-5.3,y-.3,X0+1.3,y+.3),('vctrl',126,VCTRL_LANE-.82,y-.82,X0-4.18,y+.82),
            ('vctrl',134,VCTRL_LANE-1,y-1,VCTRL_LANE+1,VCTRL_RISER_TOP)]
    vias+=[('vctrl','via_stack',X0-5,y),('vctrl','via_stack$1',VCTRL_LANE,y),('vctrl','via_stack$1',VCTRL_LANE,VCTRL_BUS_Y)]
    targets={'avss':(134,SUPPLY_LANES['avss'],round(Y0+INT_PORTS['avss'],3)),
             'sub':(134,SUPPLY_LANES['sub'],round(Y0+INT_PORTS['sub'],3)),
             'vctrl':(126,VCTRL_LANE,VCTRL_BUS_Y)}
    return boxes,vias,targets

def generate():
    import pya
    A=OUT/'integrated';A.mkdir();P=OUT/'parent/integrated'
    old=json.loads((P/'result.json').read_text());assert old['top']==OLDTOP and len(old['ports'])==17
    children={k:json.loads((OUT/'children'/k/'layout/result.json').read_text()) for k in ('pump','vco','div1','integrator')}
    L=pya.Layout();L.read(str(P/(OLDTOP+'.gds')));T=L.cell(OLDTOP);assert T is not None and L.dbu==.001
    def shapes(c):return sorted((str(L.get_info(i)),str(s)) for i in L.layer_indices() for s in c.each_shape(i))
    def instances(c):return sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in c.each_inst())
    original={c.name:(shapes(c),instances(c)) for c in L.each_cell()}
    def child_ports(key):
        p=children[key]['ports'];out={}
        for pin,v in p.items():
            coords=v['rect_um'] if isinstance(v,dict) else list(map(float,re.findall(r'-?\d+(?:\.\d+)?',v)))
            assert len(coords)==4;out[pin]=coords
        return out
    # Load every child under a unique namespace; never overwrite existing cells.
    loaded={}
    for key,top,prefix in [('pump',SWAPS['pump'][1],'c5r3k_pump_'),('vco',SWAPS['vco'][1],'c5r3k_vco_'),
                           ('div1',SWAPS['div1'][1],'c5r3k_div1_'),('integrator',INT,'c5r3k_int_')]:
        G=pya.Layout();G.read(str(OUT/'children'/key/'layout'/(top+'.gds')));assert G.cell(top) is not None and G.dbu==.001
        for c in G.each_cell():
            if c.name!=top:c.name=prefix+c.name
        assert all(L.cell(c.name) is None for c in G.each_cell()),key
        G.write(str(A/('unique-'+key+'.gds')));L.read(str(A/('unique-'+key+'.gds')));N=L.cell(top)
        for li in G.layer_indices():
            assert (pya.Region(G.cell(top).begin_shapes_rec(li))^pya.Region(N.begin_shapes_rec(L.layer(G.get_info(li))))).is_empty(),key
        loaded[key]=N
    for name,(ss,ii) in original.items():assert shapes(L.cell(name))==ss and instances(L.cell(name))==ii,name
    proof={}
    for name,(oldcell,newcell,key,position) in SWAPS.items():
        meta=next(x for x in old['instances'] if x['name']==name);assert meta['top']==oldcell
        matches=[i for i in T.each_inst() if i.cell.name==oldcell]
        if position is not None:matches=[i for i in matches if [i.dcplx_trans.disp.x,i.dcplx_trans.disp.y]==list(position)]
        assert len(matches)==1,name;I=matches[0];assert [I.dcplx_trans.disp.x,I.dcplx_trans.disp.y]==meta['position_um']
        cp=child_ports(key);assert set(cp)==set(meta['ports'])
        for pin,coords in cp.items():
            actual=pya.DBox(*coords).transformed(I.dcplx_trans);ref=meta['ports'][pin]['box_um']
            assert meta['ports'][pin]['layer']==67
            assert [round(v*1000) for v in (actual.left,actual.bottom,actual.right,actual.top)]==[round(v*1000) for v in ref],('Moved macro port',name,pin)
        bounds,transform=str(I.dbbox()),str(I.dcplx_trans)
        I.cell_index=loaded[key].cell_index();assert str(I.dcplx_trans)==transform and str(I.dbbox())==bounds,name
        meta['top']=newcell;proof[name]=dict(old=oldcell,new=newcell,transform=transform,bbox_um=bounds,ports_unchanged=True)
    # Geometry check of the integrator footprint and every new parent shape
    # against the ACTUAL parent before insertion.
    def flat(layer,dt=0):
        idx=L.find_layer(layer,dt)
        return pya.Region() if idx is None else pya.Region(T.begin_shapes_rec(idx)).merged()
    def dbox(x1,y1,x2,y2):return pya.DBox(x1,y1,x2,y2).to_itype(L.dbu)
    N=loaded['integrator'];X0,Y0=INT_ORIGIN
    footprint=pya.Region(N.bbox().transformed(pya.DTrans(X0,Y0).to_itype(L.dbu))).sized(round(2/L.dbu))
    for li in L.layer_indices():
        assert (footprint&pya.Region(T.begin_shapes_rec(li))).is_empty(),('Integrator footprint not free',str(L.get_info(li)))
    boxes,vias,targets=route_plan();new={}
    for net,layer,*xy in boxes:new.setdefault((net,layer),pya.Region()).insert(dbox(*xy))
    for net,cell,x,y in vias:
        C=L.cell(cell);assert C is not None,cell
        census={}
        for li in L.layer_indices():
            n,it=0,C.begin_shapes_rec(li)
            while not it.at_end():n+=1;it.next()
            if n:census[(L.get_info(li).layer,L.get_info(li).datatype)]=n
        assert census==VIA_CELLS[cell],(cell,census)
        for li in L.layer_indices():
            info=L.get_info(li)
            if info.layer in SPACE and info.datatype==0:
                r=pya.Region(C.begin_shapes_rec(li)).transformed(pya.DTrans(x,y).to_itype(L.dbu))
                new.setdefault((net,info.layer),pya.Region()).insert(r)
    check=[]
    for (net,layer),region in new.items():
        existing=flat(layer);tl,tx,ty=targets[net]
        allowed=existing.interacting(pya.Region(dbox(tx-.01,ty-.01,tx+.01,ty+.01))) if tl==layer else pya.Region()
        foreign=existing-allowed
        conflict=region.sized(round(SPACE[layer]/L.dbu))&foreign
        assert conflict.is_empty(),('New route too close to foreign parent shape',net,layer,str(conflict))
        for (other,olayer),oregion in new.items():
            if other!=net and olayer==layer:
                assert (region.sized(round(SPACE[layer]/L.dbu))&oregion).is_empty(),('New routes too close',net,other,layer)
        if tl==layer:assert not (region&allowed).is_empty(),('Route does not land on its target',net)
        check.append(dict(net=net,layer=layer,space_um=SPACE[layer],foreign_conflict_free=True,lands_on_target=tl==layer))
    # Insert the integrator and the declared routes.
    T.insert(pya.DCellInstArray(N.cell_index(),pya.DTrans(X0,Y0)))
    added=[]
    for net,layer,*xy in boxes:
        T.shapes(L.layer(layer,0)).insert(pya.DBox(*xy));added.append(dict(net=net,layer=layer,rect_um=xy))
    for net,cell,x,y in vias:
        T.insert(pya.DCellInstArray(L.cell(cell).cell_index(),pya.DTrans(x,y)));added.append(dict(net=net,via_cell=cell,xy_um=[x,y]))
    T.name=TOP
    oldshapes=original[OLDTOP][0];nowshapes=shapes(T)
    assert all(s in nowshapes for s in oldshapes) and len(nowshapes)==len(oldshapes)+len(boxes)
    # Every non-top original cell is unchanged.
    for name,(ss,ii) in original.items():
        if name!=OLDTOP:assert shapes(L.cell(name))==ss and instances(L.cell(name))==ii,name
    # Reference: replace changed macro subcircuits, add div1 and integrator.
    s=(P/'schematic.cir').read_text()
    def block(text,name):
        pattern=r'(?ms)^\.subckt '+re.escape(name)+r' .*?^\.ends '+re.escape(name)+r'\s*$'
        found=list(re.finditer(pattern,text));assert len(found)==1,name;return found[0]
    def cards(text):return [' '.join(l.lower().split()) for l in text.splitlines() if l.strip() and not l.startswith(('*','.'))]
    refs={}
    for key,top in [('pump',SWAPS['pump'][1]),('vco',SWAPS['vco'][1]),('div1',SWAPS['div1'][1]),('integrator',INT)]:
        ref=(OUT/'children'/key/'layout/schematic.cir').read_text().strip();header=next(l for l in ref.splitlines() if l.startswith('.subckt '))
        assert header.split()[1]==top;refs[key]=ref.replace(header,header+' BULK',1)
    for key in ('pump','vco','div1'):
        oldcell=SWAPS[key][0];m=block(s,oldcell)
        assert m.group(0).splitlines()[0].split()[2:]==refs[key].splitlines()[next(i for i,l in enumerate(refs[key].splitlines()) if l.startswith('.subckt '))].split()[2:]
        before,after=cards(m.group(0)),cards(refs[key]);assert len(before)==len(after)
        delta=[(a,b) for a,b in zip(before,after) if a!=b];assert delta==CARD_DELTAS[key],(key,delta)
        proof[key]['reference_card_delta']=delta
    pump_old=block(s,SWAPS['pump'][0]);s=s[:pump_old.start()]+refs['pump']+'\n'+s[pump_old.end():]
    vco_old=block(s,SWAPS['vco'][0]);s=s[:vco_old.start()]+refs['vco']+'\n'+s[vco_old.end():]
    s=s.replace(' '+SWAPS['pump'][0]+'\n',' '+SWAPS['pump'][1]+'\n').replace(' '+SWAPS['vco'][0]+'\n',' '+SWAPS['vco'][1]+'\n')
    lines=s.splitlines(keepends=True)
    d1=[i for i,l in enumerate(lines) if l.startswith('Xdiv1 ')];assert len(d1)==1 and lines[d1[0]].split()[-1]==SWAPS['div1'][0]
    lines[d1[0]]=lines[d1[0]].replace(SWAPS['div1'][0],SWAPS['div1'][1])
    end=[i for i,l in enumerate(lines) if l.strip()=='.ends '+OLDTOP];assert len(end)==1
    lines.insert(end[0],'Xint vctrl avss sub avss '+INT+'\n')
    s=''.join(lines)+'\n'+refs['div1']+'\n\n'+refs['integrator']+'\n'
    s=s.replace(OLDTOP,TOP)
    assert len(re.findall(r'(?m)^Xdiv2 .* '+re.escape(SWAPS['div1'][0])+r'$',s))==1
    assert len(re.findall(r'(?m)^Xdiv1 .* '+re.escape(SWAPS['div1'][1])+r'$',s))==1
    assert SWAPS['pump'][0] not in s and SWAPS['vco'][0] not in s
    (A/'schematic.cir').write_text(s)
    # Reference faults.
    rint=next(l for l in refs['integrator'].splitlines() if ' rppd ' in l);assert ' w=2u l=23u ' in rint and s.count(rint)==1
    (A/'wrong-integrator.cir').write_text(s.replace(rint,rint.replace(' l=23u ',' l=46u '),1))
    (A/'div1-reverted.cir').write_text(s.replace(re.findall(r'(?m)^Xdiv1 .*$',s)[0],re.findall(r'(?m)^Xdiv1 .*$',s)[0].replace(SWAPS['div1'][1],SWAPS['div1'][0]),1))
    opt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index());L.write(str(A/(TOP+'.gds')),opt)
    # Physical fault: remove only the new vctrl TopMetal2 riser.
    riser=[z for z in T.each_shape(L.layer(134,0)) if z.is_box() and abs(z.box.left*L.dbu-(VCTRL_LANE-1))<1e-6 and abs(z.box.top*L.dbu-VCTRL_RISER_TOP)<1e-6]
    assert len(riser)==1;cut=riser[0].box;riser[0].delete();L.write(str(A/'integrator-open.gds'),opt);T.shapes(L.layer(134,0)).insert(cut)
    old['instances'].append(dict(name='integrator',top=INT,position_um=list(INT_ORIGIN),bbox_um=str(N.dbbox().transformed(pya.DTrans(X0,Y0))),
        ports={p:dict(net=p,layer=67,box_um=[X0,Y0+y-.6,X0+2,Y0+y+.6],side='left') for p,y in INT_PORTS.items()}))
    old.update(top=TOP,status='GENERATED_C5R3K_PARENT_REQUIRES_NATIVE_CHECKS',parent_drc_pass=False,parent_lvs_pass=False,closed_loop_accepted=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False)
    old['prior_integration_proof']=old.get('integration_proof')
    old['integration_proof']=dict(swaps=proof,integrator=dict(origin_um=list(INT_ORIGIN),footprint_free_with_2um_margin=True,route_checks=check,added=added),
        other_cells_unchanged=True,existing_parent_shapes_unchanged=True,expected_native_devices=DEVICES)
    def physical(layout,t,li):
        reg=pya.Region();it=t.begin_shapes_rec(li)
        while not it.at_end():
            z=it.shape()
            if z.is_box() or z.is_polygon() or z.is_path():reg.insert(z.polygon.transformed(it.trans()))
            else:assert z.is_text()
            it.next()
        return reg.merged()
    for source,target in [(TOP+'.gds','flat.gds'),('integrator-open.gds','integrator-open-flat.gds')]:
        F=pya.Layout();F.read(str(A/source));U=F.cell(TOP)
        geometry={str(F.get_info(li)):physical(F,U,li) for li in F.layer_indices()}
        direct=sorted(z.text.string for li in F.layer_indices() for z in U.each_shape(li) if z.is_text());assert direct==sorted(old['ports'])
        allowed={}
        for x in old['instances']:allowed.setdefault(x['top'],set()).update(x['ports'])
        removed=[]
        for name,ports in allowed.items():
            cell=F.cell(name);assert cell is not None,name
            for li in F.layer_indices():
                info=F.get_info(li)
                if info.datatype!=25 or info.layer not in [8,10,30,50,67,126,134]:continue
                for z in list(cell.each_shape(li)):
                    if z.is_text() and z.text.string in ports:removed.append((name,z.text.string));z.delete()
        assert len(removed)==sum(len(p) for p in allowed.values()),(len(removed),sum(len(p) for p in allowed.values()))
        for li in F.layer_indices():assert (geometry[str(F.get_info(li))]^physical(F,U,li)).is_empty()
        so=pya.SaveLayoutOptions();so.select_cell(U.cell_index());F.write(str(A/target),so)
    from hashlib import sha256
    def h(p):return sha256(Path(p).read_bytes()).hexdigest()
    old['inputs']={str(p):h(p) for p in [Path(__file__),P/'result.json',P/(OLDTOP+'.gds'),P/'schematic.cir',
        *[OUT/'children'/k/'layout'/n for k in ('pump','vco','div1','integrator') for n in ('result.json','schematic.cir')],
        *[OUT/'children'/k/'layout'/(t+'.gds') for k,t in (('pump',SWAPS['pump'][1]),('vco',SWAPS['vco'][1]),('div1',SWAPS['div1'][1]),('integrator',INT))]]}
    old['outputs']={p.name:h(p) for p in A.iterdir() if p.is_file()}
    (A/'result.json').write_text(json.dumps(old,indent=2)+'\n')

def verify(app):
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    from check_ihp_drc import digest,record_result
    from check_pcie_rx_cell import execute
    from prepare_ihp_drc import validate_lock,verify as verify_file
    A=OUT/'integrated';D=OUT/'physical';D.mkdir();g=json.loads((A/'result.json').read_text())
    pins={Path(p):v for p,v in g['inputs'].items()};pins.update({A/n:v for n,v in g['outputs'].items()})
    pins.update({p:digest(p) for p in [app,A/'result.json',ROOT/'hw/soc/flow/audit_klayout_lvs.py']})
    for typ in ('drc','lvs'):
        p=ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json';lock=json.loads(p.read_text());validate_lock(lock);pins[p]=digest(p)
        assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
        for row in lock['files']:
            p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify_file(p.read_bytes(),row);pins[p]=row['sha256']
    assert all(digest(p)==v for p,v in pins.items())
    r=dict(status='RUNNING',inputs={str(p):v for p,v in pins.items()},steps={},expected_native_devices=DEVICES,qualified_pex=False,full_phy_accepted=False)
    def save():(D/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    for name in ('drc','lvs','lvs_flat','wrong_integrator','div1_reverted','integrator_open'):
        q=D/name;q.mkdir();step=r['steps'][name]={}
        try:
            gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/('integrator-open-flat.gds' if name=='integrator_open' else 'flat.gds')
            ref=A/{'wrong_integrator':'wrong-integrator.cir','div1_reverted':'div1-reverted.cir'}.get(name,'schematic.cir');typ='drc' if name=='drc' else 'lvs'
            entry=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc' if typ=='drc' else 'lvs/sg13g2.lvs')
            opts=[f'input={gds}',f'topcell={TOP}',f'log={q/"deck.log"}','run_mode='+('deep' if name in ('drc','lvs') else 'flat')]
            opts+=([f'report={q/"drc.lyrdb"}','threads=2','no_recommended=False','precheck_drc=False'] if typ=='drc' else [f'schematic={ref}',f'report={q/"result.lvsdb"}',f'target_netlist={q/"extracted.cir"}','thr=2','no_simplify=true','top_lvl_pins=true'])
            cmd=[app,'klayout','-b','-zz','-r',entry]
            for option in opts:cmd+=['-rd',option]
            step['execution']=execute(cmd,q,'run');save();assert step['execution']['returncode']==0
            if name=='drc':
                step['measurement']=record_result(q,TOP,0,pins);assert step['measurement']['category_count']==560 and step['measurement']['status']=='PASS'
            else:
                step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',q/'result.lvsdb','--top',TOP,'--deck-log',q/'deck.log','--output',q/'audit.json'],q,'audit')
                a=json.loads((q/'audit.json').read_text());step['audit']=a
                if name in ('lvs','lvs_flat'):
                    assert step['audit_execution']['returncode']==0 and a['status']=='PASS within comparison scope'
                    assert not a['extraction_diagnostics'] and set(a['circuit_status_counts'])=={'Match'}
                    roots=[c for c in a['circuits'] if c['layout']==TOP];assert len(roots)==1
                    assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==DEVICES
                    rows=[]
                    for raw in (q/'extracted.cir').read_text().splitlines():
                        l=raw.strip()
                        if l.startswith('+'):assert rows;rows[-1]+=' '+l[1:].strip()
                        elif l and not l.startswith('*'):rows.append(l)
                    headers=[l.split() for l in rows if l.lower().startswith('.subckt ')]
                    assert len({x[1].lower() for x in headers})==len(headers)
                    ports=[x[2:] for x in headers if x[1]==TOP];assert len(ports)==1 and len(ports[0])==17 and set(ports[0])==set(g['ports'])
                else:
                    assert step['audit_execution']['returncode']==1 and a['status']=='FAIL' and 'Deck explicitly reported a mismatch' in a['reasons']
            step['status']='PASS' if name in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT'
        except BaseException as e:step.update(status='FAILED',error=repr(e))
        save();print(name,step['status'],flush=True)
    assert all(digest(p)==v for p,v in pins.items())
    passed=all(s['status'] in ('PASS','REJECTED_EXPECTED_FAULT') for s in r['steps'].values())
    r['status']='PASS_C5R3K_PARENT849_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_C5R3K_PARENT_NATIVE_CHECKS';save();assert passed
    return r
