#!/usr/bin/env python3
"""Same-input hosted baseline/ACK mapping and unplaced three-corner screening."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['baseline', 'ack'], required=True)
    args = parser.parse_args()
    output = ROOT / 'cloud-ack-map' / args.profile
    output.mkdir(parents=True, exist_ok=False)
    status = dict(status='RUNNING', profile=args.profile, adopted=False,
                  scope='Unplaced comparison only. Vendor SRAM models, original clocks. No routed timing, full PHY, qualified RC or production signoff.')
    def save():
        (output / 'result.json').write_text(json.dumps(status, indent=2) + '\n')
    save()
    try:
        spec = json.loads((ROOT / 'docs/evidence/pcie-ack-map-cloud-input-20261012.json').read_text())
        archive = ROOT / spec['archive']
        assert sha(archive) == spec['sha256']
        inputs = output / 'inputs'
        with tarfile.open(archive) as tar:
            tar.extractall(inputs, filter='data')
        manifest = json.loads((inputs / 'manifest.json').read_text())
        for name, pin in manifest['files'].items():
            assert sha(inputs / name) == pin['sha256']
        mapping = output / 'map'
        mapping.mkdir()
        oldroot = manifest['old_root']
        oldpdk = manifest['old_pdk']
        oldoutput = oldroot + '/hw/soc/out/pcie-npu-wake-20261012/map16'
        recipe = (inputs / manifest['recipe']).read_text()
        if args.profile == 'ack':
            old = oldroot + '/hw/soc/out/pcie-replay-successor-register-20261012/candidate01/soc_pcie_replay_tx.v'
            new = oldroot + '/hw/soc/out/pcie-ack-delta-lookahead-20261012/candidate01/soc_pcie_replay_tx.v'
            assert recipe.count(old) == 1
            recipe = recipe.replace(old, new)
        recipe = recipe.replace(oldoutput, str(mapping)).replace(oldroot, str(inputs / 'root')).replace(oldpdk, str(inputs / 'pdk'))
        script = mapping / 'synthesis.ys'
        script.write_text(recipe)
        yosys = shutil.which('yosys')
        assert yosys
        status['runtime'] = subprocess.check_output([yosys, '-V'], text=True).strip()
        status['archive_sha256'] = spec['sha256']
        save()
        with (mapping / 'synthesis.log').open('w') as log:
            subprocess.run([yosys, '-s', str(script)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        mapped = json.loads((mapping / 'soc_top.mapped.json').read_text())['modules']['soc_top']
        macros = dict(collections.Counter(c['type'] for c in mapped['cells'].values() if c['type'].startswith('RM_IHPSG13')))
        assert sum(macros.values()) == 20
        status['macros'] = macros
        status['ports'] = {n: [p['direction'], len(p['bits'])] for n, p in mapped['ports'].items()}
        status['parameters'] = mapped['parameter_default_values']
        status['mapped_cells'] = len(mapped['cells'])
        save()
        constraints = output / 'constraints'
        subprocess.run([sys.executable, str(ROOT / 'scripts/pcie_soc_constraints.py'),
                        '--mapped-json', str(mapping / 'soc_top.mapped.json'), '--out', str(constraints)], check=True)
        template = (inputs / 'root/hw/soc/out/pcie-ack-delta-lookahead-20261012/read05.py').read_text()
        changes = {
            "b=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012'": f'b=Path({str(output)!r})',
            "app=root/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'": f'app=Path({os.environ["CLOUD_APPIMAGE"]!r})',
            "net=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012/map04/soc_top.netlist.v'": f'net=Path({str(mapping / "soc_top.netlist.v")!r})',
            "sdc=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012/constraints04/development.sdc'": f'sdc=Path({str(constraints / "development.sdc")!r})',
            oldpdk: str(inputs / 'pdk'),
        }
        for old, new in changes.items():
            assert template.count(old) == 1, old
            template = template.replace(old, new)
        screen = output / 'screen.py'
        screen.write_text(template)
        subprocess.run([sys.executable, str(screen)], check=True)
        result = json.loads((output / 'screen05/result.json').read_text())
        assert result['status'] == 'COMPLETE_UNPLACED_REPAIR_REQUIRES_GRAPH_AND_PORT_PROOF'
        assert all(sha(inputs / name) == pin['sha256'] for name, pin in manifest['files'].items())
        status['status'] = 'COMPLETE_UNPLACED_SCREEN_NOT_TIMING_CLOSURE'
        status['screen_result'] = result
    except BaseException as error:
        status.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
