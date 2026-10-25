#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Whole-PD420 conductor graph and actual intrinsic terminal reference planes.

Pin annotations removed by the parent router are recovered only from an exactly
identical native primitive drawing in the pinned source child GDS. No target
geometry is edited, and no RC/electrical acceptance is inferred from bindings.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-retimed-hybrid-v2-wire-inputs'
TOP='nssoc_cdr_pd420_hybrid_tail_v2'
METALS=(8,10,30,50,67,126,134)
MODELS={'npn13G2','rppd','ptap1','cmim','nmos'}

def recover():
    import pya
    parent=OUT/'parent';G=parent/'layout'/(TOP+'.gds')
    def signature(layout,cell):
        drawing=[]
        for idx in layout.layer_indexes():
            info=layout.get_info(idx)
            if info.layer in METALS and info.datatype in (2,25):continue
            reg=pya.Region(cell.begin_shapes_rec(idx)).merged()
            if not reg.is_empty():drawing.append((info.layer,info.datatype,sorted(p.to_s()for p in reg.each())))
        assert drawing
        return hashlib.sha256(json.dumps(sorted(drawing),separators=(',',':')).encode()).hexdigest()
    sources={};inputs={}
    for path in sorted((parent/'inputs').rglob('*.gds')):
        inputs[str(path)]=sha(path);L=pya.Layout();L.read(str(path));assert L.dbu==.001
        for c in L.each_cell():
            kind=c.name.split('$')[0]
            if kind not in MODELS or list(c.each_inst()):continue
            pins=[]
            for m in METALS:
                pins.extend([m,[s.box.left,s.box.bottom,s.box.right,s.box.top]]for s in c.each_shape(L.layer(m,2))if s.is_box())
            if not pins:continue
            key=(kind,signature(L,c));row=dict(source=str(path),cell=c.name,pins=sorted(pins),drawing_sha256=key[1])
            if key in sources:assert sources[key]['pins']==row['pins'],'Identical drawing has inconsistent source annotation'
            else:sources[key]=row
    L=pya.Layout();L.read(str(G));mapped={}
    for c in L.each_cell():
        kind=c.name.split('$')[0]
        if kind not in MODELS or list(c.each_inst()):continue
        key=(kind,signature(L,c))
        if kind=='cmim':continue # Its intrinsic plates are bound directly from actual drawing.
        assert key in sources,(c.name,key)
        mapped[c.name]=sources[key]
    assert mapped and {c.split('$')[0]for c in mapped}==MODELS-{'cmim'}
    r=dict(status='PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING',cells=mapped,inputs=inputs,target_gds_sha256=sha(G),target_geometry_edited=False)
    (OUT/'wire/source-pins.json').write_text(json.dumps(r,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--recover',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.recover:recover();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,wire_rc_extracted=False,full_phy_accepted=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,label):
        log=OUT/(label+'.log')
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert rc==0,(label,rc)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-hybrid420-parent-physical-pass-20261018.json').read_text())
        prior,proof=reports.restore_report('cdr-retimed-hybrid-v2-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',list(pin['report']['outputs']))
        assert prior==pin['report']and prior['sources_unchanged'];r['physical_source']=proof
        plane=json.loads((ROOT/'docs/evidence/cdr-retimed-hybrid-v2-planes-pass-20261018.json').read_text())
        assert plane['report']['physical_source']['summary_sha256']==pin['summary_sha256']
        assert plane['report']['native_planes']['native_terminal_count']==1186
        observed,plane_proof=reports.restore_report('cdr-retimed-hybrid-v2-planes',plane['run'],plane['summary_sha256'],plane['parts_sha256'],OUT/'planes',['native-planes.json'])
        assert observed==plane['report'] and observed['sources_unchanged']
        assert json.loads((OUT/'planes/native-planes.json').read_text())==observed['native_planes']
        r['plane_source']=plane_proof
        methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
        wire=OUT/'wire';wire.mkdir();adaptations={}
        for name in ('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            original=methods[name]['text'];assert hashlib.sha256(original.encode()).hexdigest()==methods[name]['sha256']
            text=original;changes=[]
            def replace(a,b):
                nonlocal text
                assert text.count(a)==1,(name,a,text.count(a));text=text.replace(a,b);changes.append(dict(before=a,after=b))
            if name!='dedup01.py':
                for old,new in [("/'layout91/","/'parent/layout/"),("/'physical92/lvs/","/'parent/physical/lvs_flat/")]:
                    count=text.count(old);assert count>=1,(name,old)
                    text=text.replace(old,new);changes.append(dict(before=old,after=new,count=count))
                replace('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP)
            if name in ('locate01.py','anchors01.py'):
                replace("('sg13_hv_nmos','B')", "('sg13_lv_nmos','B'),('sg13_hv_nmos','B')")
            if name=='anchors01.py':
                replace("elif cls.name in ('sg13_hv_nmos','sg13_hv_pmos'):", "elif cls.name in ('sg13_lv_nmos','sg13_hv_nmos','sg13_hv_pmos'):")
            if name=='probe01.py':
                replace('c.pin_count()==12','c.pin_count()==25')
                replace('dict(npn13G2=19,rppd=8,ptap1=27)','dict(npn13G2=100,sg13_lv_nmos=22,rppd=102,cap_cmim=11,ptap1=185)')
                # A second layout path occurs in the source hash binding.
                text=text.replace("P/'layout91/result.json'","P/'parent/layout/result.json'")
            if name=='locate01.py':
                replace("models=dict(npn13G2='npn13G2',rppd='rppd',ptap1='ptap1')","models=dict(npn13G2='npn13G2',rppd='rppd',ptap1='ptap1',cmim='cap_cmim',nmos='sg13_lv_nmos')")
                replace('len(physical)==54','len(physical)==420');replace('len(used)==54','len(used)==420');replace('PASS_ALL_54_DEVICES','PASS_ALL_420_DEVICES')
            if name=='anchors01.py':
                replace('geo=json.loads',"recovered=json.loads((B/'source-pins.json').read_text())['cells']\ngeo=json.loads")
                start=text.index(' pins=[]\n for idx in g.layer_indices():');end=text.index(' for td in cls.terminal_definitions():',start)
                old=text[start:end]
                replace(old," localpins=[(m,pya.Box(*b))for m,b in recovered.get(cell.name,{}).get('pins',[])]\n pins=[(m,b.transformed(tr))for m,b in localpins if m in mapping]\n")
                replace("local=[s.box for s in cell.each_shape(g.layer(8,2))if s.is_box()]","local=[b for m,b in localpins if m==8]")
                replace("emitter=[s.box for s in cell.each_shape(g.layer(10,2))if s.is_box()]","emitter=[b for m,b in localpins if m==10]")
                # The same source path is also recorded in the input list.
                text=text.replace("P/'layout91/result.json'","P/'parent/layout/result.json'")
                replace('len(rows)==154 and len(anchors)==112','len(rows)==1186 and len(anchors)==802')
                replace('PASS_154_NATIVE_TERMINALS_WITH_100_METAL_AND_54_BODY_REFERENCES','PASS_1186_NATIVE_TERMINALS_WITH_777_METAL_AND_409_BODY_REFERENCES')
                replace('public_ports=12','public_ports=25')
            if name=='dedup01.py':replace('len(anchors)>12','len(anchors)>25')
            (wire/name).write_text(text);adaptations[name]=dict(original_sha256=methods[name]['sha256'],adapted_sha256=sha(wire/name),changes=changes)
        r['method_adaptations']=adaptations;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        run([app,'python',Path(__file__),'--recover'],'source-annotation-recovery')
        r['recovered_annotations']=json.loads((wire/'source-pins.json').read_text());save()
        for name in adaptations:run([app,'python',wire/name],name)
        r['geometry']=json.loads((wire/'native05/result.json').read_text())
        r['devices']=json.loads((wire/'device-locations01.json').read_text())
        r['anchors']=json.loads((wire/'anchors08.json').read_text());save()
        assert r['geometry']['native_device_count']==420 and r['geometry']['native_terminal_count']==1186
        assert r['anchors']['logical_anchor_count']==802 and r['anchors']['public_ports']==25
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=777,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=409)
        assert all(sha(OUT/'parent'/n)==v for n,v in prior['outputs'].items())
        assert all(sha(wire/n)==v['adapted_sha256']for n,v in adaptations.items())
        r['sources_unchanged']=True;r['status']='PASS_PD420_WHOLE_METAL_GRAPH_AND_ACTUAL_TERMINAL_ANCHORS_REQUIRES_FRESH_RC'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
