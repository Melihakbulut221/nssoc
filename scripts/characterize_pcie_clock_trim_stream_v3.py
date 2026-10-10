#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate phase-aware1us replay/pair; preserves original endpoint-metric FAIL."""
import argparse
from array import array
import hashlib
import json
import lzma
import math
from pathlib import Path
import re
import shutil
import struct
import sys
import urllib.request

import numpy as np
import characterize_pcie_clock_trim_stream_v2 as lifecycle
import analyze_pcie_clock_thermal_cycles_v1 as phase

previous = lifecycle.previous
base, tiny = lifecycle.base, lifecycle.tiny
sha, require, atomic = lifecycle.sha, lifecycle.require, lifecycle.atomic
PartQueue = previous.PartQueue
STOP, MIN_FREE_BYTES = previous.STOP, previous.MIN_FREE_BYTES
LIFECYCLE_SHA = '39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
PHASE_SHA = '100b15ebe2a107054f14af36797db7e19415d65536afa77406404252bcf28884'
NG47_SHA = 'eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8'
WARNING_SOURCE = dict(debian_source='47+ds-1~bpo13+1',
    archive_sha256='004b2f7af4c862ed56a89a353e87889b58c21a5a56d13f45a9138d681c3f5dad',
    file='src/frontend/outitf.c',sha256='995538492e4549ef42aecc74f3d3c1e95da279c029d959d62b27063c2adaeae2',
    function='OUTpBeginPlot',lines=[131,163],
    preserved_source_capsule_sha256='db37bede480cb2981ab003b6f04ac8199af54c70e1c7c4f9d5f270347c8e591c',
    semantics='Linux estimate stop/step*columns*sizeof(double) is printed without file/FIFO predicate; no error return or runtime equation modification')
RELEASE = 'https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'
MAX_PHASE_ROWS = 100000
PRIOR_REVIEW_SHA = 'a11cae7320ef525daf5dc6087157edee0843ab784d891c96cf5f97dfbd4b857e'
PRIOR_REVIEW_PATH = Path(__file__).resolve().parents[1]/'hw/soc/out/pcie-clock-trim-20261004/longstream-v2-result/review.json'


def classify_log(log, capture, hbts, runtime_sha, step, returncode):
    """Classify only the proven ng47 memory estimate; keep all other guards."""
    require(runtime_sha == NG47_SHA and returncode == 0, 'Exact native47 successful execution')
    require(capture['step_s'] == step and capture['stop_s'] >= 12e-9, 'Native analysis identity')
    pattern = (r'(?m)^Warning: memory required \(([0-9.]+) ([GMK]?)B\), made of\n'
        r'       (\d+) nodes and approximately ([0-9.e+]+) time steps,\n'
        r'       is more than the DRAM memory available \(([0-9.]+) ([GMK]?)B\)!\n'
        r'       Swapping data to SSD may slow down the simulation\.\n')
    matches = list(re.finditer(pattern, log))
    require(len(matches) <= 1, 'At most one exact memory advisory')
    classified = []
    cleaned = log
    for match in matches:
        required, units, nodes, count, available, available_units = match.groups()
        scale = {'':1, 'K':1024, 'M':1024**2, 'G':1024**3}
        expected_steps = capture['stop_s'] / step
        expected_bytes = expected_steps * len(capture['columns']) * 8
        got_required, got_available = float(required)*scale[units], float(available)*scale[available_units]
        require(int(nodes) == len(capture['columns']) == 167 and math.isclose(float(count), expected_steps, rel_tol=1e-6), 'Exact advisory vector/step estimate')
        require(math.isclose(got_required, expected_bytes, rel_tol=1e-5) and 0 < got_available < got_required, 'Exact advisory memory estimate')
        classified.append(dict(literal=match.group(),estimated_bytes=expected_bytes,available_bytes_reported=got_available,source=WARNING_SOURCE))
        cleaned = cleaned.replace(match.group(), '', 1)
    # This only classifies the exact advisory in a separate in-memory review.
    # The original native file/hash and original strict rejection are retained.
    original = base.old.diagnostics(log)
    native = tiny.native_log(cleaned, capture, hbts)
    return dict(original_strict_diagnostics=original, informational_memory_advisories=classified,
        all_other_warnings_errors_rejected=True, native_structural_checks=native,
        decoded_original_log_text_sha256=hashlib.sha256(log.encode()).hexdigest(),log_file_modified=False)


def phase_convergence(times, clock, thermal, stop, legacy):
    require(len(thermal) == 53, 'All53 thermal states')
    rows = {}
    for name, values in sorted(thermal.items()):
        metric = phase.cycles(times, clock, values, stop-8e-9, stop)
        centers, means = np.asarray(metric['centers_s']), np.asarray(metric['means'])
        rates = []
        counts = []
        for i in range(4):
            mask = (centers >= stop-8e-9+i*2e-9) & (centers < stop-8e-9+(i+1)*2e-9)
            require(np.count_nonzero(mask) >= 2, 'Complete cycles in each of four fixed2ns windows')
            counts.append(int(np.count_nonzero(mask)))
            rates.append(float(np.max(np.abs(np.diff(means[mask])/np.diff(centers[mask])*1e-9))))
        metric.update(fixed2ns_max_abs_cycle_mean_rates_k_per_ns=rates, fixed2ns_complete_cycle_counts=counts)
        rows[name] = metric
    checks = dict(
        final_four_frequency_means_within100ppm=legacy['checks']['final_four_frequency_means_within100ppm'],
        all_cycle_mean_rates_within_original_limit=all(x['max_abs_adjacent_mean_rate_per_ns'] <= base.THERMAL_RATE_V_PER_NS for x in rows.values()),
        all_four_block_rates_nonincreasing_with_original_tolerance=all(all(b <= a + base.RATE_INCREASE_TOLERANCE_V_PER_NS for a,b in zip(x['fixed2ns_max_abs_cycle_mean_rates_k_per_ns'], x['fixed2ns_max_abs_cycle_mean_rates_k_per_ns'][1:])) for x in rows.values()))
    return dict(declared_window_s=[stop-8e-9,stop], thermal_nodes=rows, checks=checks,
        converged=all(checks.values()),rate_limit_k_per_ns=base.THERMAL_RATE_V_PER_NS,
        nonincrease_tolerance_k_per_ns=base.RATE_INCREASE_TOLERANCE_V_PER_NS,
        original_endpoint_metric_preserved=True,
        scope='Finite phase-invariant stationarity screen of saved samples; not infinite-time equilibrium or frequency-lock acceptance')


class Meter(previous.Meter):
    def __init__(self, columns, hbts, case, stop=STOP):
        super().__init__(columns,hbts,case,stop)
        self.phase_names = ['time','v(clkp)','v(clkn)'] + sorted(n for n in columns if n.endswith('.t)') or n.endswith('.dt)'))
        require(len(self.phase_names) == 56, 'Bounded exact phase vector census')
        self.phase_data = {n:array('d') for n in self.phase_names}
        self.before_phase = None

    def phase_append(self,row):
        require(len(self.phase_data['time']) < MAX_PHASE_ROWS, 'Bounded phase-window storage')
        for name in self.phase_names:
            value = row[self.index[name]]
            self.phase_data[name].append(min(value,self.stop) if name == 'time' else value)

    def push(self,row):
        super().push(row)
        if row[self.index['time']] < self.stop-8e-9:
            self.before_phase = row
        else:
            if not self.phase_data['time'] and self.before_phase is not None:
                self.phase_append(self.before_phase)
                self.before_phase = None
            self.phase_append(row)

    def finish(self):
        value = super().finish()
        d = self.phase_data
        conv = phase_convergence(d['time'],np.asarray(d['v(clkp)'])-np.asarray(d['v(clkn)']),
            {n:d[n] for n in self.phase_names[3:]}, self.stop,value['convergence'])
        value['phase_convergence'] = conv
        value['phase_invariant_screen_pass'] = all(value['safety_checks'].values()) and value['final_clock_window']['functional_pass'] and conv['converged']
        return value


def capture_stream(
    stream,
    output,
    expected,
    hbts,
    case,
    prefix,
    stop=STOP,
    publisher=None,
    rows_per_part=previous.PART_ROWS,
    reclaim=True,
    min_free_bytes=MIN_FREE_BYTES,
):
    require(sys.byteorder == "little", "Pinned x86 binary format")
    output = Path(output)
    output.mkdir()
    header, meta = tiny.parse_header(stream, expected)
    require(meta["declared_points"] == 0, "Native nonseekable zero-count header")
    (output / "header.bin").write_bytes(header)
    meter = Meter(meta["columns"], hbts, case, stop)
    queue = PartQueue(
        output / "parts",
        prefix,
        meta["columns"],
        publisher,
        rows_per_part,
        reclaim,
        min_free_bytes,
    )
    decoder = struct.Struct("<" + "d" * len(meta["columns"]))
    pending, raw_hash = bytearray(), hashlib.sha256(header)
    try:
        while data := stream.read(65536):
            raw_hash.update(data)
            pending.extend(data)
            count = len(pending) // decoder.size
            for i in range(count):
                sample = bytes(pending[i * decoder.size : (i + 1) * decoder.size])
                meter.push(decoder.unpack(sample))
                queue.append(sample)
            del pending[: count * decoder.size]
        trailer = bytes(pending)
        (output / "trailer.bin").write_bytes(trailer)
        require(
            trailer == str(queue.rows).encode(), "Exact completed native count trailer"
        )
        measurement = meter.finish()
        ledger = queue.finish()
        result = dict(
            **meta,
            rows=queue.rows,
            stop_s=stop,
            step_s=case["step_s"],
            raw_sha256=raw_hash.hexdigest(),
            payload_sha256=ledger["payload_sha256"],
            header_sha256=sha(output / "header.bin"),
            trailer_sha256=sha(output / "trailer.bin"),
            ledger_sha256=sha(output / "parts/parts.json"),
            measurement=measurement,
            status="PASS_COMPLETE_CAPTURE",
            live_release_publication=type(publisher) is lifecycle.OwnedPublisher,
            semantic_screen_pass=measurement["phase_invariant_screen_pass"],
        )
        atomic(output / "capture.json", result)
        return result
    except BaseException as error:
        atomic(
            output / "failure.json",
            dict(
                status="INCOMPLETE_OR_INVALID_CAPTURE",
                error=repr(error),
                observed_rows=queue.rows,
                completed_parts=len(queue.parts),
            ),
        )
        raise


def bind_prior_outputs(prior):
    require(sha(PRIOR_REVIEW_PATH) == PRIOR_REVIEW_SHA, 'Exact sealed failed-capture inventory')
    proof = json.loads(PRIOR_REVIEW_PATH.read_text())
    require(proof['native_result_sha256'] == phase.RESULT_SHA and proof['source_inputs_rehashed'] == 101, 'Original capture proof identity')
    inventory = proof['native_output_inventory']
    name = proof['case']['name']
    required = {'result.json','producer.py','spinit',*(name+'/'+n for n in ('run.log','initial-op.dat','bench.cir',base.prior.FILE,'capture/header.bin','capture/trailer.bin','capture/parts/parts.json'))}
    require(required <= set(inventory), 'Complete original native log/OP/deck/interface binding')
    pins = {str(PRIOR_REVIEW_PATH):PRIOR_REVIEW_SHA}
    for rel,pin in inventory.items():
        path = Path(prior)/rel
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], 'Original output changed: '+rel)
        pins[str(path)] = pin['sha256']
    return pins


def bind_generated(expected):
    pins = {}
    for path,text in expected.items():
        path = Path(path)
        require(path.read_bytes() == text.encode(), 'Exact generated native input: '+str(path))
        pins[str(path.resolve())] = hashlib.sha256(text.encode()).hexdigest()
    return pins


def source_pins(prior):
    require(sha(lifecycle.__file__) == LIFECYCLE_SHA and sha(phase.__file__) == PHASE_SHA, 'Frozen lifecycle and phase methods')
    prior = Path(prior)
    require(sha(prior/'result.json') == phase.RESULT_SHA, 'Exact preserved first1us failure')
    record = json.loads((prior/'result.json').read_text())
    pins = dict(record['source_sha256'])
    pins.update(bind_prior_outputs(prior))
    pins[str(prior/'result.json')] = phase.RESULT_SHA
    pins[str(Path(__file__).resolve())] = sha(__file__)
    pins[str(Path(phase.__file__).resolve())] = PHASE_SHA
    # The new phase reducer uses NumPy; bind its installed code/binaries too.
    for p in Path(np.__file__).parent.rglob('*'):
        if p.is_file() and p.suffix in ('.py','.so'):
            pins[str(p.resolve())] = sha(p)
    pins[str(Path(sys.executable).resolve())] = sha(Path(sys.executable).resolve())
    verify_pins(pins)
    return record,pins


def verify_pins(pins):
    require(all(sha(name) == digest for name,digest in pins.items()), 'All exact producer/runtime/model inputs unchanged')


def retrieve_part(row,path):
    require(row['asset']['url'] == RELEASE+row['name'] and row['asset']['sha256'] == row['sha256'], 'Exact original public asset address')
    require(shutil.disk_usage(path.parent).free >= MIN_FREE_BYTES + row['bytes'], 'Preserve512MiB during bounded public replay')
    require(not path.exists(), 'Fresh public part scratch')
    count=0
    with urllib.request.urlopen(row['asset']['url'],timeout=60) as remote,path.open('xb') as local:
        while data := remote.read(1024*1024):
            count += len(data)
            require(count <= row['bytes'], 'No public asset overrun')
            local.write(data)
    require(count == row['bytes'] and sha(path) == row['sha256'], 'Public complete compressed identity')


def replay_first(prior,output):
    prior,output = Path(prior).resolve(),Path(output).resolve()
    record,pins = source_pins(prior)
    require(not output.exists() and output.is_relative_to(Path('/dev/shm')), 'Fresh RAM replay output')
    output.mkdir()
    atomic(output/'source-pins.json',pins)
    row = record['cases'][0]
    folder = prior/row['case']['name']
    cap = row['capture']
    require(row['execution']['returncode'] == 0 and cap['rows'] == 2000011 and cap['stop_s'] == STOP and cap['step_s'] == .5e-12, 'Exact completed first native capture')
    lp = folder/'capture/parts/parts.json'
    require(sha(lp) == cap['ledger_sha256'], 'Original part ledger pin')
    ledger = json.loads(lp.read_text())
    require(ledger['status'] == 'PASS_PUBLISHED_PARTS' and len(ledger['parts']) == 31 and ledger['columns'] == cap['columns'], 'Exact31 original parts')
    circuit = (folder/base.prior.FILE).read_text()
    hbts = base.driver.contract(circuit,4)
    parent_circuit = next(Path(n) for n in pins if n.endswith('/'+row['case']['name']+'/'+base.prior.FILE))
    require(circuit == parent_circuit.read_text(), 'Frozen circuit in reused native capture')
    meter = Meter(cap['columns'],hbts,row['case'])
    payload = hashlib.sha256()
    header,trailer = (folder/'capture/header.bin').read_bytes(),(folder/'capture/trailer.bin').read_bytes()
    require(hashlib.sha256(header).hexdigest() == cap['header_sha256'] and hashlib.sha256(trailer).hexdigest() == cap['trailer_sha256'], 'Raw header/trailer identity')
    import io
    parsed_header,parsed = tiny.parse_header(io.BytesIO(header),base.prior.vectors(hbts))
    require(parsed_header == header and parsed['columns'] == cap['columns'], 'Original native interface bijection')
    raw_hash = hashlib.sha256(header)
    decoder = struct.Struct('<'+'d'*len(cap['columns']))
    seen,part_receipts = 0,[]
    state = dict(status='REPLAYING_ORIGINAL_PARTS',original_status=record['status'],source_sha256=pins,parts=part_receipts)
    atomic(output/'progress.json',state)
    try:
        for i,p in enumerate(ledger['parts']):
            require(p['index'] == i and p['first_row'] == seen and p['name'] == f"{ledger['prefix']}-part{i:05d}.bin.xz", 'Unique ordered original coverage')
            publication_path = lp.parent/f'publication-{i:05d}.json'
            require(sha(publication_path) == p['receipt_sha256'], 'Original publication receipt')
            publication_record = json.loads(publication_path.read_text())
            require(publication_record['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and publication_record['assets'] == [p['asset']], 'Exact two-path original receipt')
            require(p['status'] == 'PUBLIC_VERIFIED' and p['asset']['authenticated_roundtrip'] is True and p['asset']['anonymous_roundtrip'] is True, 'Original permanent retention')
            path = output/p['name']
            retrieve_part(p,path)
            with lzma.open(path,'rb') as f:
                raw = f.read(p['uncompressed_bytes']+1)
            require(len(raw) == p['uncompressed_bytes'] == p['rows']*decoder.size and hashlib.sha256(raw).hexdigest() == p['uncompressed_sha256'], 'Exact uncompressed original part')
            for values in decoder.iter_unpack(raw):
                meter.push(values)
            payload.update(raw);raw_hash.update(raw);seen += p['rows']
            part_receipts.append(dict(index=i,rows=p['rows'],name=p['name'],compressed_sha256=p['sha256'],uncompressed_sha256=p['uncompressed_sha256'],public_anonymous_roundtrip=True,all_values_replayed=True))
            path.unlink()  # Only this exact freshly re-downloaded public duplicate.
            del raw
            atomic(output/'progress.json',state)
        raw_hash.update(trailer)
        require(seen == cap['rows'] and trailer == str(seen).encode() and payload.hexdigest() == cap['payload_sha256'] and raw_hash.hexdigest() == cap['raw_sha256'], 'Complete original native raw stream')
        measurement = meter.finish()
        legacy = {k:v for k,v in measurement.items() if k not in ('phase_convergence','phase_invariant_screen_pass')}
        require(legacy == row['measurement'], 'All original fulltime safety/clock/thermal reductions exactly reproduce')
        native = classify_log((folder/'run.log').read_text(),cap,hbts,NG47_SHA,.5e-12,row['execution']['returncode'])
        op = base.driver.parent.init.startup.initial_op(folder/'initial-op.dat',base.prior.vectors(hbts))
        require(max(map(abs,op.values())) <= 1e-10, 'Exact original zero-source OP')
        verify_pins(pins)
        new_row = dict(case=row['case'],measurement=measurement,native=native,initial_op=op,execution=row['execution'],reused_original_native=True,original_capture=cap,original_status=record['status'])
        result = dict(status='PASS_V3_FIRST_CAPTURE_REPLAY' if measurement['phase_invariant_screen_pass'] else 'FAIL_V3_FIRST_CAPTURE_SCREEN',source_sha256=pins,original_result_path=str(prior/'result.json'),parts=part_receipts,rows=seen,raw_sha256=raw_hash.hexdigest(),first_case=new_row,original_v2_status_preserved=record['status'],original_v2_error_preserved=record['error'],native_rerun=False,second_case_started=False,scope='Separate complete raw replay with phase-aware finite screen. Original v2ERROR and endpoint metric FAIL unchanged; no timestep-pair/PLL/CDR/PCIe/fullPEX acceptance.')
        atomic(output/'result.json',result)
        return result
    except BaseException as error:
        state.update(status='ERROR_REPLAY_INCOMPLETE',error=repr(error))
        atomic(output/'progress.json',state)
        raise


def run_second(first,parent,output,prefix):
    first,parent,output = map(lambda p:Path(p).resolve(),(first,parent,output))
    prior_replay = json.loads((first/'result.json').read_text())
    require(prior_replay['status'] == 'PASS_V3_FIRST_CAPTURE_REPLAY' and prior_replay['rows'] == 2000011, 'Complete source-bound first replay before second native')
    pins = dict(prior_replay['source_sha256']);verify_pins(pins)
    require(pins[str(Path(__file__).resolve())] == sha(__file__), 'Same frozen v3 source as full first replay')
    require(not output.exists() and output.is_relative_to(Path('/dev/shm')), 'Fresh second-case output')
    require(shutil.disk_usage('/dev/shm').free >= 1024**3, 'Initial1GiB free-space gate')
    previous_parent,old_pins = lifecycle.verify_parent(parent)
    for name,digest in old_pins.items():
        require(name in pins and pins[name] == digest, 'Exact original40ns parent/source closure')
    pins[str(first/'result.json')] = sha(first/'result.json')
    case = previous_parent['cases'][1]['case']
    require(case['step_s'] == .25e-12 and [prior_replay['first_case']['case'],case] == base.cases(), 'Original exact timestep pair')
    runtime = next(Path(n) for n,h in pins.items() if Path(n).name == 'ngspice' and h == NG47_SHA)
    output.mkdir();(output/'producer.py').write_bytes(Path(__file__).read_bytes())
    (output/'spinit').write_text(base.driver.parent.init.SPINIT)
    record = dict(status='RUNNING_V3_SECOND_CASE',source_sha256=pins,cases=[prior_replay['first_case']],original_v2_status='ERROR_INCOMPLETE',prior_failure_superseded=False)
    atomic(output/'result.json',record)
    folder = output/case['name'];folder.mkdir()
    source = parent/case['name'];circuit = (source/base.prior.FILE).read_text()
    (folder/base.prior.FILE).write_text(circuit)
    (folder/'bench.cir').write_text(lifecycle.long_deck((source/'bench.cir').read_text(),case['step_s']))
    expected_deck = lifecycle.long_deck((source/'bench.cir').read_text(),case['step_s'])
    pins.update(bind_generated({folder/'bench.cir':expected_deck,folder/base.prior.FILE:circuit,
        output/'spinit':base.driver.parent.init.SPINIT,output/'producer.py':Path(__file__).read_text()}))
    verify_pins(pins)
    hbts = base.driver.contract(circuit,4);expected = base.prior.vectors(hbts)
    row = dict(case=case,status='NATIVE_RUNNING');record['cases'].append(row)
    atomic(output/'result.json',record)
    try:
        cap,execution = lifecycle.native_wait(runtime,folder,folder/'run.log',lambda f,owner:capture_stream(f,folder/'capture',expected,hbts,case,prefix,publisher=lifecycle.OwnedPublisher(owner)))
        row.update(capture=cap,execution=execution,measurement=cap['measurement'])
        require(cap['live_release_publication'] is True, 'Live public retention required')
        row['native'] = classify_log((folder/'run.log').read_text(),cap,hbts,sha(runtime),case['step_s'],execution['returncode'])
        row['initial_op'] = base.driver.parent.init.startup.initial_op(folder/'initial-op.dat',expected)
        require(max(map(abs,row['initial_op'].values())) <= 1e-10, 'Exact zero-source initialOP')
        verify_pins(pins)
        row.update(status='COMPLETE',outputs={str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()})
        record['pair_agreement'] = base.pair_agreement(record['cases'])
        record['status'] = 'PASS_V3_LIMITED_PHASE_INVARIANT1US_PAIR' if all(c['measurement']['phase_invariant_screen_pass'] for c in record['cases']) and record['pair_agreement']['pass_pair'] else 'FAIL_V3_LIMITED_PHASE_INVARIANT1US_PAIR'
        record['scope'] = 'New finite phase-aware pair only; no replacement of historicalFAIL, infinite-time equilibrium,8GHz lock,PLL/CDR/PCIe/fullPEX acceptance'
        atomic(output/'result.json',record)
    except BaseException as error:
        record.update(status='ERROR_V3_INCOMPLETE',error=repr(error));atomic(output/'result.json',record);raise
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command',required=True)
    r = sub.add_parser('replay-first')
    for name in ('prior','out'):r.add_argument('--'+name,type=Path,required=True)
    n = sub.add_parser('run-second')
    for name in ('first','parent','out'):n.add_argument('--'+name,type=Path,required=True)
    n.add_argument('--release-prefix',required=True)
    a = ap.parse_args()
    result = replay_first(a.prior,a.out) if a.command == 'replay-first' else run_second(a.first,a.parent,a.out,a.release_prefix)
    if result['status'] not in ('PASS_V3_FIRST_CAPTURE_REPLAY','PASS_V3_LIMITED_PHASE_INVARIANT1US_PAIR'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
