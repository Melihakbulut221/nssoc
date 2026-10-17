#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore the actual l5p7 physical clock model, never retune stale wire RC."""
import json,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
def restore(out,inputs):
    receipt=json.loads((ROOT/'docs/evidence/tx-clock-l5p7-full32-source-20261017.json').read_text())
    archive=out/'first-clock-source.tar.gz';fetch(receipt['url'],receipt['sha256'],archive)
    assert archive.stat().st_size==receipt['bytes']
    dest=out/'first-clock-source';dest.mkdir()
    with tarfile.open(archive)as tar:tar.extractall(dest,filter='data')
    archive.unlink();source=dest/'cloud-tx-clock-reference-compose-l5p7'
    assert sha(source/'result.json')==receipt['summary_sha256']
    result=json.loads((source/'result.json').read_text())
    assert result['source_head']==receipt['source_head'] and result['variant']=='l5p7'
    assert result['status']=='PASS_RAW6_AND_ALL13R28C_EXACT_CLOCK_COMPOSITION_WITH11_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
    assert result['source_unchanged'] and len(result['controls'])==11 and all(c['rejected']for c in result['controls'])
    assert len(result['outputs'])==479 and all(sha(source/n)==h for n,h in result['outputs'].items())
    model=source/'clock6-wire.spice';assert sha(model)==result['model_sha256']==receipt['model_sha256']
    for name in ('resistors_mod.lib','sg13g2_hbt_mod.lib'):
        assert sha(inputs/'models'/name)==sha(source/'inputs/tx-clock-reference-intrinsic-l5p7/pdk/libs.tech/ngspice/models'/name)
    return model,source,receipt
