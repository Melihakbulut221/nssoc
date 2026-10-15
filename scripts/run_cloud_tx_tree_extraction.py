#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract the real162-device4:1core and its intermacro metal with strict native RC audits."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

from run_cloud_tx_layout_repair import ROOT, fetch, sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--placement-profile',choices=('baseline','compact_vertical'),default='baseline')
    profile=parser.parse_args().placement_profile
    args=argparse.Namespace(variant='tree4',circuit_profile='assembly4',boundary_pins=True,
        boundary_policy='nearest_pair_tight',prepared_layout=False)
    expected_boundary_policy='nearest_pair_tight'
    spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
    spec['circuits']['assembly4']={'top':'nssoc_tx_tree4_core_v1'}
    runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
    tree=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    selected=tree if profile=='baseline' else tree['placement_variants'][profile]
    receipt=selected['verified_hierarchical_assembly']
    assert receipt.get('placement_profile','baseline')==profile
    assert receipt['devices']==162 and receipt['public_ports']==22
    if profile=='baseline':assert receipt['exact_flat_geometry_preserved']
    else:assert receipt['frozen_child_drawing_regions_equal'] and not receipt['exact_flat_geometry_preserved']
    out=ROOT/'hw/soc/out/cloud-tx-tree-assembly'
    assert not out.exists()
    out.parent.mkdir(parents=True,exist_ok=True)
    archive=out.parent/'cloud-tree-extraction-input.tar.gz'
    result = dict(status='RUNNING', placement_profile=profile, variant=args.variant, circuit_profile=args.circuit_profile, boundary_pins=args.boundary_pins, boundary_pin_policy=expected_boundary_policy, adopted=False,
                  qualified_pex=False, serial_phy_complete=False,
                  scope='Actual162-device three-macro4:1core, including real intermacro wires and shared supplies. Exact native RC graph, terminal ownership and C conservation required. Intrinsic body/substrate/RF qualification, loaded waves,32:1/four-lane/fullPHY and mainchip signoff remain open.',
                  physical_source=receipt, runtime_source=runtime, method_source=spec)

    def run(command, label):
        log = out / (label + '.log')
        with log.open('w') as stream:
            code = subprocess.call([str(x) for x in command], cwd=ROOT,
                                   stdout=stream, stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-12000:], flush=True)
            raise RuntimeError(f'{label}: exit {code}')

    try:
        if not args.prepared_layout:
            fetch(receipt['url'], receipt['sha256'], archive)
            assert archive.stat().st_size == receipt['bytes']
            with tarfile.open(archive) as tar:
                tar.extractall(ROOT, filter='data')
            archive.unlink()
        physical = json.loads((out / 'result.json').read_text())
        assert physical['status']=='PASS_ACTUAL_TREE162_NATIVE_DRC_LVS_FAULTS_REQUIRES_PARENT_RC_AND_WAVES'
        assert physical['layout'].get('placement_profile','baseline')==profile
        if profile=='baseline':assert physical['layout']['exact_flat_geometry_preserved']
        else:
            assert physical['layout']['frozen_child_drawing_regions_equal']
            assert physical['layout']['placement']['b']['transform']=='m90 353.985,330'
            assert physical['layout']['placement']['f']['transform']=='r0 550,112'
            assert [v['length_um'] for v in physical['layout']['routes'][:4]]==[356.015]*4
        assert physical['layout']['total_devices']==162 and len(physical['layout']['ports'])==22
        for gate in ('lvs','lvs_flat'):
            audit=physical['physical']['steps'][gate]['audit']
            assert audit['status']=='PASS within comparison scope' and not audit['extraction_diagnostics']
            assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==162
        assert physical['physical']['steps']['drc']['measurement']['markers']==0
        for name, digest in physical['layout']['outputs'].items():
            assert sha(out / 'layout' / name) == digest
        frozen_geometry = {str(p): sha(p) for sub in ('layout', 'physical')
                           for p in (out / sub).rglob('*') if p.is_file()}

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
                    'probe01.py': [('c.pin_count()==12','c.pin_count()==22'),
                        ('dict(npn13G2=19,rppd=8,ptap1=27)','dict(npn13G2=57,rppd=24,ptap1=81)')],
                    'locate01.py': [('len(physical)==54','len(physical)==162'),('len(used)==54','len(used)==162'),
                        ('PASS_ALL_54_DEVICES','PASS_ALL_162_DEVICES')],
                    'anchors01.py': [('len(rows)==154 and len(anchors)==112','len(rows)==462 and len(anchors)==322'),
                        ('PASS_154_NATIVE_TERMINALS_WITH_100_METAL_AND_54_BODY_REFERENCES','PASS_462_NATIVE_TERMINALS_WITH_300_METAL_AND_162_BODY_REFERENCES'),('public_ports=12','public_ports=22')],
                    'dedup01.py': [('len(anchors)>12','len(anchors)>22')],
                    'audit-rc48.py': [
                        ("==['18']","==['42']"), ("==['17']","==['41']"),
                        ('len(nodes)==17','len(nodes)==41'),
                        ('set(range(1,18))','set(range(1,42))',2),
                        ("len(before['ports'])==17","len(before['ports'])==41"),
                        ("len(connected)==17 and len({c['component'] for c in connected})==17",
                         "len(connected)==41 and len({c['component'] for c in connected})==41"),
                        ('len(retire)==17','len(retire)==41'),('len(markers)==17','len(markers)==41'),
                        ('connected_wire_components=17','connected_wire_components=41'),
                        ('collapsed_matrix_entries=18**2','collapsed_matrix_entries=42**2'),
                        ('len(a)==112','len(a)==322'),
                        ('ACTUAL_TERMINAL_METAL_POINT_REFERENCE=100,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=54','ACTUAL_TERMINAL_METAL_POINT_REFERENCE=300,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=162'),
                        ('len(native_rows)==154','len(native_rows)==462'),('len(ports)==112','len(ports)==322'),
                        ("len(after['ports'])==112","len(after['ports'])==322"),
                        ('original_devices=54,public_ports=12,physical_wire_components=17,geometry_probes=112,logical_metal_references=100,metal_device_terminals=100',
                         'original_devices=162,public_ports=22,physical_wire_components=41,geometry_probes=322,logical_metal_references=300,metal_device_terminals=300'),
                        ('unmodeled_body_well_terminals=54','unmodeled_body_well_terminals=162')],
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
        for method in ('probe01.py', 'locate01.py', 'anchors01.py', 'dedup01.py'):
            run([app, 'python', wire / method], method)
        graph=json.loads((wire/'native05/result.json').read_text())
        assert graph['wire_component_count']==41 and graph['native_electrical_net_count']==42
        assert graph['native_device_count']==162 and graph['native_terminal_count']==462
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
