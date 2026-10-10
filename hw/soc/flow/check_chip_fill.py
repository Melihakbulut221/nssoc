#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise real fill, checkpoint resume and geometry-corruption rejection."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import klayout.db as db

p = argparse.ArgumentParser()
for name in ('tool', 'config', 'fill', 'audit', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
source = out / 'source.gds'
layout = db.Layout()
layout.dbu = 0.001
cell = layout.create_cell('probe_chip')
cell.shapes(layout.layer(189, 0)).insert(db.Box(0, 0, 200000, 100000))
wire = layout.create_cell('wire')
wire.shapes(layout.layer(8, 0)).insert(db.Box(1000, 1000, 180000, 2000))
cell.insert(db.CellInstArray(wire.cell_index(), db.Trans()))
cell.shapes(layout.layer(126, 0)).insert(db.Box(5000, 5000, 15000, 15000))
layout.write(str(source))
command = [sys.executable, str(a.fill), str(source), str(out / 'run'), '--tool', str(a.tool),
           '--config', str(a.config), '--audit', str(a.audit), '--tile-size', '100']
for name, options in [('initial', ['--max-tiles', '1']), ('resume', ['--resume'])]:
    with (out / (name + '.log')).open('w') as log:
        subprocess.run(command + options, stdout=log, stderr=subprocess.STDOUT, check=True)
progress = json.loads((out / 'run/progress.json').read_text())
assert progress['status'] == 'GENERATED_ALL_TILES' and progress['resumed_from_count'] == 1
assert len(progress['completed_tiles']) == 2
assert all(row['added_polygons'] > 0 for row in progress['completed_tiles'])
checks = {}
for defect in ('removed_source_shape', 'added_nonfill_shape', 'removed_source_instance'):
    changed = db.Layout()
    changed.read(str(out / 'run/checkpoint.gds'))
    if defect == 'removed_source_shape':
        changed.cell('wire').shapes(changed.layer(8, 0)).clear()
    elif defect == 'added_nonfill_shape':
        changed.top_cell().shapes(changed.layer(8, 0)).insert(db.Box(0, 0, 1000, 1000))
    else:
        for instance in changed.top_cell().each_inst():
            if instance.cell.name == 'wire':
                instance.delete()
                break
    mutant = out / (defect + '.gds')
    changed.write(str(mutant))
    report = out / (defect + '.json')
    with (out / (defect + '.log')).open('w') as log:
        code = subprocess.run([sys.executable, str(a.audit), str(source), str(mutant), str(report)],
                              stdout=log, stderr=subprocess.STDOUT).returncode
    result = json.loads(report.read_text())
    assert code == 1 and result['status'] == 'FAIL' and result['errors']
    checks[defect] = dict(returncode=code, rejected=True, errors=result['errors'])
(out / 'result.json').write_text(json.dumps(dict(status='PASS_FILL_RESUME_AND_NEGATIVE_CONTROLS',
    completed_tiles=2, controls=checks, physical_acceptance=False), indent=2) + '\n')
print('PASS: real fill, resume, and three geometry-corruption controls')
