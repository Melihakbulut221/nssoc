#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Clip actual input geometry for each bounded fill task; merge fill additions only."""
import argparse
import gc
import hashlib
import json
import math
import lzma
import sys
from pathlib import Path
import resource
import shutil
import subprocess
import time
import klayout.db as db

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--tile-size', type=float, default=500)
p.add_argument('--max-tiles', type=int)
p.add_argument('--resume', action='store_true')
p.add_argument('--tool', type=Path, required=True)
p.add_argument('--config', type=Path, required=True)
p.add_argument('--audit', type=Path, required=True)
a = p.parse_args()
assert a.tile_size > 0 and (a.max_tiles is None or a.max_tiles > 0)
source = a.source.resolve(strict=True)
out = a.output.resolve()
if not a.resume:
    out.mkdir(exist_ok=False)
else:
    assert (out / 'progress.json').is_file()
binary = a.tool.resolve(strict=True)
config = a.config.resolve(strict=True)
audit_script = a.audit.resolve(strict=True)
allowed = [(n, 22) for n in (1, 5, 8, 10, 30, 50, 67, 126, 134)]

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def save(path, record):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=2) + '\n')
    tmp.replace(path)

layout = db.Layout()
layout.read(str(source))
assert len(layout.top_cells()) == 1
top = layout.top_cell()
boundary = db.Region(top.begin_shapes_rec(layout.layer(189, 0)))
assert boundary.count() == 1 and boundary.is_box()
area = boundary.bbox().to_dtype(layout.dbu)
nx, ny = math.ceil(area.width()/a.tile_size), math.ceil(area.height()/a.tile_size)
hashes = {str(x): sha(x) for x in [source, binary, config, Path(__file__).resolve(),
                                  audit_script]}
record = dict(status='RUNNING', scope='Experimental clipped-input fill; no physical or timing acceptance.',
    expected_tiles=nx*ny, requested_tiles=a.max_tiles or nx*ny,
    tile_size_um=a.tile_size, halo_um=30, input_sha256=hashes,
    completed_tiles=[], diearea_um=[area.left, area.bottom, area.right, area.top])
if a.resume:
    previous = json.loads((out / 'progress.json').read_text())
    assert previous['input_sha256'] == hashes, 'Inputs changed; resume rejected'
    assert previous['tile_size_um'] == a.tile_size and previous['expected_tiles'] == nx*ny
    assert previous['diearea_um'] == record['diearea_um']
    rows = previous['completed_tiles']
    assert [r['index'] for r in rows] == list(range(len(rows)))
    assert len(rows) <= record['requested_tiles']
    if rows:
        latest = Path(rows[-1]['checkpoint'])
        assert sha(latest) == rows[-1]['checkpoint_sha256'], 'Checkpoint changed'
        layout = db.Layout()
        layout.read(str(latest))
        assert len(layout.top_cells()) == 1
        top = layout.top_cell()
    record['completed_tiles'] = rows
    record['resumed_from_count'] = len(rows)
save(out / 'progress.json', record)

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (10*1024**3, 10*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def window(index, bounds):
    tile = out / f'tile-{index:03d}'
    attempt = 0
    while tile.exists():
        attempt += 1
        tile = out / f'tile-{index:03d}-attempt-{attempt}'
    tile.mkdir()
    clip = db.Layout()
    clip.dbu = layout.dbu
    # clip_into copies shapes by internal layer index; the target must already
    # associate every index with its original GDS layer/datatype.
    for layer_index in layout.layer_indexes():
        clip.insert_layer_at(layer_index, layout.get_info(layer_index))
    left, bottom, right, upper = bounds
    clipped = layout.clip_into(top, clip, db.DBox(left-30, bottom-30, right+30, upper+30))
    assert len(clip.top_cells()) == 1 and clip.dbu == layout.dbu
    assert all(clip.get_info(i) == layout.get_info(i) for i in layout.layer_indexes())
    marker = clip.layer(189, 0)
    # Only the explicit boundary in the diagnostic clip is replaced. Original
    # full-layout geometry is never erased or copied back from this clip.
    for cell in clip.each_cell():
        cell.shapes(marker).clear()
    clipped.shapes(marker).insert(db.DBox(*bounds).to_itype(clip.dbu))
    before = tile / 'before.gds'
    after = tile / 'after.gds'
    clip.write(str(before))
    shutil.copy2(before, after)
    cmd = [str(binary), '-j', '2', 'fill', '--process', 'ihp-sg13g2',
           '--config-file', str(config), str(after)]
    start = time.monotonic()
    with (tile / 'run.log').open('x') as log:
        try:
            code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                  preexec_fn=limits).returncode
        except subprocess.TimeoutExpired:
            code = 124
    result = dict(index=index, bounds_um=bounds, command=cmd, returncode=code,
                  before_sha256=sha(before), elapsed_seconds=time.monotonic()-start)
    save(tile / 'result.json', result)
    assert code == 0, f'Fill failed for tile {index}'
    # Existing audit checks every clipped source cell and original instance;
    # the merge below adds only the verified fill-layer geometric difference.
    with (tile / 'geometry.log').open('x') as log:
        audit = subprocess.run([sys.executable, str(audit_script),
            str(before), str(after), str(tile / 'geometry.json')],
            stdout=log, stderr=subprocess.STDOUT)
    assert audit.returncode == 0, f'Geometry audit failed for tile {index}'
    filled = db.Layout()
    filled.read(str(after))
    assert filled.dbu == layout.dbu and len(filled.top_cells()) == 1
    child_name = f'NS_GDSFILL_TILE_{index:03d}'
    assert layout.cell(child_name) is None
    child = layout.create_cell(child_name)
    count = 0
    for layer in allowed:
        old = db.Region(clipped.begin_shapes_rec(clip.layer(*layer)))
        new = db.Region(filled.top_cell().begin_shapes_rec(filled.layer(*layer)))
        assert (old-new).is_empty(), 'Removed prior fill'
        additions = new-old
        inner = db.Region(db.DBox(*bounds).to_itype(layout.dbu))
        assert (additions-inner).is_empty(), 'Fill escaped its window'
        count += additions.count()
        child.shapes(layout.layer(*layer)).insert(additions)
    top.insert(db.CellInstArray(child.cell_index(), db.Trans()))
    checkpoint = out / 'checkpoint.gds'
    layout.write(str(checkpoint))
    result.update(after_sha256=sha(after), added_polygons=count,
                  checkpoint_sha256=sha(checkpoint), checkpoint=str(checkpoint))
    # Retain each intermediate byte-for-byte, compressed; bounded disk use.
    for raw in [before, after, checkpoint]:
        packed = tile / (raw.name + '.xz')
        with raw.open('rb') as src, lzma.open(packed, 'wb', preset=1) as dst:
            shutil.copyfileobj(src, dst)
        with lzma.open(packed, 'rb') as check:
            assert hashlib.file_digest(check, 'sha256').hexdigest() == sha(raw)
        if raw != checkpoint:
            raw.unlink()
    result['archived_checkpoint'] = str(tile / 'checkpoint.gds.xz')
    result['archived_checkpoint_sha256'] = sha(tile / 'checkpoint.gds.xz')
    save(tile / 'result.json', result)
    return result

started = time.monotonic()
try:
    for index in range(len(record['completed_tiles']), min(nx*ny, record['requested_tiles'])):
        ix, iy = index % nx, index // nx
        left, bottom = area.left+ix*a.tile_size, area.bottom+iy*a.tile_size
        bounds = [left, bottom, min(left+a.tile_size, area.right), min(bottom+a.tile_size, area.top)]
        print(f'Tile {index+1}/{nx*ny}: {bounds}', flush=True)
        row = window(index, bounds)
        assert all(sha(Path(path)) == expected for path, expected in hashes.items())
        record['completed_tiles'].append(row)
        record['elapsed_seconds'] = time.monotonic()-started
        record['latest_checkpoint'] = row['checkpoint']
        save(out / 'progress.json', record)
        gc.collect()
    record['status'] = ('GENERATED_ALL_TILES' if len(record['completed_tiles']) == nx*ny
                        else 'PARTIAL_DIAGNOSTIC')
    if record['status'] == 'GENERATED_ALL_TILES':
        with (out / 'final-geometry.log').open('w') as log:
            result = subprocess.run([sys.executable, str(audit_script), str(source),
                str(out / 'checkpoint.gds'), str(out / 'final-geometry.json')],
                stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode == 0, 'Final source geometry preservation failed'
        record['final_geometry_sha256'] = sha(out / 'final-geometry.json')
        record['physical_acceptance'] = False
    save(out / 'progress.json', record)
    print(record['status'], flush=True)
except Exception as error:
    record.update(status='ERROR', error=str(error))
    save(out / 'progress.json', record)
    raise
