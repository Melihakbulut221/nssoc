#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate a chip fill candidate with pinned tools and geometry-preservation audits.

No native elapsed-time watchdog. This is not density/DRC/LVS/timing acceptance.
"""
import argparse
import json
from pathlib import Path
import resource
import subprocess

from bootstrap_flow import verify as verify_tool
from fetch_evidence_assets import fetch, validate, verify
from run_chip_native_shard import restore
from run_chip_ring_route import digest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='PREPARING', physical_acceptance=False, manufacturing_approval=False)

    def save():
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    save()
    try:
        manifest = args.manifest.resolve()
        rows = validate(json.loads(manifest.read_text()))
        if len(rows) != 1:
            raise ValueError('Exactly one immutable fill bundle required')
        if args.archive:
            archive = args.archive.resolve()
            verify(archive, rows[0])
        else:
            fetch(rows[0], out)
            archive = out / rows[0]['name']
        bundle = out / 'bundle'
        inventory = restore(archive, bundle)
        pins = {bundle / n: v['sha256'] for n, v in inventory.items()}
        app = ROOT / 'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
        verify_tool(app, 'x86_64')
        script = ROOT / 'hw/soc/flow/fill_chip_windows.py'
        audit = ROOT / 'hw/soc/flow/audit_fill_preservation.py'
        check = ROOT / 'hw/soc/flow/check_chip_fill.py'
        for p in (app, manifest, Path(__file__).resolve(), script, audit, check,
                  ROOT / 'scripts/run_chip_native_shard.py', ROOT / 'scripts/run_chip_ring_route.py'):
            pins[p] = digest(p)
        tool = bundle / 'tool/gdsfill'
        tool.chmod(0o755)
        command = [str(app), 'python', str(script), str(bundle / 'input/chip.gds'),
                   str(out / 'fill'), '--tool', str(tool), '--config', str(bundle / 'config.yaml'),
                   '--audit', str(audit), '--tile-size', '500']
        result.update(status='PREPARED', command=command, gds_sha256=digest(bundle / 'input/chip.gds'),
                      input_sha256={str(p): v for p, v in pins.items()})
        save()
        if args.prepare_only:
            return
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (12 * 1024**3,) * 2)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        probe = [str(app), 'python', str(check), '--tool', str(tool),
                 '--config', str(bundle / 'config.yaml'), '--fill', str(script),
                 '--audit', str(audit), '--output', str(out / 'probe')]
        with (out / 'probe.log').open('x') as log:
            subprocess.run(probe, stdout=log, stderr=subprocess.STDOUT, check=True,
                           preexec_fn=limits)
        result['status'] = 'RUNNING'
        save()
        with (out / 'run.log').open('x') as log:
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                  preexec_fn=limits).returncode
        result['process_returncode'] = code
        save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError('Fill input or method changed')
        progress = json.loads((out / 'fill/progress.json').read_text())
        geometry = json.loads((out / 'fill/final-geometry.json').read_text())
        if (code or progress['status'] != 'GENERATED_ALL_TILES'
                or progress['expected_tiles'] != 56 or len(progress['completed_tiles']) != 56
                or geometry['errors'] or not geometry['status'].startswith('PASS')):
            raise ValueError('Incomplete fill or failed geometry preservation')
        result.update(status='CANDIDATE_REQUIRES_NATIVE_CHECKS', output_sha256=digest(out / 'fill/checkpoint.gds'),
                      geometry=geometry, completed_tiles=56)
        save()
    except Exception as exc:
        result.update(status='ERROR', error=repr(exc))
        save()
        raise


if __name__ == '__main__':
    main()
