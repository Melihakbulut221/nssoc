#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Integrate a real filter candidate into the actual845 PLL; never PHY acceptance."""
import argparse,copy,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-filter-parent'
OLDTOP='nssoc_pll845_rhi140_pbuf10_pfd94d2_development_v1'
TOP='nssoc_pll845_rhi140_c9_pbuf10_pfd94d2_development_v1'
CHILD='nssoc_pump_filter13_rhi140_c9_v1'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'

def generate():
    import pya
    A=OUT/'integrated';A.mkdir()
    P=OUT/'parent';C=OUT/'child/layout'
    old=json.loads((P/'result.json').read_text());child=json.loads((C/'result.json').read_text())
    assert old['top']==OLDTOP and len(old['ports'])==17
    meta=next(x for x in old['instances'] if x['name']=='pump');oldchild=meta['top']
    assert oldchild.startswith('nssoc_pump_filter13_rhi140')
    L=pya.Layout();L.read(str(P/(OLDTOP+'.gds')));T=L.cell(OLDTOP);assert T is not None
    G=pya.Layout();G.read(str(C/(CHILD+'.gds')));N=G.cell(CHILD);assert N is not None
    assert L.dbu==G.dbu==.001
    def shapes(layout,c):return sorted((str(layout.get_info(i)),str(s)) for i in layout.layer_indices() for s in c.each_shape(i))
    def instances(c):return sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in c.each_inst())
    original={c.name:(shapes(L,c),instances(c)) for c in L.each_cell()}
    matches=[i for i in T.each_inst() if i.cell.name==oldchild];assert len(matches)==1;I=matches[0]
    oldbounds=str(I.dbbox());oldtransform=str(I.dcplx_trans)
    assert set(child['ports'])==set(meta['ports']) and len(child['ports'])==7
    for pin,bounds in child['ports'].items():
        coords=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',bounds)));assert len(coords)==4
        actual=pya.DBox(*coords).transformed(I.dcplx_trans)
        reference=meta['ports'][pin]['box_um']
        assert [round(v*1000) for v in [actual.left,actual.bottom,actual.right,actual.top]]==[round(v*1000) for v in reference], ('Moved macro port',pin,actual,reference)
    # Copy into a fresh namespace. Never overwrite existing PCells or macros.
    for cell in G.each_cell():
        if cell.name!=CHILD:cell.name='filter9_'+cell.name
    assert all(L.cell(c.name) is None for c in G.each_cell())
    G.write(str(A/'unique-child.gds'));L.read(str(A/'unique-child.gds'));N=L.cell(CHILD)
    for name,(ss,ii) in original.items():assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ii,name
    for li in G.layer_indices():
        assert (pya.Region(G.cell(CHILD).begin_shapes_rec(li))^pya.Region(N.begin_shapes_rec(L.layer(G.get_info(li))))).is_empty()
    I.cell_index=N.cell_index();assert str(I.dcplx_trans)==oldtransform and str(I.dbbox())==oldbounds
    T.name=TOP
    assert shapes(L,T)==original[OLDTOP][0]
    assert instances(T)==sorted((CHILD if row[0]==oldchild else row[0],*row[1:]) for row in original[OLDTOP][1])
    for name,(ss,ii) in original.items():
        if name!=OLDTOP:assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ii,name
    s=(P/'schematic.cir').read_text();pattern=r'(?ms)^\.subckt '+re.escape(oldchild)+r' .*?^\.ends '+re.escape(oldchild)+r'\s*$'
    match=re.search(pattern,s);assert match and len(re.findall(pattern,s))==1
    ref=(C/'schematic.cir').read_text().strip();header=next(l for l in ref.splitlines() if l.startswith('.subckt '))
    oldports=match.group(0).splitlines()[0].split()[2:]
    assert oldports==header.split()[2:]+['BULK']
    ref=ref.replace(header,header+' BULK',1)
    def cards(text):return [l.lower().split() for l in text.splitlines() if l.strip() and not l.startswith(('*','.'))]
    before=cards(match.group(0));after=cards(ref);assert len(before)==len(after)==30
    delta=[(a,b) for a,b in zip(before,after,strict=True) if a!=b];assert len(delta)==1
    a,b=delta[0];assert 'cap_cmim' in a and 'w=10u' in a and 'l=10u' in a
    assert b==[{'w=10u':'w=9u','l=10u':'l=9u'}.get(v,v) for v in a]
    candidate=s[:match.start()]+ref+'\n'+s[match.end():]
    candidate=candidate.replace(oldchild,CHILD).replace(OLDTOP,TOP)
    expected_line='Xpump up down vctrl vco_avdd div_avdd avss sub avss '+CHILD
    assert expected_line in candidate
    (A/'schematic.cir').write_text(candidate)
    cap=next(l for l in ref.splitlines() if ' cap_cmim ' in l);assert cap.count('w=9u l=9u')==1
    wrong=ref.replace(cap,cap.replace('w=9u l=9u','w=10u l=9u'),1)
    assert candidate.count(ref)==1
    (A/'wrong-cap.cir').write_text(candidate.replace(ref,wrong,1))
    opt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index());L.write(str(A/(TOP+'.gds')),opt)
    labels={z.text.string:z.text.y for z in N.each_shape(L.layer(67,25)) if z.is_text()};assert 'vctrl' in labels
    y=labels['vctrl'];bus=[z for z in N.each_shape(L.layer(67,0)) if z.is_box() and z.box.left==0 and z.box.top+z.box.bottom==2*y]
    assert len(bus)==1;cut=bus[0].box;bus[0].delete();L.write(str(A/'vctrl-open.gds'),opt);N.shapes(L.layer(67,0)).insert(cut)
    meta['top']=CHILD;meta['bbox_um']=oldbounds
    old.update(top=TOP,status='GENERATED_FILTER_PARENT_REQUIRES_NATIVE_CHECKS',parent_drc_pass=False,parent_lvs_pass=False,closed_loop_accepted=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False)
    old['integration_proof']=dict(only_changed_macro='pump',other_cell_shapes_and_instances_unchanged=True,parent_own_shapes_unchanged=True,all7ports_unchanged=True,pump_transform_unchanged=True,pump_bbox_unchanged=True,only_intrinsic_change=delta,expected_native_devices=845)
    old['inputs']={str(p):sha(p) for p in [Path(__file__),P/'result.json',P/(OLDTOP+'.gds'),P/'schematic.cir',C/'result.json',C/(CHILD+'.gds'),C/'schematic.cir']}
    def physical(layout,t,li):
        reg=pya.Region();it=t.begin_shapes_rec(li)
        while not it.at_end():
            z=it.shape()
            if z.is_box() or z.is_polygon() or z.is_path():reg.insert(z.polygon.transformed(it.trans()))
            else:assert z.is_text()
            it.next()
        return reg.merged()
    for source,target in [(TOP+'.gds','flat.gds'),('vctrl-open.gds','vctrl-open-flat.gds')]:
        F=pya.Layout();F.read(str(A/source));U=F.cell(TOP)
        geometry={str(F.get_info(li)):physical(F,U,li) for li in F.layer_indices()}
        direct=sorted(z.text.string for li in F.layer_indices() for z in U.each_shape(li) if z.is_text());assert direct==sorted(old['ports'])
        allowed={x['top']:set(x['ports']) for x in old['instances']};removed=[]
        for name,ports in allowed.items():
            cell=F.cell(name);assert cell is not None,name
            for li in F.layer_indices():
                info=F.get_info(li)
                if info.datatype!=25 or info.layer not in [8,10,30,50,67,126,134]:continue
                for z in list(cell.each_shape(li)):
                    if z.is_text() and z.text.string in ports:removed.append((name,z.text.string));z.delete()
        assert len(removed)==sum(len(p) for p in allowed.values())
        for li in F.layer_indices():assert (geometry[str(F.get_info(li))]^physical(F,U,li)).is_empty()
        assert sorted(z.text.string for li in F.layer_indices() for z in U.each_shape(li) if z.is_text())==direct
        so=pya.SaveLayoutOptions();so.select_cell(U.cell_index());F.write(str(A/target),so)
    old['outputs']={p.name:sha(p) for p in A.iterdir() if p.is_file()}
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
    for name in ('drc','lvs','lvs_flat','wrong_cap','vctrl_open'):
        q=D/name;q.mkdir();step=r['steps'][name]={}
        try:
            gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/('vctrl-open-flat.gds' if name=='vctrl_open' else 'flat.gds')
            ref=A/('wrong-cap.cir' if name=='wrong_cap' else 'schematic.cir');typ='drc' if name=='drc' else 'lvs'
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
    r['status']='PASS_ACTUAL845_FILTER_PARENT_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_FILTER_PARENT_NATIVE_CHECKS';save();assert passed
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],size_um=9,accepted=False,qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False,
        scope='Real candidate pump in original845device PLL parent. Exact nonpump geometry and parent wires/port positions must remain unchanged. Fresh parent DRC/deep+flat transistor LVS/actual width and open faults. New RC and physically matched electrical acquisition still required.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        packed=OUT/'restore.tar.gz'
        fetch(BASE+'cloud-results-38672085461-1-pll-pfd-layout/pfd94-layout-38672085461-1.tar.gz','ff8837dce9298abd8cb649eceb5b86dcd8e48454d7175002096b4b5b80a4205b',packed);assert packed.stat().st_size==11295468
        with tarfile.open(packed) as tar:
            prefix='hw/soc/out/cloud-pfd-layout/';names=['result.json','integrated/result.json','integrated/schematic.cir','integrated/'+OLDTOP+'.gds']
            members=tar.getmembers();assert len(members)==len({m.name for m in members})
            for name in names:
                m=tar.getmember(prefix+name);assert m.isfile();dest=OUT/('parent-source.json' if name=='result.json' else 'parent/'+name.split('/',1)[1]);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
        assert sha(OUT/'parent-source.json')=='22cae097bdb7c2a3fa77abaad4ebeff772fb08c1769c1e4fc10664f90f1e6f35'
        assert sha(OUT/'parent/schematic.cir')=='6de9c745fa2911ce732d1f772b28ac8147b476690d97152266c3554bd02d800d'
        parent=json.loads((OUT/'parent/result.json').read_text());assert sha(OUT/'parent'/(OLDTOP+'.gds'))==parent['outputs'][OLDTOP+'.gds']
        fetch(BASE+'cloud-results-38848309907-1-pll-filter-layout-9/pll-filter-layout-9-38848309907-1.tar.gz.part0000','2a8e067beb6b2598a3eab4bc88d79acf0b5a5e8cb4a2f26a214a36c0629297cf',packed);assert packed.stat().st_size==248708
        with tarfile.open(packed) as tar:
            prefix='cloud-pll-filter-layout/';names=['result.json','layout/result.json','layout/schematic.cir','layout/'+CHILD+'.gds','layout/'+CHILD+'.lef']
            members=tar.getmembers();assert len(members)==len({m.name for m in members})
            for name in names:
                m=tar.getmember(prefix+name);assert m.isfile();dest=OUT/'child'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
        assert sha(OUT/'child/result.json')=='ae90bac4182e79be42f41aedea9605ade46d2f80b5a127c7f38f7b25534ba0ad'
        child=json.loads((OUT/'child/result.json').read_text());assert child['physical']['status']=='PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(OUT/'child/layout'/n)==v for n,v in child['layout']['outputs'].items())
        fetch(BASE+'cloud-results-38848974954-1-pll-filter-lef-9/pll-filter-lef-9-38848974954-1.summary.json','c9063e0252331b4c7a8281784b36cb55dd470505db53bd92689dc6adc34fad24',OUT/'child-lef.json')
        lef=json.loads((OUT/'child-lef.json').read_text());assert lef['status']=='PASS_RESTORED_PUMP_LEF_WITH_PRIOR_DRC_LVS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
        assert lef['source_evidence']['layout_outputs']==child['layout']['outputs']
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app);save()
        with (OUT/'generate.log').open('w') as log:code=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--generate'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'generate.log').read_text()[-12000:],flush=True)
        assert code==0,'Parent geometry generation failed'
        r['integrated']=json.loads((OUT/'integrated/result.json').read_text());save()
        r['physical']=verify(app)
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        r['status']='PASS_REAL_FILTER_PARENT_DRC_LVS_REQUIRES_NEW_RC_AND_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for k in ('integrated','physical'):
            q=OUT/k/'result.json'
            if q.exists():r[k]=json.loads(q.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
