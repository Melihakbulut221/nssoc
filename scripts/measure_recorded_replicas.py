#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Re-measure the original signoff-6x2 DEF/netlist from the verified snapshot.

The frozen measurement instrument is unchanged. Extraction uses temporary
scratch space, verifies every recorded byte and rejects differing live files.
These historical cell outlines do not establish radiation qualification.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sw/tests'))
sys.path.insert(0, str(ROOT / 'hw/openlane'))
from evidence import recorded_bundle
from replica_placement import measure

METADATA = ROOT / 'docs/evidence/historical-recovery-20260920.json'
RUN = Path('hw/openlane/pilot_ihp/runs/signoff-6x2')
REPLICAS = ['u_pilot.u_cfg_a', 'u_pilot.u_cfg_b', 'u_pilot.u_cfg_c']


def measure_recorded(metadata=METADATA, live_root=ROOT):
    with tempfile.TemporaryDirectory(prefix='nssoc-replica-evidence-') as scratch:
        restored = recorded_bundle(metadata, Path(scratch), live_root=live_root)
        result = measure(restored / RUN, REPLICAS)
    result['_recorded_scope'] = ('re-measured from hash-verified original signoff-6x2 '
                                 'DEF/netlist snapshot; not a current-layout or radiation verdict')
    return result


if __name__ == '__main__':
    print(json.dumps(measure_recorded(), indent=2))
