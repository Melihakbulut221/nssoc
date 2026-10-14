#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume the newer exact postCTS chip on hosted runners with fresh routing."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tarfile
from read_opensta_phase_slacks import parse_phases

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-newer-postcts'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, expected, path):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', url, '-o', str(path)], check=True)
    assert sha(path) == expected, path


def execute(script, label):
    tcl = OUT / (label + '.tcl')
    tcl.write_text(script)
    log = OUT / (label + '.log')
    with log.open('w') as stream:
        process = subprocess.Popen([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', str(tcl)],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            stream.write(line)
            stream.flush()
            print(f'[{label}] {line}', end='', flush=True)
        code = process.wait()
    text = log.read_text(errors='replace')
    if code or re.search(r'(?m)^(Error:|\[ERROR)', text):
        print(text[-12000:], flush=True)
        raise RuntimeError((label, code))
    return text


def cugr_gate(text):
    """Independent fail-closed checks: CUGR's printed wire overflow is rounded.

    Also require zero overflowing nets and nonnegative floating resource,
    then the original full routed-net count. This is an experimental guide
    screen only; detailed routing/DRC, connectivity and extracted STA remain.
    """
    nets = re.findall(r'(?m)^(\d+) / (\d+) nets have overflow\.$', text)
    wire = re.findall(r'(?m)^total wire overflow:\s+(\S+)\s*$', text)
    resource = re.findall(r'(?m)^min resource:\s+(\S+)\s*$', text)
    routed = re.findall(r'\[INFO GRT-0014\] Routed nets: (\d+)', text)
    assert nets and len(wire)==1 and len(resource)==1 and len(routed)==1, 'Incomplete CUGR report'
    bad, total = map(int,nets[-1]); overflow=float(wire[0]); minimum=float(resource[0])
    assert total>0 and bad==0, 'CUGR nets still overflow'
    assert math.isfinite(overflow) and overflow==0, 'CUGR wire overflow'
    assert math.isfinite(minimum) and minimum>=0, 'CUGR fractional resource deficit'
    assert int(routed[0])==113556, 'Original full-chip routed-net coverage changed'
    return dict(overflowing_nets=bad,solver_nets=total,total_wire_overflow=overflow,
        minimum_resource=minimum,routed_nets=int(routed[0]),
        scope='Experimental CUGR native guide screen, not detailed-route/signoff acceptance')


def self_test():
    good='0 / 113556 nets have overflow.\ntotal wire overflow:   0\nmin resource: 0\n[INFO GRT-0014] Routed nets: 113556\n'
    assert cugr_gate(good)['routed_nets']==113556
    faults=[good.replace('0 /','1 /'),good.replace('overflow:   0','overflow:   1'),
        good.replace('resource: 0','resource: -0.000001'),good.replace('resource: 0','resource: nan'),
        good.replace('overflow:   0','overflow:   inf'),good.replace('nets: 113556','nets: 113555')]
    faults += ['\n'.join(good.splitlines()[:i]+good.splitlines()[i+1:])+'\n' for i in range(4)]
    for bad in faults:
        try: cugr_gate(bad)
        except (AssertionError,ValueError): continue
        raise AssertionError('Incomplete/overflowing CUGR control accepted')
    print(json.dumps(dict(status='PASS_CUGR_FAIL_CLOSED_CONTROLS',positive=1,negative=len(faults))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grid-profile', choices=['baseline'], default='baseline')
    parser.add_argument('--placement-profile', choices=['none','left_compact','left_spread','local_optimize','local_optimize_buffers','local_data_endpoints','routability_data'], default='none')
    parser.add_argument('--ethernet-hold-depth', type=int, choices=[0,2], default=0)
    parser.add_argument('--macro-routing-profile', choices=['baseline','reserve_m5','halo1'], default='baseline')
    parser.add_argument('--critical-nets-percentage', type=int, choices=[0,30], default=0)
    parser.add_argument('--routing-seed', type=int, choices=[0,13], default=0)
    parser.add_argument('--router-solver', choices=['fast_route','cugr'], default='fast_route')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--cugr-empty-net-cleanup', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if args.cugr_empty_net_cleanup:
        assert args.router_solver=='cugr'
    if args.router_solver=='cugr':
        assert args.placement_profile=='local_optimize_buffers' and args.ethernet_hold_depth==2
        assert args.macro_routing_profile=='baseline' and args.routing_seed==13
        assert args.critical_nets_percentage==0 and args.grid_profile=='baseline'
        self_test()
    if args.routing_seed:
        assert args.critical_nets_percentage == 0
        assert args.placement_profile in ('local_optimize_buffers','routability_data')
        assert args.ethernet_hold_depth == 2 and args.macro_routing_profile in ('baseline', 'halo1')
    if args.critical_nets_percentage:
        assert args.placement_profile == 'local_optimize_buffers'
        assert args.ethernet_hold_depth == 2 and args.macro_routing_profile == 'baseline'
        assert args.grid_profile == 'baseline'

    # Frozen OpenROAD dcf36133 uses grid_origin only when saving guides.
    # Nonzero values did not move the routing partition (run38472175339).
    # Reject these obsolete trials through argparse rather than repeating them.
    if args.placement_profile == 'routability_data':
        assert args.routing_seed == 13 and args.ethernet_hold_depth == 2
        assert args.macro_routing_profile == 'baseline' and args.critical_nets_percentage == 0
    origin_um = (0., 0.)
    if args.macro_routing_profile == 'halo1':
        assert args.routing_seed == 13 and args.critical_nets_percentage == 0
        assert args.placement_profile == 'local_optimize_buffers'
        assert args.ethernet_hold_depth == 2
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False,
        grid_profile=args.grid_profile, grid_origin_um=origin_um, placement_profile=args.placement_profile,
        ethernet_hold_depth=args.ethernet_hold_depth,
        macro_routing_profile=args.macro_routing_profile,
        critical_nets_percentage=args.critical_nets_percentage, routing_seed=args.routing_seed,
        routing_capacity_perturbation_percentage=0, router_solver=args.router_solver,
        scope='Newer packet-interface chip with Ethernet cross-read pipeline, replay successor and RX-return metadata. Exact saved postCTS readback precedes fresh global routing. No full serial PHY, detailed route, extracted signoff or adoption.')
    def save():
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    try:
        spec = json.loads((ROOT / 'docs/evidence/cloud-newer-postcts-input-20261013.json').read_text())
        inputs = OUT / 'inputs'
        inputs.mkdir()
        for group in spec['archives']:
            pin = group['archive']
            packed = OUT / pin['name']
            fetch(pin['url'], pin['sha256'], packed)
            assert packed.stat().st_size == pin['bytes']
            with tarfile.open(packed) as tar:
                for local, record in group['members'].items():
                    member = tar.getmember(record['path'])
                    assert member.isfile() or member.islnk()
                    # extractfile resolves tar hard links in the archive only.
                    data = tar.extractfile(member).read()
                    assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
                    (inputs / local).write_bytes(data)
            packed.unlink()
        prior = json.loads((inputs / 'prior-result.json').read_text())
        physical = json.loads((inputs / 'physical-result.json').read_text())
        assert prior['status'] == 'COMPLETE_PLACEMENT_ESTIMATED_NOT_SIGNOFF' and prior['unchanged']
        assert physical['status'] == 'POSTCTS_RETURNED_REQUIRES_ALLGROUP_READBACK' and physical['unchanged'] and physical['returncode'] == 0
        libspec = json.loads((ROOT / 'docs/evidence/cloud-routed-setup-input-20261012.json').read_text())
        packed = OUT / 'libraries.tar.gz'
        fetch(libspec['archive_url'], libspec['sha256'], packed)
        libs = OUT / 'library-inputs'
        with tarfile.open(packed) as tar:
            tar.extractall(libs, filter='data')
        packed.unlink()
        replacements = {}
        for old, digest in prior['inputs'].items():
            if old.endswith('.lib'):
                matches = [p for p in libs.rglob(Path(old).name) if sha(p) == digest]
                assert len(matches) == 1, old
                replacements[old] = str(matches[0])
            elif old.endswith('.odb'):
                assert sha(inputs / 'postcts.odb') == digest
                replacements[old] = str(inputs / 'postcts.odb')
            elif old.endswith('.sdc'):
                assert sha(inputs / 'physical.sdc') == digest
                replacements[old] = str(inputs / 'physical.sdc')
        assert len(replacements) == 11
        script = (inputs / 'prior.tcl').read_text()
        assert sha(inputs / 'prior.tcl') == prior['outputs']['screen.tcl']
        assert sha(inputs / 'prior.log') == prior['outputs']['screen.log']
        for old, new in replacements.items():
            assert script.count(old) == 1, old
            script = script.replace(old, new)
        assert '/home/hasanmelih' not in script
        protected = {str(p): sha(p) for p in [*inputs.iterdir(), *(Path(p) for p in replacements.values())]}
        result['source_inputs'] = protected
        original = parse_phases((inputs / 'prior.log').read_text(), 'CORNER')
        replay = parse_phases(execute(script, 'reproduced-postcts'), 'CORNER')
        assert replay.keys() == original.keys()
        for phase, value in original.items():
            assert value['groups'].keys() == replay[phase]['groups'].keys()
            for group, v in value['groups'].items():
                assert abs(v['worst_slack_ns'] - replay[phase]['groups'][group]['worst_slack_ns']) <= 1e-6, (phase, group)
        result['postcts_reproduced'] = replay
        result['status'] = 'EXACT_POSTCTS_REPRODUCED_STARTING_FRESH_GLOBAL_ROUTE'
        save()
        placement_source=inputs/'postcts.odb'
        if args.ethernet_hold_depth:
            evidence=json.loads((ROOT/'docs/evidence/cloud-ethernet-hold-estimate-20261013.json').read_text())
            case=next(c for c in evidence['cases'] if c['depth']==args.ethernet_hold_depth)
            packed=OUT/'ethernet-hold-source.tar.gz'
            fetch(case['archive']['url'],case['archive']['sha256'],packed)
            assert packed.stat().st_size==case['archive']['bytes']
            with tarfile.open(packed) as archive:
                raw=archive.extractfile('cloud-ethernet-hold/result.json').read()
                assert hashlib.sha256(raw).hexdigest()==case['summary_sha256']
                hold=json.loads(raw)
                assert hold['status']=='COMPLETE_NATIVE_GMII_HOLD_ECO_ESTIMATE_NOT_SIGNOFF'
                assert hold['logic']['status']=='PASS within scope'
                assert hold['inversion_control']=='EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
                assert hold['no_new_violation_or_worsened_existing_negative_group']
                assert hold['all_corner_gmii_output_hold_nonnegative']
                assert hold['geometry']['retained_instances']==113771 and hold['geometry']['added_instances']==20
                raw=archive.extractfile('cloud-ethernet-hold/candidate.odb').read()
                assert hashlib.sha256(raw).hexdigest()==case['candidate_odb_sha256']==hold['outputs']['candidate.odb']
            packed.unlink()
            placement_source=inputs/'ethernet-hold.odb';placement_source.write_bytes(raw)
            protected[str(placement_source)]=sha(placement_source)
            script=script.replace(str(inputs/'postcts.odb'),str(placement_source))
            measured=parse_phases(execute(script,'reproduced-ethernet-hold'),'CORNER')
            for phase,row in measured.items():
                assert set(row['groups'])==set(case['candidate'][phase])
                for group,value in row['groups'].items():
                    assert abs(value['worst_slack_ns']-case['candidate'][phase][group])<=1e-6,(phase,group)
                    assert abs(replay[phase]['groups'][group]['worst_slack_ns']-case['baseline'][phase][group])<=1e-6
            result['ethernet_hold']=dict(evidence=case,exact_placement_timing_reproduced=measured)
            save()
        if args.placement_profile != 'none':
            if args.placement_profile in ('local_data_endpoints','routability_data'):
                assert args.ethernet_hold_depth==2 and args.macro_routing_profile=='baseline'
                incremental_evidence = ('docs/evidence/cloud-seed13-buffers-route-failure-20261014.json'
                    if args.placement_profile == 'routability_data' else 'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json')
                evidence=json.loads((ROOT/incremental_evidence).read_text())
                assert evidence['status']=='FAILED_NATIVE_GLOBAL_ROUTE_CONGESTION'
                packed=OUT/'previous-placement.tar.gz'
                pin=evidence['receipt'];fetch(pin['url'],pin['sha256'],packed)
                assert packed.stat().st_size==pin['bytes']
                with tarfile.open(packed) as archive:
                    raw=archive.extractfile('cloud-newer-postcts/result.json').read()
                    assert hashlib.sha256(raw).hexdigest()==evidence['summary_sha256']
                    previous=json.loads(raw)
                    assert previous['status']=='FAIL_OR_ERROR'
                    assert previous['placement_profile']=='local_optimize_buffers' and previous['ethernet_hold_depth']==2
                    for local,member in [('previous-relocated.odb','relocated-placement.odb'),
                                         ('previous-failed-global.odb','failed-global.odb')]:
                        raw=archive.extractfile('cloud-newer-postcts/'+member).read()
                        assert hashlib.sha256(raw).hexdigest()==evidence['failure_outputs'][member]
                        (inputs/local).write_bytes(raw);protected[str(inputs/local)]=sha(inputs/local)
                packed.unlink()
                script=script.replace(str(placement_source),str(inputs/'previous-relocated.odb'))
                placement_source=inputs/'previous-relocated.odb'
                measured=parse_phases(execute(script,'reproduced-previous-placement'),'CORNER')
                expected=previous['relocated_placement_timing']
                assert set(measured)==set(expected)
                for phase,row in measured.items():
                    assert set(row['groups'])==set(expected[phase]['groups'])
                    for group,value in row['groups'].items():
                        assert abs(value['worst_slack_ns']-expected[phase]['groups'][group]['worst_slack_ns'])<=1e-6,(phase,group)
                result['incremental_source']=dict(failed_run=evidence['run'], source_odb_sha256=sha(placement_source), exact_placement_timing_reproduced=measured)
                if args.placement_profile == 'routability_data':
                    fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38471402795-1-congestion-seed13_buffers/newer-congestion-probe-38471402795-1.json',
                          'ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b',OUT/'endpoint-diagnosis.json')
                else:
                    fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38392685463-1-congestion-local_optimize_buffers/newer-congestion-probe-38392685463-1.json',
                          '962bf2b58b82799d346cb48a45a5af1d88fac6c10a2b582a2c41fc445000917f',OUT/'endpoint-diagnosis.json')
            else:
                fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/newer-congestion-probe-38333836529-1.json',
                      '1d19f4d2bdf24f865144b28c57060c3cfed96ac3d0a4a79b23ce23f12c0a027c',OUT/'endpoint-diagnosis.json')
            def native_placement(mode):
                with (OUT/f'placement-{mode}.log').open('w') as log:
                    code=subprocess.call([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',
                                          str(ROOT/'scripts/repair_cloud_macro_channels.py')],
                        env=dict(os.environ,NSSOC_PLACEMENT_MODE=mode,NSSOC_PLACEMENT_PROFILE=args.placement_profile,
                                 NSSOC_ETHERNET_HOLD_DEPTH=str(args.ethernet_hold_depth)),
                        stdout=log,stderr=subprocess.STDOUT)
                assert code==0,(mode,code,(OUT/f'placement-{mode}.log').read_text()[-6000:])
            native_placement('prepare')
            placement_command=('improve_placement -max_displacement {20 8}' if args.placement_profile in ('local_optimize','local_optimize_buffers','local_data_endpoints')
                               else 'detailed_placement -max_displacement {200 100}')
            if args.placement_profile == 'routability_data':
                # Frozen dcf36133 GPL: skip initial placement; RUDY-directed
                # inflation spreads only selected combinational data cells.
                # Timing-driven resize is OFF (native default). No circuit ECO.
                placement_command = ('set_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\n'
                    'set_global_routing_layer_adjustment Metal1-TopMetal2 0.2\n'
                    'help global_placement\n'
                    'global_placement -skip_initial_place -routability_driven -density 0.55\n'
                    'detailed_placement')
                result['routability_placement'] = dict(target_density=0.55,
                    source_run=evidence['run'], clock_and_sequential_cells_fixed=True,
                    sram_and_boundary_pins_fixed=True, proven_hold_eco_cells_fixed=True,
                    native_timing_driven_resize=False, routing_capacity_inflated=False,
                    native_commit='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0',
                    scope='Candidate placement only; complete native invariants, all-corner STA and zero-overflow global route required. No signoff.')
            execute(f'read_db {{{OUT/"proposed-placement.odb"}}}\n'
                    f'set_thread_count 2\n{placement_command}\n'
                    'check_placement -verbose\n'
                    f'write_db {{{OUT/"legalized-placement.odb"}}}\n','legalize-macro-channels')
            native_placement('verify')
            result['placement_repair']=json.loads((OUT/'placement-repair.json').read_text())
            script=script.replace(str(placement_source),str(OUT/'relocated-placement.odb'))
            result['relocated_placement_timing']=parse_phases(execute(script,'relocated-placement-sta'),'CORNER')
            assert result['relocated_placement_timing'].keys()==replay.keys()
            result['status']='PLACEMENT_INVARIANTS_AND_STA_COMPLETE_GLOBAL_ROUTE_PENDING'
            save()
            if os.environ.get('GITHUB_ACTIONS')=='true':
                checkpoint=OUT/(f'newer-postcts-placement-{args.placement_profile}-'
                    f'{os.environ["GITHUB_RUN_ID"]}-{os.environ["GITHUB_RUN_ATTEMPT"]}.pre-route.json')
                checkpoint.write_text(json.dumps(result,indent=2)+'\n')
                from publish_cloud_results import publish_results
                publish_results('route-'+args.placement_profile, [checkpoint])
        if (args.critical_nets_percentage or args.routing_seed) and args.placement_profile != 'routability_data':
            # Resume the same135overflow candidate, not the rejected420overflow
            # endpoint move. Reject any nondeterministic placement difference.
            evidence=json.loads((ROOT/'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json').read_text())
            expected=evidence['failure_outputs']['relocated-placement.odb']
            assert sha(OUT/'relocated-placement.odb') == expected, 'Routing comparison changed placement'
            result['routing_order_source' if args.routing_seed else 'routing_priority_source'] = dict(run=evidence['run'],
                placement_sha256=expected, source_evidence_sha256=sha(ROOT/'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json'),
                scope=('Native net ordering seed13; capacity perturbation is explicitly zero. ' if args.routing_seed else 'Native timing-critical net preference changes. ')+'Same cells, placement, SDC, PDK RC, routing layers, layer adjustment and zero-overflow gate. Any conservative macro halo is recorded separately. Requires actual routing and all-corner timing.')
            save()
        if args.cugr_empty_net_cleanup:
            fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38590905780-1-congestion-seed13_buffers/newer-congestion-probe-38590905780-1.json',
                'f1d71b542a4e46f5475ee77bd4e4b7f58c5c05f6aad91e1f0151d7400c68b5b8', OUT/'cugr-empty-net-diagnosis.json')
            native_placement('prepare_cugr')
            result['cugr_input_cleanup']=json.loads((OUT/'cugr-input-proof.json').read_text())
            assert result['cugr_input_cleanup']['status']=='PASS_EXACT_THREE_ZERO_TERMINAL_DECLARATIONS_REMOVED'
            script=script.replace(str(OUT/'relocated-placement.odb'),str(OUT/'cugr-input.odb'))
            assert str(OUT/'cugr-input.odb') in script
            protected[str(OUT/'cugr-input.odb')]=sha(OUT/'cugr-input.odb')
            save()
        rc = json.loads((ROOT / 'docs/evidence/cloud-global-route-rc-20261013.json').read_text())
        prefix = script.split('set_wire_rc -signal')[0]
        commands = [prefix, 'set_thread_count 2', 'check_placement -verbose',
                    'set_cmd_units -resistance kOhm -capacitance pF -time ns']
        for corner in ('slow', 'typical', 'fast'):
            for layer, values in rc['layers_rc'].items():
                commands.append(f'set_layer_rc -corner {corner} -layer {layer} -resistance {values["res"]} -capacitance {values["cap"]}')
            for via, resistance in rc['vias_r'].items():
                commands.append(f'set_layer_rc -corner {corner} -via {via} -resistance {resistance}')
            commands += [f'set_wire_rc -corner {corner} -signal -layer Metal2', f'set_wire_rc -corner {corner} -clock -layer Metal4']
        commands += [f'set_routing_layers -signal {rc["routing_layers"]} -clock {rc["routing_layers"]}',
                     f'set_global_routing_layer_adjustment Metal1-TopMetal2 {rc["adjustment"]}',
                     'set route_dbu [[ord::get_db_block] getDbUnitsPerMicron]']
        if args.macro_routing_profile == 'halo1':
            # Exact runtime GlobalRouter.cpp:4705-4716 grows each macro OBS by
            # one native tile in the direction perpendicular to its tracks.
            # This only reserves more routing space, never creates capacity.
            source=json.loads((ROOT/'docs/evidence/cloud-seed13-buffers-route-failure-20261014.json').read_text())
            assert sha(OUT/'relocated-placement.odb') == source['failure_outputs']['relocated-placement.odb']
            commands += ['help set_macro_extension', 'set_macro_extension 1',
                         'puts NSSOC_MACRO_OBSTRUCTION_EXTENSION_ONE_GCELL']
            result['macro_halo_comparison'] = dict(baseline_run=source['run'],
                exact_placement_sha256=source['failure_outputs']['relocated-placement.odb'],
                macro_extension_gcells=1, native_default_gcells=0,
                runtime_commit='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0',
                source_url='https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/GlobalRouter.cpp#L4705',
                scope='Conservative native macro obstruction halo on exact seed13 placement. No guide offset, OBS removal, capacity inflation, port exclusion, congestion waiver or timing exception. Fresh global routing and all-corner timing required.')
            save()
        if args.macro_routing_profile == 'reserve_m5':
            # Native diagnosis found through-nets over obstructed SRAM bodies,
            # while actual macro signal pins are on Metal2, not Metal5. Reserve
            # Metal5 only over these four exact macros so GRT must choose other
            # legal layers or go around. Never inflate capacity or remove OBS.
            evidence_path = ROOT/'docs/evidence/cloud-sram-pin-access-20261013.json'
            evidence = json.loads(evidence_path.read_text())
            assert evidence['status'] == 'PASS_EXACT_CONGESTION_CONNECTIVITY_DIAGNOSIS_NOT_ROUTE_CLOSURE'
            macros = evidence['macro_pin_access']
            assert len(macros) == 4
            regions = []
            for name, macro in sorted(macros.items()):
                assert '{' not in name and '}' not in name
                assert macro['master'] == 'RM_IHPSG13_2P_256x16_c2_bm_bist'
                assert {p['layer'] for p in macro['pin_shapes'] if p['signal_type']=='SIGNAL'} == {'Metal2'}
                bounds = macro['bbox_um']
                commands += [f'set hotspot_inst [[ord::get_db_block] findInst {{{name}}}]',
                    'if {[[$hotspot_inst getMaster] getName] ne {'+macro['master']+'}} {error "SRAM master changed"}',
                    'if {[$hotspot_inst getOrient] ne {'+macro['orientation']+'}} {error "SRAM orientation changed"}',
                    'set hotspot_bbox [$hotspot_inst getBBox]']
                for getter, value in zip(('xMin','yMin','xMax','yMax'), bounds, strict=True):
                    commands.append(f'if {{[$hotspot_bbox {getter}] != round({value} * $route_dbu)}} {{error "SRAM region changed"}}')
                commands.append('set_global_routing_region_adjustment {'+' '.join(map(str,bounds))+'} -layer Metal5 -adjustment 1.0')
                regions.append(dict(instance=name, master=macro['master'], bbox_um=bounds,
                                    layer='Metal5', adjustment=1.0))
            result['macro_routing_reservation'] = dict(source_evidence_sha256=sha(evidence_path),
                regions=regions, scope='Conservative GRT resource restriction only; native SRAM pin shapes, OBS, placement, connectivity, SDC and capacity on other layers unchanged. Full routing and timing acceptance still required.')
            commands.append('puts "NSSOC_VERIFIED_FOUR_SRAM_METAL5_RESERVATIONS"')
            save()
        if args.routing_seed:
            # Net-order exploration only. Never randomize/inflate any edge capacity.
            commands += ['help set_global_routing_random',
                         f'set_global_routing_random -seed {args.routing_seed} -capacities_perturbation_percentage 0',
                         'puts NSSOC_NET_ORDER_ONLY_ZERO_CAPACITY_PERTURBATION']
        solver_option = ' -use_cugr' if args.router_solver=='cugr' else ''
        if solver_option:
            result['solver_comparison']=dict(baseline_run=38448901835,
                source='https://github.com/The-OpenROAD-Project/OpenROAD/tree/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt',
                experimental_not_production=True, unchanged_layer_adjustment=rc['adjustment'],
                scope='Exact132overflow placement, all nets and original SDC/RC. Native3D alternative; no capacity inflation, no regional adjustments ignored, no constraint waiver. Require independent zero-overflow/coverage checks; detailed route and extraction remain.')
            save()
        priority_option = ''
        if args.critical_nets_percentage:
            commands += ['estimate_parasitics -placement',
                         'puts NSSOC_TIMING_PRIORITY_30_SAME_PLACEMENT_AND_CAPACITY']
            priority_option = ' -critical_nets_percentage 30'
        commands += [
                     f'set route_origin [list [expr {{round({origin_um[0]} * $route_dbu)}}] [expr {{round({origin_um[1]} * $route_dbu)}}]]',
                     'puts "NSSOC_GUIDE_OFFSET_DBU_FIXED_ZERO $route_origin"',
                     f'if {{[catch {{global_route{solver_option}{priority_option} -grid_origin $route_origin -congestion_iterations 100 -congestion_report_file {{{OUT / "congestion.rpt"}}} -verbose}} route_error]}} {{',
                     f'  write_db {{{OUT / "failed-global.odb"}}}',
                     f'  catch {{write_guides {{{OUT / "failed-route.guide"}}}}}',
                     '  puts stderr "NSSOC_FAILED_ROUTE_PARTIAL_STATE_ONLY $route_error"',
                     '  exit 1', '}',
                     f'write_db {{{OUT / "global.odb"}}}', f'write_guides {{{OUT / "route.guide"}}}',
                     f'estimate_parasitics -global_routing -spef_file {{{OUT / "estimated"}}}',
                     'check_setup -verbose', 'report_parasitic_annotation -report_unannotated']
        for corner in ('slow', 'typical', 'fast'):
            for delay in ('max', 'min'):
                commands += [f'puts CORNER_{corner}_{delay}', f'report_checks -corner {corner} -path_delay {delay} -group_path_count 20 -fields {{slew cap fanout}} -digits 6']
            commands += [f'puts ELECTRICAL_{corner}', f'report_check_types -corner {corner} -max_slew -max_capacitance -max_fanout -violators -digits 6']
        route_script = '\n'.join(commands) + '\n'
        assert '-allow_congestion' not in route_script and '-infinite_cap' not in route_script
        routed = execute(route_script, 'global-route')
        if args.router_solver=='cugr':
            result['cugr_gate']=cugr_gate(routed)
        result['global_route'] = parse_phases(routed, 'CORNER')
        assert result['global_route'].keys() == replay.keys()
        for phase in replay:
            assert result['global_route'][phase]['groups'].keys() == replay[phase]['groups'].keys()
        assert all(sha(Path(p)) == digest for p, digest in protected.items())
        result['status'] = ('COMPLETE_EXPERIMENTAL_CUGR_GUIDES_REQUIRES_DETAILED_ROUTE_CONNECTIVITY_AND_EXTRACTION'
            if args.router_solver=='cugr' else 'COMPLETE_NEWER_CHIP_GLOBAL_ROUTE_REQUIRES_DETAILED_ROUTING_AND_EXTRACTION')
        result['outputs'] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'result.json'}
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        result['failure_outputs'] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'result.json'}
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
