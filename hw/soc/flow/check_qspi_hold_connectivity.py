# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run with OpenROAD -python, setting BEFORE_ODB and AFTER_ODB to the two views."""
import hashlib
import json
import os
from pathlib import Path

import odb


PORT = "qspi_sck_o"
CELL_PREFIX = "qspi_sck_hold_"
NET_PREFIX = "qspi_sck_dly_"


def connectivity(path, expect_chain):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    block = db.getChip().getBlock()
    cells = sorted(block.getInsts(), key=lambda i: i.getName())
    inserted = {i.getName() for i in cells if i.getName().startswith(CELL_PREFIX)}
    assert len(inserted) == (14 if expect_chain else 0)
    internal = {n.getName() for n in block.getNets() if n.getName().startswith(NET_PREFIX)}
    assert len(internal) == len(inserted)
    edge = block.findBTerm(PORT).getNet()
    assert edge.getName() == PORT and len(edge.getBTerms()) == 1
    visited = set()
    collapsed = set()
    while len(visited) < len(inserted):
        drivers = [p for p in edge.getITerms() if p.getMTerm().getIoType() == "OUTPUT"]
        assert len(drivers) == 1
        cell = drivers[0].getInst()
        assert cell.getName() in inserted - visited
        assert cell.getMaster().getName() == "sg13g2_dlygate4sd3_1"
        pins = {p.getMTerm().getName(): p.getNet() for p in cell.getITerms()}
        assert pins["X"].getName() == edge.getName()
        assert pins["VDD"].getName() == "VPWR" and pins["VSS"].getName() == "VGND"
        edge = pins["A"]
        assert edge.getName() in internal - collapsed
        assert len(edge.getITerms()) == 2 and not edge.getBTerms()
        collapsed.add(edge.getName())
        visited.add(cell.getName())
    assert visited == inserted and collapsed == internal

    digest = hashlib.sha256()
    def record(*row):
        digest.update(json.dumps(row, separators=(",", ":")).encode() + b"\n")

    for inst in cells:
        if inst.getName() in inserted:
            continue
        record("cell", inst.getName(), inst.getMaster().getName())
        for pin in sorted(inst.getITerms(), key=lambda t: t.getMTerm().getName()):
            net = pin.getNet()
            name = net.getName() if net else None
            record("pin", pin.getMTerm().getName(), PORT if name in collapsed else name)
    for port in sorted(block.getBTerms(), key=lambda p: p.getName()):
        net = port.getNet()
        record("port", port.getName(), port.getIoType(), net.getName() if net else None)
    return digest.hexdigest(), len(cells) - len(inserted)


if __name__ == "__main__":
    before, after = (Path(os.environ[k]) for k in ("BEFORE_ODB", "AFTER_ODB"))
    original = connectivity(before, False)
    repaired = connectivity(after, True)
    assert original == repaired, "Connectivity outside the series delay chain changed"
    print(json.dumps({"original_instances": original[1], "canonical_sha256": original[0],
                      "validated_series_cells": 14, "added_cells_supply_connections_verified": True}))
