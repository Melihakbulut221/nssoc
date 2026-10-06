#!/usr/bin/env python3
"""Independent terminal/source-map closure after the full saved raw scan."""
from pathlib import Path
import hashlib
import json
import os

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
O = Path(__file__).resolve().parent


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def identity(pid):
    path = Path(f'/proc/{pid}/stat')
    if not path.exists():
        return None
    words = path.read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, state=words[0], process_group=int(words[2]), start_ticks=words[19])


def main():
    result = json.loads((O / 'result.json').read_text())
    assert result['findings'] == [] and all(result['numerical']['checks'].values())
    records = []
    for label in ('eighthstep', 'sixteenthstep'):
        N = Path(f'/dev/shm/nssoc-vco-v6-divider-tail115-v1-{label}-06-01')
        native = json.loads((N / 'result.json').read_text())
        assert pin(N / 'result.json') == result['inputs'][str(N / 'result.json')]
        outputs = {}
        for name, expected in native['outputs'].items():
            actual = pin(N / name)
            assert actual == expected, (label, name)
            outputs[name] = actual
        execution = json.loads((N / 'execution.json').read_text())
        owner = json.loads((N / 'owned-processes.json').read_text())
        assert execution['returncode'] == 0 and execution['elapsed_watchdog_seconds'] is None
        assert execution['address_space_limit_bytes'] == 2 * 1024**3
        assert execution['actual_affinity'] == [10]
        assert owner['status'] == 'HEALTHY' and owner['cleanup'] is None
        live_checks = []
        for process in owner['processes']:
            assert process['status'] == 'REAPED_NO_LIVE_MEMBERS'
            assert process['returncode'] == 0 and process['members_at_leader_exit'] == []
            birth = process['identity']
            current = identity(birth['pid'])
            assert current is None or current['start_ticks'] != birth['start_ticks']
            live_checks.append(dict(saved=birth, current=current))
        assert len(native['measurement']['checks']) == 13
        assert all(native['measurement']['checks'].values())
        assert len(native['safety']['all_device_bounds']) == 455
        assert all(row['passed'] for row in native['safety']['all_device_bounds'])
        records.append(dict(capture=label, result=pin(N / 'result.json'),
                            outputs=outputs, execution=execution,
                            owned_terminal=owner, exact_births_absent=live_checks))
    old = Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-eighthstep-06-01/bench.cir').read_text()
    new = Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01/bench.cir').read_text()
    before = '.tran 6.25e-13 3.4e-08 0 6.25e-13'
    after = '.tran 3.125e-13 3.4e-08 0 3.125e-13'
    assert old.count(before) == new.count(after) == 1
    assert old.replace(before, after) == new
    # The reference side is the previously independently reviewed E8 capture.
    prior = json.loads((R / 'hw/soc/out/pcie-tail115-eighthstep-wave-peer-rx-20261006/result.json').read_text())
    for key in ('all64_HBT_VCE', 'source_native_simulator_binding', 'initial_mapping',
                'actual_vco_period_counts', 'all_six_intermediate_ratios',
                'numerical_edge_times', 'frequencies_hz', 'boundaries'):
        assert result['reference'][key] == prior['candidate'][key], key
    bridge = json.loads((O / 'reader-source-bridge01.json').read_text())
    text = (O / 'review01.py').read_text()
    for edit in reversed(bridge['edits']):
        assert text.count(edit['after']) == edit['count']
        text = text.replace(edit['after'], edit['before'])
    assert text == Path(bridge['parent']['path']).read_text()
    receipt = dict(status='PASS_SAVED_N16_TERMINAL_AND_FULL_READER_ANCESTRY', findings=[],
                   raw_review=pin(O / 'result.json'), method=pin(__file__),
                   bridge=pin(O / 'reader-source-bridge01.json'),
                   source_change=dict(before=before, after=after, whole_deck_inverse=True),
                   captures=records, previous_independent_reference_exact=True,
                   boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                   scope='Saved 32 native output files and both terminal owner/execution records fully hashed; old exact native births absent. All13 measurement and455 producer bound verdicts recounted, full64 HBT bounds independently recomputed by the bound raw reader. The entire simulation deck differs only in .tran time-step/maxstep. No native, EDA, controls, signals or publication.')
    (O / 'terminal-ancestry01.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(result=pin(O / 'terminal-ancestry01.json'), captures=2,
                          output_files=sum(len(x['outputs']) for x in records)), indent=2))


if __name__ == '__main__':
    main()
