#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace both real PLL divider GDS instances and run full845 DRC/LVS plus faults."""
import argparse,json,os,re,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-divider-v2-layout'
OLDTOP='nssoc_pll845_rhi140_c9_pbuf10_pfd94d2_development_v1'
TOP='nssoc_pll845_divider3p2_v2_development'
CHILD='nssoc_clock_div4_load3p2_v2_layout'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'

def generate():
    import pya
    A=OUT/'integrated';A.mkdir();P=OUT/'parent';C=OUT/'child/layout'
    old=json.loads((P/'result.json').read_text());child=json.loads((C/'result.json').read_text())
    assert old['top']==OLDTOP and len(old['ports'])==17
    metas=[x for x in old['instances']if x['name']in ('div1','div2')]
    assert len(metas)==2 and {m['top']for m in metas}=={'nssoc_clock_div4_first28_layout'}
    oldchild=metas[0]['top']
    L=pya.Layout();L.read(str(P/(OLDTOP+'.gds')));T=L.cell(OLDTOP);assert T is not None
    G=pya.Layout();G.read(str(C/(CHILD+'.gds')));N=G.cell(CHILD);assert N is not None
    assert L.dbu==G.dbu==.001
    def shapes(layout,c):return sorted((str(layout.get_info(i)),str(s))for i in layout.layer_indices()for s in c.each_shape(i))
    def instances(c):return sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())
    original={c.name:(shapes(L,c),instances(c))for c in L.each_cell()}
    matches=[i for i in T.each_inst()if i.cell.name==oldchild];assert len(matches)==2
    bindings=[]
    for I in matches:
        position=[I.dcplx_trans.disp.x,I.dcplx_trans.disp.y]
        meta=next(m for m in metas if m['position_um']==position)
        assert set(child['ports'])==set(meta['ports'])and len(child['ports'])==7
        for pin,v in child['ports'].items():
            assert v['layer']=='Metal5'and meta['ports'][pin]['layer']==67
            actual=pya.DBox(*v['rect_um']).transformed(I.dcplx_trans)
            reference=meta['ports'][pin]['box_um']
            assert [round(x*1000)for x in [actual.left,actual.bottom,actual.right,actual.top]]==[round(x*1000)for x in reference],('Moved macro port',meta['name'],pin)
        bindings.append((I,meta,str(I.dbbox()),str(I.dcplx_trans)))
    for cell in G.each_cell():
        if cell.name!=CHILD:cell.name='div3p2v2_'+cell.name
    assert all(L.cell(c.name)is None for c in G.each_cell())
    G.write(str(A/'unique-child.gds'));L.read(str(A/'unique-child.gds'));N=L.cell(CHILD)
    for name,(ss,ii)in original.items():assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ii,name
    for li in G.layer_indices():
        assert (pya.Region(G.cell(CHILD).begin_shapes_rec(li))^pya.Region(N.begin_shapes_rec(L.layer(G.get_info(li))))).is_empty()
    for I,meta,bounds,transform in bindings:
        I.cell_index=N.cell_index();assert str(I.dcplx_trans)==transform and str(I.dbbox())==bounds
        meta['top']=CHILD;meta['bbox_um']=bounds
    T.name=TOP
    assert shapes(L,T)==original[OLDTOP][0]
    assert instances(T)==sorted((CHILD if row[0]==oldchild else row[0],*row[1:])for row in original[OLDTOP][1])
    for name,(ss,ii)in original.items():
        if name!=OLDTOP:assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ii,name
    s=(P/'schematic.cir').read_text();pattern=r'(?ms)^\.subckt '+re.escape(oldchild)+r' .*?^\.ends '+re.escape(oldchild)+r'\s*$'
    match=re.search(pattern,s);assert match and len(re.findall(pattern,s))==1
    ref=(C/'schematic.cir').read_text().strip();header=next(l for l in ref.splitlines()if l.startswith('.subckt '))
    assert match.group(0).splitlines()[0].split()[2:]==header.split()[2:]+['BULK']
    ref=ref.replace(header,header+' BULK',1)
    candidate=(s[:match.start()]+ref+'\n'+s[match.end():]).replace(oldchild,CHILD).replace(OLDTOP,TOP)
    assert len(re.findall(r'(?m)^Xdiv[12] .* '+re.escape(CHILD)+r'$',candidate))==2
    (A/'schematic.cir').write_text(candidate)
    load=next(l for l in ref.splitlines()if ' rppd 'in l and 'w=8u l=3.2u'in l)
    assert candidate.count(load)==1
    (A/'wrong-load.cir').write_text(candidate.replace(load,load.replace('l=3.2u','l=2.12u'),1))
    opt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index());L.write(str(A/(TOP+'.gds')),opt)
    li=L.layer(67,0);reg=pya.Region(N.shapes(li));port=child['ports']['QP']['rect_um']
    y=round((port[1]+port[3])/2/L.dbu);cut=pya.Box(4000,y-2000,8000,y+2000)
    assert not(reg&pya.Region(cut)).is_empty(),'Actual QP bus not at expected physical output escape'
    for shape in list(N.each_shape(li)):
        if not shape.is_text():shape.delete()
    N.shapes(li).insert(reg-pya.Region(cut));L.write(str(A/'divider-output-open.gds'),opt)
    old.update(top=TOP,status='GENERATED_BOTH_DIVIDER_V2_PARENT_REQUIRES_NATIVE_CHECKS',parent_drc_pass=False,parent_lvs_pass=False,closed_loop_accepted=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False)
    old['integration_proof']=dict(changed_macros=['div1','div2'],other_cell_shapes_and_instances_unchanged=True,parent_own_shapes_unchanged=True,all14_instance_ports_unchanged=True,divider_transforms_and_bboxes_unchanged=True,child_geometry_exact=True,expected_native_devices=845,reference='Standalone corrected v2 reference replaces old divider subcircuit with explicit common BULK. Full native comparison below is mandatory.')
    old['inputs']={str(p):sha(p)for p in [Path(__file__),P/'result.json',P/(OLDTOP+'.gds'),P/'schematic.cir',C/'result.json',C/(CHILD+'.gds'),C/'schematic.cir']}
    def physical(layout,t,li):
        reg=pya.Region();it=t.begin_shapes_rec(li)
        while not it.at_end():
            z=it.shape()
            if z.is_box()or z.is_polygon()or z.is_path():reg.insert(z.polygon.transformed(it.trans()))
            else:assert z.is_text()
            it.next()
        return reg.merged()
    for source,target in [(TOP+'.gds','flat.gds'),('divider-output-open.gds','divider-output-open-flat.gds')]:
        F=pya.Layout();F.read(str(A/source));U=F.cell(TOP)
        geometry={str(F.get_info(li)):physical(F,U,li)for li in F.layer_indices()}
        direct=sorted(z.text.string for li in F.layer_indices()for z in U.each_shape(li)if z.is_text());assert direct==sorted(old['ports'])
        allowed={x['top']:set(x['ports'])for x in old['instances']};removed=[]
        for name,ports in allowed.items():
            cell=F.cell(name);assert cell is not None,name
            for li in F.layer_indices():
                info=F.get_info(li)
                if info.datatype!=25 or info.layer not in [8,10,30,50,67,126,134]:continue
                for z in list(cell.each_shape(li)):
                    if z.is_text()and z.text.string in ports:removed.append((name,z.text.string));z.delete()
        assert len(removed)==sum(len(p)for p in allowed.values())
        for li in F.layer_indices():assert(geometry[str(F.get_info(li))]^physical(F,U,li)).is_empty()
        assert sorted(z.text.string for li in F.layer_indices()for z in U.each_shape(li)if z.is_text())==direct
        so=pya.SaveLayoutOptions();so.select_cell(U.cell_index());F.write(str(A/target),so)
    old['outputs']={p.name:sha(p)for p in A.iterdir()if p.is_file()}
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
    r=dict(status='RUNNING',inputs={str(p):v for p,v in pins.items()},steps={},expected_native_devices=845,qualified_pex=False,full_phy_accepted=False)
    def save():(D/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    for name in ('drc','lvs','lvs_flat','wrong_load','divider_output_open'):
        q=D/name;q.mkdir();step=r['steps'][name]={}
        try:
            gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/('divider-output-open-flat.gds' if name=='divider_output_open' else 'flat.gds')
            ref=A/('wrong-load.cir' if name=='wrong_load' else 'schematic.cir');typ='drc' if name=='drc' else 'lvs'
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
                    assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==845
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
    r['status']='PASS_ACTUAL845_DIVIDER_V2_PARENT_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_DIVIDER_V2_PARENT_NATIVE_CHECKS';save();assert passed
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False,scope='Both real corrected divider GDS instances inserted into actual845PLL. Preserve14instance ports, bboxes, transforms, parent wires and other macro geometry. Full native mainDRC/deep+flat845transistorLVS and wrong-load/output-cut faults. Fresh parent RC/planes and electrical acquisition remain separate requirements.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        packed=OUT/'restore.tar.gz'
        fetch(BASE+'cloud-results-38849617327-1-pll-filter-parent-9/pll-filter-parent-9-38849617327-1.tar.gz.part0000','04a31bfc2e4fafa5595f3f51d265f9fc299a1d930e30ac642f7bda71ef56059d',packed);assert packed.stat().st_size==1640383
        with tarfile.open(packed)as tar:
            names=['result.json','integrated/result.json','integrated/schematic.cir','integrated/'+OLDTOP+'.gds'];prefix='cloud-pll-filter-parent/'
            members=tar.getmembers();assert len(members)==len({m.name for m in members})
            for name in names:
                m=tar.getmember(prefix+name);assert m.isfile();dest=OUT/('parent-source.json'if name=='result.json'else'parent/'+name.split('/',1)[1]);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
        assert sha(OUT/'parent-source.json')=='e0b8195dc9b09a2c0825c4618b2112e0b347309ba9917fccc59aff4a429d4676'
        prior=json.loads((OUT/'parent-source.json').read_text());assert prior['status']=='PASS_REAL_FILTER_PARENT_DRC_LVS_REQUIRES_NEW_RC_AND_WAVES'
        assert sha(OUT/'parent'/(OLDTOP+'.gds'))=='28dc06bb9c729ecca1a49e457a787d1ac367960080cfcca6a7d6695623334b40'
        child,proof=reports.restore_report('pll-divider-load3p2v2-physical',38975762261,'f20bddda06c6d1765645de357ed50710127cc2af4bda3a796516bf31eb25124d','0566cf48bfdb598c0392a1598a6b07e21df7e1519911f53335422e14e97d0011',OUT/'child',('layout/result.json','layout/schematic.cir','layout/'+CHILD+'.gds'))
        assert child['status']=='PASS_DIVIDER_LOAD3P2V2_PARENT_FIRST_LOADS_RESTORED_NATIVE_PHYSICAL_SCREEN_REQUIRES_FRESH_RC_AND_ACQUISITION'
        assert sha(OUT/'child/layout'/(CHILD+'.gds'))=='265d5245f5b406aa20c20647afbe9d87ad9e8f1493cfe3cae3fed9d64885a71b'
        r['child_source']=proof;save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app);save()
        with(OUT/'generate.log').open('w')as log:code=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--generate'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'generate.log').read_text()[-12000:],flush=True)
        assert code==0,'Both-divider parent geometry generation failed'
        r['integrated']=json.loads((OUT/'integrated/result.json').read_text());save()
        r['physical']=verify(app)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r['status']='PASS_REAL_BOTH_DIVIDER_V2_PARENT_DRC_LVS_REQUIRES_PARENT_RC_PLANES_AND_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for k in ('integrated','physical'):
            q=OUT/k/'result.json'
            if q.exists():r[k]=json.loads(q.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
