#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audited read-layout adaptation; original waveform and electrical gates retained."""
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import types
import traceback
import pll845_contiguous_columns as cache
import read_pll845_sparse_completed as reader
import cloud_pll845_complete_terminal_envelopes as wrapper
import run_cloud_pll865_snapshot as pll

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-pll845-complete-terminal-envelopes'
MANIFEST = ROOT / 'scripts/pll845-contiguous-reader-method.json'
_lock = threading.RLock()
_state = {}
_stopped = threading.Event()

def phase(name, **details):
    with _lock:
        _state.update(phase=name, monotonic_s=time.monotonic(), **details)
        record = dict(_state)
        record['utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        if OUT.exists():
            tmp = OUT / 'reader-progress.json.tmp'
            tmp.write_text(json.dumps(record, indent=2) + '\n')
            tmp.replace(OUT / 'reader-progress.json')
    print('PLL_READER_PROGRESS ' + json.dumps(record, sort_keys=True), flush=True)

def heartbeat():
    while not _stopped.wait(60):
        with _lock: current = _state.get('phase', 'STARTING')
        diagnostics = {}
        for name in ('io','status'):
            p = Path('/proc/self') / name
            if p.exists():
                lines = p.read_text().splitlines()
                diagnostics[name] = [s for s in lines if name == 'io' or s.startswith(('VmRSS:','VmHWM:'))]
        phase(current, process=diagnostics)

def verified():
    manifest = json.loads(MANIFEST.read_text())
    for name, digest in manifest['protected_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, ('Source drift', name)
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == manifest['driver_sha256']
    cache.analyzer_inputs(ROOT/'scripts/review_pcie_pll_acquisition_v1.py', pll.acquisition_cycle_diagnosis)
    return manifest

def adapted(module, edits, extra):
    source = Path(module.__file__).read_text()
    for item in edits:
        assert source.count(item['before']) == 1, ('Nonunique exact adaptation', item['before'])
        source = source.replace(item['before'], item['after'], 1)
    namespace = dict(module.__dict__)
    namespace['__name__'] = 'audited_' + module.__name__
    exec(compile(source, str(module.__file__) + ':contiguous-storage-adaptation', 'exec'), namespace)
    namespace.update(extra)
    return namespace['main']

def cached_columns(names, values):
    phase('COPY_ORIGINAL_ANALYZER_COLUMNS')
    data, receipt = cache.columns(names, values, progress=phase)
    (OUT/'contiguous-column-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    phase('FROZEN_ACQUISITION_ANALYSIS')
    return data

def controls():
    manifest = verified()
    adapted(reader, manifest['reader_edits'], {'_phase':phase, '_cached_columns':cached_columns})
    adapted(wrapper, manifest['wrapper_edits'], {'_phase':phase})
    result = cache.controls(pll.acquisition_analyzer(), pll.acquisition_cycle_diagnosis)
    result['source_manifest_sha256'] = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    return result

def interrupted(signum, frame):
    phase('INTERRUPTED', signal=signum, interrupted=True)
    raise SystemExit(128 + signum)

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    manifest = verified()
    reader_main = adapted(reader, manifest['reader_edits'],
                          {'_phase':phase, '_cached_columns':cached_columns})
    wrapper_main = adapted(wrapper, manifest['wrapper_edits'],
                           {'_phase':phase, 'original':types.SimpleNamespace(main=reader_main)})
    for sig in (signal.SIGTERM, signal.SIGINT): signal.signal(sig, interrupted)
    faulthandler.enable()
    faulthandler.dump_traceback_later(300, repeat=True)
    timer = threading.Thread(target=heartbeat, daemon=True)
    timer.start()
    phase('STARTING', storage_adaptation=True, source_manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
          full_phy_accepted=False)
    try:
        wrapper_main()
        phase('COMPLETE_READER')
    except BaseException as error:
        phase('READER_EXIT_WITH_ERROR_OR_ORIGINAL_REJECTION', error=repr(error))
        raise
    finally:
        _stopped.set()
        faulthandler.cancel_dump_traceback_later()
        if OUT.exists():
            (OUT/'storage-adaptation-method.json').write_bytes(MANIFEST.read_bytes())
            old = ROOT/'cloud-pll845-sparse-completed-reader/result.json'
            if old.exists(): (OUT/'original-reader-result.json').write_bytes(old.read_bytes())
            report_path = OUT/'result.json'
            if report_path.exists():
                report = json.loads(report_path.read_text())
                report['reader_storage_adaptation'] = dict(
                    method_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                    original_reader_source_unchanged=True, exact_execution_edits_declared=True,
                    original_waveform_unchanged=True, original_acquisition_thresholds_unchanged=True)
                report['outputs'] = {str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in OUT.rglob('*') if p.is_file() and p != report_path}
                report_path.write_text(json.dumps(report,indent=2)+'\n')

if __name__ == '__main__':
    if '--controls' in sys.argv: print(json.dumps(controls(),indent=2))
    else: main()
