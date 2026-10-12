#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native, fixed-oracle TX mux operating-point study on hosted runners."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, digest, dest):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent',
                    '--show-error', url, '-o', str(dest)], check=True)
    assert sha(dest) == digest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--point', required=True)
    parser.add_argument('--kind', choices=('compact', 'wire'), required=True)
    parser.add_argument('--layout-composition', type=Path,
                        help='Hosted source-bound composition directory for a real layout candidate')
    parser.add_argument('--interconnect', choices=('actual', 'no_cap', 'low_r', 'low_r_no_cap',
        'low_r_supply', 'low_r_return', 'low_r_inputs', 'low_r_internal', 'low_r_bias', 'low_r_outputs'), default='actual')
    args = parser.parse_args()
    spec_path = ROOT / 'docs/evidence/pcie-tx-cloud-input-20261013.json'
    spec = json.loads(spec_path.read_text())
    values = spec['points'][args.point]
    out = ROOT / 'cloud-tx-operating-point'
    out.mkdir(exist_ok=False)
    inputs = out / 'inputs'
    inputs.mkdir()
    config_path = inputs / 'config.json'
    config = dict(name=args.point, hbt='hbt_typ', resistor='res_typ', temperature_c=27, supply_scale=1.0)
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    result = dict(status='RUNNING', point=args.point, kind=args.kind, interconnect=args.interconnect,
                  operating_point=dict(zip(spec['point_order'], values, strict=True)),
                  accepted=False, scope='Final2:1 mux plus compact TX driver only. Ideal input common modes and bias; development distributed wire RC is not qualified RF PEX. Full serializer/PLL/CDR/PHY and production acceptance remain open.')
    try:
        archive = inputs / 'source.tar.gz'
        fetch(spec['receipt']['url'], spec['receipt']['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(inputs, filter='data')
        archive.unlink()
        manifest = json.loads((inputs / 'manifest.json').read_text())
        assert all(sha(inputs / n) == r['sha256'] for n, r in manifest['files'].items())
        for bundle in spec['method_archives']:
            fetch(bundle['url'], bundle['sha256'], archive)
            with tarfile.open(archive) as tar:
                for name, digest in bundle['members'].items():
                    member = tar.getmember(name)
                    assert member.isfile() and member.size < 1024 * 1024
                    data = tar.extractfile(member).read()
                    assert hashlib.sha256(data).hexdigest() == digest
                    target = inputs / Path(name).name
                    assert not target.exists()
                    target.write_bytes(data)
            archive.unlink()
        if args.layout_composition is not None:
            assert args.kind == 'wire' and args.interconnect == 'actual' and args.point == 'baseline'
            source = args.layout_composition.resolve()
            assert source.is_relative_to(ROOT)
            composed = json.loads((source / 'result.json').read_text())
            assert composed['status'] == 'PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT'
            assert composed['composition']['counts']['devices'] == 54
            assert all(sha(source / name) == digest for name, digest in composed['outputs'].items())
            wire = inputs / 'mux54-wire01.spice'
            wire.rename(inputs / 'original-wire.source')
            shutil.copyfile(source / 'mux54-wire01.spice', wire)
            shutil.copyfile(source / 'result.json', inputs / 'layout-composition.json')
            result['actual_layout_composition'] = dict(variant=composed['variant'],
                report_sha256=sha(source / 'result.json'), mux_sha256=sha(wire),
                extraction_source=composed['source'], counts=composed['composition']['counts'])
        if args.interconnect != 'actual':
            assert args.point == 'baseline' and args.kind == 'wire'
            wire = inputs / 'mux54-wire01.spice'
            original = wire.read_text()
            (inputs / 'original-wire.source').write_text(original)
            parent = {}

            def root(node):
                parent.setdefault(node, node)
                if parent[node] != node:
                    parent[node] = root(parent[node])
                return parent[node]

            edges = []
            for line in original.splitlines():
                fields = line.split()
                if fields and fields[0].lower().startswith('r'):
                    assert len(fields) == 4
                    parent[root(fields[1])] = root(fields[2])
                    edges.append(fields)
            ports = next(l.split()[2:] for l in original.splitlines() if l.lower().startswith('.subckt'))
            groups = {}
            for fields in edges:
                key = root(fields[1])
                groups.setdefault(key, dict(ports=[], edges=[]))['edges'].append(fields)
            for port in ports:
                if root(port) in groups:
                    groups[root(port)]['ports'].append(port)
            classes = {}
            for key, group in groups.items():
                public = set(group['ports'])
                labels = []
                for name, names in dict(supply={'avdd'}, return_={'avss', 'sub'},
                    inputs={'ap', 'an', 'bp', 'bn', 'sp', 'sn'}, bias={'iref'}, outputs={'op', 'on'}).items():
                    if public & names:
                        labels.append(name.removesuffix('_'))
                if not public:
                    labels = ['internal']
                assert len(labels) == 1, group
                classes[key] = labels[0]
            components = [dict(category=classes[key], ports=g['ports'],
                resistor_count=len(g['edges']), sum_resistance_ohm=sum(float(e[3]) for e in g['edges']),
                largest_edges=sorted(g['edges'], key=lambda e:float(e[3]), reverse=True)[:5])
                for key, g in groups.items()]
            (out / 'wire-components.json').write_text(json.dumps(components, indent=2) + '\n')
            result['wire_components'] = components
            changed, resistors, capacitors, selected = [], 0, 0, 0
            for line in original.splitlines():
                fields = line.split()
                if fields and fields[0].lower().startswith(('r', 'c')):
                    assert len(fields) == 4, line
                    float(fields[3])
                    if fields[0].lower().startswith('r'):
                        resistors += 1
                        category = classes[root(fields[1])]
                        if args.interconnect in ('low_r', 'low_r_no_cap') or args.interconnect == 'low_r_' + category:
                            fields[3] = '0.001'
                            line = ' '.join(fields)
                            selected += 1
                    else:
                        capacitors += 1
                        if args.interconnect in ('no_cap', 'low_r_no_cap'):
                            continue
                changed.append(line)
            assert (resistors, capacitors) == (229, 301)
            if args.interconnect.startswith('low_r'):
                assert selected > 0
            wire.write_text('\n'.join(changed) + '\n')
            result['diagnostic_mutation'] = dict(resistors=resistors, capacitors=capacitors, selected_resistors=selected,
                original_sha256=hashlib.sha256(original.encode()).hexdigest(), mutated_sha256=sha(wire),
                note='Causal diagnostic only. Explicit metal resistors become1milliohm and/or metal capacitors are removed. Device models, layout and measurement limits unchanged. Mutated parasitics cannot be adopted or used as physical acceptance.')
        ng = Path(os.environ['CLOUD_NGSPICE'])
        assert sha(ng) == spec['native_runtime']['executable_sha256']
        tx = ROOT / 'hw/soc/analog/pcie/tx_cml_rsil.spice'
        assert sha(tx) == spec['tx_sha256']
        # Load frozen functions without running their old local controller.
        saved_argv = sys.argv
        sys.argv = [str(inputs / 'native101.py'), str(config_path), '.00025']
        try:
            native = load('frozen_native101', inputs / 'native101.py')
        finally:
            sys.argv = saved_argv
        native.MODELS = inputs / 'models'
        native.MUX = inputs / f'mux54-{args.kind}01.spice'
        native.TX, native.NG, native.OSDI = tx, ng, inputs / 'r3_cmc.osdi'
        native.BIAS = .0005
        baseline, _, _, _ = native.deck('nominal')
        original_pwl = native.pwl

        def configured_pwl(bits, cm, amp, period, invert=False):
            assert period in (native.UI, 2 * native.UI)
            cm, amp = values[2:] if period == native.UI else values[:2]
            return original_pwl(bits, cm, amp, period, invert)

        native.pwl = configured_pwl
        deck, bindings, vectors, bits = native.deck('nominal')
        pattern = r'(?ms)^V[abs][pn] [^\n]+ PWL\(.*?\)'
        untouched_before, n1 = re.subn(pattern, '<prospective_input_source>', baseline)
        untouched_after, n2 = re.subn(pattern, '<prospective_input_source>', deck)
        assert n1 == n2 == 6 and untouched_before == untouched_after
        if args.point == 'baseline':
            assert deck == baseline
        run = out / 'native'
        run.mkdir()
        (run / 'bench.cir').write_text(deck)
        (run / 'spinit').write_text('set num_threads=1\n')
        # Both candidate netlists are restored, but the frozen reviewer locates
        # the simulated mux through the active input manifest. Do not bind the
        # unused compact netlist as if it were part of the wire simulation.
        paths = [p for p in inputs.rglob('*') if p.is_file()
                 and (not p.name.startswith('mux54-') or p == native.MUX)] + [tx, ng, Path(__file__), spec_path, run / 'bench.cir', run / 'spinit']
        assert {p for p in paths if p.suffix == '.spice'} == {native.MUX, tx}
        pins = {str(p): sha(p) for p in paths}
        record = dict(status='RUNNING', config=config, inputs=pins,
                      prospective_operating_point=result['operating_point'],
                      measurement_oracle_unchanged=True, full_phy_accepted=False)

        def save_native():
            (run / 'result.json').write_text(json.dumps(record, indent=2) + '\n')

        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
            resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2,) * 2)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

        save_native()
        env = {k: v for k, v in os.environ.items() if k not in
               ('LD_PRELOAD', 'PYTHONPATH', 'PYTHONHOME', 'GH_TOKEN', 'GITHUB_TOKEN')}
        env.update(SPICE_SCRIPTS=str(run), RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1')
        start = time.monotonic()
        with (run / 'run.log').open('w') as log:
            code = subprocess.call([ng, '-n', '-b', 'bench.cir'], cwd=run, env=env,
                                   stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
        log = (run / 'run.log').read_text(errors='replace')
        record.update(returncode=code, elapsed_s=time.monotonic() - start,
                      diagnostics=[line for line in log.splitlines() if any(word in line.lower() for word in
                                   ['warning', 'error', 'nan', 'singular', 'stepping', 'too small', 'jmax', 'vmax'])])
        save_native()
        if code or not (run / 'wave.dat').exists():
            print(log[-12000:], flush=True)
            raise RuntimeError('Native transient did not finish')
        op = np.loadtxt(run / 'op.dat', skiprows=1)
        assert op.size == len(vectors) + 1 and np.isfinite(op).all() and np.max(np.abs(op)) <= 1e-10
        flags = re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$', log)
        assert [x[0] for x in flags] == ['q.' + n + '.qnpn13g2' for n in bindings]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$', body) == ['1'] for name, body in flags)
        record.update(zero_source_op=True, native_off_flags=[x[0] for x in flags],
                      measurement=native.measure(run / 'wave.dat', bindings, vectors, bits))
        record['inputs_unchanged'] = all(sha(p) == digest for p, digest in pins.items())
        assert record['inputs_unchanged']
        raw, packed = run / 'wave.dat', run / 'wave.dat.gz'
        raw_pin = dict(bytes=raw.stat().st_size, sha256=sha(raw))
        with raw.open('rb') as source, gzip.open(packed, 'xb', compresslevel=1) as dest:
            shutil.copyfileobj(source, dest)
        h, size = hashlib.sha256(), 0
        with gzip.open(packed, 'rb') as stream:
            while block := stream.read(1024 * 1024):
                h.update(block)
                size += len(block)
        assert dict(bytes=size, sha256=h.hexdigest()) == raw_pin
        record.update(lossless_raw_wave=raw_pin, compressed_readback_passed=True)
        raw.unlink()
        record['outputs'] = {p.name: sha(p) for p in run.iterdir() if p.is_file() and p.name != 'result.json'}
        record['status'] = 'MEASURED_REQUIRES_INDEPENDENT_REVIEW'
        save_native()
        review = load('frozen_review54', inputs / 'review54.py').review(run)
        (out / 'independent-review.json').write_text(json.dumps(review, indent=2) + '\n')
        result.update(independent_status=review['status'], signals=review['signals'],
                      failed_devices={n: d for n, d in review['devices'].items() if not (d['post_passed'] and d['whole_upper_passed'])},
                      diagnostics=review['diagnostics'],
                      status='COMPLETE_FIXED_ORACLE_COMPONENT_STUDY_NOT_PHY_ACCEPTANCE')
        if args.point == 'baseline' and args.kind == 'wire' and args.interconnect == 'actual' and args.layout_composition is None:
            assert abs(review['signals']['minimum_margin_v'] - (-.26647000795532216)) < 1e-6
            assert review['signals']['wrong_sign_samples'] == 128
            result['previous_failed_wire_baseline_reproduced'] = True
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
