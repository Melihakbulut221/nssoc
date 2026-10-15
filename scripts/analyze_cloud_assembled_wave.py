#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnose exact assembled-core native wave failures without changing their oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import numpy as np
import networkx as nx
from run_cloud_tx_layout_repair import ROOT, fetch, sha
import run_cloud_tx_mux4 as mux
from analyze_cloud_tx_tree_wave import transition_table
from cloud_tx_stream import read_streamed_wave
from build_pcie_local_vco_hybrid_v6 import statements, number


def native_conductor_map(graph, anchors):
    """Name actual R-connected components using all independently bound terminals."""
    groups=list(nx.connected_components(graph))
    assert len(groups)==41, 'Unexpected full-tree metal conductor count'
    membership={node:i for i,group in enumerate(groups)for node in group}
    names={}
    terminals=[r for r in anchors['rows']if r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE']
    assert len(terminals)==300
    for row in terminals:
        component=membership[row['wire_anchor']]
        assert names.setdefault(component,row['native_net'])==row['native_net'], 'Conflicting native conductor label'
    assert set(names)==set(range(41)) and len(set(names.values()))==41, 'Missing or aliased conductor labels'
    for rail in ('avdd','avss','sub'):
        assert names[membership[rail]]==rail, 'Changed public rail connection'
    return {node:names[index]for node,index in membership.items()}


def verify_study_captures(selected, out):
    """Read back every pinned capture on the hosted runner, without local archives."""
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    verified=[]
    for study in selected['loaded_studies']:
        for record in study['cases']:
            packed=out/'capture-readback.tar.gz'
            fetch(record['url'],record['sha256'],packed)
            assert packed.stat().st_size==record['bytes']
            hashes={};summary=None;seen=set()
            with tarfile.open(packed,'r|gz')as tar:
                for entry in tar:
                    assert entry.name not in seen, 'Duplicate capture archive member'
                    seen.add(entry.name)
                    if entry.name=='cloud-tx-mux4/result.json':
                        assert entry.isfile()
                        raw=tar.extractfile(entry).read()
                        assert hashlib.sha256(raw).hexdigest()==record['summary_sha256']
                        summary=json.loads(raw)
                    elif entry.name.startswith('cloud-tx-mux4/native/') and entry.isfile():
                        hashes[entry.name[len('cloud-tx-mux4/'):]]=hashlib.file_digest(tar.extractfile(entry),'sha256').hexdigest()
            assert summary is not None
            assert summary['assembled_core_scope']['source']['sha256']==selected['verified_composition']['sha256']
            assert summary['condition']==record['condition'] and summary['fault']==record['fault']
            assert summary['assembled_core_scope']['mode']==record['mode']
            assert summary['component_screen_passed']==record['component_screen_passed']
            assert summary['review']['signals']==record['signals']
            for name,h in summary['outputs'].items():
                assert hashes[name]==h, 'Changed native capture output '+name
            verified.append(dict(run=study['run'],mode=record['mode'],condition=record['condition'],fault=record['fault'],
                archive_asset=record['archive_asset'],archive_sha256=sha(packed),archive_bytes=packed.stat().st_size,
                summary_sha256=record['summary_sha256'],all_native_outputs_verified=summary['outputs'],
                component_screen_passed=record['component_screen_passed']))
            packed.unlink()
    return verified


# Additional numerical-transport bounds; these do not replace original
# 100mV/150mV/device gates or constitute PCIe electrical qualification.
STEP_LIMITS=dict(voltage_v=1e-3,original_sample_margin_v=1e-4,edge_s=1e-13,source_energy_relative=.01)


def step_metrics(coarse, fine, contract):
    ta,va=coarse;tb,vb=fine
    assert ta[0]==tb[0]==0 and abs(ta[-1]-mux.STOP)<1e-15 and abs(tb[-1]-mux.STOP)<1e-15
    assert np.all(np.diff(ta)>0) and np.all(np.diff(tb)>0)
    assert set(va)==set(vb)==set(contract['vectors'])
    voltage={};current={}
    for name in contract['vectors']:
        assert len(va[name])==len(ta) and len(vb[name])==len(tb)
        assert np.isfinite(va[name]).all() and np.isfinite(vb[name]).all()
        delta=float(np.max(abs(va[name]-np.interp(ta,tb,vb[name]))))
        (voltage if name.startswith('v(') else current)[name]=delta
    assert voltage and current
    times=np.asarray([mux.START+(i+p)*mux.UI for i in range(len(contract['bits']))for p in (.3,.5,.7)])
    signs=np.repeat(np.asarray(contract['bits'])*2-1,3)
    ya=va['v(op)']-va['v(on)'];yb=vb['v(op)']-vb['v(on)']
    ma=np.interp(times,ta,ya)*signs;mb=np.interp(times,tb,yb)*signs
    margin_error=float(np.max(abs(ma-mb)))
    edges={};edge_counts_equal=True;max_edge=0.
    for direction,sign in [('rising',1),('falling',-1)]:
        def cross(t,y):
            y=y*sign;k=np.flatnonzero((y[:-1]<0)&(y[1:]>=0))
            e=t[k]-y[k]*(t[k+1]-t[k])/(y[k+1]-y[k])
            return e[(e>mux.START+.5*mux.UI)&(e<mux.STOP-.5*mux.UI)]
        a,b=cross(ta,ya),cross(tb,yb);same=len(a)==len(b) and len(a)>0
        edge_counts_equal &= same
        delta=float(np.max(abs(a-b)))if same else None
        if delta is not None:max_edge=max(max_edge,delta)
        edges[direction]=dict(coarse_count=len(a),fine_count=len(b),maximum_absolute_difference_s=delta)
    energies={}
    for rail in contract['rails']:
        def energy(t,v):return float(np.trapezoid(-v['v('+rail+')']*v['i(v'+rail+')'],t))
        a,b=energy(ta,va),energy(tb,vb);assert a>0 and b>0
        energies[rail]=dict(coarse_j=a,fine_j=b,relative_difference=abs(a-b)/max(abs(a),abs(b)))
    gates=dict(all_voltage_vectors=max(voltage.values())<=STEP_LIMITS['voltage_v'],
        original_sample_margins=margin_error<=STEP_LIMITS['original_sample_margin_v'],
        identical_output_crossing_count=bool(edge_counts_equal),
        output_edge_times=bool(edge_counts_equal and max_edge<=STEP_LIMITS['edge_s']),
        source_energy=all(x['relative_difference']<=STEP_LIMITS['source_energy_relative']for x in energies.values()))
    return dict(limits=STEP_LIMITS,voltage_max_absolute_difference_v=voltage,current_max_absolute_difference_a=current,
        original_samples=len(times),original_sample_margin_max_absolute_difference_v=margin_error,
        coarse_minimum_original_margin_v=float(ma.min()),fine_minimum_original_margin_v=float(mb.min()),
        output_edges=edges,source_energy=energies,gates=gates,passed=all(gates.values()),
        fitted_phase=False,fitted_latency=False,comparison_grid='Every original coarse native timestamp; fine data linearly interpolated only for transport comparison. Original engineering reviews use each unmodified native capture.',
        edge_window_s=[mux.START+.5*mux.UI,mux.STOP-.5*mux.UI])


def step_controls():
    ta=np.linspace(0,mux.STOP,68001);tb=np.linspace(0,mux.STOP,136001)
    def values(t,shift=0.,offset=0.):
        y=.25*np.sin(2*np.pi*4e9*(t+shift))
        return {'v(op)':y+offset,'v(on)':-y,'v(avdd)':np.full_like(t,2.5),'i(vavdd)':np.full_like(t,-.001)}
    contract=dict(vectors=list(values(ta)),bits=[i%2 for i in range(256)],rails=['avdd'])
    assert step_metrics((ta,values(ta)),(tb,values(tb)),contract)['passed']
    bads=[(tb,values(tb,offset=.01)),(tb,values(tb,shift=2e-12)),(tb,dict(values(tb),**{'i(vavdd)':np.full_like(tb,-.002)})),
        (tb[:-1],{k:v[:-1]for k,v in values(tb).items()}),(tb,{k:v for k,v in values(tb).items()if k!='v(on)'})]
    for bad in bads:
        try: passed=step_metrics((ta,values(ta)),bad,contract)['passed']
        except (AssertionError,KeyError):passed=False
        assert not passed,'Malformed/shifted numerical control accepted'
    return dict(positive=1,negative=len(bads),voltage_offset_time_shift_energy_truncation_and_missing_vector_rejected=True)


def compare_timesteps(selected, profile, step_pair='original', solver_profile='default'):
    assert step_pair in ('original','fine')
    conditions=[('hot_low',.5),('hot_low_quarter_step',.25)] if step_pair=='original' else [('hot_low_eighth_step',.125),('hot_low_sixteenth_step',.0625)]
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-tx-tree-assembly';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_SOURCE_BOUND_STEP_COMPARISON',placement_profile=profile,step_pair=step_pair,solver_profile=solver_profile,limits=STEP_LIMITS,
        full_phy_accepted=False,original_engineering_gates_changed=False,qualified_pex=False)
    try:
        result['controls']=step_controls();result['pairs']={}
        for mode in ('compact','wire'):
            captures=[];contracts=[];summaries=[];benches=[]
            for condition,step in conditions:
                cases=[(study,c)for study in selected['loaded_studies']for c in study['cases']if c['mode']==mode and c['condition']==condition and c['fault']=='none' and c.get('pre_bias','native_res')=='native_res' and c.get('solver_profile','default')==solver_profile]
                assert len(cases)==1
                study,record=cases[0];directory=out/(mode+'-'+condition);directory.mkdir()
                packed=out/'step-source.tar.gz';fetch(record['url'],record['sha256'],packed)
                assert packed.stat().st_size==record['bytes']
                prefix='cloud-tx-mux4/'
                modelrel='wire96/tree162-wire01.spice'if mode=='wire'else'binding96/tree162-compact01.spice'
                modelname=prefix+'inputs/assembled-core/hw/soc/out/cloud-tx-tree-assembly/'+modelrel
                seen=set();model_hash=None
                with tarfile.open(packed,'r|gz')as tar:
                    for entry in tar:
                        assert entry.name not in seen;seen.add(entry.name)
                        if entry.name==prefix+'result.json':
                            assert entry.isfile();raw=tar.extractfile(entry).read()
                            assert hashlib.sha256(raw).hexdigest()==record['summary_sha256']
                            (directory/'original-summary.json').write_bytes(raw)
                        elif entry.name==modelname:
                            assert entry.isfile();model_hash=hashlib.file_digest(tar.extractfile(entry),'sha256').hexdigest()
                        elif entry.name.startswith(prefix+'native/')and entry.isfile():
                            rel=Path(entry.name[len(prefix):]);assert not rel.is_absolute()and '..'not in rel.parts
                            dest=directory/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                            with tar.extractfile(entry)as src,dest.open('xb')as dst:
                                import shutil
                                shutil.copyfileobj(src,dst)
                packed.unlink();summary=json.loads((directory/'original-summary.json').read_text())
                scope=summary['assembled_core_scope']
                assert scope['placement_profile']==profile and scope['source']['sha256']==selected['verified_composition']['sha256']
                assert scope['mode']==mode and model_hash==selected['verified_composition']['outputs'][modelrel]
                for name,h in summary['outputs'].items():assert sha(directory/name)==h
                contract=json.loads((directory/'native/contract.json').read_text())
                assert contract['condition']['step_ps']==step and contract['streams']==4 and contract['fault']=='none'
                assert contract['source_bits_sha256']==record['signals']['source_bits_sha256']
                fresh=mux.review(directory/'native',contract)
                for key in ('signals','interfaces','hbt_devices','mos_devices','failed_hbts','failed_mos','all_engineering_gates_passed'):
                    assert fresh[key]==summary['review'][key],key
                t,v,transport=read_streamed_wave(directory/'native/wave.raw',contract['vectors'],mux.STOP,step*1e-12)
                captures.append((t,{name:v[name]for name in contract['vectors']}));contracts.append(contract);summaries.append(summary)
                bench=(directory/'native/bench.cir').read_text()
                tran=f'tran {step*1e-12:.14g} {mux.STOP:.14g} 0 {step*1e-12:.14g}'
                assert bench.count(tran)==1;benches.append(bench.replace(tran,'SAME_NATIVE_END_START_ONLY_STEP_DIFFERS'))
            import copy
            a,b=copy.deepcopy(contracts)
            a['condition']['step_ps']=b['condition']['step_ps']=None
            assert a==b,'Native contracts differ beyond timestep'
            assert benches[0]==benches[1],'Native benches differ beyond timestep'
            def circuit_inputs(summary):
                # The two generated files have just been compared byte-for-byte
                # after normalizing only the explicit integration timestep.
                # Their original hashes must still match each archived capture.
                generated=('native/bench.cir','native/contract.json')
                for rel in generated:
                    matches=[h for name,h in summary['inputs'].items()if name.endswith('/cloud-tx-mux4/'+rel)]
                    assert matches==[summary['outputs'][rel]], 'Generated input/output hash mismatch'
                return {k:v for k,v in summary['inputs'].items()
                    if not k.endswith('/docs/evidence/pcie-tree4-assembly-input-20261015.json')
                    and not any(k.endswith('/cloud-tx-mux4/'+rel)for rel in generated)}
            assert circuit_inputs(summaries[0])==circuit_inputs(summaries[1]),'Captured circuit/model inputs differ'
            metrics=step_metrics(*captures,contracts[0])
            result['pairs'][mode]=dict(metrics=metrics,original_reviews_passed=[s['review']['all_engineering_gates_passed']for s in summaries],
                original_native_outputs=[s['outputs']for s in summaries],same_model_source_sha256=selected['verified_composition']['sha256'],
                contract_equal_except_step=True,bench_equal_except_step=True,circuit_model_inputs_equal=True)
            # Original raw files remain in their hash-verified source releases.
            # Do not republish multi-gigabyte duplicates in this comparison.
            for condition,_ in conditions:
                (out/(mode+'-'+condition)/'native/wave.raw').unlink()
            del captures,contracts,summaries
            import gc
            gc.collect()
        result['numerical_component_screen_passed']=all(p['metrics']['passed']and all(p['original_reviews_passed'])for p in result['pairs'].values())
        result['status']='COMPLETE_SOURCE_BOUND_TIMESTEP_COMPARISON_NOT_PHY_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'step-comparison-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ('status','placement_profile')}),flush=True)



def trace_rail_geometry(selected,profile):
    """Recover native extraction provenance before touching any ground geometry."""
    import re
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-tx-tree-assembly';out.mkdir(parents=True,exist_ok=False)
    receipt=selected['verified_composition'];diagnosis=selected['ground_path_diagnosis']
    targets=[r for r in diagnosis['supply_resistor_path_upper_bounds']['avss']if r['device']in (6,7)and r['terminal']=='E']
    assert len(targets)==2 and diagnosis['original_review_preserved']
    names={r['name']for t in targets for e in t['largest_native_segments']for r in e['native_resistors']}
    nodes={n for t in targets for e in t['largest_native_segments']for n in e['nodes']}
    native_nodes=nodes|{n.removeprefix('P_')for n in nodes}
    result=dict(status='RUNNING',placement_profile=profile,source=receipt,source_diagnosis_run=diagnosis['run'],
        targets=targets,accepted=False,geometry_changed=False,qualified_pex=False,serial_phy_complete=False)
    try:
        packed=out/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],packed)
        assert packed.stat().st_size==receipt['bytes']
        prefix='hw/soc/out/cloud-tx-tree-assembly/'
        inventory=[];hits={};methods={};models={};exported={};summary=None
        source_dir=out/'rail-source';source_dir.mkdir()
        geometry_files={'layout/nssoc_tx_tree4_core_v1.gds','layout/result.json','physical/lvs/result.lvsdb','wire96/native05/result.json','wire96/anchors08.json','wire96/device-locations01.json','wire96/rc03/pump_wires.mag','wire96/rc03/pump_wires.ext','wire96/rc03/pump_wires.res.ext'}
        patterns={s:re.compile(r'(?<![A-Za-z0-9_.])'+re.escape(s)+r'(?![A-Za-z0-9_.])',re.I)for s in native_nodes|names}
        with tarfile.open(packed,'r|gz')as archive:
            seen=set()
            for item in archive:
                assert item.name not in seen;seen.add(item.name)
                if not item.isfile()or not item.name.startswith(prefix):continue
                rel=item.name[len(prefix):]
                if rel=='composition-result.json':
                    data=archive.extractfile(item).read();assert hashlib.sha256(data).hexdigest()==receipt['summary_sha256'];summary=json.loads(data);continue
                # Read the source package entirely on hosted runner. No geometrical or native model edits.
                if not rel.startswith(('wire96/','binding96/','layout/'))and rel not in geometry_files:continue
                data=archive.extractfile(item).read();h=hashlib.sha256(data).hexdigest()
                if rel in geometry_files:
                    dest=source_dir/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
                inventory.append(dict(path=rel,bytes=len(data),sha256=h))
                if rel in receipt['outputs']:
                    assert h==receipt['outputs'][rel];exported[rel]=h
                if not rel.endswith(('.py','.tcl','.json','.ext','.spice','.sp','.cir','.res','.sim','.nodes','.coords','.txt','.log')):continue
                try:text=data.decode('utf-8')
                except UnicodeDecodeError:continue
                lines=text.splitlines();matches=[]
                for i,line in enumerate(lines):
                    matched=[n for n,pat in patterns.items()if pat.search(line)]
                    if matched:matches.append(dict(line=i+1,matched=matched,text=line))
                if matches:hits[rel]=dict(sha256=h,line_count=len(lines),matches=matches)
                if rel.endswith(('run-rc01.py','compose-tree.py','compose49.py','probe01.py')):
                    methods[rel]=text
                if rel in ('wire96/native05/result.json','wire96/device-locations01.json','wire96/rc03/result.json'):
                    models[rel]=json.loads(text)
        assert summary is not None and summary['status']==receipt['status']
        assert exported==receipt['outputs'], 'Every original composition export must match'
        assert 'wire96/tree162-wire01.spice' in hits
        assert names<=set(n for m in hits['wire96/tree162-wire01.spice']['matches']for n in m['matched'])
        assert all((source_dir/p).is_file()for p in geometry_files)
        helper=out/'probe-native-rail-geometry.py';helper.write_text("# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n# SPDX-License-Identifier: Apache-2.0\nimport pya,json,hashlib\nfrom pathlib import Path\nB=Path(__file__).resolve().parent;S=B/'rail-source'\ng=pya.Layout();g.read(str(S/'layout/nssoc_tx_tree4_core_v1.gds'))\nl=pya.LayoutVsSchematic();l.read(str(S/'physical/lvs/result.lvsdb'))\nmeta=json.loads((S/'wire96/native05/result.json').read_text());mapping=meta['native_layer_mapping']\nanchors=json.loads((S/'wire96/anchors08.json').read_text());placement=json.loads((S/'layout/result.json').read_text())\nc=l.netlist().top_circuit();nets={n.name:n for n in c.each_net()};assert 'avss'in nets\nregions={m:{name:l.shapes_of_net(n,l.layer_by_index(int(index)),True)for name,n in nets.items()}for m,index in mapping.items()}\nfor m,index in mapping.items():\n original=pya.Region(g.top_cell().begin_shapes_rec(g.layer(int(m),0))).merged()\n recovered=pya.Region()\n for reg in regions[m].values():recovered+=reg\n assert(original^recovered.merged()).is_empty(),('Lost native layout metal',m)\ndef box(x1,y1,x2,y2):return pya.DBox(x1,y1,x2,y2).to_itype(g.dbu)\ndef nearby(area):\n q=pya.Region(area);result={}\n for m,byname in regions.items():\n  found={}\n  for name,reg in byname.items():\n   piece=(reg&q).merged()\n   if not piece.is_empty():found[name]=dict(area_dbu2=piece.area(),polygons=[str(p)for p in piece.each()])\n  result[m]=found\n return result\npoints=[]\nfor a in anchors['rows']:\n if a['device']not in(6,7)or a['terminal']!='E':continue\n assert a['native_net']=='avss'\n at=pya.Point(*a['point_dbu']);m=str(a['metal'])if 'metal'in a else '10'\n assert l.probe_net(l.layer_by_index(int(mapping['10'])),at).name=='avss'\n points.append(dict(anchor=a,window_um=[at.x*g.dbu-12,at.y*g.dbu-4,at.x*g.dbu+12,at.y*g.dbu+4],\n  surrounding_native_geometry=nearby(box(at.x*g.dbu-12,at.y*g.dbu-4,at.x*g.dbu+12,at.y*g.dbu+4))))\ncandidates=[]\nfor x in(800.4,803.0,806.875,810.0,813.0):\n for y in(320.24,327.44):\n  candidates.append(dict(x_um=x,y_um=y,one_um_square=nearby(box(x-.5,y-.5,x+.5,y+.5)),five_um_square=nearby(box(x-2.5,y-2.5,x+2.5,y+2.5))))\nheaders={}\nfor name in('pump_wires.mag','pump_wires.ext','pump_wires.res.ext'):\n headers[name]=(S/'wire96/rc03'/name).read_text().splitlines()[:14]\nresult=dict(status='PASS_UNCHANGED_GDS_NATIVE_NET_GEOMETRY_QUERY_NOT_REPAIR',dbu_um=g.dbu,placement=placement,\n native_mapping=mapping,terminal_points=points,candidate_landings=candidates,magic_headers=headers,\n return_corridor=nearby(box(790,312,820,530)),\n inputs={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest()for p in S.rglob('*')if p.is_file()},geometry_changed=False)\n(B/'native-rail-geometry.json').write_text(json.dumps(result,indent=2)+'\\n');print(result['status'])\n")
        import subprocess
        with (out/'native-rail-geometry.log').open('w')as log:
            code=subprocess.call([os.environ['CLOUD_APPIMAGE'],'python',str(helper)],stdout=log,stderr=subprocess.STDOUT)
        assert code==0, (out/'native-rail-geometry.log').read_text()[-6000:]
        result['native_geometry_query']=json.loads((out/'native-rail-geometry.json').read_text())
        result.update(status='COMPLETE_SOURCE_BOUND_NATIVE_RAIL_PROVENANCE_NOT_LAYOUT_REPAIR',inventory=inventory,
            exact_matching_lines=hits,method_sources=methods,native_geometry_metadata=models,
            verified_composition_outputs=exported,
            qualification='Exact archive bytes and native resistor/node labels; coordinates/layer semantics still require interpretation and native binding checks before any geometry repair.')
        packed.unlink()
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        (out/'rail-geometry-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ('status','placement_profile','geometry_changed')}),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placement-profile',choices=('baseline','compact_vertical','compact_m5_supply','compact_edge_supply'),default='baseline')
    parser.add_argument('--compare-timestep',action='store_true')
    parser.add_argument('--trace-rail-geometry',action='store_true')
    parser.add_argument('--step-pair',choices=('original','fine'),default='original')
    parser.add_argument('--solver-profile',choices=('default','tight_trap','tight_gear2','breakpoint_1as'),default='default')
    parser.add_argument('--condition',choices=('hot_low','hot_low_res_bcs','cold_high_res_wcs','cold_high_hbt_wcs'),default='hot_low')
    parser.add_argument('--bias-profile',choices=('native_res','native_res_tc'),default='native_res')
    args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    selected=spec if args.placement_profile=='baseline' else spec['placement_variants'][args.placement_profile]
    if args.trace_rail_geometry:
        assert not args.compare_timestep and args.bias_profile=='native_res'
        trace_rail_geometry(selected,args.placement_profile);return
    if args.bias_profile!='native_res':
        assert not args.compare_timestep
        selected=dict(selected,loaded_studies=selected['bias_candidates'][args.bias_profile]['loaded_studies'])
    if args.compare_timestep:
        compare_timesteps(selected,args.placement_profile,args.step_pair,args.solver_profile);return
    cases=[(s,c) for s in selected['loaded_studies']for c in s['cases']if c['condition']==args.condition and c['mode']=='wire' and c['fault']=='none' and c.get('pre_bias','native_res')==args.bias_profile and c.get('solver_profile','default')==args.solver_profile]
    assert len(cases)==1
    study,record=cases[0]
    out=ROOT/'hw/soc/out/cloud-tx-tree-assembly';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',placement_profile=args.placement_profile,condition=args.condition,bias_profile=args.bias_profile,source_run=study['run'],source=record,
        native_acceptance_changed=False,qualified_pex=False,serial_phy_complete=False)
    try:
        packed=out/'wave-source.tar.gz';fetch(record['url'],record['sha256'],packed)
        assert packed.stat().st_size==record['bytes']
        root='cloud-tx-mux4/'
        geometry=root+'inputs/assembled-core/hw/soc/out/cloud-tx-tree-assembly/'
        wanted={root+'result.json':'original-summary.json',root+'native/contract.json':'native/contract.json',
            root+'native/wave.raw':'native/wave.raw',root+'native/op.dat':'native/op.dat',root+'native/bench.cir':'native/bench.cir',
            **{geometry+n:n for n in ['wire96/tree162-wire01.spice','wire96/anchors08.json','wire96/tree-interface-probes.json','binding96/binding01.json']}}
        found=set()
        with tarfile.open(packed,'r|gz')as tar:
            for entry in tar:
                if entry.name not in wanted:continue
                assert entry.isfile() and entry.name not in found
                target=out/wanted[entry.name];target.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(entry)as src,target.open('xb')as dst:
                    import shutil
                    shutil.copyfileobj(src,dst)
                found.add(entry.name)
        assert found==set(wanted)
        assert sha(out/'original-summary.json')==record['summary_sha256']
        prior=json.loads((out/'original-summary.json').read_text());scope=prior['assembled_core_scope']
        assert scope.get('placement_profile','baseline')==args.placement_profile
        assert scope['source']['sha256']==selected['verified_composition']['sha256']
        for name in ['contract.json','wave.raw','op.dat','bench.cir']:
            assert sha(out/'native'/name)==prior['outputs']['native/'+name]
        for name in ['wire96/tree162-wire01.spice','wire96/tree-interface-probes.json','binding96/binding01.json']:
            assert sha(out/name)==scope['source']['outputs'][name]
        # The anchor JSON was included in the source-bound composition input.
        composition_anchor_key=next(k for k in scope['source']['controls']['inputs'] if k.endswith('/anchors08.json'))
        assert sha(out/'wire96/anchors08.json')==scope['source']['controls']['inputs'][composition_anchor_key]
        contract=json.loads((out/'native/contract.json').read_text())
        assert hashlib.sha256(bytes(contract['bits'])).hexdigest()==record['signals']['source_bits_sha256']
        assert contract['interface_probes']==scope['interface_probes']['modes']['wire']
        fresh=mux.review(out/'native',contract)
        # Re-review also executes the new missing/alias/coverage guards. No
        # approximation, phase fitting or changed pass/fail result is permitted.
        for key in ['signals','interfaces','hbt_devices','mos_devices','failed_hbts','failed_mos','all_engineering_gates_passed']:
            assert fresh[key]==prior['review'][key],key
        t,values,transport=read_streamed_wave(out/'native/wave.raw',contract['vectors'],mux.STOP,contract['condition']['step_ps']*1e-12)
        def v(node):return np.zeros_like(t) if node=='0' else values['v('+node+')']
        delay=transition_table(t,v('sp')-v('sn'),v('mp')-v('mn'),v('op')-v('on'),contract['bits'])
        failed=[]
        for index,bit in enumerate(contract['bits']):
            for phase in (.3,.5,.7):
                at=mux.START+(index+phase)*mux.UI
                margin=float(np.interp(at,t,v('op')-v('on'))*(2*bit-1))
                if margin>=.1:continue
                branch='a' if index%2==0 else 'b'
                nodes=['sp','sn','mp','mn','op','on',*contract['interface_probes'][branch+'p'],*contract['interface_probes'][branch+'n']]
                failed.append(dict(index=index,bit=bit,previous_bit=contract['bits'][index-1] if index else None,phase=phase,margin_v=margin,
                    transition=next((r for r in delay['events']if r['index']==index),None),
                    trace=[dict(time_s=float(at+dt*1e-12),offset_from_original_sample_ps=dt,
                        volts={n:float(np.interp(at+dt*1e-12,t,v(n)))for n in nodes})for dt in (-10,-5,0,5,10)]))
        assert len(failed)==record['signals']['below_100mv_samples']
        # Full native extrema, without shifting original review/sample windows.
        device_extrema={};active=np.flatnonzero(t>=mux.START)
        for name in fresh['failed_hbts']:
            row=contract['hbt'][name];collector,base,emitter,substrate=row['terminals']
            ce=v(collector)-v(emitter);be=v(base)-v(emitter)
            current=values['@q.'+name+'.qnpn13g2[ic]']/row['nx']
            points=dict(minimum_post_vce=int(active[np.argmin(ce[active])]),
                maximum_whole_abs_vbe=int(np.argmax(abs(be))),maximum_whole_abs_current=int(np.argmax(abs(current))))
            contexts=list(dict.fromkeys([*row['terminals'],'avdd','clkbias','ra','rb','mr','sap','san','sbp','sbn','sp','sn']))
            device_extrema[name]=dict(native_terminals=row['terminals'],emitters=row['nx'],events={label:dict(
                time_s=float(t[index]),vce_v=float(ce[index]),vbe_v=float(be[index]),ic_per_emitter_a=float(current[index]),
                volts={n:float(v(n)[index])for n in contexts},
                nearby=[dict(time_s=float(t[j]),vce_v=float(ce[j]),vbe_v=float(be[j]),ic_per_emitter_a=float(current[j]))
                    for j in range(max(0,index-2),min(len(t),index+3))])for label,index in points.items()})
        # Read the actual distributed-wire capacitor burden and a physical
        # resistor-path upper bound between stage output and each final base.
        rows=statements((out/'wire96/tree162-wire01.spice').read_text())
        graph=nx.Graph()
        for row in rows[1:-1]:
            if not row[0].startswith('R'):continue
            x,y=row[1:3];res=float(number(row[3]))
            # Parallel edges use conductance addition; the resulting shortest
            # path remains a path bound, NOT a full network effective resistance.
            previous=graph.get_edge_data(x,y,{}).get('resistance')
            originals=list(graph.get_edge_data(x,y,{}).get('native_resistors',[]))
            originals.append(dict(name=row[0],ohms=res))
            graph.add_edge(x,y,resistance=res if previous is None else 1/(1/res+1/previous),native_resistors=originals)
        binding=json.loads((out/'binding96/binding01.json').read_text())
        anchors=json.loads((out/'wire96/anchors08.json').read_text());by={(r['device'],r['terminal']):r for r in anchors['rows']}
        refs=json.loads((out/'wire96/tree-interface-probes.json').read_text())['references']
        conductor=native_conductor_map(graph,anchors)
        # An actually conflicting terminal witness must not be accepted as a
        # new conductor identity. This exercises the exact source-bound graph.
        import copy
        corrupted=copy.deepcopy(anchors)
        row=next(r for r in corrupted['rows']if r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE')
        row['native_net']='intentionally_wrong_native_conductor'
        try:
            native_conductor_map(graph,corrupted)
        except AssertionError:
            wrong_conductor_rejected=True
        else:
            raise AssertionError('Conflicting native conductor witness accepted')
        power={}
        for rail in ('avdd','avss','sub'):
            terminals=[r for r in anchors['rows']if r['native_net']==rail and r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE']
            assert terminals
            power[rail]=[]
            for r in terminals:
                path=nx.shortest_path(graph,rail,r['wire_anchor'],weight='resistance')
                segments=[dict(nodes=[x,y],effective_parallel_edge_ohms=graph[x][y]['resistance'],
                    native_resistors=graph[x][y]['native_resistors'])for x,y in zip(path,path[1:])]
                for edge in segments:
                    assert all(p['ohms']>0 for p in edge['native_resistors'])
                    assert np.isclose(edge['effective_parallel_edge_ohms'],1/sum(1/p['ohms']for p in edge['native_resistors']),rtol=1e-12,atol=1e-15)
                total=sum(edge['effective_parallel_edge_ohms']for edge in segments)
                assert np.isclose(total,nx.shortest_path_length(graph,rail,r['wire_anchor'],weight='resistance'),rtol=1e-12,atol=1e-15)
                power[rail].append(dict(device=r['device'],model=r['model'],terminal=r['terminal'],point_dbu=r['point_dbu'],
                    wire_anchor=r['wire_anchor'],resistance_path_upper_bound_ohm=total,path_nodes=path,
                    segment_count=len(segments),largest_native_segments=sorted(segments,key=lambda e:e['effective_parallel_edge_ohms'],reverse=True)[:12],
                    segment_provenance='Exact exported native resistor names/values; parallel edges combined by conductance. Path bound only, not solved IR or effective rail resistance.'))
        intermacro={}
        for label,ref in refs.items():
            net=ref['endpoints'][0]['native_net'];sinks=ref['intrinsic_terminals'];group=nx.node_connected_component(graph,sinks[0]['wire_anchor'])
            candidates=[]
            for d in binding['devices']:
                if d['model']!='rppd' or number(d['parameters']['w'])!=number('4u') or number(d['parameters']['l'])!=number('1.8u'):continue
                for term,native in d['native_nodes'].items():
                    if native==net and term!='rppd_sub':candidates.append(by[d['native_id'],term])
            assert len(candidates)==1
            source=candidates[0]['wire_anchor'];assert source in group
            cap_out=cap_internal=0.;external={}
            for row in rows[1:-1]:
                if not row[0].startswith('C'):continue
                x,y=row[1:3];value=float(number(row[3]));ix,iy=x in group,y in group
                if ix and iy:cap_internal+=value
                elif ix or iy:
                    cap_out+=value;other=y if ix else x;external[other]=external.get(other,0.)+value
            external_native={}
            for node,value in external.items():
                assert node=='wire_cref' or node in conductor, 'Unnamed capacitance attachment'
                native='wire_cref' if node=='wire_cref' else conductor[node]
                external_native[native]=external_native.get(native,0.)+value
            assert np.isclose(sum(external_native.values()),cap_out,rtol=1e-12,atol=1e-24), 'Capacitance grouping lost a contribution'
            intermacro[label]=dict(native_net=net,source_terminal=candidates[0],sinks=sinks,wire_nodes=len(group),
                external_capacitance_f=cap_out,within_conductor_capacitance_f=cap_internal,
                wire_cref_capacitance_f=external.get('wire_cref',0.),
                external_capacitance_by_native_conductor_f=external_native,
                path_resistance_upper_bounds_ohm={r['wire_anchor']:nx.shortest_path_length(graph,source,r['wire_anchor'],weight='resistance')for r in sinks},
                qualification='DC resistor path upper bounds and exact exported lumped C totals only; no RF/effective-resistance or substrate qualification.')
        result.update(status='COMPLETE_ASSEMBLED_SOURCE_BOUND_FAILURE_AND_INTERMACRO_DIAGNOSIS_NOT_ACCEPTANCE',
            original_review_preserved=True,failed_samples=failed,failed_hbt_native_extrema=device_extrema,transition_delays=delay,intermacro=intermacro,
            supply_resistor_path_upper_bounds=power,wrong_native_conductor_control_rejected=wrong_conductor_rejected,
            supply_qualification='Path bounds only, not solved voltage drops or effective resistance. Existing captured device terminal voltages and currents retain their original review; no uncaptured rail voltage inferred.',
            native_bias_current_a=fresh['native_bias_current_a'],clock_common_mode_range_v=fresh['clock_common_mode_range_v'],
            fresh_review={k:fresh[k]for k in ['signals','interfaces','failed_hbts','failed_mos','all_engineering_gates_passed']},
            capture={k:transport[k]for k in ['raw_sha256','columns','start_s','end_s','max_step_s','complete_unmodified_rows']})
        packed.unlink()
        all_studies=args.condition=='hot_low' and args.bias_profile=='native_res'
        readback=selected if all_studies else dict(selected,loaded_studies=[dict(study,cases=[record])])
        result['capture_readback_scope']='ALL_PINNED_STUDIES' if all_studies else 'SELECTED_SOURCE_CASE'
        result['hosted_capture_readback']=verify_study_captures(readback,out)
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'diagnosis-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ['status','placement_profile']}),flush=True)


if __name__=='__main__':main()
