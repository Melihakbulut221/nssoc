# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run with OpenROAD -python, setting BEFORE_ODB and AFTER_ODB to the two views."""
import hashlib
import json
import os
from pathlib import Path

import odb


SCK = {"qspi_sck_o": 14}
OUTPUTS = {
    "qspi_io_o[2]": 4, "qspi_cs_no[1]": 4, "qspi_cs_no[0]": 4,
    "qspi_io_oe_o[2]": 4, "qspi_io_oe_o[0]": 4, "qspi_io_oe_o[3]": 3,
    "qspi_io_oe_o[1]": 3, "qspi_io_o[0]": 3, "qspi_io_o[3]": 3,
    "qspi_io_o[1]": 3,
}


def connectivity(path, expect_chain, outputs=SCK, cell_prefix="qspi_sck_hold_", net_prefix="qspi_sck_dly_", sinks=False):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    block = db.getChip().getBlock()
    cells = sorted(block.getInsts(), key=lambda i: i.getName())
    inserted = {i.getName() for i in cells if i.getName().startswith(cell_prefix)}
    assert len(inserted) == (sum(outputs.values()) if expect_chain else 0)
    internal = {n.getName() for n in block.getNets() if n.getName().startswith(net_prefix)}
    assert len(internal) == len(inserted)
    visited = set()
    collapsed = {}
    for port, length in outputs.items():
        edge = block.findBTerm(port).getNet()
        assert edge.getName() == port and len(edge.getBTerms()) == 1
        for _ in range(length if expect_chain else 0):
            drivers = [p for p in edge.getITerms() if p.getMTerm().getIoType() == "OUTPUT"]
            assert len(drivers) == 1
            cell = drivers[0].getInst()
            assert cell.getName() in inserted - visited
            assert cell.getMaster().getName() == "sg13g2_dlygate4sd3_1"
            pins = {p.getMTerm().getName(): p.getNet() for p in cell.getITerms()}
            assert pins["X"].getName() == edge.getName()
            assert pins["VDD"].getName() == "VPWR" and pins["VSS"].getName() == "VGND"
            edge = pins["A"]
            assert edge.getName() in internal - collapsed.keys()
            assert len(edge.getITerms()) == 2 and not edge.getBTerms()
            collapsed[edge.getName()] = port
            visited.add(cell.getName())
    assert visited == inserted and collapsed.keys() == internal

    if sinks:
        local_cells = [i for i in cells if i.getName().startswith("nssoc_local_hold")]
        assert len(local_cells) == (17 if expect_chain else 0)
        sink_names = set()
        for cell in local_cells:
            assert cell.getMaster().getName() == "sg13g2_dlygate4sd3_1"
            pins = {p.getMTerm().getName(): p.getNet() for p in cell.getITerms()}
            assert pins["VDD"].getName() == "VPWR" and pins["VSS"].getName() == "VGND"
            old, new = pins["A"], pins["X"]
            assert new.getName().startswith("nssoc_local_delay") and new.getName() not in collapsed
            loads = [p for p in new.getITerms() if p.getMTerm().getIoType() == "INPUT"]
            assert len(loads) == 1 and len(new.getITerms()) == 2 and not new.getBTerms()
            terminal = loads[0]
            sink_names.add(f"{terminal.getInst().getName()}/{terminal.getMTerm().getName()}")
            collapsed[new.getName()] = old.getName()
            inserted.add(cell.getName())
        if expect_chain:
            helper = Path(__file__).with_name("interface_sink_hold_eco.tcl").read_text()
            expected_sinks = helper.split("foreach pin {", 1)[1].split("} {", 1)[0].split()
            assert sink_names == set(expected_sinks) and len(sink_names) == 17

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
            record("pin", pin.getMTerm().getName(), collapsed.get(name, name))
    for port in sorted(block.getBTerms(), key=lambda p: p.getName()):
        net = port.getNet()
        record("port", port.getName(), port.getIoType(), net.getName() if net else None)
    return digest.hexdigest(), len(cells) - len(inserted)


if __name__ == "__main__":
    before, after = (Path(os.environ[k]) for k in ("BEFORE_ODB", "AFTER_ODB"))
    profiles = {
        "sck": (SCK, "qspi_sck_hold_", "qspi_sck_dly_"),
        "outputs": (OUTPUTS, "nssoc_io_hold", "nssoc_io_delay"),
        "outputs_and_sinks": (OUTPUTS, "nssoc_io_hold", "nssoc_io_delay", True),
    }
    config = profiles[os.environ.get("QSPI_HOLD_CHAIN_SET", "sck")]
    original = connectivity(before, False, *config)
    repaired = connectivity(after, True, *config)
    assert original == repaired, "Connectivity outside the series delay chain changed"
    print(json.dumps({"original_instances": original[1], "canonical_sha256": original[0],
                      "validated_series_cells": sum(config[0].values()) + (17 if len(config) == 4 else 0), "added_cells_supply_connections_verified": True}))
