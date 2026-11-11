#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove routed wires that detailed routing cannot take back.

docs/combined-timing.md section 12.1, step NSSOC.RemoveNonOrthogonalWires of
hw/soc/pnr/routed_measure_flow.py, between PostRouteHold and detailed
routing. On the database PostRouteHold wrote: (1) every net it changed
(--nets-file) loses any wire it still carries; (2) every signal net whose
wire has a segment that is neither horizontal nor vertical (DRT-1010
otherwise) loses its wire. Detailed routing then routes those nets. Wires
with only orthogonal segments on unchanged nets are kept. Counts and the
first offending segments are printed; nothing else is changed.
"""
import os

from reader import click_odb, click, odb

D = odb.dbWireDecoder


def xy(value):
    return int(value[0]), int(value[1])


def junction_point(wire, decoder):
    try:
        p = wire.getCoord(decoder.getJunctionValue())
        return (p.getX(), p.getY()) if hasattr(p, "getX") else xy(p)
    except Exception:
        return None


def first_diagonal(wire):
    decoder = D()
    decoder.begin(wire)
    previous = None
    while True:
        op = decoder.next()
        if op == D.END_DECODE:
            return None
        if op == D.POINT:
            current = xy(decoder.getPoint())
        elif op == D.POINT_EXT:
            current = xy(decoder.getPoint_ext())
        elif op == D.PATH:
            previous = None
            continue
        elif op in (D.JUNCTION, D.SHORT, D.VWIRE):
            previous = junction_point(wire, decoder)
            continue
        else:
            continue
        if previous is not None and previous[0] != current[0] and previous[1] != current[1]:
            return previous, current
        previous = current


@click.command()
@click.option("--nets-file", default=None, help="Nets PostRouteHold changed, one per line")
@click_odb
def cli(reader, nets_file):
    block = reader.block
    dbu = block.getDbUnitsPerMicron()
    changed = set()
    if nets_file and os.path.isfile(nets_file):
        with open(nets_file) as f:
            changed = {line.strip() for line in f if line.strip()}
    removed_changed = removed_diagonal = scanned = failed = 0
    first_failure = None
    shown = 0
    for net in block.getNets():
        if net.getSigType() in ("POWER", "GROUND"):
            continue
        wire = net.getWire()
        if wire is None:
            continue
        name = net.getName()
        if name in changed:
            odb.dbWire.destroy(wire)
            removed_changed += 1
            continue
        scanned += 1
        try:
            bad = first_diagonal(wire)
        except Exception as e:  # report the decoder problem, keep going
            failed += 1
            first_failure = first_failure or f"{name}: {type(e).__name__}: {e}"
            continue
        if bad is not None:
            if shown < 40:
                (x0, y0), (x1, y1) = bad
                print(f"NSSOC_NONORTHOGONAL {name} ({x0/dbu}, {y0/dbu}) -> ({x1/dbu}, {y1/dbu})")
                shown += 1
            odb.dbWire.destroy(wire)
            removed_diagonal += 1
    print(f"NSSOC_WIRE_CLEANUP changed_nets={len(changed)} changed_wires_removed={removed_changed} "
          f"scanned={scanned} nonorthogonal_wires_removed={removed_diagonal} decode_failures={failed}")
    if first_failure:
        print(f"NSSOC_WIRE_DECODE_FAILURE {first_failure}")


if __name__ == "__main__":
    cli()
