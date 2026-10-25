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
# A routed core can have no prBoundary. The native density deck then uses
# its existing extent; the explicit fallback must not add source geometry.
extent = db.Layout()
extent.read(str(source))
extent.top_cell().shapes(extent.layer(189, 0)).clear()
extent.top_cell().shapes(extent.layer(8, 0)).insert(db.Box(0, 0, 1000, 1000))
extent.top_cell().shapes(extent.layer(8, 0)).insert(db.Box(199000, 99000, 200000, 100000))
extent_source = out / 'extent-source.gds'
extent.write(str(extent_source))
extent_command = [sys.executable, str(a.fill), str(extent_source)]
options = ['--tool', str(a.tool), '--config', str(a.config), '--audit', str(a.audit), '--tile-size', '100']
with (out / 'missing-boundary.log').open('w') as log:
    code = subprocess.run(extent_command + [str(out / 'missing-boundary')] + options,
                          stdout=log, stderr=subprocess.STDOUT).returncode
assert code != 0 and not (out / 'missing-boundary/checkpoint.gds').exists()
extent.top_cell().shapes(extent.layer(39, 4)).insert(db.Box(10000, 10000, 190000, 90000))
seal_source = out / 'seal-source.gds'
extent.write(str(seal_source))
with (out / 'ambiguous-extent.log').open('w') as log:
    code = subprocess.run([sys.executable, str(a.fill), str(seal_source),
                           str(out / 'ambiguous-extent')] + options + ['--allow-layout-extent'],
                          stdout=log, stderr=subprocess.STDOUT).returncode
assert code != 0 and not (out / 'ambiguous-extent/checkpoint.gds').exists()
with (out / 'extent.log').open('w') as log:
    subprocess.run(extent_command + [str(out / 'extent')] + options + ['--allow-layout-extent'],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
extent_record = json.loads((out / 'extent/progress.json').read_text())
assert extent_record['status'] == 'GENERATED_ALL_TILES'
assert extent_record['boundary_source'] == 'layout_extent'
assert extent_record['diearea_um'] == [0, 0, 200, 100]
assert len(extent_record['completed_tiles']) == 2
filled_extent = db.Layout()
filled_extent.read(str(out / 'extent/checkpoint.gds'))
assert db.Region(filled_extent.top_cell().begin_shapes_rec(filled_extent.layer(189, 0))).is_empty()
assert not json.loads((out / 'extent/final-geometry.json').read_text())['errors']
(out / 'result.json').write_text(json.dumps(dict(status='PASS_FILL_RESUME_AND_NEGATIVE_CONTROLS',
    completed_tiles=2, controls=checks, missing_boundary_rejected_by_default=True,
    extent_with_edgeseal_rejected=True,
    explicit_extent_tiles=2, source_boundary_not_added=True,
    physical_acceptance=False), indent=2) + '\n')
print('PASS: real fill, resume, three geometry-corruption controls, and explicit boundary-free extent')
