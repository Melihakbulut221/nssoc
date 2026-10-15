#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read the exact frozen native HBT geometry sources on a hosted runner.

This is source inspection, not native simulation, DRC/LVS or PHY acceptance.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Hosted execution only'
    root = Path(__file__).resolve().parents[1]
    spec = json.loads((root / 'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
    receipt = spec['receipt']
    raw = urllib.request.urlopen(receipt['url'], timeout=120).read()
    assert len(raw) == receipt['bytes'] and digest(raw) == receipt['sha256']
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        entries = {m.name: m for m in archive.getmembers() if m.isfile()}
        assert len(entries) == len([m for m in archive.getmembers() if m.isfile()])
        manifest_names = [n for n in entries if n == 'manifest.json']
        assert len(manifest_names) == 1
        manifest = json.loads(archive.extractfile(entries[manifest_names[0]]).read())
        verified = {}
        selected = {}
        for name, meta in manifest['files'].items():
            data = archive.extractfile(entries[name]).read()
            assert digest(data) == meta['sha256'], name
            verified[name] = digest(data)
            lower = name.lower()
            if 'npn13g2' in lower or lower.endswith('sg13g2_tech.json') or 'techparams' in lower:
                selected[name] = {'sha256': digest(data), 'bytes': len(data), 'text': data.decode()}
        assert any('npn13g2' in name.lower() for name in selected)
    cards = {}
    for name in ['tx_mux2_final_drive_v10_layout_core.spice', 'tx_mux54_passive_drive_v10.spice']:
        p = root / 'hw/soc/analog/pcie' / name
        data = p.read_bytes()
        cards[str(p.relative_to(root))] = {'sha256': digest(data), 'text': data.decode()}
    result = {'status': 'PASS_FROZEN_PDK_SOURCE_READBACK_NOT_DEVICE_QUALIFICATION',
              'source_head': os.environ['GITHUB_SHA'], 'source_receipt': receipt,
              'verified_files': verified, 'selected_sources': selected,
              'current_final_sources': cards, 'native_simulation_performed': False,
              'physical_geometry_changed': False, 'phy_accepted': False}
    Path('hbt-geometry-source-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'verified_count': len(verified),
                      'selected': list(selected), 'current_final_sources': list(cards)}))


if __name__ == '__main__':
    main()
