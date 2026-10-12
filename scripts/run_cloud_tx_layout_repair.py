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
                                             'critical_buses', 'critical_buses_wide_escape'), required=True)
    args = parser.parse_args()
    spec_path = ROOT / 'docs/evidence/pcie-tx-layout-cloud-input-20261013.json'
    spec = json.loads(spec_path.read_text())
    out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', variant=args.variant, adopted=False,
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
            if args.variant == 'critical_buses_wide_escape':
                changes.append(('escape(pin, met, net, lane, name, 4, off)',
                                'escape(pin, met, net, lane, name, 8, off)'))
            for before, after in changes:
                assert source.count(before) == 1, before
                source = source.replace(before, after)
                edits.append(dict(before=before, after=after))
        generator = out / 'generate.py'
        generator.write_text(source)
        result.update(source_bindings=spec, explicit_geometry_edits=edits,
                      generator_sha256=sha(generator), original_generator_sha256=sha(originals / 'layout91.py'))
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == spec['runtime_sha256']
        run([app, 'python', generator, '--pdk', ROOT / 'pdk', '--out', out / 'layout'], 'generation')
        generated = json.loads((out / 'layout/result.json').read_text())
        result['layout'] = generated
        # The controller is standard Python; launching it inside the AppImage
        # would make its native child invocations require a nested FUSE mount.
        run([sys.executable, originals / 'physical92.py', '--layout', out / 'layout', '--out', out / 'physical', '--app', app], 'physical')
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
