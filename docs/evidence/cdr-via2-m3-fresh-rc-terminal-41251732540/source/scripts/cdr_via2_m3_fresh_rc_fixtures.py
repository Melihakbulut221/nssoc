#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent synthetic full-census numerical fixtures; never native CAD input."""
import copy,json
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path

PORTS=['avdd','avss','sub','ird','cn','cp','dn','dp','irb','ira','irc','ibda','ibdc','ibs0','irx','xp','xn','ibs1','iry','yn','yp','irvx','irvy','vin','vip']
DISPOSITIONS=dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
ORDER={'npn13G2':['C','B','E','S'],'sg13_lv_nmos':['S','G','D','B'],'rppd':['rppd_1','rppd_2','rppd_sub'],'cap_cmim':['mim_top','mim_btm'],'ptap1':['TIE','WELL']}
BODY={'npn13G2':'S','sg13_lv_nmos':'B','rppd':'rppd_sub','ptap1':'TIE'}

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def synthetic_inputs(out,technology_root):
    out=Path(out);out.mkdir(parents=True);devices=[];geometry=[];anchor_rows=[];anchors=[];native_rows=[];schematic=[];ident=0;metal_index=0
    native_names={i+1:(PORTS[i]if i<25 else '$'+str(i+1))for i in range(113)}
    def add_anchor(label,component,detail):
        i=len(anchors);point=[10+i*10,20+i*10]
        row=dict(label=label,logical_labels=[label],native_cluster=component,wire_component=component,point_dbu=point,metal=8,detail=detail)
        anchors.append(row);return row
    widths=[8]*8+[32]*2+[36]*32+[53.335]*4+[64]*4
    dims=[3.6]*4+[4.8]*2+[40]
    for model,count in [('npn13G2',124),('sg13_lv_nmos',50),('rppd',98),('cap_cmim',7),('ptap1',221)]:
        for index in range(count):
            ident+=1
            if model=='npn13G2':params=dict(Nx=1+index%3,m=1,we=.07,le=.9)
            elif model=='sg13_lv_nmos':params=dict(L=.3,W=widths[index],AS=1,AD=1,PS=2,PD=2,rfmode=0)
            elif model=='rppd':params=dict(w=4,l=5 if ident in (184,185,222,223)else 7.4,ps=0,b=0,m=1)
            elif model=='cap_cmim':
                w=Decimal(str(dims[index]));params=dict(w=float(w),l=float(w),A=float(w*w),P=float(4*w),m=1)
            else:params=dict(A=40 if index>=217 else 4,P=44 if index>=217 else 8)
            params={k:float(v)for k,v in params.items()}
            nets={};terminal_rows=[]
            for terminal in ORDER[model]:
                if BODY.get(model)==terminal:
                    net='sub';row=dict(device=ident,terminal=terminal,model=model,native_net=net,net=net,native_cluster=114,disposition='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE')
                else:
                    component=1+metal_index%113;metal_index+=1;net=native_names[component]
                    label='T'+str(ident).zfill(3)+'_'+terminal;a=add_anchor(label,component,{})
                    row=dict(device=ident,terminal=terminal,model=model,native_net=net,net=net,native_cluster=component,wire_component=component,wire_anchor=label,point_dbu=a['point_dbu'].copy(),metal=8,disposition='ACTUAL_TERMINAL_METAL_POINT_REFERENCE')
                nets[terminal]=net;anchor_rows.append(row);terminal_rows.append(dict(name=terminal,net=net))
            devices.append(dict(native_id=ident,model=model,terminals=nets,parameters=params))
            geometry.append(dict(native_id=ident,model=model,parameters=params.copy(),terminals=terminal_rows))
            fields=[]
            for key,value in params.items():
                exponent=-12 if key in ('A','AS','AD')else -6 if key in ('w','l','ps','we','le','P','L','W','PS','PD')else 0
                fields.append(key+'='+str(Decimal(str(value))*Decimal(10)**exponent))
            prefix='Q'if model=='npn13G2'else'M'if model=='sg13_lv_nmos'else'C'if model=='cap_cmim'else'R'
            native_rows.append(' '.join([prefix+'$'+str(ident),*[nets[t]for t in ORDER[model]],model,*fields]))
            if model=='npn13G2':schematic.append(' '.join(['Q'+str(ident),*[nets[t]for t in ORDER[model]],model,'Nx='+str(params['Nx'])]))
    for i,port in enumerate(PORTS):add_anchor('P_'+port,i+1,dict(public_port=port))
    assert len(devices)==500 and len(anchor_rows)==1446 and len(anchors)==978 and metal_index==953
    anchor_record=dict(anchors=anchors,rows=anchor_rows,logical_anchor_count=978,physical_anchor_count=978,public_ports=25,logical_anchor_aliases={a['label']:a['label']for a in anchors},dispositions=DISPOSITIONS.copy())
    wire_geometry=dict(native_device_count=500,native_terminal_count=1446,wire_component_count=113,native_net_count=238,native_electrical_net_count=114,wire_components=[dict(component=i,native_cluster=i)for i in range(1,114)])
    raw='\n'.join(['.SUBCKT nssoc_cdr_pd500_resistor_v59 '+' '.join(PORTS),*native_rows,'.ENDS nssoc_cdr_pd500_resistor_v59',''])
    p=out/'inputs/parent/physical/lvs_flat/extracted.cir';p.parent.mkdir(parents=True);p.write_text(raw)
    save(out/'native-devices.json',dict(devices=devices,explicit_synthetic_fixture=True))
    save(out/'inputs/wire/device-locations01.json',dict(devices=geometry))
    save(out/'inputs/parent/layout/result.json',dict(source_plan=dict(ports=list(reversed(PORTS)))))
    (out/'inputs/parent/layout/schematic.cir').write_text('\n'.join(schematic)+'\n')
    tech=dict(ptap1_raspec='1e-6',ptap1_rpspec='1e-3')
    save(Path(technology_root)/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json',dict(techParams=tech,explicit_synthetic_fixture=True))
    cases=[]
    for length in (2,20):
        area=Decimal(2*length)*Decimal('1e-12');perimeter=Decimal(2*(2+length))*Decimal('1e-6')
        cases.append(dict(w_um=2,l_um=length,A_um2=2*length,P_um=2*(2+length),resistance_ohm=float(1/(area/Decimal('1e-6')+perimeter/Decimal('1e-3')))))
    save(out/'native-contact-oracle.json',dict(status='PASS_NATIVE_PDK_CONTACT_EQUATION_EXECUTED_REQUIRES_COMPACT_MODEL_COMPARISON',cases=cases,explicit_synthetic_fixture=True,native_pdk_executed=False))
    return dict(anchors=anchor_record,geometry=wire_geometry,devices=devices,native_text=raw)

def raw_fixture(wire,fixture,binding,include_mim):
    wire=Path(wire);(wire/'rc03').mkdir(parents=True);a=copy.deepcopy(fixture['anchors']);save(wire/'anchors08.json',a)
    groups=defaultdict(list)
    for row in a['anchors']:groups[row['wire_component']].append(row['label'])
    roots={k:v[0]for k,v in groups.items()};resistors=[];resist=[];caps=[];baseline_caps=[];ext=['scale 1000 1 0.5','style ngspice()','substrate sub! 0 0'];rep=['scale 1000 1 0.5'];log=['synthetic complete numerical fixture, no CAD executed','Total Nets: 114','Nets extracted: 113','Nets output: 113']
    mutual=[(roots[1],roots[2],10),(roots[3],roots[4],20)]
    for i,(x,y,value)in enumerate(mutual):
        ext.append('cap '+x+' '+y+' '+str(value));caps.append('C'+str(i)+' '+x+' '+y+' '+str(Decimal(value)*Decimal('1e-18')));baseline_caps.append('CB'+str(i)+' '+x+' '+y+' '+str(Decimal(value)*Decimal('1e-18')))
    for component in range(1,114):
        names=groups[component];root=roots[component];total=len(names)*100
        ext.append('node '+root+' 0 '+str(total));rep.append('subcap '+root+' '+str(-total));baseline_caps.append('CBG'+str(component)+' '+root+' sub '+str(Decimal(total)*Decimal('1e-18')))
        for name in names[1:]:ext.append('equiv '+root+' '+name)
        for i,name in enumerate(names):
            other=names[(i+1)%len(names)];ident=len(resistors);resistors.append('R'+str(ident)+' '+name+' '+other+' 2');resist.append('resist '+name+' '+other+' 2')
            rep.append('rnode '+name+' 0 100');caps.append('CG'+str(len(caps))+' '+name+' sub 1e-16')
        incident=sum(v for x,y,v in mutual if root in(x,y))
        log.append('NSSOC_V2_INTRINSIC_DISTRIBUTION '+root+' total='+str(total+incident)+' intrinsic='+str(total))
    for i,row in enumerate(a['anchors']):
        x,y=row['point_dbu'];assert x%5==y%5==0
        ext.append('port '+row['label']+' '+str(i+1)+' '+' '.join(map(str,[x//5,y//5,x//5,y//5])))
    rep+=resist;xs=[];before_xs=[]
    if include_mim:
        ext.append('parameters cap_cmim w=w l=l');lookup={(r['device'],r['terminal']):r for r in a['rows']}
        for d in binding['devices']:
            if d['model']!='cap_cmim':continue
            ident=d['native_id'];plus=lookup[ident,'mim_top'];minus=lookup[ident,'mim_btm'];x=10000+ident*10;box=[x,x+1,x+2,x+3]
            w=Decimal(d['native_parameters']['w']);l=Decimal(d['native_parameters']['l']);assert w/Decimal('.005')==int(w/Decimal('.005'))
            ext.append(' '.join(['device','csubckt','cap_cmim',*map(str,box),'w='+str(int(w/Decimal('.005'))),'l='+str(int(l/Decimal('.005'))),'None',roots[plus['wire_component']],'0','0',roots[minus['wire_component']],'0','0']))
            rep.append(' '.join(['device','csubckt','cap_cmim',*map(str,box),'None',plus['wire_anchor'],'0','0',minus['wire_anchor'],'0','0']))
            dims=['w='+str(w)+'u','l='+str(l)+'u']
            xs.append(' '.join(['X'+str(ident),plus['wire_anchor'],minus['wire_anchor'],'cap_cmim',*dims]));before_xs.append(' '.join(['X'+str(ident),roots[plus['wire_component']],roots[minus['wire_component']],'cap_cmim',*dims]))
    p=wire/'rc03';(p/'pump_wires.ext').write_text('\n'.join(ext)+'\n');(p/'pump_wires.res.ext').write_text('\n'.join(rep)+'\n')
    (p/'native.log').write_text('\n'.join(log)+'\nNSSOC_WIRE_RC_COMPLETE\n')
    (p/'wires.spice').write_text('\n'.join(['.subckt pump_wires '+' '.join(row['label']for row in a['anchors']),*resistors,*caps,*xs,'.ends pump_wires','']))
    (p/'baseline.spice').write_text('\n'.join(['.subckt pump_wires '+' '.join(roots.values()),*baseline_caps,*before_xs,'.ends pump_wires','']))
    return dict(R=len(resistors),C=len(caps),MIM=len(xs),components=len(groups),anchors=len(a['anchors']))
