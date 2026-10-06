#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent bounded publisher of immutable locally committed PLL parts.

No process in this module adopts, signals, deletes or modifies a native spool.
Network failure is recorded in this worker's own directory. A subsequent worker
can reconcile retained public assets using new receipts without solver restart.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import durable_pcie_spool_v1 as local
import publish_pcie_native_capture_v4 as publication

PUBLISHER_SHA = '1b73bd49b86090a6eeff1cf16af36a2a17a4885bb748ecc301435ee796b3b585'
TAG = 'evidence-20261006-pcie-closure'
WORKER_CAP = 512 * 1024**2
TERMINAL_HEADROOM = 16 * 1024**2
COMMAND_HEADROOM = 32 * 1024**2
SSD_FLOOR = 1024**3
MAX_RECEIPTS = 2048
require, pin = local.require, local.pin
life = publication.lifecycle


def transient_receipt(record):
    """Only the frozen producer's explicit transport exception is retryable."""
    if record.get('status') != 'FAIL' or record.get('explicit_stop') is not False:
        return False
    try:
        expression = ast.parse(record['error'], mode='eval').body
    except (KeyError, SyntaxError, TypeError):
        return False
    return (isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name)
            and expression.func.id == 'TransportError' and not expression.keywords
            and len(expression.args) == 1 and isinstance(expression.args[0], ast.Constant)
            and isinstance(expression.args[0].value, str))


def guard(directory, *, extra=0, terminal=False):
    require(shutil.disk_usage(directory).free >= (extra if terminal else SSD_FLOOR + extra),
            'Publication SSD free floor')
    used = sum(p.stat().st_size for p in Path(directory).rglob('*') if p.is_file())
    limit = WORKER_CAP if terminal else WORKER_CAP - TERMINAL_HEADROOM
    require(used + extra <= limit, 'Publication evidence byte cap')
    return used


def command(path, receipt, directory, *, stop=None):
    def check_stop():
        if stop is not None and stop.is_set():
            raise life.Cancelled('Explicit stop at publication owner handoff')
    check_stop()
    require(pin(publication.__file__)['sha256'] == PUBLISHER_SHA, 'Frozen publisher V4')
    require(pin(life.__file__)['sha256'] == publication.OWNER_SHA, 'Frozen process owner')
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'LD_PRELOAD')}
    guard(directory, extra=COMMAND_HEADROOM)
    with life.ProcessOwner(receipt.with_suffix('.owner.json')) as owner:
        check_stop()
        with receipt.with_suffix('.log').open('xb') as log:
            process = owner.launch('publisher', [sys.executable, str(Path(publication.__file__).resolve()),
                                   '--tag', TAG, '--out', str(receipt), str(path)],
                                   env=env, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT)
            while process.poll() is None:
                owner.check()
                guard(directory)
                owner.cancelled.wait(0.05)
            code = owner.complete(process)
            owner.check()
            guard(directory)
    owner.check()
    check_stop()
    guard(directory)
    require(receipt.is_file(), 'Actual publisher terminal receipt')
    record = json.loads(receipt.read_text())
    require(record.get('publisher_revision') == 4
            and record.get('source', {}).get('sha256') == PUBLISHER_SHA
            and record.get('tag') == TAG, 'Bound frozen publisher receipt')
    require((code == 0) == (record['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'),
            'Actual publisher wait code agrees with receipt')
    if record.get('explicit_stop'):
        raise life.Cancelled('Explicit publication child stop')
    return record


def validate_success(record, row, path):
    expected = {key: row[key] for key in ('bytes', 'sha256')}
    require(record['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
            and len(record['assets']) == 1, 'One completed immutable part')
    asset = record['assets'][0]
    require(asset['name'] == row['name']
            and {key: asset[key] for key in expected} == expected
            and asset['authenticated_roundtrip'] is True
            and asset['anonymous_roundtrip'] is True
            and pin(path) == expected, 'Exact retained source and dual byte readback')
    require(record['files'] == [dict(path=str(path.resolve()), name=row['name'], **expected)],
            'One exact local source declared by publication')
    return asset


def run(spool, directory, configuration_sha, *, publish=None, poll_seconds=2.0,
        retry_seconds=30.0, max_receipts=MAX_RECEIPTS, stop=None):
    """Worker-only state; transport retry is independent of local producer."""
    import threading
    import signal
    stop = threading.Event() if stop is None else stop
    if publish is None:
        def publish(path, receipt, directory):
            return command(path, receipt, directory, stop=stop)
    spool, directory = Path(spool), Path(directory)
    require(directory.resolve() != spool.resolve()
            and not directory.resolve().is_relative_to(spool.resolve()),
            'Publication evidence lives outside immutable native spool')
    require(0 < poll_seconds <= 30 and 0 < retry_seconds <= 300
            and 0 < max_receipts <= MAX_RECEIPTS, 'Bounded worker policy')
    require(pin(spool / 'configuration.json')['sha256'] == configuration_sha,
            'Externally bound immutable spool configuration')
    configuration = json.loads((spool / 'configuration.json').read_text())
    require(configuration['schema'] == 'PCIE_LOCAL_LOSSLESS_SPOOL_V1', 'Local spool schema')
    directory.mkdir()
    state = dict(status='RUNNING_INDEPENDENT_LOCAL_SPOOL_PUBLICATION',
                 spool=str(spool), configuration=pin(spool / 'configuration.json'),
                 tag=TAG, source=pin(__file__), publisher=pin(publication.__file__),
                 assets=[], attempts=[], native_result_unmodified=True,
                 physical_acceptance=False)
    handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    for sig in handlers:
        signal.signal(sig, lambda signum, frame: stop.set())
    def check():
        if stop.is_set():
            raise life.Cancelled('Explicit independent publisher stop')
        guard(directory)
        require(pin(spool / 'configuration.json') == state['configuration'],
                'Immutable spool configuration changed')
    def save(*, terminal=False):
        encoded = local.encoded(state)
        require(2 * len(encoded) <= TERMINAL_HEADROOM, 'Finite publication manifest size')
        guard(directory, extra=2 * len(encoded), terminal=terminal)
        local.atomic_json(directory / 'publication.json', state)
    try:
        save()
        while True:
            check()
            for name in ('native-terminal-invalid.json', 'terminal-retention-failure.json'):
                failure = spool / name
                if failure.exists():
                    state['native_terminal_failure'] = dict(path=str(failure), **pin(failure))
                    raise ValueError('Native terminal local manifest or retention failed; no complete publication')
            if not (spool / 'parts.json').exists():
                stop.wait(poll_seconds)
                continue
            ledger = json.loads((spool / 'parts.json').read_text())
            require(ledger['prefix'] == configuration['prefix']
                    and ledger['limits'] == configuration['limits'], 'Declared producer ledger')
            index = len(state['assets'])
            require(len(ledger['parts']) >= index, 'Committed local ledger never shrinks')
            for prior_index, published in enumerate(state['assets']):
                require(published['row'] == ledger['parts'][prior_index]
                        and pin(published['receipt']) == published['receipt_pin'],
                        'Previously published row and receipt remain immutable')
            if index < len(ledger['parts']):
                count = sum(row['rows'] for row in ledger['parts'][:index])
                row = ledger['parts'][index]
                path = local.check_row(spool, ledger, row, index, count)
                require(len(state['attempts']) < max_receipts,
                        'Finite publication attempt evidence budget; local native continues')
                receipt = directory / f'attempt-{len(state["attempts"]):05d}-part{index:05d}.json'
                attempt = dict(index=index, source=dict(path=str(path), **pin(path)),
                               receipt=str(receipt), status='RUNNING')
                state['attempts'].append(attempt)
                save()
                result = publish(path, receipt, directory)
                check()
                require(receipt.is_file(), 'Retained actual publication receipt')
                require(json.loads(receipt.read_text()) == result, 'Exact returned publication receipt')
                attempt['receipt_pin'] = pin(receipt)
                if result['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS':
                    asset = validate_success(result, row, path)
                    attempt['status'] = 'PUBLIC_VERIFIED'
                    state['assets'].append(dict(row=row, asset=asset,
                                                receipt=str(receipt), receipt_pin=pin(receipt)))
                    save()
                    continue
                if transient_receipt(result):
                    attempt['status'] = 'TRANSPORT_PENDING_LOCAL_BYTES_RETAINED'
                    save()
                    stop.wait(retry_seconds)
                    continue
                attempt['status'] = 'FATAL_PUBLICATION_LOCAL_BYTES_RETAINED'
                raise ValueError('Non-transport publication failure; no retry or source replacement')
            terminal_path = spool / 'native-terminal.json'
            if terminal_path.exists() and not (spool / 'reservation.bin').exists():
                terminal = json.loads(terminal_path.read_text())
                require(terminal['canonical_manifest'] == pin(spool / 'parts.json'),
                        'Terminal local manifest exact')
                local.inspect_spool(spool, raw=True)
                require(len(state['assets']) == len(ledger['parts']), 'All canonical parts public')
                state['native_terminal'] = dict(path=str(terminal_path), **pin(terminal_path))
                state['local_manifest'] = dict(path=str(spool / 'parts.json'), **pin(spool / 'parts.json'))
                complete = ledger['status'] == 'LOCAL_CAPTURE_COMPLETE' and not terminal['staging'] and not terminal['orphans']
                state['status'] = ('PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC' if complete
                                   else 'PASS_PARTIAL_LOCAL_PARTS_PUBLIC_NATIVE_INCOMPLETE')
                break
            stop.wait(poll_seconds)
        check()
    except BaseException as error:
        state.update(status='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED',
                     error=repr(error), explicit_stop=stop.is_set() or isinstance(error, life.Cancelled))
        raise
    finally:
        try:
            # Reserved metadata headroom permits a terminal error receipt even
            # when the ordinary free floor or operative evidence budget fails.
            save(terminal=True)
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spool', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--configuration-sha', required=True)
    args = parser.parse_args()
    result = run(args.spool, args.out, args.configuration_sha)
    print(result['status'])


if __name__ == '__main__':
    main()
