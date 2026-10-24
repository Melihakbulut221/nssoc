#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual failed LVS clusters without accepting or editing the geometry."""
import argparse,json,os,re,subprocess
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent-lvs-review'
TOP='nssoc_cdr_pd500_active_input_v57'
def native():
    import pya
    source=OUT/'source';g=json.loads((source/'layout/result.json').read_text())
    audit=json.loads((source/'physical/lvs/audit.json').read_text())
    assert audit['status']=='FAIL' and not audit['extraction_diagnostics']
    assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
    L=pya.Layout();L.read(str(source/'layout'/(TOP+'.gds')));T=L.cell(TOP);assert T is not None
    db=pya.LayoutVsSchematic();db.read(str(source/'physical/lvs/result.lvsdb'));c=db.netlist().top_circuit();assert c.name==TOP
    census=dict(Counter(d.device_class().name.lower()for d in c.each_device()));assert census==g['primitive_census']==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    layers={}
    for metal in (67,134):
        full=pya.Region(T.begin_shapes_rec(L.layer(metal,0))).merged()
        hits=[i for i in db.layer_indexes()if(db.layer_by_index(i)^full).is_empty()]
        assert len(hits)==1,(metal,hits);layers[metal]=db.layer_by_index(hits[0])
    rows=[]
    def bind(label,raw,metal,net):
        values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(values)==4
        point=pya.DBox(*values).to_itype(L.dbu).center();n=db.probe_net(layers[metal],point)
        rows.append(dict(label=label,logical_net=net,point_dbu=[point.x,point.y],metal=metal,native_cluster=None if n is None else n.cluster_id,native_name=None if n is None else n.name))
    plan=g['source_plan']
    for node in plan['nodes']:
        for pin,net in node['pins'].items():bind('A_'+node['tag']+'_'+pin,g['placements'][node['tag']]['ports'][pin],plan['types'][node['kind']]['layer'],net)
    for port,raw in g['ports'].items():bind('P_'+port,raw,134,port)
    assert len(rows)==160
    clusters={};nets={}
    for r in rows:
        clusters.setdefault(str(r['native_cluster']),[]).append(r)
        nets.setdefault(r['logical_net'],set()).add(r['native_cluster'])
    shorted={k:v for k,v in clusters.items()if len({r['logical_net']for r in v})>1}
    opened={k:sorted(v,key=lambda x:str(x))for k,v in nets.items()if len(v)>1 or None in v}
    devices=[]
    for d in c.each_device():
        dc=d.device_class();devices.append(dict(id=d.id(),model=dc.name,parameters={p.name:d.parameter(p.id())for p in dc.parameter_definitions()},terminals={t.name:dict(cluster=d.net_for_terminal(t.id()).cluster_id,name=d.net_for_terminal(t.id()).name)for t in dc.terminal_definitions()}))
    result=dict(status='DIAGNOSED_NATIVE_FAILED_LVS_NOT_ACCEPTANCE',native_census=census,anchors=rows,shorted_logical_groups=shorted,opened_logical_nets=opened,devices=devices,public_pins=[dict(name=p.name(),cluster=c.net_for_pin(p.id()).cluster_id)for p in c.each_pin()])
    def describe_device(d):
        if d is None:return None
        dc=d.device_class()
        return dict(id=d.id(),name=d.name,model=dc.name,
          parameters={p.name:d.parameter(p.id())for p in dc.parameter_definitions()},
          terminals={t.name:dict(cluster=d.net_for_terminal(t.id()).cluster_id,name=d.net_for_terminal(t.id()).name)for t in dc.terminal_definitions()})
    def describe_net(n):
        if n is None:return None
        return dict(name=n.name,cluster=n.cluster_id)
    xref=db.xref();assert xref is not None
    device_pairs=[];net_pairs=[]
    for pair in xref.each_circuit_pair():
        assert pair.first().name==TOP and pair.second().name.lower()==TOP.lower()
        for row in xref.each_device_pair(pair):
            device_pairs.append(dict(status=str(row.status()),layout=describe_device(row.first()),schematic=describe_device(row.second())))
        for row in xref.each_net_pair(pair):
            net_pairs.append(dict(status=str(row.status()),layout=describe_net(row.first()),schematic=describe_net(row.second())))
    assert sum(row['layout']is not None for row in device_pairs)==500
    assert sum(row['schematic']is not None for row in device_pairs)==500
    result['xref']=dict(device_status_counts=dict(Counter(r['status']for r in device_pairs)),net_status_counts=dict(Counter(r['status']for r in net_pairs)),
        failed_device_pairs=[r for r in device_pairs if r['status']!='Match'],failed_net_pairs=[r for r in net_pairs if r['status']!='Match'],
        all_net_pairs=net_pairs,all_device_pairs=device_pairs)
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(shorted={k:sorted({r['logical_net']for r in v})for k,v in shorted.items()},opened=opened),indent=2),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-m3-detour-drc-pass-lvs-rejection-20261024.json').read_text())
        selected=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds',*['physical/lvs/'+n for n in ('result.lvsdb','extracted.cir','deck.log','run.log','audit.json')]]
        prior,proof=reports.restore_report('cdr-sampler-active-input-v57-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['source_head']==pin['source_head'];r['original_source']=proof
        assert prior['physical']['steps']['drc']['measurement']['markers']==0 and prior['physical']['steps']['drc']['measurement']['category_count']==560
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0;r['native']=json.loads((OUT/'native.json').read_text())
        r['native_extracted_reference']=(OUT/'source/physical/lvs/extracted.cir').read_text();r['schematic_reference']=(OUT/'source/layout/schematic.cir').read_text()
        r['deck_log']=(OUT/'source/physical/lvs/deck.log').read_text()
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_ACTUAL500_LVS_CLUSTER_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
