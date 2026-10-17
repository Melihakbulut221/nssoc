#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route actual XOR cross-connections around the proven shunt-v4 CDR core.

Physical evidence only; new RC and loaded waveforms remain mandatory.
"""
import argparse,json,os,re,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-v4-parent'
CORE='nssoc_cdr_xor_load_core_layout_v4'
TOP='nssoc_cdr_xor_load_parent_v4'
PORTS=['dp','dn','ep','en','qp','qn','avdd','avss','sub','iref']
MAP=dict(ap='dp',an='dn',bp='dn',bn='dp',sp='ep',sn='en',op='qn',on='qp',avdd='avdd',avss='avss',sub='sub',iref='iref')

def generate():
    import pya
    A=OUT/'integrated';A.mkdir()
    P=OUT/'core/layout'
    m=json.loads((P/'result.json').read_text())
    assert set(m['ports'])==set(MAP)
    assert m['ports']=={'sp': '(342.985,133.64;344.985,134.84)', 'sn': '(342.985,141.64;344.985,142.84)', 'op': '(0,69.64;2,70.84)', 'on': '(0,77.64;2,78.84)', 'ap': '(0,241.64;2,242.84)', 'an': '(0,248.64;2,249.84)', 'bp': '(0,255.64;2,256.84)', 'bn': '(0,262.64;2,263.84)', 'iref': '(342.985,269.64;344.985,270.84)', 'avdd': '(0,292.64;2,293.84)', 'avss': '(0,329.64;2,330.84)', 'sub': '(0,352.64;2,353.84)'}, 'Fresh v4 pin coordinates changed; inspect before routing'
    L=pya.Layout();L.read(str(P/(CORE+'.gds')));C=L.cell(CORE)
    assert C is not None and L.dbu==.001 and str(C.dbbox())=='(0,0;344.985,355.24)'
    def snapshot(c):
        return (sorted((str(L.get_info(i)),str(s))for i in L.layer_indices()for s in c.each_shape(i)),
                sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst()))
    original={c.name:snapshot(c)for c in L.each_cell()}
    T=L.create_cell(TOP);T.insert(pya.CellInstArray(C.cell_index(),pya.Trans(40000,0)))
    pins={}
    for n,b in m['ports'].items():
        v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',b)));assert len(v)==4
        pins[n]=pya.DBox(v[0]+40,v[1],v[2]+40,v[3])
    routes=[];trunks={}
    def box(layer,b,net,kind):
        s=T.shapes(L.layer(layer,0)).insert(b)
        routes.append(dict(net=net,layer=layer,box_um=[b.left,b.bottom,b.right,b.top],kind=kind))
        return s
    def wire(a,b,layer,net):
        assert a[0]==b[0]or a[1]==b[1]
        return box(layer,pya.DBox(min(a[0],b[0])-1,min(a[1],b[1])-1,max(a[0],b[0])+1,max(a[1],b[1])+1),net,'wire')
    def via(x,y,net):
        # Native IHP TV2.a/c/d:0.9um cut with>=0.5um enclosure on both2um metals.
        for layer in (126,134):box(layer,pya.DBox(x-1,y-1,x+1,y+1),net,'via_landing')
        box(133,pya.DBox(x-.45,y-.45,x+.45,y+.45),net,'topvia2')
    portboxes={}
    def label(net,b):
        assert net not in portboxes
        T.shapes(L.layer(134,2)).insert(b)
        T.shapes(L.layer(134,25)).insert(pya.DText(net,b.center().x,b.center().y))
        portboxes[net]=str(b)
    # The external trunks sit in the empty left channel, outside ALL source geometry.
    for net,names,x in [('dp',('ap','bn'),12.0),('dn',('an','bp'),24.0)]:
        ys=[pins[n].center().y for n in names]
        trunks[net]=wire((x,min(ys)),(x,max(ys)),126,net)
        for n,y in zip(names,ys,strict=True):
            wire((x,y),(pins[n].center().x,y),134,net);via(x,y,net)
        box(134,pya.DBox(0,ys[0]-1,x+1,ys[0]+1),net,'public_access')
        label(net,pya.DBox(0,ys[0]-1,2,ys[0]+1))
    for n in ('sp','sn','op','on','avdd','avss','sub','iref'):
        net=MAP[n];b=pins[n];y=b.center().y
        if b.left==40:
            box(134,pya.DBox(0,y-1,b.right,y+1),net,'public_access')
            label(net,pya.DBox(0,y-1,2,y+1))
        else:
            assert b.right==384.985
            label(net,b)
    assert set(portboxes)==set(PORTS)and len(routes)==25
    assert all(snapshot(L.cell(n))==v for n,v in original.items()),'Source core geometry changed'
    assert len(list(T.each_inst()))==1
    ref=(P/'schematic.cir').read_text()
    headers=[l.split()for l in ref.splitlines()if l.lower().startswith('.subckt ')]
    assert len(headers)==1 and headers[0][1]==CORE and set(headers[0][2:])==set(MAP),headers
    coreports=headers[0][2:]
    actual='XCORE '+' '.join(MAP[p]for p in coreports)+' '+CORE
    wrapper='\n.subckt '+TOP+' '+' '.join(PORTS)+'\n'+actual+'\n.ends '+TOP+'\n'
    # Independently bind the intrinsic model's fixed pin order and output polarity.
    native=(ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_shunt_v4.spice').read_text()
    assert 'XCORE sub dp dn dn dp iref ep en qp qn avss avdd nssoc_cdr_xor_core_shunt_v4' in native
    (A/'schematic.cir').write_text(ref+'\n'+wrapper)
    swap='XCORE '+' '.join({'qp':'qn','qn':'qp'}.get(MAP[p],MAP[p])for p in coreports)+' '+CORE
    assert swap!=actual
    (A/'output-swap.cir').write_text(ref+'\n'+wrapper.replace(actual,swap))
    opt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index());L.write(str(A/(TOP+'.gds')),opt)
    # Actual conductor faults, not a changed expected verdict or label-only mutation.
    trunk=trunks['dp'].box;trunks['dp'].delete();L.write(str(A/'dp_open.gds'),opt)
    T.shapes(L.layer(126,0)).insert(trunk)
    bridge=box(126,pya.DBox(11,251,25,253),'FAULT_DP_DN','fault_bridge')
    L.write(str(A/'data_short.gds'),opt);bridge.delete();routes.pop()
    assert all(snapshot(L.cell(n))==v for n,v in original.items())
    def physical(layout,c,li):
        reg=pya.Region();it=c.begin_shapes_rec(li)
        while not it.at_end():
            z=it.shape()
            if z.is_box()or z.is_polygon()or z.is_path():reg.insert(z.polygon.transformed(it.trans()))
            else:assert z.is_text()
            it.next()
        return reg.merged()
    # Flat deck input suppresses ONLY original12 child labels; preserve ALL polygons.
    for source,target in [(TOP+'.gds','flat.gds'),('dp_open.gds','dp_open-flat.gds'),('data_short.gds','data_short-flat.gds')]:
        F=pya.Layout();F.read(str(A/source));U=F.cell(TOP);child=F.cell(CORE)
        geometry={str(F.get_info(li)):physical(F,U,li)for li in F.layer_indices()}
        removed=[]
        for li in F.layer_indices():
            info=F.get_info(li)
            if info.layer==134 and info.datatype==25:
                for z in list(child.each_shape(li)):
                    if z.is_text()and z.text.string in MAP:removed.append(z.text.string);z.delete()
        assert sorted(removed)==sorted(MAP)
        for li in F.layer_indices():assert (geometry[str(F.get_info(li))]^physical(F,U,li)).is_empty()
        direct=[s.text.string for li in F.layer_indices()for s in U.each_shape(li)if s.is_text()]
        assert sorted(direct)==sorted(PORTS)
        so=pya.SaveLayoutOptions();so.select_cell(U.cell_index());F.write(str(A/target),so)
    # Explicit parent LEF candidate. Native LEF integration is a separate required gate.
    width,height=T.dbbox().width(),T.dbbox().height()
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {TOP}','  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {width:.3f} BY {height:.3f} ;','  SYMMETRY X Y ;']
    for n in PORTS:
        b=pya.DBox.from_s(portboxes[n]);direction='OUTPUT'if n in ('qp','qn')else('INOUT'if n in ('avdd','avss','sub')else'INPUT')
        use='POWER'if n=='avdd'else('GROUND'if n in ('avss','sub')else'SIGNAL')
        lef += [f'  PIN {n}',f'    DIRECTION {direction} ;',f'    USE {use} ;','    PORT','      LAYER TopMetal2 ;',f'      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;','    END',f'  END {n}']
    lef += ['  OBS']
    for layer in ['Metal1','Metal2','Metal3','Metal4','Metal5','TopMetal1']:
        lef += [f'    LAYER {layer} ;',f'    RECT 0 0 {width:.3f} {height:.3f} ;']
    # Subtract pin access rectangles from the top-metal obstruction.
    obs=pya.Region(T.bbox())
    for b in portboxes.values():obs-=pya.Region(pya.DBox.from_s(b).to_itype(.001))
    lef+=['    LAYER TopMetal2 ;']
    for poly in obs.decompose_trapezoids_to_region().each():
        b=poly.bbox().to_dtype(.001)
        lef += [f'    RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;']
    lef+=['  END',f'END {TOP}','END LIBRARY'];(A/(TOP+'.lef')).write_text('\n'.join(lef)+'\n')
    result=dict(status='GENERATED_REAL_XOR_PARENT_REQUIRES_NATIVE_GATES',top=TOP,ports=portboxes,core_port_map=MAP,routes=routes,
        core_shape_and_instance_snapshot_unchanged=True,core_offset_um=[40,0],expected_native_devices=54,
        inputs={str(p):sha(p)for p in [Path(__file__),P/'result.json',P/(CORE+'.gds'),P/'schematic.cir',ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_shunt_v4.spice']},
        qualified_pex=False,full_phy_accepted=False,lef_native_verified=False)
    result['outputs']={p.name:sha(p)for p in A.iterdir()if p.is_file()}
    (A/'result.json').write_text(json.dumps(result,indent=2)+'\n')

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
    r=dict(status='RUNNING',inputs={str(p):v for p,v in pins.items()},steps={},expected_native_devices=54,qualified_pex=False,full_phy_accepted=False)
    def save():(D/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    for name in ('drc','lvs','lvs_flat','dp_open','data_short','output_swap'):
        q=D/name;q.mkdir();step=r['steps'][name]={}
        try:
            gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/(name+'-flat.gds' if name in ('dp_open','data_short') else 'flat.gds')
            ref=A/('output-swap.cir' if name=='output_swap' else 'schematic.cir');typ='drc' if name=='drc' else 'lvs'
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
                    assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==54
                    rows=[]
                    for raw in (q/'extracted.cir').read_text().splitlines():
                        l=raw.strip()
                        if l.startswith('+'):assert rows;rows[-1]+=' '+l[1:].strip()
                        elif l and not l.startswith('*'):rows.append(l)
                    headers=[l.split() for l in rows if l.lower().startswith('.subckt ')]
                    assert len({x[1].lower() for x in headers})==len(headers)
                    ports=[x[2:] for x in headers if x[1]==TOP];assert len(ports)==1 and len(ports[0])==10 and set(ports[0])==set(g['ports'])
                else:
                    assert step['audit_execution']['returncode']==1 and a['status']=='FAIL' and 'Deck explicitly reported a mismatch' in a['reasons']
            step['status']='PASS' if name in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT'
        except BaseException as e:step.update(status='FAILED',error=repr(e))
        save();print(name,step['status'],flush=True)
    assert all(digest(p)==v for p,v in pins.items())
    passed=all(s['status'] in ('PASS','REJECTED_EXPECTED_FAULT') for s in r['steps'].values())
    r['status']='PASS_CDR_XOR_PARENT54_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_CDR_XOR_PARENT_NATIVE_CHECKS';save();assert passed
    return r

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,cdr_accepted=False,full_phy_accepted=False,qualified_pex=False,main_chip_integrated=False,
        scope='Actual metal/via XOR crossed parent around unchanged54device shunt-v4 core. Native560category DRC, deep/flat transistor LVS and actual open/short/output-polarity controls. Fresh parent RC, loaded waveforms, sampled phase detector, complete CDR/serialPHY and mainchip integration remain required.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-v4-core-physical-pass-20261017.json').read_text())
        prior,proof=reports.restore_report('cdr-v4-core-layout',pin['source_run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'core',
            ['layout/result.json','layout/schematic.cir','layout/'+CORE+'.gds','layout/'+CORE+'.lef'])
        assert prior==pin['report']and prior['sources_unchanged']and prior['physical']['status']=='PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
        r['core_source']=proof
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'runtime.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        r['method_hashes']={str(p):sha(p)for p in [Path(__file__),ROOT/'scripts/compare_cloud_routed_endpoints.py',ROOT/'scripts/run_cloud_tx_layout_repair.py']};save()
        with (OUT/'generate.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--generate'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'generate.log').read_text()[-16000:],flush=True)
        assert rc==0,'Actual parent generation failed'
        r['integrated']=json.loads((OUT/'integrated/result.json').read_text());save()
        r['physical']=verify(app)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(Path(p))==v for p,v in r['method_hashes'].items())
        r['sources_unchanged']=True;r['status']='PASS_CDR_XOR_PARENT_PHYSICAL_REQUIRES_FRESH_RC_LOADED_WAVES_AND_CDR'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for k in ('integrated','physical'):
            p=OUT/k/'result.json'
            if p.exists():r[k]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
