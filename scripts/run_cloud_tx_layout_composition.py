#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind each candidate's native devices to its newly extracted physical wires."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from run_cloud_tx_layout_repair import ROOT, fetch, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', required=True)
    p.add_argument('--circuit-profile', choices=('baseline','cascade14','cascade16','final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8'), default='baseline')
    p.add_argument('--prepared-extraction', action='store_true',
                   help='Consume source-bound native extraction from this same hosted job')
    args = p.parse_args()
    spec = json.loads((ROOT / 'docs/evidence/pcie-tx-cloud-composition-input-20261013.json').read_text())
    out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'
    dest = ROOT / 'cloud-tx-layout-composition'
    dest.mkdir(exist_ok=False)
    archive = dest / 'input.tar.gz'
    source = (dict(prepared_extraction_result_sha256=sha(out / 'extraction-result.json'),
                   job_commit=os.environ.get('GITHUB_SHA')) if args.prepared_extraction else
              (spec if args.circuit_profile=='baseline' else spec['circuits'][args.circuit_profile])['variants'][args.variant])
    result = dict(status='RUNNING', variant=args.variant, circuit_profile=args.circuit_profile, adopted=False, source=source)

    def restore(receipt, directory):
        fetch(receipt['url'], receipt['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(directory, filter='data')
        archive.unlink()

    def run(command, label):
        log = dest / (label + '.log')
        with log.open('w') as stream:
            code = subprocess.call([str(x) for x in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-10000:], flush=True)
            raise RuntimeError(f'{label}: exit {code}')

    try:
        if not args.prepared_extraction:
            assert not out.exists()
            restore(result['source'], ROOT)
        extraction = json.loads((out / 'extraction-result.json').read_text())
        assert extraction['variant'] == args.variant
        assert extraction.get('circuit_profile','baseline') == args.circuit_profile
        assert extraction['status'] == 'PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS'
        protected = {str(q): sha(q) for sub in ('layout', 'physical', 'wire96') for q in (out / sub).rglob('*') if q.is_file()}
        layout = json.loads((ROOT / 'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        if not args.prepared_extraction:
            restore(layout['receipt'], ROOT)
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        assert all(sha(ROOT / n) == v['sha256'] for n, v in manifest['files'].items())
        electrical = json.loads((ROOT / 'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
        inputs = dest / 'model-inputs'
        inputs.mkdir()
        restore(electrical['receipt'], inputs)
        manifest = json.loads((inputs / 'manifest.json').read_text())
        assert all(sha(inputs / n) == v['sha256'] for n, v in manifest['files'].items())
        modeldir = ROOT / 'pdk/libs.tech/ngspice/models'
        modeldir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(inputs / 'models', modeldir)
        helper = ROOT / 'hw/soc/out/pcie-tail115-connected570-source-20261006/compose_source01.py'
        helper.parent.mkdir(parents=True, exist_ok=True)
        receipt = spec['helpers']['composition_parser']
        fetch(receipt['url'], receipt['sha256'], helper)
        binding = out / 'binding96'
        binding.mkdir()
        fetch(spec['binding_archive']['url'], spec['binding_archive']['sha256'], archive)
        adapted = {}
        with tarfile.open(archive) as tar:
            for name, digest in spec['binding_methods'].items():
                target = binding / Path(name).name
                target.write_bytes(tar.extractfile(name).read())
                assert sha(target) == digest
                original = target.read_text()
                source = original.replace("'physical92/", "'physical/")
                if args.circuit_profile!='baseline':
                    source=source.replace('nssoc_tx_mux2_passive_topmetal_layout_v1',
                        spec['circuits'][args.circuit_profile]['top'])
                source = source.replace("Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')", "R/'pdk'")
                (binding / (target.name + '.original')).write_text(original)
                target.write_text(source)
                adapted[name] = dict(original_sha256=digest, adapted_sha256=sha(target))
        archive.unlink()
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == layout['runtime_sha256']
        run([app, 'python', binding / 'export01.py'], 'export-native-devices')
        run([sys.executable, binding / 'build-devices01.py'], 'native-device-model-binding')
        wire = out / 'wire96'
        source = (wire / 'compose49.py').read_text()
        assert source.count("B/'audit48.json'") == 1
        # Preserve the source unchanged; run a path-adapted copy beside it.
        composition = wire / 'compose-cloud.py'
        composition.write_text(source.replace("B/'audit48.json'", "B/'audit.json'"))
        run([sys.executable, composition], 'compose-real-wires')
        report = json.loads((wire / 'composition01.json').read_text())
        assert report['status'] == 'SOURCE_ONLY_NATIVE54_WITH_DISTRIBUTED_METAL_RC'
        assert report['counts']['devices'] == 54
        audit = extraction['audit']
        assert report['counts']['R'] == audit['actual_exported_resistors']
        assert report['counts']['C'] == audit['actual_exported_capacitors']
        for q in (wire / 'mux54-wire01.spice', binding / 'mux54-compact01.spice'):
            shutil.copyfile(q, dest / q.name)
        assert all(sha(Path(n)) == digest for n, digest in protected.items())
        result.update(status='PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT',
                      adaptations=adapted, composition=report,
                      outputs={q.name: sha(q) for q in dest.glob('*.spice')},
                      extraction_source_sha256=sha(out / 'extraction-result.json'),
                      scope='Actual54 device binding and actual candidate RC, without RF qualification or PHY acceptance.')
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (dest / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result[k] for k in ('status', 'variant', 'adopted')}), flush=True)


if __name__ == '__main__':
    main()
