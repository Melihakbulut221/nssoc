#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract actual hosted TX candidate wires with frozen native graph audits."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

from run_cloud_tx_layout_repair import ROOT, fetch, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--circuit-profile', choices=('baseline','cascade14','cascade16','final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8'), default='baseline')
    parser.add_argument('--prepared-layout', action='store_true',
                        help='Consume the verified layout generated in this same hosted job')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
    runtime = json.loads((ROOT / 'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
    out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'
    if args.prepared_layout:
        receipt = dict(prepared_layout_result_sha256=sha(out / 'result.json'),
                       job_commit=os.environ.get('GITHUB_SHA'))
    else:
        receipt = (spec if args.circuit_profile=='baseline' else spec['circuits'][args.circuit_profile])['variants'][args.variant]
        assert not out.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    archive = out.parent / 'cloud-extraction-input.tar.gz'
    result = dict(status='RUNNING', variant=args.variant, circuit_profile=args.circuit_profile, adopted=False,
                  qualified_pex=False, serial_phy_complete=False,
                  scope='Real wire geometry and native distributed RC graph; electrical waveform acceptance and RF qualification remain required.',
                  physical_source=receipt, runtime_source=runtime, method_source=spec)

    def run(command, label):
        log = out / (label + '.log')
        with log.open('w') as stream:
            code = subprocess.call([str(x) for x in command], cwd=ROOT,
                                   stdout=stream, stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-12000:], flush=True)
            raise RuntimeError(f'{label}: exit {code}')

    try:
        if not args.prepared_layout:
            fetch(receipt['url'], receipt['sha256'], archive)
            assert archive.stat().st_size == receipt['bytes']
            with tarfile.open(archive) as tar:
                tar.extractall(ROOT, filter='data')
            archive.unlink()
        physical = json.loads((out / 'result.json').read_text())
        assert physical['variant'] == args.variant
        assert physical.get('circuit_profile','baseline') == args.circuit_profile
        assert physical['status'] == 'PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
        for name, digest in physical['layout']['outputs'].items():
            assert sha(out / 'layout' / name) == digest
        frozen_geometry = {str(p): sha(p) for sub in ('layout', 'physical')
                           for p in (out / sub).rglob('*') if p.is_file()}

        rt = out / 'magic-cloud'
        rt.mkdir()
        fetch(runtime['receipt']['url'], runtime['receipt']['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(rt, filter='data')
        archive.unlink()
        manifest = json.loads((rt / 'manifest.json').read_text())
        assert all(sha(rt / n) == r['sha256'] for n, r in manifest['files'].items())
        raw = ROOT / 'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True, exist_ok=True)
        fetch(spec['raw_parser']['url'], spec['raw_parser']['sha256'], raw)

        wire = out / 'wire96'
        wire.mkdir()
        originals = out / 'frozen-extraction-methods'
        originals.mkdir()
        fetch(spec['method_archive']['url'], spec['method_archive']['sha256'], archive)
        edits = {}
        with tarfile.open(archive) as tar:
            for name, digest in spec['methods'].items():
                data = tar.extractfile(name).read()
                target = originals / Path(name).name
                target.write_bytes(data)
                assert sha(target) == digest
                source = data.decode()
                changes = []
                if args.circuit_profile!='baseline':
                    before='nssoc_tx_mux2_passive_topmetal_layout_v1'
                    after=spec['circuits'][args.circuit_profile]['top']
                    if before in source:
                        changes.append(dict(before=before,after=after,count=source.count(before)))
                        source=source.replace(before,after)
                for before, after in (
                    ("/'layout91/", "/'layout/"),
                    ("/'physical92/", "/'physical/"),
                    ("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')", "B.parent/'magic-cloud/runtime/lib'"),
                    ("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')", "B.parent/'magic-cloud/tech'"),
                ):
                    if before in source:
                        changes.append(dict(before=before, after=after, count=source.count(before)))
                        source = source.replace(before, after)
                if target.name == 'mutations48.py':
                    # Use two real distinct TX ports, not inherited PLL names.
                    before = 'R_EXTRA P_cp P_cn 1'
                    assert source.count(before) == 1
                    source = source.replace(before, 'R_EXTRA P_op P_on 1')
                    changes.append(dict(before=before, after='R_EXTRA P_op P_on 1', count=1))
                (wire / target.name).write_text(source)
                edits[target.name] = dict(original_sha256=digest, adapted_sha256=sha(wire / target.name), changes=changes)
        archive.unlink()
        result['method_adaptations'] = edits
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        for method in ('probe01.py', 'locate01.py', 'anchors01.py', 'dedup01.py'):
            run([app, 'python', wire / method], method)
        run([sys.executable, wire / 'run-rc01.py'], 'native-extraction')
        capture = json.loads((wire / 'rc03/result.json').read_text())
        result['capture'] = capture
        assert capture['returncode'] == 0 and capture['status'] == 'NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        run([sys.executable, wire / 'audit-rc48.py', wire / 'rc03',
             wire / 'anchors08.json', wire / 'audit.json'], 'native-audit')
        audit = json.loads((wire / 'audit.json').read_text())
        result['audit'] = audit
        assert audit['status'] == 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable, wire / 'mutations48.py'], 'native-fault-controls')
        controls = json.loads((wire / 'native-mutations01.json').read_text())
        result['controls'] = controls
        assert controls['status'] == 'PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert all(sha(Path(n)) == digest for n, digest in frozen_geometry.items())
        assert all(sha(rt / n) == r['sha256'] for n, r in manifest['files'].items())
        result['status'] = 'PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        out.mkdir(parents=True, exist_ok=True)
        (out / 'extraction-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result[k] for k in ('status', 'variant', 'adopted')}), flush=True)


if __name__ == '__main__':
    main()
