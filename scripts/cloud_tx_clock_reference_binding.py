#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Export source-bound six-device native clock terminal geometry, before RC."""
import argparse,copy,json,math,os,sys
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_tx_clock_reference_lef import SOURCES,TOP
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
ORDER={'npn13G2':['C','B','E','S'],'rppd':['rppd_1','rppd_2','rppd_sub'],'ptap1':['TIE','WELL']}
PORTS={'avdd','cm','avss','sub'}
SELECTED=('layout/result.json','layout/'+TOP+'.gds','layout/schematic.cir','check/lvs/result.lvsdb','check/lvs_flat/result.lvsdb')

def export(source,out):
    import pya
    geometry=json.loads((source/'layout/result.json').read_text())
    L=pya.Layout();L.read(str(source/'layout'/(TOP+'.gds')));top=L.cell(TOP);assert top is not None and L.dbu==.001
    conductor=pya.Region(top.begin_shapes_rec(L.layer(67,0))).merged()
    modes={}
    for mode in ['lvs','lvs_flat']:
        database=source/('check/'+mode+'/result.lvsdb');lvs=pya.LayoutVsSchematic();lvs.read(str(database));c=lvs.netlist().circuit_by_name(TOP)
        assert c is not None and c.pin_count()==4
        layers=[i for i in lvs.layer_indexes()if (lvs.layer_by_index(i)^conductor).is_empty()];assert len(layers)==1
        names={};probes=[]
        for name,rect in geometry['ports'].items():
            q=pya.DBox.from_s(rect).center();point=pya.Point(round(q.x/L.dbu),round(q.y/L.dbu))
            n=lvs.probe_net(lvs.layer_by_index(layers[0]),point);assert n is not None
            key=str(n.cluster_id);assert key not in names;names[key]=name;probes.append(dict(name=name,cluster=key,point_dbu=[point.x,point.y]))
        assert set(names.values())==PORTS
        rows=[]
        for d in c.each_device():
            cls=d.device_class();assert cls.name in ORDER;terms={}
            for t in cls.terminal_definitions():
                n=d.net_for_terminal(t.id());assert n is not None
                shapes=lvs.shapes_of_terminal(d.terminal_ref(t.id()));assert shapes
                terms[t.name]=dict(cluster=str(n.cluster_id),native_name=n.name,shapes=[dict(layer=int(i),bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p)for p in r.each()])for i,r in shapes.items()])
            assert set(terms)==set(ORDER[cls.name])
            rows.append(dict(id=int(d.id()),model=cls.name,parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},terminals=terms))
        assert Counter(r['model']for r in rows)==Counter(npn13G2=1,rppd=2,ptap1=3)
        q=next(r for r in rows if r['model']=='npn13G2')
        # Internal names follow the source topology; neither can alias a public net.
        for terminal,name in [('E','er'),('S','BULK')]:
            cluster=q['terminals'][terminal]['cluster'];assert cluster not in names;names[cluster]=name
        used={t['cluster']for r in rows for t in r['terminals'].values()};assert set(names)==used and len(names)==6
        for r in rows:
            for t in r['terminals'].values():t['logical_net']=names[t['cluster']]
        modes[mode]=dict(devices=rows,probes=probes,net_map=names,database_sha256=sha(database))
    (out/'native.json').write_text(json.dumps(dict(status='EXPORTED_NATIVE_CLOCK_TERMINALS_NOT_RC_ACCEPTANCE',gds_sha256=sha(source/'layout'/(TOP+'.gds')),dbu=L.dbu,modes=modes),indent=2)+'\n')

def bind(record,variant):
    expected_length={'l6p2':6.2,'l6p5':6.5}[variant];bound={}
    for mode,data in record['modes'].items():
        rows=data['devices'];assert len(rows)==6 and len({r['id']for r in rows})==6,'Native device census changed'
        assert Counter(r['model']for r in rows)==Counter(npn13G2=1,rppd=2,ptap1=3),'Native model census changed'
        q=next(r for r in rows if r['model']=='npn13G2');p=q['parameters']
        assert set(p)=={'we','le','Nx','m'} and all(math.isfinite(v)for v in p.values()),'HBT parameter census changed'
        assert p['Nx']==p['m']==1 and abs(p['we']-.07)<1e-12 and abs(p['le']-.9)<1e-12,'HBT geometry changed'
        def nodes(r):
            assert set(r['terminals'])==set(ORDER[r['model']]),'Native terminal identity changed'
            return [r['terminals'][t]['logical_net']for t in ORDER[r['model']]]
        assert nodes(q)==['cm','cm','er','BULK'],'HBT terminal mapping changed'
        result=[dict(path='xclock.xref',native_id=q['id'],model=q['model'],parameters=p,terminals=q['terminals'])]
        seen=set()
        for r in rows:
            if r['model']!='rppd':continue
            n=nodes(r);p=r['parameters'];assert n[2]=='BULK','Resistor body changed'
            endpoints=frozenset(n[:2])
            if endpoints=={'er','avss'}:path='xclock.xoffset';length=expected_length
            elif endpoints=={'avdd','cm'}:path='xclock.xfeed';length=14.5
            else:raise AssertionError('Resistor endpoint mapping changed')
            assert path not in seen;seen.add(path)
            assert set(p)=={'w','l','ps','b','m'},'Resistor parameter census changed'
            assert abs(p['w']-4)<1e-9 and abs(p['l']-length)<1e-9 and p['ps']==p['b']==0 and p['m']==1,'Resistor geometry changed'
            result.append(dict(path=path,native_id=r['id'],model=r['model'],parameters=p,terminals=r['terminals']))
        assert seen=={'xclock.xoffset','xclock.xfeed'}
        taps=[r for r in rows if r['model']=='ptap1']
        for r in taps:
            assert nodes(r)==['sub','BULK'],'Finite contact terminal mapping changed'
            assert set(r['parameters'])=={'A','P'} and abs(r['parameters']['A']-4)<1e-9 and abs(r['parameters']['P']-8)<1e-9,'Finite contact geometry changed'
            result.append(dict(path='physical.ptap'+str(r['id']),native_id=r['id'],model=r['model'],parameters=r['parameters'],terminals=r['terminals']))
        assert sum(len(r['terminals'])for r in rows)==16
        bound[mode]=result
    assert set(bound)=={'lvs','lvs_flat'}
    return bound

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=sorted(SOURCES),required=True);p.add_argument('--export',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';out=ROOT/('hw/soc/out/cloud-tx-clock-reference-binding-'+args.variant);source=out/'source'
    if args.export:export(source,out);return
    out.mkdir(parents=True,exist_ok=False);reports.OUT=out;spec=SOURCES[args.variant]
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,source_run=38941785196,qualified_pex=False,serial_phy_complete=False,wire_rc_extracted=False,simulator_checked=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        prior,proof=reports.restore_report('tx-clock-reference-'+args.variant,38941785196,spec['summary'],spec['parts'],source,SELECTED);result['source']=proof
        assert prior['source_head']=='4a6550887640d452523888967c76eb709ef60277' and prior['source_unchanged'] and prior['variant']==args.variant
        assert prior['status']=='PASS_NATIVE_CLOCK_REFERENCE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        steps=prior['physical_checks']['steps'];assert len(steps)==9 and all(s['status']==('PASS'if n in ['drc','lvs','lvs_flat']else'REJECTED_EXPECTED_FAULT')for n,s in steps.items())
        assert sha(source/'layout'/(TOP+'.gds'))==spec['gds']
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['export']=execute([app,'python',Path(__file__).resolve(),'--variant',args.variant,'--export'],out,'export');save()
        assert result['export']['returncode']==0,(out/'export.log').read_text()[-10000:]
        native=json.loads((out/'native.json').read_text());assert native['gds_sha256']==spec['gds'];result['bindings']=bind(native,args.variant)
        controls=[]
        for fault in ['missing_contact','wrong_hbt_Nx','hbt_emitter_base_swapped','body_short','wrong_offset_length','wrong_feed_endpoint']:
            bad=copy.deepcopy(native);rows=bad['modes']['lvs_flat']['devices'];q=next(r for r in rows if r['model']=='npn13G2')
            if fault=='missing_contact':rows.remove(next(r for r in rows if r['model']=='ptap1'))
            elif fault=='wrong_hbt_Nx':q['parameters']['Nx']=2
            elif fault=='hbt_emitter_base_swapped':q['terminals']['E']['logical_net'],q['terminals']['B']['logical_net']=q['terminals']['B']['logical_net'],q['terminals']['E']['logical_net']
            elif fault=='body_short':q['terminals']['S']['logical_net']='avss'
            elif fault=='wrong_offset_length':next(r for r in rows if r['model']=='rppd'and {r['terminals'][t]['logical_net']for t in ORDER['rppd'][:2]}=={'er','avss'})['parameters']['l']=7
            else:
                r=next(r for r in rows if r['model']=='rppd'and 'avdd'in [t['logical_net']for t in r['terminals'].values()]);next(t for t in r['terminals'].values()if t['logical_net']=='avdd')['logical_net']='avss'
            (out/(fault+'.json')).write_text(json.dumps(bad,indent=2)+'\n')
            try:bind(bad,args.variant)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted native terminal/model corruption '+fault)
        assert len(controls)==6
        result['controls']=controls;result['native_sha256']=sha(out/'native.json')
        assert all(sha(source/p)==prior['outputs'][p]for p in SELECTED)
        result.update(status='PASS_NATIVE_CLOCK6_TERMINAL_GEOMETRY_AND_SIX_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
