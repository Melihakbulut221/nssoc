#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh paired global routing of the proven four-cell ECO; no signoff claim."""
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


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('baseline', 'buffered'), required=True)
    args = parser.parse_args()
    out = ROOT / 'cloud-global-setup'
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', profile=args.profile, adopted=False,
        scope='Fresh global routing using identical PDK fitted RC and original constraints. Requires detailed routing, extracted RC, DRC, antenna and full timing before acceptance. No full serial PHY signoff.')
    try:
        spec = json.loads((ROOT / 'docs/evidence/cloud-routed-setup-screen-20261012.json').read_text())
        archive = out / 'input.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', spec['archive_url'], '-o', str(archive)], check=True)
        assert sha(archive) == spec['archive_sha256']
        result['source_archive_sha256'] = sha(archive)
        assert not (ROOT / 'cloud-routed-setup').exists()
        with tarfile.open(archive) as tar:
            tar.extractall(ROOT, filter='data')
        archive.unlink()
        source = ROOT / 'cloud-routed-setup'
        prior = json.loads((source / 'result.json').read_text())
        assert prior['status'] == 'COMPLETE_FOUR_CELL_ESTIMATE_REQUIRES_ROUTING_AND_EXTRACTION'
        assert prior['logic']['status'] == 'PASS within scope'
        assert prior['geometry']['status'] == 'PASS_ONLY_THREE_RESIZED_BUFFERS_AND_ONE_INSERTED_BUFFER'
        assert prior['inverted_buffer_control'] == 'EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
        inputs = source / 'inputs'
        manifest = json.loads((inputs / 'manifest.json').read_text())
        assert all(sha(inputs / name) == pin['sha256'] for name, pin in manifest['files'].items())
        template = (inputs / manifest['original_tcl']).read_text()
        for old, name in sorted(manifest['paths'].items(), key=lambda pair: -len(pair[0])):
            template = template.replace(old, str(inputs / name))
        prefix = template.split('puts "Reading OpenROAD database')[0]
        original = json.loads((inputs / manifest['baseline_result']).read_text())
        sdc = inputs / manifest['paths'][original['binding']['observations']['sdc']['path']]
        odb = source / args.profile / 'placed.odb'
        config = ROOT / 'docs/evidence/cloud-global-route-rc-20261013.json'
        rc = json.loads(config.read_text())
        result['inputs'] = {str(p.relative_to(ROOT)): sha(p) for p in (odb, sdc, config, Path(__file__))}
        lines = [prefix, f'read_db {{{odb}}}', f'read_sdc {{{sdc}}}',
                 'set_propagated_clock [all_clocks]', 'check_placement -verbose',
                 'set_thread_count 2', 'set_cmd_units -resistance kOhm -capacitance pF -time ns',
                 'report_units']
        for corner in ('slow', 'typical', 'fast'):
            for layer, values in rc['layers_rc'].items():
                lines.append(f'set_layer_rc -corner {corner} -layer {layer} -resistance {values["res"]} -capacitance {values["cap"]}')
            for via, resistance in rc['vias_r'].items():
                lines.append(f'set_layer_rc -corner {corner} -via {via} -resistance {resistance}')
            lines += [f'set_wire_rc -corner {corner} -signal -layer Metal2',
                      f'set_wire_rc -corner {corner} -clock -layer Metal4',
                      f'report_layer_rc -corner {corner}']
        lines += [f'set_routing_layers -signal {rc["routing_layers"]} -clock {rc["routing_layers"]}',
                  f'set_global_routing_layer_adjustment Metal1-TopMetal2 {rc["adjustment"]}',
                  f'global_route -congestion_iterations 100 -congestion_report_file {{{out / "congestion.rpt"}}} -verbose',
                  f'write_guides {{{out / "route.guide"}}}',
                  f'write_global_route_segments {{{out / "route.segments"}}}',
                  f'write_db {{{out / "global.odb"}}}',
                  f'estimate_parasitics -global_routing -spef_file {{{out / "estimated"}}}',
                  'check_setup -verbose', 'report_parasitic_annotation -report_unannotated']
        for corner in ('slow', 'typical', 'fast'):
            for delay in ('max', 'min'):
                lines += [f'puts CORNER_{corner}_{delay}',
                          f'report_checks -corner {corner} -path_delay {delay} -group_path_count 20 -fields {{slew cap fanout}} -digits 6']
            lines += [f'puts ELECTRICAL_{corner}',
                      f'report_check_types -corner {corner} -max_slew -max_capacitance -max_fanout -violators -digits 6']
        script = out / 'route.tcl'
        script.write_text('\n'.join(lines) + '\n')
        assert 'read_spef' not in script.read_text() and '-allow_congestion' not in script.read_text()
        with (out / 'native.log').open('w') as log:
            code = subprocess.call([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', str(script)],
                                   stdout=log, stderr=subprocess.STDOUT)
        text = (out / 'native.log').read_text(errors='replace')
        result['returncode'] = code
        if code or re.search(r'(?m)^(?:Error:|\[ERROR)', text):
            print(text[-14000:], flush=True)
            raise RuntimeError('Native global routing/STA failed; full log preserved')
        result['phases'] = parse_phases(text, 'CORNER')
        for phase, values in result['phases'].items():
            assert values['groups'].keys() == prior['estimates'][args.profile][phase]['groups'].keys()
        assert all(sha(ROOT / name) == digest for name, digest in result['inputs'].items())
        result['outputs'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
        result['status'] = 'COMPLETE_GLOBAL_ROUTE_ESTIMATE_REQUIRES_DETAIL_ROUTE_EXTRACTION'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'phases'}), flush=True)


if __name__ == '__main__':
    main()
