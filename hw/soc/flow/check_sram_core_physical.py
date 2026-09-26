#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run all independent physical decks on the exact LVS-qualified SRAM core.

Run inside the pinned LibreLane environment. No geometry or rule is changed.
Every deck must finish normally and pass independently; resource failures stay
ERROR. This is physical verification, not pad/package or manufacturing approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

from bounded_process import bounded_run


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gds', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.tag):
        parser.error('Unsafe tag')
    root = Path(__file__).resolve().parents[3]
    gds = args.gds.resolve(strict=True)
    receipt = args.receipt.resolve(strict=True)
    accepted = json.loads(receipt.read_text())
    if (accepted['status'] != 'PASS_BOUND_FULL_CHIP_SRAM_INTEGRATION_LVS'
            or accepted['final_views']['klayout_gds']['sha256'] != sha(gds)):
        parser.error('GDS differs from full-chip LVS acceptance')
    out = root / 'hw/soc/out' / args.tag
    out.mkdir(exist_ok=False)
    scripts = root / 'hw/soc/flow'
    inputs = {str(p): sha(p) for p in [gds, receipt, Path(__file__),
              scripts / 'check_ihp_drc.py', scripts / 'check_ihp_drc_partitioned.py',
              scripts / 'prepare_ihp_drc.py', scripts / 'bounded_process.py',
              root / 'hw/soc/pnr/ihp-drc.lock.json']}
    result = dict(status='RUNNING', input_sha256=inputs, cases=[],
                  scope='Unmodified full LVS-qualified core GDS; all recommended main tables, antenna and density sanity. No layout exclusions.',
                  manufacturing_acceptance=False)

    def save():
        temp = out / 'result.tmp'
        temp.write_text(json.dumps(result, indent=2) + '\n')
        temp.replace(out / 'result.json')

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (7 * 1024**3, 7 * 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (400 * 1024**2, 400 * 1024**2))

    save()
    for deck in ['density', 'antenna', 'main']:
        tag = args.tag + '-' + deck
        script = 'check_ihp_drc_partitioned.py' if deck == 'main' else 'check_ihp_drc.py'
        command = [sys.executable, str(scripts / script), str(gds), '--top', 'soc_top',
                   '--tag', tag, '--threads', '1']
        if deck == 'main':
            command += ['--timeout-seconds', '7200']
        else:
            command += ['--deck', deck]
        row = dict(deck=deck, command=command, status='RUNNING',
                   address_space_bytes=7 * 1024**3, max_output_file_bytes=400 * 1024**2)
        result['cases'].append(row)
        save()
        started = time.monotonic()
        with (out / (deck + '.log')).open('x') as log:
            code = bounded_run(command, stdout=log,
                               timeout=15000 if deck == 'main' else 3600,
                               preexec_fn=limits).returncode
        row.update(returncode=code, elapsed_seconds=time.monotonic() - started)
        measured = root / 'hw/soc/out' / tag / 'result.json'
        if measured.is_file():
            row['measurement'] = json.loads(measured.read_text())
            row['result_sha256'] = sha(measured)
        status = row.get('measurement', {}).get('status', 'ERROR')
        row['status'] = status if (code, status) in [(0, 'PASS'), (1, 'FAIL')] else 'ERROR'
        for path, expected in inputs.items():
            if sha(path) != expected:
                row['status'] = 'ERROR'
                row['error'] = 'Input changed: ' + path
        save()
        print(deck, row['status'], flush=True)
    result['status'] = ('PASS_ALL_THREE_PHYSICAL_DECKS' if all(
        row['status'] == 'PASS' for row in result['cases']) else 'OPEN_PHYSICAL_GATES')
    save()
    print(result['status'])
    raise SystemExit(0 if result['status'] == 'PASS_ALL_THREE_PHYSICAL_DECKS' else 1)


if __name__ == '__main__':
    main()
