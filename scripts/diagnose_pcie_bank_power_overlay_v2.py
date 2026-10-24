#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same finite powered experiment after actual parallel power-metal repair.

The351 intrinsic devices/body assumptions and frozen external recipe stay exact.
Only independently audited physical wire R/C changes. This remains a diagnostic,
not qualified PEX, RF, startup, CDR/BER or full model-range acceptance.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time

import diagnose_pcie_bank_powered_v1 as prior

h = prior.h
PINS = {
    'composition': prior.COMPOSITION_SHA,
    'prior_hybrid': prior.HYBRID_SHA,
    'prior_anchors': h.PINS['anchors'],
    'anchors': '67bc426521a60cce145a85ee428504db16eb3e20ade87d43e3b2ffdcd984717c',
    'wires': '696e47f1aa6356e01f566a54dfe7cfe7a14b7d4ee3fb4cb63d9bd5ed89eb2f9f',
    'rc_review': '29c3a3302987111398ab257d3dca7982b211488d84953b4388c3a5ade1ca9540',
    'geometry_review': '6893c7289375a2ceaf9fc784be29c3cd9cfd93a4e45ae00cfdf28cb020015fbc',
}
PRIOR_SHA = 'e289e33da592cbfdca37f4b7bf30c743addf524c4abe378a813f1974e12182e6'
COUNTS = {'R': 33733, 'C': 16788}
BODY_ASSUMPTION = ('BODY_ESD_RETURN and WIRE_CREF independently held at ideal0V externally; '
                   'no inferred internal body-to-metal link')


def wire_records(text, counts=COUNTS):
    rows = h.statements(text)
    h.require(rows[0][:2] == ['.subckt', 'bank_wires'] and rows[-1] == ['.ends'], 'Wire wrapper changed')
    records = rows[1:-1]; names = set()
    for row in records:
        h.require(len(row) == 4 and row[0][0] in 'RC', 'Unexpected wire element')
        h.require(row[0].lower() not in names, 'Duplicate wire element'); names.add(row[0].lower())
        h.require(row[1] != row[2] and h.number(row[3]) > 0, 'Invalid physical wire element')
    h.require(Counter(r[0][0] for r in records) == counts, 'Physical R/C census changed')
    return rows[0][2:], records


def physical_wire_contract(anchors, ports, records):
    by = {a['label']: a for a in anchors['anchors']}
    h.require(len(by) == len(ports) == 804 and set(by) == set(ports), 'Actual804 wire anchors changed')
    graph = h.Union()
    for name, a, b, _ in records:
        if name.startswith('R'): graph.join(a, b)
    owners = {}; components = {}
    for label, a in by.items():
        root = graph.find(label); component = a['wire_component']
        h.require(root not in owners or owners[root] == component, 'Physical wire short')
        h.require(component not in components or components[component] == root, 'Physical wire open')
        owners[root] = component; components[component] = root
    h.require(set(owners.values()) == set(range(1,129)) and len(owners) == 128, 'Actual128 conductor census changed')
    h.require(all(graph.find(n) in owners for n in graph.parent), 'Unanchored physical resistor network')
    for row in records:
        h.require(all(n == 'sub' or n in graph.parent for n in row[1:3]), 'Unknown physical C terminal')
    return {a['label']: a['detail']['name'] for a in anchors['anchors'] if a['kind'] == 'PUBLIC_PORT_REFERENCE'}


def compose(comp, anchors, old_anchors, prior_text, wire_text):
    for key in ('anchors', 'unmodeled_body_well_terminals', 'actual_metal_terminals', 'body_well_terminals'):
        h.require(anchors[key] == old_anchors[key], 'Original physical terminal/body identity changed')
    old = h.statements(prior_text)
    h.require(old[0][2:] == comp['ports'], 'Prior physical port identity changed')
    h.require(old[1:352] == [d['line'].split() for d in comp['records']], 'Original351 device lines changed')
    h.require(len(comp['records']) == 351 and Counter(d['model'] for d in comp['records']) == h.CENSUS,
              'Original intrinsic census changed')
    ports, records = wire_records(wire_text)
    public = physical_wire_contract(anchors, ports, records)
    h.require(len(public) == len(set(public.values())) == 56 and
              sorted(public.values()) + ['BODY_ESD_RETURN', 'WIRE_CREF'] == comp['ports'], 'Public source interface changed')
    def node(name):
        if name == 'sub': return 'WIRE_CREF'
        if name in public: return public[name]
        h.require(re.fullmatch(r'[TP]\d+(?:\.n\d+)?', name) is not None, 'Unexpected native wire spelling')
        return 'w_' + name
    mapping = {n: node(n) for r in records for n in r[1:3]}
    h.require(len(set(n.lower() for n in mapping.values())) == len(mapping), 'Physical node collision')
    lines = ['* Actual power-overlay native wire RC, unchanged351 intrinsic devices; NOT qualified PEX.',
             '.subckt nssoc_bank_hybrid_open_v1 ' + ' '.join(comp['ports'])]
    lines += [d['line'] for d in comp['records']]
    lines += [' '.join([r[0], node(r[1]), node(r[2]), r[3]]) for r in records]
    lines += ['.ends nssoc_bank_hybrid_open_v1', '']
    return '\n'.join(lines)


def owned_size(out):
    paths = set(map(Path, prior.OWN_ROOTS)) | {out}
    for pattern in ('nssoc-power-overlay-*', 'nssoc-magic-area-product-v4-*', 'nssoc-area-v4-*'):
        paths.update(Path('/dev/shm').glob(pattern))
    return sum(prior.regular_size(p) for p in paths)


def stop_owned(proc):
    """Only owned resource/error/cancel cleanup; never elapsed cancellation."""
    try: os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.wait(); return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        proc.poll()  # Reap the group leader promptly, also when it ignores TERM.
        try: os.killpg(proc.pid, 0)
        except ProcessLookupError:
            proc.wait(); return
        time.sleep(.05)
    try: os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError: pass
    proc.wait()


def run_native(root, ngspice, out, save, row):
    fifo = root / 'wave.fifo'; os.mkfifo(fifo)
    # Parent keeper prevents a reader-open deadlock when a native process aborts
    # before wrdata. It is noninheritable; close after all owned writers stop.
    keeper = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    stream = row['stream']; stream.setdefault('raw_bytes', 0); proc = None
    reader = threading.Thread(target=prior.stream_wave, args=(fifo, root/'wave.dat.gz', stream), daemon=True)
    reader.start()
    env = {k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME')}
    env['SPICE_SCRIPTS'] = str(root.resolve()); env['OMP_NUM_THREADS'] = '1'
    start = time.monotonic(); reason = None
    try:
        with (root/'native.log').open('w') as log:
            proc = subprocess.Popen([str(ngspice.resolve()), '-n', '-b', 'bench.cir'], cwd=root, env=env,
                                    preexec_fn=prior.limits, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            row['pid'] = proc.pid; save()
            while proc.poll() is None:
                free = prior.shared_free(); size = owned_size(out)
                row['resources'].append(dict(elapsed_s=time.monotonic()-start,shared_free=free,own_scratch=size,
                                             stream_raw_bytes=stream.get('raw_bytes',0)))
                if free < 512*1024**2: reason = 'SHARED_512MIB_RESERVE'
                elif size > 80*1024**2: reason = 'OWN_80MIB_SCRATCH_LIMIT'
                elif stream.get('error'): reason = 'WAVE_CAPTURE_ERROR'
                if reason: break
                save(); time.sleep(2)
    finally:
        if proc is not None: stop_owned(proc)
        os.close(keeper)
        # Native writer is reaped and keeper closed, so EOF drains the reader.
        reader.join(timeout=5)
        if reader.is_alive():
            row['collector_failure'] = 'WAVE_COLLECTOR_DID_NOT_DRAIN'
        fifo.unlink()
        row.update(returncode=proc.returncode if proc else None,elapsed_seconds=time.monotonic()-start,resource_stop=reason)
    h.require(not reader.is_alive(), 'Wave collector failed to drain after native reap')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in [*PINS, 'model_receipt', 'ngspice', 'pdk', 'osdi_root', 'out']:
        ap.add_argument('--'+name.replace('_','-'), type=Path, required=True)
    args = ap.parse_args()
    for name,digest in PINS.items():
        h.require(h.pin(getattr(args,name))['sha256'] == digest, 'Frozen overlay input changed: '+name)
    for p,digest in [(Path(prior.__file__),PRIOR_SHA),(Path(h.__file__),prior.METHOD_SHA),(args.ngspice,prior.NG_SHA)]:
        h.require(h.pin(p)['sha256'] == digest,'Frozen inherited method/runtime changed')
    comp = json.loads(args.composition.read_text()); anchors = json.loads(args.anchors.read_text())
    rc = json.loads(args.rc_review.read_text()); geometry = json.loads(args.geometry_review.read_text())
    h.require(rc['status'] == 'PASS_AREA_PATCH_FULL804_TERMINAL128_WIRE_NATIVE_R_AND_EXACT_POINT_C_EXPORT' and
              rc['variant'] == 'overlay' and not rc['new_negative_points'], 'Native physical RC not accepted')
    h.require(geometry['status'] == 'PASS_GEOMETRY_STRICT351DEVICE56PORT_LVS804ANCHORS128CONDUCTORS_NO_RC_YET', 'Native geometry/anchor guard failed')
    h.require(rc['inputs'][str(args.wires)] == h.pin(args.wires), 'RC source bridge changed')
    h.require(geometry['outputs']['anchors.json'] == h.pin(args.anchors), 'Geometry anchor bridge changed')
    hybrid = compose(comp, anchors, json.loads(args.prior_anchors.read_text()), args.prior_hybrid.read_text(), args.wires.read_text())
    receipt = json.loads(args.model_receipt.read_text()); models = args.pdk/'libs.tech/ngspice/models'
    osdis = [args.osdi_root/n for n in ('r3_cmc.osdi','psp103.osdi','psp103_nqs.osdi')]
    for p in [*models.glob('*.lib'),*osdis]:
        h.require(str(p) in receipt['inputs'] and h.pin(p) == receipt['inputs'][str(p)],'Native model/OSDI changed')
    args.out.mkdir(parents=True,exist_ok=False)
    inputs = {str(p):h.pin(p) for p in [Path(__file__),Path(prior.__file__),Path(h.__file__),*[getattr(args,k) for k in PINS],args.model_receipt,args.ngspice,*models.glob('*.lib'),*osdis]}
    mapping = prior.physical_to_ideal(comp,anchors)
    record = dict(status='RUNNING',inputs=inputs,cases=[],full_pex_qualified=False,elapsed_cancellation=False,
                  body_reference_assumption=BODY_ASSUMPTION,wire_counts=COUNTS,unchanged_devices=351,unchanged_finite_contacts=109,
                  unchanged_metal_terminals=748,unmodeled_body_well_terminals=313,external_recipe_and_metrology='Exact frozen powered-v1 functions',
                  inherited_model_range_limitation='One HVPMOS width32um exceeds documented0.30..10um range; retained identically in both cases.',
                  purpose='Actual same-external-condition physical power-route comparison; no4ns proof of eventual startup/failure or BER/CDR acceptance')
    def save():
        temp=args.out/'result.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(args.out/'result.json')
    save()
    for mode in ('intrinsic_only','distributed_wire'):
        h.require(prior.shared_free()>512*1024**2 and owned_size(args.out)<80*1024**2,'Resource reserve unavailable')
        root=args.out/mode;root.mkdir();contract=prior.vector_contract(comp,mapping,mode)
        (root/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (root/'bank.spice').write_text(prior.circuit(comp,hybrid,mapping,mode))
        (root/'bench.cir').write_text(prior.deck(comp,contract,models,osdis))
        (root/'spinit').write_text('* Exact model OSDIs loaded explicitly by this private diagnostic.\n')
        row=dict(mode=mode,status='RUNNING',stream={},resources=[]);record['cases'].append(row);save()
        try:
            run_native(root,args.ngspice,args.out,save,row)
            h.require(row['returncode']==0 and row['resource_stop'] is None,'Native process/resource failure')
            h.require(row['stream'].get('complete') is True and not row['stream'].get('error'),'Incomplete lossless waveform stream')
            row['audit']=prior.audit_native(root,contract);row['status']='COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE'
        except BaseException as error:
            row.update(status='FAIL_PRESERVED',error=type(error).__name__+': '+str(error));save()
            if not isinstance(error,Exception):raise
        row['outputs']={p.name:h.pin(p) for p in root.iterdir() if p.is_file()};save()
        if row['status']=='FAIL_PRESERVED':break
    h.require(all(h.pin(p)==v for p,v in inputs.items()),'Frozen source/runtime/input changed')
    record['status']='COMPLETE_PAIRED_DIAGNOSTIC_NOT_ACCEPTANCE' if len(record['cases'])==2 and all(c['status']=='COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE' for c in record['cases']) else 'FAIL_PRESERVED'
    save();print(record['status'])
    if record['status']=='FAIL_PRESERVED':raise SystemExit(1)


if __name__ == '__main__':main()
