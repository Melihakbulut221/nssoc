#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate real upper-metal TX geometries and run unchanged physical gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, digest, target):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent',
                    '--show-error', url, '-o', str(target)], check=True)
    assert sha(target) == digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('baseline', 'topmetal_trunks', 'topmetal_trunks_narrow_bus',
                                             'critical_buses', 'critical_buses_wide_escape',
                                             'critical_buses_supply_escape', 'critical_buses_power_trunks'), required=True)
    parser.add_argument('--circuit-profile', choices=('baseline','cascade14','final_drive_v5'), default='baseline')
    args = parser.parse_args()
    spec_path = ROOT / 'docs/evidence/pcie-tx-layout-cloud-input-20261013.json'
    spec = json.loads(spec_path.read_text())
    out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', variant=args.variant, circuit_profile=args.circuit_profile, adopted=False,
        scope='Real generated layout with54native devices. DRC/LVS and physical fault controls only; new native RC extraction and full waveform validation still required before any electrical adoption. No main-chip or full serial PHY acceptance.')

    def run(command, name):
        log = out / (name + '.log')
        with log.open('w') as stream:
            code = subprocess.call([str(x) for x in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-16000:], flush=True)
            for child in sorted((out / 'physical').glob('*/run.log')):
                print(str(child) + '\n' + child.read_text(errors='replace')[-4000:], flush=True)
            raise RuntimeError(f'{name} failed with exit{code}')

    try:
        archive = out / 'input.tar.gz'
        fetch(spec['receipt']['url'], spec['receipt']['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(ROOT, filter='data')
        archive.unlink()
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        assert all(sha(ROOT / n) == r['sha256'] for n, r in manifest['files'].items())
        originals = out / 'original-methods'
        originals.mkdir()
        for bundle in spec['method_archives']:
            fetch(bundle['url'], bundle['sha256'], archive)
            with tarfile.open(archive) as tar:
                for name, digest in bundle['members'].items():
                    member = tar.getmember(name)
                    assert member.isfile() and member.size < 1024 * 1024
                    data = tar.extractfile(member).read()
                    assert hashlib.sha256(data).hexdigest() == digest
                    if name.endswith('.spice'):
                        target = ROOT / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        target = originals / Path(name).name
                    target.write_bytes(data)
            archive.unlink()
        source = (originals / 'layout91.py').read_text()
        edits = []
        physical_source=(originals/'physical92.py').read_text()
        if args.circuit_profile in ('cascade14','final_drive_v5'):
            if args.circuit_profile=='cascade14':
                circuit=ROOT/'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v2.spice'
                expected='c97692bcc4389c256479631e820a4293b79121d2225d767f5635429cd7dd0805'
                top='nssoc_tx_mux2_cascade14_layout_v1'
            else:
                from audit_tx_final_layout_source import audit
                circuit=ROOT/'hw/soc/analog/pcie/tx_mux2_final_drive_v5_layout_core.spice'
                native=ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v5.spice'
                expected='c74d1e0d2b7d7f1093653ee1d5ece27649ae97b1485e998fe3f4ff1b78cbfcdf'
                assert sha(native)=='75242abe73341e04ba62b2d4a41abf5e55b725ecec6eeb55dbf6abbbe8f2232d'
                result['circuit_equivalence_before_generation']=audit(circuit.read_text(),native.read_text())
                top='nssoc_tx_mux2_final_drive_v5_layout_v1'
            assert sha(circuit)==expected
            for before,after in [
                ('hw/soc/out/pcie-tx-mux2-20261012/tx_mux2_hbt_passive_fast_v1.spice',str(circuit.relative_to(ROOT))),
                ('4d7606b3c14ef06de2d25ce46c266dcef3635fe602218b3a8932f7f061e53101',expected),
                ('nssoc_tx_mux2_passive_topmetal_layout_v1',top)]:
                assert source.count(before)==1,before
                source=source.replace(before,after)
                edits.append(dict(before=before,after=after))
            assert physical_source.count('nssoc_tx_mux2_passive_topmetal_layout_v1')==1
            physical_source=physical_source.replace('nssoc_tx_mux2_passive_topmetal_layout_v1',top)
            result['circuit_source']=dict(path=str(circuit.relative_to(ROOT)),sha256=expected)
            result['scope']='Native '+args.circuit_profile+' circuit used in32:1 schematic tree, now generated as54physical devices including27substrate contacts. Same560DRC rules, strict hierarchical/flat transistor LVS and five physical/reference faults. No extracted electrical acceptance, assembled serializer layout or fullPHY/chip acceptance.'
        if args.variant != 'baseline':
            changes = [
                ('30+26*c,30+14*r', '30+28.8*c,30+14*r'),
                ('238+12*(i-19)', '260.4+14.4*(i-19)'),
                ('(collector, 1, n[0], x - 9, 0.04)', '(collector, 1, n[0], x - 10.8, 0.04)'),
                ('(base, 1, n[1], x - 6, -0.04)', '(base, 1, n[1], x - 7.2, -0.04)'),
                ('(m2[0], 2, n[2], x - 3, 0)', '(m2[0], 2, n[2], x - 3.6, 0)'),
                ('x - 6 + 3 * k', 'x - 7.2 + 3.6 * k'),
                ('"sub", x + 15', '"sub", x + 14.4'),
                ('via(3, 4, lane, y)', 'via(3, 6, lane, y)'),
                ('box(4, x - 0.6, min(sy, y) - 0.2, x + 0.6, max(sy, y) + 0.2)',
                 'box(6, x - 0.82, min(sy, y) - 0.2, x + 0.82, max(sy, y) + 0.2)'),
                ('via(4, 7, x, y)', 'via(6, 7, x, y)'),
                ('    for x, y in kelvin:via(2, 5, round(x/0.005)*0.005, round(y/0.005)*0.005, 4)\n',
                 '    # Return connections use the new thick trunks; omit the bypass.\n'),
                ('    box(5, min(x for x,y in kelvin)-1, min(y for x,y in kelvin)-6, max(x for x,y in kelvin)+1, max(y for x,y in kelvin)+6)\n',
                 '    # Old Metal5 bypass would short the new low via stacks.\n'),
            ]
            if args.variant == 'topmetal_trunks_narrow_bus':
                changes.append(("width = 16 if net in ['avdd','avss'] else 4", "width = 16 if net in ['avdd','avss'] else 3"))
            if args.variant.startswith('critical_buses'):
                changes.append(('    for i, net in enumerate(sorted(terminals)):',
                    "    ordered_nets = ['qn','qp','ea','eb','tail','sp','sn','op','on','ap','an','bp','bn','iref','avdd','avss','sub']\n"
                    "    assert len(ordered_nets) == len(terminals) and set(ordered_nets) == set(terminals)\n"
                    "    for i, net in enumerate(ordered_nets):"))
                # TM2.bR requires5um beside wide lines with>50um parallel run.
                # These are exactly the three gaps adjacent to the two supply
                # buses in the explicit critical-net order above.
                changes.append(('cursor_y = y + half + 3',
                                "cursor_y = y + half + (5 if net in ['iref','avdd','avss'] else 3)"))
            if args.variant in ('critical_buses_wide_escape','critical_buses_supply_escape','critical_buses_power_trunks'):
                changes.append(('escape(pin, met, net, lane, name, 4, off)',
                                'escape(pin, met, net, lane, name, 8, off)'))
            if args.variant in ('critical_buses_supply_escape','critical_buses_power_trunks'):
                # Actual measured tail-emitter lift differs from the reference
                # return. Reduce native supply/return metal resistance in GDS;
                # keep signal escape geometry and all circuit devices intact.
                # The same native DRC/LVS/fault checks decide legality.
                changes.append(('        box(3, lane - 0.2, y - 0.2, x + 0.2, y + 0.2)',
                    "        half_escape = 0.4 if net in ['avdd','avss'] else 0.2\n"
                    '        box(3, lane - half_escape, y - half_escape, x + half_escape, y + half_escape)'))
                changes.append(('            box(6, x - 0.82, min(sy, y) - 0.2, x + 0.82, max(sy, y) + 0.2)',
                    "            half_trunk = 1.0 if net in ['avdd','avss'] else 0.82\n"
                    '            box(6, x - half_trunk, min(sy, y) - 0.2, x + half_trunk, max(sy, y) + 0.2)'))
            if args.variant == 'critical_buses_power_trunks':
                # More room between routing lanes permits wider native power
                # trunks without stealing spacing from adjacent signal metal.
                # This is a new physical candidate, not a scaled RC surrogate.
                changes += [
                    ('30+28.8*c,30+14*r','30+38.4*c,30+14*r'),
                    ('260.4+14.4*(i-19)','337.2+19.2*(i-19)'),
                    ('(collector, 1, n[0], x - 10.8, 0.04)','(collector, 1, n[0], x - 14.4, 0.04)'),
                    ('(base, 1, n[1], x - 7.2, -0.04)','(base, 1, n[1], x - 9.6, -0.04)'),
                    ('(m2[0], 2, n[2], x - 3.6, 0)','(m2[0], 2, n[2], x - 4.8, 0)'),
                    ('x - 7.2 + 3.6 * k','x - 9.6 + 4.8 * k'),
                    ('"sub", x + 14.4','"sub", x + 19.2'),
                    ("half_trunk = 1.0 if net in ['avdd','avss'] else 0.82",
                     "half_trunk = 1.64 if net in ['avdd','avss'] else 0.82"),
                    ("width = 16 if net in ['avdd','avss'] else 4",
                     "width = 32 if net in ['avdd','avss'] else 4"),
                ]
            if args.circuit_profile == 'final_drive_v5' and args.variant == 'critical_buses_power_trunks':
                # Actual first-layout extraction shorted ea to avdd: D20's
                # 18um resistor contact via at x365.4 meets D21's ea escape
                # lane x366 at the same y. DRC alone did not detect this.
                # Move whole resistor banks, preserving every device value.
                # 28.8um would align the prior substrate trunk (+19.2)
                # with the next signal lane (-9.6), also a real LVS short.
                changes.append(('337.2+19.2*(i-19)', '337.2+38.4*(i-19)'))
            for before, after in changes:
                assert source.count(before) == 1, before
                source = source.replace(before, after)
                edits.append(dict(before=before, after=after))
        generator = out / 'generate.py'
        generator.write_text(source)
        physical_method=out/'verify-physical.py'
        physical_method.write_text(physical_source)
        result.update(source_bindings=spec, explicit_geometry_edits=edits,
                      generator_sha256=sha(generator), original_generator_sha256=sha(originals / 'layout91.py'),
                      physical_method_sha256=sha(physical_method),original_physical_method_sha256=sha(originals/'physical92.py'))
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == spec['runtime_sha256']
        run([app, 'python', generator, '--pdk', ROOT / 'pdk', '--out', out / 'layout'], 'generation')
        generated = json.loads((out / 'layout/result.json').read_text())
        result['layout'] = generated
        if args.circuit_profile=='final_drive_v5':
            result['generated_reference_equivalence']=audit(circuit.read_text(),native.read_text(),
                (out/'layout/schematic.cir').read_text())
        # The controller is standard Python; launching it inside the AppImage
        # would make its native child invocations require a nested FUSE mount.
        run([sys.executable, physical_method, '--layout', out / 'layout', '--out', out / 'physical', '--app', app], 'physical')
        physical = json.loads((out / 'physical/result.json').read_text())
        assert physical['status'] == 'PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
        result['physical'] = {k: v for k, v in physical.items() if k != 'inputs'}
        assert all(sha(ROOT / n) == r['sha256'] for n, r in manifest['files'].items())
        result['status'] = 'PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        report = out / 'physical/result.json'
        if report.exists():
            result['physical'] = json.loads(report.read_text())
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('layout', 'physical', 'source_bindings')}), flush=True)


if __name__ == '__main__':
    main()
