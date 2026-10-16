#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual full-driver finger junctions before electrical RC composition.

Native LVS compares W/L, not junction parameters. Export raw and combined
values independently, normalize D/S by actual nets, retain any disagreement.
This does not qualify extraction, substrate spreading, timing or serial PHY.
"""
import argparse,copy,json,math,os,re,sys
from collections import Counter
from pathlib import Path
import cloud_tx_input_driver as physical
from cloud_tx_driver_lef import SOURCE
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;TOP=physical.TOP;OUT=ROOT/'hw/soc/out/cloud-tx-driver-junctions'

def export():
    import pya
    source=OUT/'inputs/tx-input-driver/cloud-tx-input-driver'
    prior=json.loads((source/'result.json').read_text());geometry=prior['geometry']
    layout=pya.Layout();layout.read(str(source/'base/layout.gds'));top=layout.cell(TOP)
    assert top is not None
    hvboxes=[str(i.cell.dbbox().transformed(i.dcplx_trans)) for i in top.each_inst() if i.cell.name=='nssoc_tx_hv_ng10_v1']
    assert len(hvboxes)==4
    records={}
    for mode,count in [('raw_flat_lvs',100),('aggregate_flat_lvs',12)]:
        path=source/('check-'+mode)/'result.lvsdb'
        lvs=pya.LayoutVsSchematic();lvs.read(str(path));c=lvs.netlist().circuit_by_name(TOP)
        assert c is not None and c.pin_count()==6
        layer_map={}
        for metal in [30,67]:
            conductor=pya.Region(top.begin_shapes_rec(layout.layer(metal,0))).merged()
            candidates=[i for i in lvs.layer_indexes() if (lvs.layer_by_index(i)^conductor).is_empty()]
            assert len(candidates)==1,(metal,candidates)
            layer_map[metal]=candidates[0]
        names={};probes=[]
        def probe(name,metal,point):
            xy=pya.Point(round(point[0]/layout.dbu),round(point[1]/layout.dbu))
            net=lvs.probe_net(lvs.layer_by_index(layer_map[metal]),xy)
            assert net is not None,('Unbound native conductor',name,point)
            identity=str(net.cluster_id)
            assert identity not in names or names[identity]==name,('Logical short',name,names.get(identity))
            names[identity]=name;probes.append(dict(logical_net=name,cluster=identity,metal=metal,point_dbu=[xy.x,xy.y]))
        for r in geometry['routes']:
            assert r['connection_present'];probe(r['net'],30,r['source_um'])
        for name,s in geometry['ports'].items():
            box=pya.DBox.from_s(s);q=box.center();probe(name,67,[q.x,q.y])
        rows=[]
        for dev in c.each_device():
            cls=dev.device_class();terms={};bbox=pya.Box()
            for t in cls.terminal_definitions():
                net=dev.net_for_terminal(t.id());assert net is not None
                shapes=lvs.shapes_of_terminal(dev.terminal_ref(t.id()));assert shapes
                tb=pya.Box()
                for reg in shapes.values():tb+=reg.bbox()
                terms[t.name]=dict(cluster=str(net.cluster_id),native_name=net.name,
                    shapes=[dict(layer=int(i),bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p) for p in r.each()]) for i,r in shapes.items()])
                if t.name in ('S','D','G'):bbox+=tb
            row=dict(id=int(dev.id()),model=cls.name,parameters={p.name:dev.parameter(p.id()) for p in cls.parameter_definitions()},terminals=terms)
            if cls.name.startswith('sg13_'):row['active_bbox_um']=str(bbox.to_dtype(layout.dbu))
            rows.append(row)
        assert len(rows)==count
        # Bodies are finite-contact nodes, never aliases to source/supply.
        for model,name in [('sg13_hv_nmos','BULK'),('sg13_lv_nmos','BULK'),('sg13_lv_pmos','NWELL')]:
            ids={r['terminals']['B']['cluster'] for r in rows if r['model']==model};assert len(ids)==1
            ident=ids.pop();assert ident not in names or names[ident]==name;names[ident]=name
        used={v['cluster'] for r in rows for v in r['terminals'].values()}
        remaining=used-set(names);assert len(remaining)==1,remaining
        ident=remaining.pop()
        assert any(r['model']=='sg13_lv_nmos' and r['terminals']['G']['cluster']==ident for r in rows)
        names[ident]='xbuf.net1'
        assert len(names)==12 and set(names)==used
        assert len(set(names.values()))==12
        for r in rows:
            for t in r['terminals'].values():t['logical_net']=names[t['cluster']]
        records[mode]=dict(devices=rows,net_map=names,probes=probes,database_sha256=sha(path))
    result=dict(status='EXPORTED_RAW_AND_COMBINED_NATIVE_JUNCTIONS_NOT_ELECTRICAL_ACCEPTANCE',
        dbu=layout.dbu,source_run=SOURCE['run'],gds_sha256=sha(source/'base/layout.gds'),hv_boxes_um=hvboxes,
        source_core_rows=geometry['original_core_rows'],native=records)
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')

def microns(value):
    suffix={'u':1.,'n':.001,'p':.000001}
    return float(value[:-1])*suffix[value[-1]] if value[-1] in suffix else float(value)*1e6

def bind(record):
    rows=record['native']['raw_flat_lvs']['devices'];original=record['source_core_rows']
    assert len(rows)==100,'Raw device count changed'
    assert Counter(r['model'] for r in rows)==Counter(sg13_lv_nmos=22,sg13_lv_pmos=22,sg13_hv_nmos=40,rppd=4,ptap1=10,ntap1=2),'Model census changed'
    used=set();groups=[]
    boxes=sorted([[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',s)] for s in record['hv_boxes_um']])
    for core in original:
        if not core['model'].startswith('sg13_'):continue
        model=core['model'];d,g,s,_=core['nets'];body='NWELL' if model.endswith('pmos') else 'BULK'
        matching=[]
        for r in rows:
            if r['model']!=model:continue
            t={k:v['logical_net'] for k,v in r['terminals'].items()}
            if t['G']!=g or {t['D'],t['S']}!={d,s}:continue
            assert t['B']==body,'Body mapping changed'
            if model=='sg13_hv_nmos':
                box=boxes[int(core['path'].rsplit('_',1)[1])]
                actual=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',r['active_bbox_um'])]
                if not(box[0]<=actual[0] and box[1]<=actual[1] and box[2]>=actual[2] and box[3]>=actual[3]):continue
            matching.append(r)
        ng=int(core['params']['ng']);assert len(matching)==ng,('Finger census changed',core['path'],len(matching),ng)
        assert not(used&{r['id'] for r in matching}),'Finger reused';used.update(r['id'] for r in matching)
        width=microns(core['params']['w']);length=microns(core['params']['l'])
        totals=dict(W=0.,AD=0.,AS=0.,PD=0.,PS=0.);orientation=[]
        for r in matching:
            p=r['parameters'];assert all(k in p and math.isfinite(p[k]) and p[k]>0 for k in ('W','L','AD','AS','PD','PS')),'Missing or invalid native MOS parameter'
            assert abs(p['W']-width/ng)<1e-9 and abs(p['L']-length)<1e-9,'Finger W/L changed'
            swap=r['terminals']['D']['logical_net']!=d
            totals['W']+=p['W']
            for dest,other in [('AD','AS'),('AS','AD'),('PD','PS'),('PS','PD')]:totals[dest]+=p[other if swap else dest]
            orientation.append(dict(native_id=r['id'],drain_source_swapped=swap,original_parameters=p))
        assert abs(totals['W']-width)<1e-9
        original_junctions={k.upper():float(v)*(1e12 if k.startswith('a') else 1e6) for k,v in core['params'].items() if k in ('ad','as','pd','ps')}
        groups.append(dict(path=core['path'],model=model,nets=[d,g,s,body],finger_count=ng,parameters_um=totals,length_um=length,
            source_junctions_um=original_junctions,differences_from_source_um={k:totals[k]-v for k,v in original_junctions.items()},fingers=orientation))
    assert len(used)==84 and len(groups)==8,'Incomplete physical MOS coverage'
    return groups

def audit():
    record=json.loads((OUT/'native.json').read_text());groups=bind(record)
    controls=[]
    for fault in ['missing_finger','wrong_width','wrong_gate','body_short','missing_junction_parameter']:
        altered=copy.deepcopy(record);rows=altered['native']['raw_flat_lvs']['devices'];r=next(r for r in rows if r['model']=='sg13_lv_nmos')
        if fault=='missing_finger':rows.remove(r)
        elif fault=='wrong_width':r['parameters']['W']*=.99
        elif fault=='wrong_gate':r['terminals']['G']['logical_net']='din'
        elif fault=='body_short':r['terminals']['B']['logical_net']='avss'
        else:del r['parameters']['AD']
        try:bind(altered)
        except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted corrupted native record '+fault)
    comparisons=[]
    for r in record['native']['aggregate_flat_lvs']['devices']:
        if not r['model'].startswith('sg13_'):continue
        t={k:v['logical_net'] for k,v in r['terminals'].items()};matching=[g for g in groups if g['model']==r['model'] and g['nets'][1]==t['G'] and set(g['nets'][::2])=={t['D'],t['S']}]
        assert matching,('Unmatched combined device',r['id'])
        d=matching[0]['nets'][0];swap=t['D']!=d
        normalized={k:r['parameters'][other if swap else k] for k,other in [('AD','AS'),('AS','AD'),('PD','PS'),('PS','PD')]}
        expected={k:sum(g['parameters_um'][k] for g in matching) for k in normalized}
        delta={k:normalized[k]-expected[k] for k in normalized}
        comparisons.append(dict(native_id=r['id'],paths=[g['path'] for g in matching],normalized_combined=normalized,raw_net_oriented_sum=expected,delta=delta,equal=all(abs(x)<1e-9 for x in delta.values())))
    assert len(comparisons)==5
    result=dict(status='PASS_NATIVE_FINGER_BINDING_AND_FAULTS_JUNCTION_COMPARISON_MEASURED_NOT_ELECTRICAL_ACCEPTANCE',
        native_source_sha256=sha(OUT/'native.json'),groups=groups,negative_controls=controls,aggregate_comparison=comparisons,
        aggregate_junction_reproduction_passed=all(x['equal'] for x in comparisons),
        source_junction_parameters_equal=all(all(abs(v)<1e-9 for v in g['differences_from_source_um'].values()) for g in groups if g['source_junctions_um']),
        no_electrical_model_emitted=True,qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status']);print('Combined junction reproduction:',result['aggregate_junction_reproduction_passed'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');args=parser.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.export:export();return
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,qualified_pex=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert all(v['expected_verdict_observed'] for v in prior['steps'].values() if 'expected_verdict_observed' in v)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['export']=execute([app,'python',Path(__file__).resolve(),'--export'],OUT,'export');save()
        if result['export']['returncode']:
            print((OUT/'export.log').read_text(errors='replace')[-12000:]);raise RuntimeError('Native junction export failed')
        audit();result['audit']=json.loads((OUT/'audit.json').read_text())
        assert all(sha(source/p)==v for p,v in prior['outputs'].items())
        result['status']=result['audit']['status']
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
