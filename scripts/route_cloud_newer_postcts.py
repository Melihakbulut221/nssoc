#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume the newer exact postCTS chip on hosted runners with fresh routing."""
import argparse
import hashlib
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grid-profile', choices=['baseline', 'half_x', 'half_y', 'half_xy'], default='baseline')
    parser.add_argument('--placement-profile', choices=['none','left_compact','left_spread','local_optimize'], default='none')
    args = parser.parse_args()
    # The actual failed report has7.2um gcells. Half-cell offsets change only
    # partition alignment, never placement, routing capacity or physical rules.
    origin_um = {'baseline': (0., 0.), 'half_x': (3.6, 0.),
                 'half_y': (0., 3.6), 'half_xy': (3.6, 3.6)}[args.grid_profile]
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False,
        grid_profile=args.grid_profile, grid_origin_um=origin_um, placement_profile=args.placement_profile,
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
        if args.placement_profile != 'none':
            fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/newer-congestion-probe-38333836529-1.json',
                  '1d19f4d2bdf24f865144b28c57060c3cfed96ac3d0a4a79b23ce23f12c0a027c',OUT/'endpoint-diagnosis.json')
            def native_placement(mode):
                with (OUT/f'placement-{mode}.log').open('w') as log:
                    code=subprocess.call([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',
                                          str(ROOT/'scripts/repair_cloud_macro_channels.py')],
                        env=dict(os.environ,NSSOC_PLACEMENT_MODE=mode,NSSOC_PLACEMENT_PROFILE=args.placement_profile),
                        stdout=log,stderr=subprocess.STDOUT)
                assert code==0,(mode,code,(OUT/f'placement-{mode}.log').read_text()[-6000:])
            native_placement('prepare')
            placement_command=('improve_placement -max_displacement {20 8}' if args.placement_profile=='local_optimize'
                               else 'detailed_placement -max_displacement {200 100}')
            execute(f'read_db {{{OUT/"proposed-placement.odb"}}}\n'
                    f'set_thread_count 2\n{placement_command}\n'
                    'check_placement -verbose\n'
                    f'write_db {{{OUT/"legalized-placement.odb"}}}\n','legalize-macro-channels')
            native_placement('verify')
            result['placement_repair']=json.loads((OUT/'placement-repair.json').read_text())
            script=script.replace(str(inputs/'postcts.odb'),str(OUT/'relocated-placement.odb'))
            result['relocated_placement_timing']=parse_phases(execute(script,'relocated-placement-sta'),'CORNER')
            assert result['relocated_placement_timing'].keys()==replay.keys()
            result['status']='PLACEMENT_INVARIANTS_AND_STA_COMPLETE_GLOBAL_ROUTE_PENDING'
            save()
            if os.environ.get('GITHUB_ACTIONS')=='true':
                checkpoint=OUT/(f'newer-postcts-placement-{args.placement_profile}-'
                    f'{os.environ["GITHUB_RUN_ID"]}-{os.environ["GITHUB_RUN_ATTEMPT"]}.pre-route.json')
                checkpoint.write_text(json.dumps(result,indent=2)+'\n')
                subprocess.run(['gh','release','upload','cloud-migration-20261012-000',str(checkpoint)],check=True)
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
                     'set route_dbu [[ord::get_db_block] getDbUnitsPerMicron]',
                     f'set route_origin [list [expr {{round({origin_um[0]} * $route_dbu)}}] [expr {{round({origin_um[1]} * $route_dbu)}}]]',
                     'puts "NSSOC_ROUTING_GRID_ORIGIN_DBU $route_origin"',
                     f'if {{[catch {{global_route -grid_origin $route_origin -congestion_iterations 100 -congestion_report_file {{{OUT / "congestion.rpt"}}} -verbose}} route_error]}} {{',
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
        result['global_route'] = parse_phases(routed, 'CORNER')
        assert result['global_route'].keys() == replay.keys()
        for phase in replay:
            assert result['global_route'][phase]['groups'].keys() == replay[phase]['groups'].keys()
        assert all(sha(Path(p)) == digest for p, digest in protected.items())
        result['status'] = 'COMPLETE_NEWER_CHIP_GLOBAL_ROUTE_REQUIRES_DETAILED_ROUTING_AND_EXTRACTION'
        result['outputs'] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'result.json'}
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        result['failure_outputs'] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'result.json'}
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
