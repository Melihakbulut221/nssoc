#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh native wire extraction of actual31macro32:1 tree; not qualified PHY PEX."""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import ROOT,fetch,sha

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    parser=argparse.ArgumentParser()
    parser.add_argument('--variant',choices=('budget_balanced_v5',),default='budget_balanced_v5')
    parser.add_argument('--placement-pitch',choices=('compact_columns',),default='compact_columns')
    parser.add_argument('--return-rail',choices=('wide64',),default='wide64')
    selected_args=parser.parse_args();selected=selected_args.variant
    tight=selected_args.placement_pitch=='tight'
    assert not tight or selected=='budget_balanced_v5'
    wide64=selected_args.return_rail=='wide64'
    assert wide64 and not tight and selected=='budget_balanced_v5'
    high3=selected in ('budget_high3','budget_balanced_v5')
    trim=selected=='budget_balanced_v5'
    args=argparse.Namespace(variant='tree32_'+selected,circuit_profile='assembly32')
    spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
    top='nssoc_tx_tree32_'+selected+('_timing_priority_core_v1'if wide64 else'_tight_core_v1'if tight else'_core_v1')
    spec['circuits']['assembly32']={'top':top}
    runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
    receipt_name='tx-tree32-balanced-v5-physical-pass-20261017.json' if trim else 'tx-tree32-high3-physical-pass-20261017.json' if high3 else 'tx-tree32-budget-physical-pass-20261017.json'
    if tight:receipt_name='tx-tree32-tight-physical-pass-20261017.json'
    if wide64:receipt_name='tx-fast-wire24-physical-pass-20261020.json'
    receipt=json.loads((ROOT/'docs/evidence'/receipt_name).read_text())
    assert receipt['source_run']==39339196396 and receipt['source_head']=='7a4d047b8bae3cb3da682550b99bf87866107d7d'
    assert receipt['summary_sha256']=='00aa1d6cef157845fe73f185e0350b54f372d2c6e0c7dba2773ed629131f6263'
    assert receipt['sha256']=='6e131bf83bb44258874986fcfd85a2189f8e99964c6588257605f89567fcb410'
    out=ROOT/'hw/soc/out'/('cloud-tx-tree32-balanced-v5-assembly' if trim else 'cloud-tx-tree32-high3-assembly' if high3 else 'cloud-tx-tree32-budget-assembly')
    if tight:out=ROOT/'hw/soc/out/cloud-tx-tree32-tight-assembly'
    if wide64:out=ROOT/'hw/soc/out/cloud-tx-fast-wire24-physical'
    assert not out.exists()
    out.parent.mkdir(parents=True,exist_ok=True)
    archive=out.parent/'tree32-extraction-input.tar.gz'
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,
        circuit_profile=args.circuit_profile,adopted=False,qualified_pex=False,serial_phy_complete=False,
        physical_source=receipt,runtime_source=runtime,method_source=spec,
        scope='Actual31macro32:1 core,1674native devices and all60 intermacro wires. Native graph/terminal ownership/C conservation and13 faults required. Body spreading/RF qualification, full loaded waves, fourlanes/RX/CDR/PLL and mainchip remain open.')
    def run(command,label):
        log=out/(label+'.log')
        with log.open('w')as stream:
            code=subprocess.call([str(x)for x in command],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-12000:],flush=True)
            raise RuntimeError(f'{label}: exit {code}')
    try:
        fetch(receipt['url'],receipt['sha256'],archive)
        assert archive.stat().st_size==receipt['bytes']
        with tarfile.open(archive)as tar:tar.extractall(out.parent,filter='data')
        archive.unlink()
        assert sha(out/'result.json')==receipt['summary_sha256']
        physical=json.loads((out/'result.json').read_text())
        assert physical['status']=='PASS_TX28_FAST_DATA_WIRE24_NATIVE_PHYSICAL_REQUIRES_FRESH_RC_AND_LOADED_GATES'
        assert physical['source_head']==receipt['source_head']
        basepin=json.loads((ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json').read_text())
        assert basepin['run']==39304550527 and basepin['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
        baseline=basepin['report']
        assert baseline['variant']==selected
        assert physical==receipt['report'], 'Exact physical parent summary changed'
        assert all(sha(out/n)==v for n,v in physical['outputs'].items()), 'Physical archive member changed'
        assert baseline['placement_pitch']==dict(name='compact_columns',column_um=700.,row_um=600.,inverse_topology_matches_original=True)
        if tight:
            assert baseline['placement_pitch']==dict(name='tight',column_um=700.,row_um=422.,inverse_topology_matches_original=True)
            assert basepin['placement_pitch']==baseline['placement_pitch']
        result['placement_pitch']=baseline.get('placement_pitch',dict(name='compact_columns',column_um=700.,row_um=600.))
        if wide64:
            assert baseline['return_rail']==basepin['return_rail']
            assert baseline['return_rail']['profile']=='wide64'and baseline['return_rail']['trunk_and_bus_width_um']==64.
            result['return_rail']=baseline['return_rail']
        assert baseline['emitter_budget']['reference_emitters']==(719 if high3 else 899)
        assert baseline['emitter_budget']['recommended_rules_enabled'] and not baseline['emitter_budget']['waiver']
        assert baseline['layout']['outputs']==basepin['layout_outputs']
        gp=baseline['geometry_delta']
        assert gp==baseline['geometry_delta']
        assert gp['status']=='PASS_TIMING_PRIORITY_ACTUAL31_PLACEMENTS_FROZEN_CHILDREN_60_ROUTES_AND_THREE_FAULTS'
        assert gp['controls']==['wrong_actual_row_metadata','native_child_conductor_removed','actual_parent_trunk_cut']
        assert gp['reference_devices_unchanged']and gp['actual_native_children_unchanged']
        assert gp['fixed_leaf_and_final_rows']==17 and gp['signal_legs']==60
        assert gp['plan']==baseline['data_route_plan']
        assert gp['maximum_after_um']==baseline['layout']['parent_signal_centerline_max_um']
        assert gp['maximum_after_um']<gp['maximum_before_um']*.8
        assert gp['plan']['row_lattice']['quantum_um']==600.
        assert gp['plan']['row_lattice']['private_diagnosis_run']==39263440258
        assert all(abs((v-gp['plan']['original_rows_um'][k])/600.-round((v-gp['plan']['original_rows_um'][k])/600.))<1e-9 for k,v in gp['plan']['row_targets_um'].items())
        assert gp['plan']['solver']['first_mip_gap']==gp['plan']['solver']['second_mip_gap']==0.
        priority=gp['plan']['timing_priority']
        assert priority['maximum_weighted_after']<priority['maximum_weighted_before']
        assert priority['stage_maxima']['1']['after']<priority['stage_maxima']['1']['before']
        assert baseline['return_rail']['final_column_trunk_width_um']==128. and baseline['return_rail']['final_column_trunk_offset_from_right_um']==340.
        assert baseline['return_rail']['local_final_strap_width_um']==6. and baseline['return_rail']['final_strap_top_via_columns']==baseline['return_rail']['final_strap_top_via_rows']==2
        from check_tx_v5_timing_priority_sources import check
        check()
        for method in ['scripts/cloud_tx_v5_timing_priority_assembly.py','scripts/check_tx_v5_timing_priority_geometry.py']:
            bound=baseline['layout']['inputs']if method.endswith('_assembly.py')else gp['inputs']
            assert sha(ROOT/method)==bound[str(ROOT/method)]
        assert sha(ROOT/'scripts/plan_tx_v5_timing_priority_rows.py')==baseline['planner_sha256']
        result['independent_data_route_geometry']=gp

        # Preserve every prior placement/return/child gate on the immutable baseline.
        # New physical verification independently proves the only allowed width delta.
        result['baseline_data_route_geometry']=gp
        gp=json.loads((out/'geometry-delta.json').read_text())
        assert gp==physical['geometry_delta']and physical['sources_unchanged']
        assert gp['status']=='PASS_EXACT28_PARENT_SIGNAL_WIDTHS_NATIVE_DEVICES_VIAS_PORTS_AND_THREE_FAULTS'
        assert gp['original_vias_children_placements_pins_and_other_layers_equal']and gp['serialized_gds_verified']
        assert gp['widths_um']==dict(original=4.,candidate=2.4,retained_landings=4.)
        assert {x['name']for x in gp['controls']}=={'restore_removed_wide_metal','cut_actual_narrow_trunk','change_native_child_geometry'}
        assert all(x['rejected']for x in gp['controls'])and len(gp['controls'])==3
        assert gp['source_gds_sha256']==basepin['layout_outputs'][top+'.gds']
        assert gp['candidate_gds_sha256']==physical['layout']['outputs'][top+'.gds']
        assert physical['physical_source']['summary_sha256']==basepin['summary_sha256']
        assert physical['outputs']['source/verify-tree32.py']==basepin['outputs']['verify-tree32.py']
        assert physical['layout']['outputs']==receipt['layout_outputs']
        for key in ('ports','bbox_um','placements','origin_translation_um','total_devices','core_devices','substrate_contacts','parent_signal_centerline_sum_um','parent_signal_centerline_max_um'):
            assert physical['layout'][key]==baseline['layout'][key],key
        for ext in ('.lef',):
            assert physical['layout']['outputs'][top+ext]==baseline['layout']['outputs'][top+ext]
        assert physical['layout']['outputs']['schematic.cir']==baseline['layout']['outputs']['schematic.cir']
        changed=[]
        for old,new in zip(baseline['layout']['signal_routes'],physical['layout']['signal_routes'],strict=True):
            wanted=dict(old)
            if not old['net'].startswith('p16_'):
                wanted.update(width_um=2.4,landing_width_um=4.);changed.append(old['net'])
            assert new==wanted
        assert changed==gp['changed_routes']and len(changed)==28
        from check_tx_fast_wire24_sources import check as current_geometry
        current_geometry()
        result['independent_data_route_geometry']=gp
        layout=physical['layout']
        assert layout['total_devices']==1674 and len(layout['ports'])==162
        assert len(layout['signal_routes'])==60 and layout['frozen_child_drawing_regions_equal']
        assert len(layout['placements'])==31
        assert sum(v['kind']=='pre_low'for v in layout['placements'].values())==28
        for gate in ('lvs','lvs_flat'):
            audit=physical['physical']['steps'][gate]['audit']
            assert audit['status']=='PASS within comparison scope'and not audit['extraction_diagnostics']
            assert audit['circuit_status_counts']=={'Match':1}and len(audit['circuits'])==1
            assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==1674
        drc=physical['physical']['steps']['drc']['measurement']
        assert drc['markers']==0 and drc['category_count']==560
        assert all(physical['physical']['steps'][n]['status']=='REJECTED_EXPECTED_FAULT'for n in ('wrong_finger_count','missing_hbt','q_open','rail_short','offgrid'))
        for name,digest in layout['outputs'].items():assert sha(out/'layout'/name)==digest
        frozen_geometry={str(p):sha(p)for sub in ('layout','physical')for p in (out/sub).rglob('*')if p.is_file()}
        # Expected source topology, independently checked against native LVS
        # below:31*17 conductors minus90 shared-rail merges minus60 wires=377.
        # Each macro has100 metal and54 intrinsic body terminal references.
        result['expected_census']=dict(devices=1674,terminals=4774,metal_terminals=3100,
            intrinsic_body_terminals=1674,ports=162,probes=3262,wire_components=377,nets_including_body=378)
        rt = out / 'magic-cloud'
        rt.mkdir()
        fetch(runtime['receipt']['url'], runtime['receipt']['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(rt, filter='data')
        archive.unlink()
        manifest = json.loads((rt / 'manifest.json').read_text())
        assert all(sha(rt / n) == r['sha256'] for n, r in manifest['files'].items())
        raw = ROOT / 'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True, exist_ok=True)
        fetch(spec['raw_parser']['url'], spec['raw_parser']['sha256'], raw)

        wire = out / 'wire96'
        wire.mkdir()
        originals = out / 'frozen-extraction-methods'
        originals.mkdir()
        fetch(spec['method_archive']['url'], spec['method_archive']['sha256'], archive)
        edits = {}
        with tarfile.open(archive) as tar:
            for name, digest in spec['methods'].items():
                data = tar.extractfile(name).read()
                target = originals / Path(name).name
                target.write_bytes(data)
                assert sha(target) == digest
                source = data.decode()
                changes = []
                # Scope changes are exact device/port counts, not weakened
                # geometry, graph, RC conservation or negative-control gates.
                replacements={
                    'probe01.py': [('c.pin_count()==12','c.pin_count()==162'),
                        ('dict(npn13G2=19,rppd=8,ptap1=27)','dict(npn13G2=589,rppd=248,ptap1=837)')],
                    'locate01.py': [('len(physical)==54','len(physical)==1674'),('len(used)==54','len(used)==1674'),
                        ('PASS_ALL_54_DEVICES','PASS_ALL_1674_DEVICES')],
                    'anchors01.py': [('len(rows)==154 and len(anchors)==112','len(rows)==4774 and len(anchors)==3262'),
                        ('PASS_154_NATIVE_TERMINALS_WITH_100_METAL_AND_54_BODY_REFERENCES','PASS_4774_NATIVE_TERMINALS_WITH_3100_METAL_AND_1674_BODY_REFERENCES'),('public_ports=12','public_ports=162')],
                    'dedup01.py': [('len(anchors)>12','len(anchors)>162')],
                    'audit-rc48.py': [
                        ("==['18']","==['378']"), ("==['17']","==['377']"),
                        ('len(nodes)==17','len(nodes)==377'),
                        ('set(range(1,18))','set(range(1,378))',2),
                        ("len(before['ports'])==17","len(before['ports'])==377"),
                        ("len(connected)==17 and len({c['component'] for c in connected})==17",
                         "len(connected)==377 and len({c['component'] for c in connected})==377"),
                        ('len(retire)==17','len(retire)==377'),('len(markers)==17','len(markers)==377'),
                        ('connected_wire_components=17','connected_wire_components=377'),
                        ('collapsed_matrix_entries=18**2','collapsed_matrix_entries=378**2'),
                        ('len(a)==112','len(a)==3262'),
                        ('ACTUAL_TERMINAL_METAL_POINT_REFERENCE=100,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=54','ACTUAL_TERMINAL_METAL_POINT_REFERENCE=3100,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=1674'),
                        ('len(native_rows)==154','len(native_rows)==4774'),('len(ports)==112','len(ports)==3262'),
                        ("len(after['ports'])==112","len(after['ports'])==3262"),
                        ('original_devices=54,public_ports=12,physical_wire_components=17,geometry_probes=112,logical_metal_references=100,metal_device_terminals=100',
                         'original_devices=1674,public_ports=162,physical_wire_components=377,geometry_probes=3262,logical_metal_references=3100,metal_device_terminals=3100'),
                        ('unmodeled_body_well_terminals=54','unmodeled_body_well_terminals=1674')],
                }
                for replacement in replacements.get(target.name,[]):
                    before,after,*count=replacement;expected=count[0] if count else 1
                    assert source.count(before)==expected,(target.name,before)
                    source=source.replace(before,after);changes.append(dict(before=before,after=after,count=expected))
                if args.circuit_profile!='baseline':
                    before='nssoc_tx_mux2_passive_topmetal_layout_v1'
                    after=spec['circuits'][args.circuit_profile]['top']
                    if before in source:
                        changes.append(dict(before=before,after=after,count=source.count(before)))
                        source=source.replace(before,after)
                for before, after in (
                    ("/'layout91/", "/'layout/"),
                    ("/'physical92/", "/'physical/"),
                    ("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')", "B.parent/'magic-cloud/runtime/lib'"),
                    ("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')", "B.parent/'magic-cloud/tech'"),
                ):
                    if before in source:
                        changes.append(dict(before=before, after=after, count=source.count(before)))
                        source = source.replace(before, after)
                if target.name == 'mutations48.py':
                    # Use two real distinct TX ports, not inherited PLL names.
                    before = 'R_EXTRA P_cp P_cn 1'
                    assert source.count(before) == 1
                    source = source.replace(before, 'R_EXTRA P_mp P_mn 1')
                    changes.append(dict(before=before, after='R_EXTRA P_mp P_mn 1', count=1))
                    # A new layout can make the first exported R a bridge.
                    # Preserve the dedicated topology-mismatch negative control
                    # by removing one actual non-bridge R, rather than accepting
                    # a different early rejection or weakening the clean audit.
                    selector = "# Select one real R whose deletion preserves every connected component.\nresistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\\d+ \\S+ \\S+ \\S+',line)]\nassert len(resistor_rows)==len(parsed['resistors'])\nfrom collections import Counter\nedge_counts=Counter(frozenset((f[1],f[2])) for i,f in resistor_rows)\nbridges={frozenset(e) for e in nx.bridges(graph)}\ndrop_index,drop_fields=next((i,f) for i,f in resistor_rows if edge_counts[frozenset((f[1],f[2]))]>1 or frozenset((f[1],f[2])) not in bridges)\ndropped_rows=rows[:drop_index]+rows[drop_index+1:]\ndropped_text='\\n'.join(dropped_rows)+'\\n'\ndropped_parsed=m.rawparser.parse_spice(dropped_text)\nassert len(dropped_parsed['resistors'])==len(parsed['resistors'])-1\nkept_graph=nx.Graph();kept_graph.add_edges_from((x,y) for x,y,v in dropped_parsed['resistors'])\nassert set(kept_graph)==set(graph)\nassert {frozenset(c) for c in nx.connected_components(kept_graph)}=={frozenset(c) for c in nx.connected_components(graph)}\n"
                    before = 'cases=[\n'
                    assert source.count(before)==1
                    after = selector + before
                    source=source.replace(before,after)
                    changes.append(dict(before=before,after=after,count=1))
                    before = "re.sub(r'^R\\d+ .*\\n','',text,count=1,flags=re.M)"
                    assert source.count(before)==1
                    source=source.replace(before,'dropped_text')
                    changes.append(dict(before=before,after='dropped_text',count=1))
                (wire / target.name).write_text(source)
                edits[target.name] = dict(original_sha256=digest, adapted_sha256=sha(wire / target.name), changes=changes)
        archive.unlink()
        result['method_adaptations'] = edits
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        if wide64:
            result['geometry_delta']=json.loads((out/'geometry-delta.json').read_text())
            assert result['geometry_delta']==physical['geometry_delta']==gp
            assert all(c['rejected']for c in gp['controls'])and len(gp['controls'])==3
            assert gp['status']=='PASS_EXACT28_PARENT_SIGNAL_WIDTHS_NATIVE_DEVICES_VIAS_PORTS_AND_THREE_FAULTS'
        for method in ('probe01.py', 'locate01.py', 'anchors01.py', 'dedup01.py'):
            run([app, 'python', wire / method], method)
        graph=json.loads((wire/'native05/result.json').read_text())
        assert graph['wire_component_count']==377 and graph['native_electrical_net_count']==378
        assert graph['native_device_count']==1674 and graph['native_terminal_count']==4774
        # This census is independently established from actual GDS/LVS ownership,
        # not inferred from whatever number the resistor exporter prints.
        result['native_geometry_census']={k:graph[k] for k in ('wire_component_count','native_electrical_net_count','native_device_count','native_terminal_count')}
        run([sys.executable, wire / 'run-rc01.py'], 'native-extraction')
        capture = json.loads((wire / 'rc03/result.json').read_text())
        result['capture'] = capture
        assert capture['returncode'] == 0 and capture['status'] == 'NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        run([sys.executable, wire / 'audit-rc48.py', wire / 'rc03',
             wire / 'anchors08.json', wire / 'audit.json'], 'native-audit')
        audit = json.loads((wire / 'audit.json').read_text())
        result['audit'] = audit
        assert audit['status'] == 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable, wire / 'mutations48.py'], 'native-fault-controls')
        controls = json.loads((wire / 'native-mutations01.json').read_text())
        result['controls'] = controls
        assert controls['status'] == 'PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert all(sha(Path(n)) == digest for n, digest in frozen_geometry.items())
        assert all(sha(rt / n) == r['sha256'] for n, r in manifest['files'].items())
        result['status'] = 'PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        out.mkdir(parents=True, exist_ok=True)
        (out / 'extraction-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result[k] for k in ('status', 'variant', 'adopted')}), flush=True)


if __name__ == '__main__':
    main()
