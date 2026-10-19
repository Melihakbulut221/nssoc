#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual31-macro32:1 core; native physical gates, no waveform/PHY acceptance."""
import argparse,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-tree32-assembly'
TOP='nssoc_tx_tree32_core_v1'
CHILD_PORTS='ap an bp bn sp sn op on avdd avss sub iref'.split()

def topology(column_pitch=1000.,row_pitch=600.):
    assert (column_pitch,row_pitch) in ((1000.,600.),(700.,600.))
    from run_cloud_tx_mux4 import tree_plan
    plan=tree_plan(32)
    nodes=[dict(n,kind='pre')for n in plan['nodes']]
    nodes.append(dict(label='f',inputs=['a','b'],clock='s',reference='mr',stride=1,offset=0,kind='final'))
    by={n['label']:n for n in nodes};assert len(by)==31
    # Independent binary selection truth table: every serial position selects
    # exactly the intended parallel input, before any GDS/reference generation.
    def selected(index,table):
        label='f';seen=set()
        while not re.fullmatch(r'd\d+',label):
            assert label not in seen;seen.add(label);n=table[label]
            label=n['inputs'][(index//n['stride'])%2]
        return label
    assert [selected(i,by)for i in range(32)]==['d'+str(i)for i in range(32)]
    bad={k:dict(v,inputs=list(v['inputs']))for k,v in by.items()}
    bad['p16_0']['inputs'][0]='d1'
    assert [selected(i,bad)for i in range(32)]!=['d'+str(i)for i in range(32)]
    # Physical rows follow the binary subtree, keeping each parent in the gap
    # between its two children. No external frontend or clock macro is implied.
    leaf_order=[]
    def visit(label):
        n=by[label]
        if n['stride']==16:leaf_order.append(label)
        else:
            for child in n['inputs']:visit(child)
    visit('f');assert len(leaf_order)==16 and len(set(leaf_order))==16
    def row(label):
        if label in leaf_order:return leaf_order.index(label)*row_pitch
        return sum(row(c)for c in by[label]['inputs'])/2
    maps={};ports=[]
    for n in nodes:
        tag=n['label'];a,b=n['inputs'];out='m'if tag=='f'else tag
        maps[tag]=dict(zip(CHILD_PORTS,[a+'p',a+'n',b+'p',b+'n',n['clock']+'p',n['clock']+'n',out+'p',out+'n','avdd','avss','sub',n['reference']],strict=True))
        n['x_um']=(4-(n['stride'].bit_length()-1))*column_pitch
        n['y_um']=row(tag)
    ports=[f'd{i}{suffix}'for i in range(32)for suffix in ('p','n')]
    ports += [n['clock']+s for n in nodes for s in ('p','n')]
    ports += [n['reference']for n in nodes]+['mp','mn','avdd','avss','sub']
    assert len(ports)==len(set(ports))==162
    return dict(nodes=nodes,maps=maps,ports=ports,source_plan=plan,selection_fault_rejected=True,
        column_pitch_um=column_pitch,row_pitch_um=row_pitch)

def flatten(text,tag,mapping):
    rows=text.splitlines();headers=[l.split()for l in rows if l.lower().startswith('.subckt ')]
    assert len(headers)==1 and headers[0][2:]==CHILD_PORTS
    out=[]
    for line in rows:
        if not line.strip()or line.startswith(('*','.')):continue
        r=line.split()
        if r[0].startswith('Q'):count,model=4,'npn13G2'
        elif r[0].startswith('RPTAP'):count,model=2,'ptap1'
        elif r[0].startswith('RD'):count,model=3,'rppd'
        else:raise ValueError(r[0])
        assert r[count+1]==model
        r[0]=r[0][0]+tag+'_'+r[0][1:]
        r[1:count+1]=[mapping.get(n,'BULK'if n=='BULK'else tag+'_'+n)for n in r[1:count+1]]
        out.append(' '.join(r))
    assert len(out)==54 and sum(r.startswith('Q')for r in out)==19
    return out

def generate():
    import xml.etree.ElementTree as ET
    source=ROOT/'pdk/libs.tech/klayout/python';sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    plan=json.loads((OUT/'plan.json').read_text());maps=plan['maps'];ports=plan['ports']
    lyp=source.parent/'tech/sg13g2.lyp'
    layers={p.findtext('name')[:-8]:int(p.findtext('source').split('/')[0])for p in ET.parse(lyp).getroot().iter('properties')if p.findtext('name','').endswith('.drawing')}
    L=pya.Layout();L.dbu=.001;top=L.create_cell(TOP)
    protected={str(Path(__file__).resolve()):sha(Path(__file__).resolve()),str(OUT/'plan.json'):sha(OUT/'plan.json'),str(lyp):sha(lyp)}
    children={}
    pre_top='nssoc_tx_mux2_cascade158_nx3_balanced_v5_layout_v1'if plan['variant']=='budget_balanced_v5'else'nssoc_tx_mux2_cascade158_nx3_layout_v1'if plan['variant']=='budget_high3'else'nssoc_tx_mux2_cascade158_layout_v1'
    child_types=[('pre',pre_top),('final','nssoc_tx_mux2_final_drive_v10_layout_v1')]
    if plan['variant']in ('budget_high8','budget_high3','budget_balanced_v5'):child_types.append(('pre_low','nssoc_tx_mux2_cascade158_nx1_balanced_v5_layout_v1'if plan['variant']=='budget_balanced_v5'else'nssoc_tx_mux2_cascade158_nx1_layout_v1'))
    for kind,childname in child_types:
        directory=OUT/'inputs'/kind/'layout';data=json.loads((directory/'result.json').read_text())
        for name,digest in data['outputs'].items():assert sha(directory/name)==digest;protected[str(directory/name)]=digest
        old=pya.Layout();old.read(str(directory/(childname+'.gds')));child=old.cell(childname);assert child and old.dbu==L.dbu
        copied=L.create_cell('core_'+kind);copied.copy_tree(child)
        for dt in (2,25):
            shapes=copied.shapes(L.layer(layers['TopMetal2'],dt));assert sum(1 for _ in shapes.each())==12;shapes.clear()
        for idx in old.layer_indexes():
            info=old.get_info(idx)
            if info.datatype==0:assert (pya.Region(child.begin_shapes_rec(idx)).merged()^pya.Region(copied.begin_shapes_rec(L.layer(info.layer,0))).merged()).is_empty()
        children[kind]=(copied,data,directory)
    placements={};pins={};schematic=['* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut','* SPDX-License-Identifier: CERN-OHL-W-2.0','.subckt '+TOP+' '+' '.join(ports)]
    for n in plan['nodes']:
        tag=n['label'];child,data,directory=children[n['kind']]
        assert child.dbbox().left==0 and child.dbbox().bottom==0
        assert child.dbbox().height() < plan['row_pitch_um'], 'Actual child exceeds row pitch; old tight placement is invalid'
        assert child.dbbox().width()+300 < plan['column_pitch_um'], 'Native macro and parent channels exceed column pitch'
        tr=pya.DTrans(2,True,n['x_um']+child.dbbox().right,n['y_um'])
        top.insert(pya.DCellInstArray(child.cell_index(),tr))
        pins[tag]={p:pya.DBox(*map(float,re.findall(r'-?\d+(?:\.\d+)?',box))).transformed(tr)for p,box in data['ports'].items()}
        placements[tag]=dict(kind=n['kind'],transform=str(tr),bbox_um=str(child.dbbox().transformed(tr)),ports={p:str(b)for p,b in pins[tag].items()})
        schematic.extend(flatten((directory/'schematic.cir').read_text(),tag,maps[tag]))
    schematic.append('.ends '+TOP);assert len(schematic)==1678
    def box(layer,x1,y1,x2,y2):top.shapes(L.layer(layers[layer],0)).insert(pya.DBox(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)))
    def via(x,y,power=False,bottom='TopMetal1',upper='TopMetal2',params=None):
        opts=params or dict(vn_columns=2,vn_rows=1,vt1_rows=1,vt2_columns=4 if power else 2,vt2_rows=4 if power else 1)
        c=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=upper,**opts));assert c and not c.is_empty()
        b=c.dbbox();top.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(round((x-b.center().x)/.005)*.005,round((y-b.center().y)/.005)*.005)))
    def center(tag,pin):q=pins[tag][pin].center();return q.x,q.y
    routes=[]
    def stub(tag,pin,x,width,power=False):
        px,py=center(tag,pin);box('TopMetal2',min(px,x)-width/2,py-width/2,max(px,x)+width/2,py+width/2);via(x,py,power);return py
    # Every parent gets four distinct TM1 channels outside its right boundary.
    for n in plan['nodes']:
        if n['stride']==16:continue
        parent=n['label'];right=max(b.right for b in pins[parent].values())
        for k,(child,op,ip)in enumerate([(n['inputs'][0],'op','ap'),(n['inputs'][0],'on','an'),(n['inputs'][1],'op','bp'),(n['inputs'][1],'on','bn')]):
            # Four observed same-layer overlaps in native failed39154915645.
            # Share replacement tracks only where their physical Y intervals are disjoint.
            shift={'p8_2p':48.,'p8_2n':48.,'p8_7p':24.,'p8_7n':24.}.get(maps[child][op],0.)
            x=right+40+12*k+shift;y0=stub(child,op,x,4);y1=stub(parent,ip,x,4)
            box('TopMetal1',x-2,min(y0,y1)-2,x+2,max(y0,y1)+2)
            assert maps[child][op]==maps[parent][ip]
            routes.append(dict(centerline_length_um=abs(center(child,op)[0]-x)+abs(y1-y0)+abs(center(parent,ip)[0]-x),net=maps[child][op],endpoints=[child+'.'+op,parent+'.'+ip],x_um=x,y_um=[y0,y1],width_um=4,fault_cut_um=[x-3,(y0+y1)/2-.5,x+3,(y0+y1)/2+.5]))
    assert len(routes)==60 and len({r['net']for r in routes})==60
    # Each column has separate external AVDD/AVSS/SUB trunks. Global buses
    # are below every child; never draw a global rail through macro bodies.
    rail_ends={k:[]for k in ('avdd','avss','sub')}
    return_width=plan.get('return_rail_width_um',32.);assert return_width in (32.,64.)
    return_geometry=[]
    for level in range(5):
        pitch=plan['column_pitch_um']
        group=[n for n in plan['nodes']if n['x_um']==pitch*level];assert group
        x0=pitch*level;right=max(b.right for n in group for b in pins[n['label']].values())
        for net,width,x,ybus in [('avdd',32.,right+140.,-100.),('sub',4.,right+200.,-300.),('avss',return_width if level<4 else 256.,x0-40. if level<4 else right+340.,-200.)]:
            ys=[stub(n['label'],net,x,32. if net=='avss'else width,True)for n in group]
            if net=='avss':return_geometry.append(dict(layer='TopMetal1',box_um=[x-width/2,ybus-width/2,x+width/2,max(ys)+width/2],width_um=width))
            box('TopMetal1',x-width/2,ybus-width/2,x+width/2,max(ys)+width/2);via(x,ybus,True)
            rail_ends[net].append((x,ybus,width))
    for net,ends in rail_ends.items():
        xs=[x for x,y,w in ends];y=ends[0][1];w=ends[0][2]
        box('TopMetal2',min(xs)-w/2,y-w/2,max(xs)+w/2,y+w/2)
        if net=='avss':return_geometry.append(dict(layer='TopMetal2',box_um=[min(xs)-w/2,y-w/2,max(xs)+w/2,y+w/2],width_um=w))
    assert len(return_geometry)==6
    # Widen only the final TM1 strap4to6um; retain the original via arrays.
    # Lower Metal2 emitter accesses and every child drawing stay unchanged.
    final=next(n for n in plan['nodes']if n['label']=='f');x=final['x_um']+334.785-280.875;yy=final['y_um'];end_y=yy+330.24
    for y in (yy+132.230,yy+139.435):via(x,y,bottom='Metal2',upper='TopMetal1',params=dict(vn_columns=8,vn_rows=1,vt1_columns=2,vt1_rows=2))
    box('TopMetal1',x-3,yy+130.230,x+3,end_y+2);via(x,end_y,params=dict(vt2_columns=2,vt2_rows=2))
    public={}
    for n in plan['nodes']:
        tag=n['label']
        for pin,b in pins[tag].items():
            net=maps[tag][pin]
            if net in ports and net not in public:public[net]=('TopMetal2',b)
    assert set(public)==set(ports)
    # Expose supply ports on actual parent buses so real short controls touch
    # parent metal, independently of retained child geometry.
    for net,ends in rail_ends.items():
        x,y,w=ends[0];public[net]=('TopMetal2',pya.DBox(x-w/2,y-w/2,x+w/2,y+w/2))
    for net,(layer,b)in public.items():
        top.shapes(L.layer(layers[layer],2)).insert(b);top.shapes(L.layer(layers[layer],25)).insert(pya.DText(net,b.left,b.center().y))
    bounds=top.dbbox();dx,dy=-bounds.left,-bounds.bottom;top.transform(pya.Trans(round(dx/L.dbu),round(dy/L.dbu)))
    public={n:(layer,b.transformed(pya.DTrans(dx,dy)))for n,(layer,b)in public.items()}
    for r in routes:
        x1,y1,x2,y2=r['fault_cut_um'];r['fault_cut_um']=[x1+dx,y1+dy,x2+dx,y2+dy]
    sys.path.insert(0,str(ROOT/'hw/soc/flow'));import make_pcie_clock_vco_v6_local_v1 as writer
    writer.TOP=TOP;writer.PORTS=ports;writer.use_direction=lambda n:('POWER','INOUT')if n=='avdd'else('GROUND','INOUT')if n in ('avss','sub')else('SIGNAL','OUTPUT'if n in ('mp','mn')else 'INPUT')
    dest=OUT/'layout';dest.mkdir();top.write(str(dest/(TOP+'.gds')));(dest/'schematic.cir').write_text('\n'.join(schematic)+'\n');(dest/(TOP+'.lef')).write_text(writer.lef(pya,L.dbu,top.dbbox(),public))
    result=dict(status='GENERATED_UNVERIFIED_TREE32_1674_DEVICES',inputs=protected,outputs={p.name:sha(p)for p in dest.iterdir()},ports={n:str(b)for n,(_,b)in public.items()},bbox_um=str(top.dbbox()),parent_return_geometry_before_origin_translation=return_geometry,parent_signal_centerline_sum_um=sum(r['centerline_length_um']for r in routes),parent_signal_centerline_max_um=max(r['centerline_length_um']for r in routes),placement_pitch=dict(column_um=plan['column_pitch_um'],row_um=plan['row_pitch_um']),placements=placements,origin_translation_um=[dx,dy],signal_routes=routes,core_devices=837,substrate_contacts=837,total_devices=1674,frozen_child_drawing_regions_equal=True,serial_phy_complete=False,main_chip_integrated=False,qualified_pex=False,electrical_accepted=False,scope='Actual30pre+1final native macros,60intermacro signal wires and shared supplies/body. Clock/bias generation,64CMOSdrivers,loadedTX/fourlanes/mainchip and all electrical/RC gates remain outside this core.')
    (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    global OUT,TOP
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true')
    p.add_argument('--placement-pitch',choices=('compact_columns',),default='compact_columns')
    p.add_argument('--return-rail',choices=('wide64',),default='wide64')
    p.add_argument('--variant',choices=('budget_balanced_v5',),default='budget_balanced_v5');a=p.parse_args()
    if a.variant in ('budget_high8','budget_high3','budget_balanced_v5'):
        OUT=ROOT/('hw/soc/out/cloud-tx-tree32-'+({'budget_high8':'budget','budget_high3':'high3','budget_balanced_v5':'balanced-v5'}[a.variant])+'-assembly')
        TOP='nssoc_tx_tree32_'+a.variant+'_core_v1'
    if a.placement_pitch=='compact_columns':
        assert a.variant=='budget_balanced_v5'
        OUT=ROOT/'hw/soc/out/cloud-tx-tree32-tight-assembly'
        TOP='nssoc_tx_tree32_budget_balanced_v5_tight_core_v1'
    if a.return_rail=='wide64':
        assert a.variant=='budget_balanced_v5'and a.placement_pitch=='compact_columns'
        OUT=ROOT/'hw/soc/out/cloud-tx-v5-final-trunk256-assembly'
        TOP='nssoc_tx_tree32_budget_balanced_v5_final_trunk256_core_v1'
    if a.generate:generate();return
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=a.variant,serial_phy_complete=False,main_chip_integrated=False,qualified_pex=False,electrical_accepted=False)
    def run(command,label):
        with (OUT/(label+'.log')).open('w')as f:code=subprocess.call(list(map(str,command)),stdout=f,stderr=subprocess.STDOUT)
        if code:print((OUT/(label+'.log')).read_text(errors='replace')[-12000:],flush=True);raise RuntimeError((label,code))
    try:
        plan=topology(700.,600.)if a.placement_pitch=='compact_columns'else topology();plan['variant']=a.variant
        plan['placement_pitch']=a.placement_pitch
        # Inverse placement transform must recover the original bit topology,
        # maps, roles, clocks, references and every original macro coordinate.
        original=topology();check=json.loads(json.dumps(plan))
        check.pop('variant');check.pop('placement_pitch')
        if a.placement_pitch=='compact_columns':
            for n in check['nodes']:
                n['x_um']=round(n['x_um']/700.*1000.,9)
                n['y_um']=round(n['y_um']/600.*600.,9)
            check['column_pitch_um']=1000.;check['row_pitch_um']=600.
        assert check==original,'Placement changed original selector topology'
        # Explicit frequency-priority physical rows; original selector truth table,
        # references, clocks, cell choices and every device remain unchanged.
        row_targets={'a':4200.,'b':4800.,'p4_0':3600.,'p4_2':4200.,'p4_1':4800.,'p4_3':5400.}
        before_rows=json.loads(json.dumps(plan))
        for node in plan['nodes']:
            if node['label']in row_targets:node['y_um']=row_targets[node['label']]
        restored=json.loads(json.dumps(plan));oldrows={n['label']:n['y_um']for n in before_rows['nodes']}
        for node in restored['nodes']:node['y_um']=oldrows[node['label']]
        assert restored==before_rows
        plan['fast_stage_rows_um']=row_targets;result['fast_stage_rows_um']=row_targets
        result['signal_track_shift_um']={'p8_2p':48.,'p8_2n':48.,'p8_7p':24.,'p8_7n':24.}
        plan['return_rail_width_um']=64. if a.return_rail=='wide64'else 32.
        result['return_rail']=dict(profile=a.return_rail,trunk_and_bus_width_um=plan['return_rail_width_um'],child_stub_width_um=32.,local_final_strap_width_um=6.,final_column_trunk_width_um=256.,final_column_trunk_offset_from_right_um=340.,final_strap_top_via_columns=2,final_strap_top_via_rows=2,power_vias_columns=4,power_vias_rows=4,scope='Final-column AVSS TM1 trunk widens128to256um at its existing center. The6um local final strap and all via arrays retain the exact verified strap6 geometry. Other column trunks, bottom bus width, child stubs/drawings, lower emitter vias, AVDD/SUB, signals, topology and devices stay unchanged. No resistance scaling or electrical claim.')
        result['placement_pitch']=dict(name=a.placement_pitch,column_um=plan['column_pitch_um'],row_um=plan['row_pitch_um'],inverse_topology_matches_original=True)
        result['placement_scope']='Six final-stage macro rows change explicitly; parent routes are regenerated. Other macro rows and all cell sizes stay fixed. Frozen child drawings, devices, topology and acceptance rules unchanged. New RC and loaded waveforms mandatory; no parasitic or electrical pass inferred.'
        if a.variant in ('budget_high8','budget_high3','budget_balanced_v5'):
            for n in plan['nodes']:
                if n['kind']=='pre' and n['stride']>=4:n['kind']='pre_low'
            assert sum(n['kind']=='pre_low'for n in plan['nodes'])==28
            assert {n['label']for n in plan['nodes']if n['kind']=='pre'}=={'a','b'}
        (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');result['plan']=plan
        spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text());source=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'restore.tar.gz'
        fetch(source['receipt']['url'],source['receipt']['sha256'],packed)
        with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        if a.variant in ('budget_high8','budget_high3','budget_balanced_v5'):
            low_spec=ROOT/('docs/evidence/tx-pre-nx1-balanced-v5-physical-input-20261017.json'if a.variant=='budget_balanced_v5'else'docs/evidence/tx-pre-nx1-physical-input-20261017.json')
            spec['children']['pre_low']=json.loads(low_spec.read_text())
            result['scaled_cell_receipt_sha256']=sha(low_spec)
            if a.variant in ('budget_high3','budget_balanced_v5'):
                high_spec=ROOT/('docs/evidence/tx-pre-nx3-balanced-v5-physical-input-20261017.json'if a.variant=='budget_balanced_v5'else'docs/evidence/tx-pre-nx3-physical-input-20261017.json')
                spec['children']['pre']=json.loads(high_spec.read_text())
                result['high_cell_receipt_sha256']=sha(high_spec)
        for kind,row in spec['children'].items():
            fetch(row['url'],row['sha256'],packed);assert packed.stat().st_size==row['bytes']
            with tarfile.open(packed)as t:
                prefix=row.get('archive_prefix','hw/soc/out/cloud-tx-layout-repair/');prior=json.load(t.extractfile(prefix+'result.json'));assert prior['status']=='PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
                assert prior['variant']==row['variant']and prior['circuit_profile']==row['circuit_profile']and prior['boundary_pin_policy']=='nearest_pair_tight'
                if kind in ('pre','pre_low'):
                    assert hashlib.sha256(json.dumps(prior,sort_keys=True).encode()).hexdigest() == row['canonical_summary_sha256']
                if kind=='pre'and a.variant in ('budget_high3','budget_balanced_v5'):
                    assert prior['prestage_sizing']['nx']==3 and prior['prestage_sizing']['emitters']==55
                    assert prior['prestage_sizing']['candidate_sha256']==('e41ee27d762dbdb2cbe658ac38168fcdcb7869b2195a64761fb38396cd2f0f76'if a.variant=='budget_balanced_v5'else'3f4a896077a8791a617296fece3703c0641be8fcf381b9be0cc18cbd6563109d')
                    assert prior['prestage_sizing']['native_schematic_evidence_run']==(39060767622 if a.variant=='budget_balanced_v5'else 38999900875)
                    assert prior['physical']['status']=='PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
                    assert prior['physical']['steps']['drc']['measurement']['category_count']==560
                    assert prior['physical']['steps']['drc']['measurement']['markers']==0
                    assert all(prior['physical']['steps'][k]['status']=='REJECTED_EXPECTED_FAULT'for k in ('wrong_finger_count','missing_hbt','q_open','rail_short','offgrid'))
                if kind=='pre_low':
                    assert prior['prestage_sizing']['nx']==1 and prior['prestage_sizing']['emitters']==19
                    assert prior['prestage_sizing']['candidate_sha256']==('6ca409feb9337f2c960b6f15e7ee85c6885bf568e012cc484c5c059e43d26632'if a.variant=='budget_balanced_v5'else'af7f182a4cb33684e1ca191cfd34462786f7afa2942395de61ff2693514e2dcd')
                    assert prior['physical']['status']=='PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
                    assert prior['physical']['steps']['drc']['measurement']['category_count']==560
                    assert not prior['physical']['steps']['drc']['measurement']['categories']
                for name in ['layout/result.json','layout/schematic.cir',*['layout/'+n for n in row['generated_outputs']if n.endswith(('.gds','.lef'))],'verify-physical.py']:
                    raw=t.extractfile(prefix+name).read();target=OUT/'inputs'/kind/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                    if Path(name).name in row['generated_outputs']:assert hashlib.sha256(raw).hexdigest()==row['generated_outputs'][Path(name).name]
            packed.unlink()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==source['runtime_sha256'];run([app,'python',Path(__file__).resolve(),'--generate','--variant',a.variant,'--placement-pitch',a.placement_pitch,'--return-rail',a.return_rail],'generate')
        generated=json.loads((OUT/'layout/result.json').read_text());result['layout']=generated
        run([app,'python',ROOT/'scripts/check_tx_v5_final_trunk256_geometry.py',OUT],'exact-trunk256-geometry')
        result['trunk_geometry_delta']=json.loads((OUT/'trunk256-geometry-delta.json').read_text())
        method=(OUT/'inputs/pre/verify-physical.py').read_text()
        child_top='nssoc_tx_mux2_cascade158_nx3_balanced_v5_layout_v1'if a.variant=='budget_balanced_v5'else'nssoc_tx_mux2_cascade158_nx3_layout_v1'if a.variant=='budget_high3'else'nssoc_tx_mux2_cascade158_layout_v1'
        edits=[('TOP = "'+child_top+'"','TOP = '+repr(TOP)),("PORTS = ['ap','an','bp','bn','sp','sn','op','on','avdd','avss','sub','iref']",'PORTS = '+repr(plan['ports'])),('"QD0 "','"Qf_D0 "'),('"QD1 "','"Qf_D1 "'),('!= 54','!= 1674'),('TX_MUX54','TX_TREE1674')]
        for before,after in edits:assert method.count(before)==1;method=method.replace(before,after)
        old=next(l for l in method.splitlines()if 'li=L.layer(134,0);before=pya.Region'in l);cut=generated['signal_routes'][0]['fault_cut_um']
        new='    li=L.layer(126,0);before=pya.Region(top.shapes(li));cut=pya.Region(pya.DBox('+','.join(map(str,cut))+').to_itype(L.dbu));after=before-cut;assert before.area()!=after.area();top.shapes(li).clear();top.shapes(li).insert(after)'
        method=method.replace(old,new)
        # Preserve every physical gate and the overall failure. Check transistor
        # connectivity/faults first so the known emitter-count DRC failure does
        # not hide whether this larger topology is actually connected.
        original_order='\n'.join('            '+repr(n).replace("'",'"')+',' for n in ('drc','lvs','lvs_flat','wrong_finger_count','missing_hbt','q_open','rail_short','offgrid'))
        new_order='\n'.join('            '+repr(n).replace("'",'"')+',' for n in ('lvs','lvs_flat','wrong_finger_count','missing_hbt','q_open','rail_short','offgrid','drc'))
        assert method.count(original_order)==1
        method=method.replace(original_order,new_order)
        reference=(OUT/'layout/schematic.cir').read_text()
        hbts=[l for l in reference.splitlines()if l.startswith('Q')]
        emitters=sum(int(re.search(r'\bNx=(\d+)\b',l)[1])for l in hbts)
        expected_emitters={'baseline':4427,'budget_high8':899,'budget_high3':719,'budget_balanced_v5':719}[a.variant]
        assert len(hbts)==589 and emitters==expected_emitters
        if a.variant in ('budget_high8','budget_high3','budget_balanced_v5'):
            for n in plan['nodes']:
                expected={'pre_low':19,'pre':55 if a.variant in ('budget_high3','budget_balanced_v5')else 145,'final':77}[n['kind']]
                actual=sum(int(re.search(r'\bNx=(\d+)\b',l)[1])for l in hbts if l.startswith('Q'+n['label']+'_'))
                assert actual==expected,(n['label'],actual,expected)
        result['emitter_budget']=dict(reference_hbts=589,reference_emitters=emitters,
            four_lane_tree_reference_projection=4*emitters,recommended_chip_maximum=4000,
            rule='npn13G2.bR',recommended_rules_enabled=True,waiver=False,
            source='IHP-Open-PDK@5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/feol/6_1_npnsubstratetie.drc',
            scope='Exact reference census; native DRC independently screens physical geometry. PLL/CDR/clock/TX and other chip devices are additional; four-tree projection is not a whole-chip pass. Original4427-emitter physical failure remains retained, with no disabled rule.')
        verification=OUT/'verify-tree32.py';verification.write_text(method)
        run([sys.executable,verification,'--layout',OUT/'layout','--out',OUT/'physical','--app',app],'physical')
        result['physical']=json.loads((OUT/'physical/result.json').read_text());assert result['physical']['status']=='PASS_NATIVE_PDK_TX_TREE1674_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        # Compare every drawing layer to the exact v5 baseline that failed the
        # full-wire test; allow only the six external return rectangle unions.
        (OUT/'candidate-physical.json').write_text(json.dumps(dict(status='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE',return_rail=result['return_rail'],physical=result['physical']),indent=2)+'\n')
        run([app,'python',ROOT/'scripts/check_tx_v5_fast_stage_isolated_geometry.py',OUT],'exact-column-geometry')
        result['geometry_delta']=json.loads((OUT/'column-geometry-delta.json').read_text())
        assert result['geometry_delta']['status']=='PASS_FAST_STAGE_ROWS_FROZEN_CHILDREN_TOPOLOGY_AND_NATIVE_PLACEMENT'
        result['status']='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error))
        if (OUT/'physical/result.json').exists():result['physical']=json.loads((OUT/'physical/result.json').read_text())
        raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
