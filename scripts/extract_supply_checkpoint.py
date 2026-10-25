#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract the pinned chip's seven-metal graph and prepare a complete IO checkpoint.

No time watchdog. A separate process must verify the prepared checkpoint and
run the complete-window audit; extraction success alone is not acceptance.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import resource
import time

from audit_supply_checkpoint import validate_plan
from check_chip_supply_connectivity import GDS_SHA256, sha, validate_native
from supply_checkpoint_staged import prepare

METALS = [8, 10, 30, 50, 67, 126, 134]
VIAS = [19, 29, 49, 66, 125, 133]


def derive(db, gds, top_name, threads=1):
    """Match the unchanged native conductor/via cuts; retain floating cells."""
    layout = db.Layout()
    options = db.LoadLayoutOptions()
    mapping = db.LayerMap()
    pairs = [(v, dt) for v in METALS for dt in (0, 22, 24, 29)]
    pairs += [(v, 0) for v in VIAS + [27, 36]]
    for i, (v, dt) in enumerate(pairs):
        mapping.map(f"{v}/{dt}", i)
    options.set_layer_map(mapping, False)
    layout.read(str(gds), options)
    if layout.dbu != .001 or layout.cell(top_name) is None:
        raise ValueError("Expected nanometre units and named top cell")
    native = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, layout.cell(top_name), []))
    native.threads = threads
    native.include_floating_subcircuits = True
    cache = {}

    def reg(v, dt=0):
        if (v, dt) not in cache:
            cache[v, dt] = native.make_polygon_layer(layout.layer(v, dt), f"raw_{v}_{dt}")
        return cache[v, dt]

    conductors = []
    for v in METALS:
        region = (reg(v) + reg(v, 22)) - reg(v, 24) - reg(v, 29)
        if v in (126, 134):
            region -= reg(27)
        region = region.merged()
        conductors.append(region)
        native.register(region, "metal" + str(v))
        native.connect(region)
        print("METAL", v, region.count(), flush=True)
    for i, v in enumerate(VIAS):
        region = (reg(v) - reg(36) if v == 125 else reg(v)).merged()
        native.register(region, "via" + str(v))
        native.connect(region)
        native.connect(conductors[i], region)
        native.connect(region, conductors[i+1])
    return native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gds", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--memory-gib", type=int, default=8, choices=range(4, 17))
    parser.add_argument("--threads", type=int, default=1, choices=[1, 2, 4])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    record = dict(status="PREPARING", full_chip_lvs_accepted=False, manufacturing_approval=False)
    start = time.monotonic()

    def save(status):
        record.update(status=status, recorded=datetime.now().astimezone().isoformat(),
                      elapsed_seconds=time.monotonic()-start,
                      peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        target = args.output / "result.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(record, indent=2) + "\n")
        temp.replace(target)

    save("PREPARING")
    try:
        memory = Path('/proc/meminfo').read_text()
        available = int(dict(row.split(':', 1) for row in memory.splitlines())["MemAvailable"].split()[0])*1024
        limit = args.memory_gib * 1024**3
        record.update(memory_before=memory, address_space_limit_bytes=limit, threads=args.threads)
        if available < limit + 1024**3:
            raise ValueError("Insufficient memory: requested cap plus 1 GiB reserve required")
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if sha(args.gds) != GDS_SHA256 or sha(args.plan) != args.plan_sha256:
            raise ValueError("Unexpected GDS or window-plan hash")
        files = validate_native(args.references)
        methods = [Path(__file__).resolve()] + [Path(__file__).with_name(name) for name in (
            'check_chip_supply_connectivity.py', 'audit_supply_checkpoint.py',
            'plan_chip_supply_probes.py', 'probe_supply_components.py',
            'supply_checkpoint.py', 'supply_checkpoint_staged.py')]
        pins = {str(p.resolve()): sha(p) for p in [args.gds, args.plan, *files, *methods]}
        plan = json.loads(args.plan.read_text())
        validate_plan(plan, dict(input_sha256=pins, dbu=.001, floating_subcircuits_retained=True))
        if plan['io_instances'] != 314 or plan['port_windows'] != 10526:
            raise ValueError("Expected the complete verified IO inventory")
        record.update(input_sha256=pins, io_instances=314, port_windows=10526)
        save("DERIVING_METALS")
        import klayout.db as db

        native = derive(db, args.gds, "nssoc_chip", args.threads)
        save("EXTRACTING_FULL_METAL")
        print("EXTRACT_FULL_METAL", flush=True)
        native.extract_netlist()
        save("PREPARING_CHECKPOINT")
        probes = [dict(layer='metal'+str(w['gds_layer']), box_dbu=w['box_nm']) for w in plan['windows']]
        prepare(db, native, args.output / 'checkpoint', probes, 'nssoc_chip', pins,
                checkpoint_layers=['metal'+str(v) for v in METALS] + ['via'+str(v) for v in VIAS])
        record['prepared_sha256'] = sha(args.output / 'checkpoint/prepared.json')
        save("PREPARED_REQUIRES_SEPARATE_VERIFICATION_AND_AUDIT")
        return 0
    except Exception as error:
        record['error'] = repr(error)
        save('ERROR')
        raise


if __name__ == '__main__':
    raise SystemExit(main())
