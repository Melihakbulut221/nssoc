#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Unchanged original audit plus read-only serialized writer raw-opcode witness."""
import os
from pathlib import Path
import sys
sys.path.insert(0,"/work/tail-source/scripts")
sys.path.insert(0,"/work/source/scripts")
import odb
import mainchip_built_engine_route_prefix_native as original
import mainchip_original_clock_restoration_native as n
import mainchip_built_engine_route_tail_contract as c
import mainchip_two_signal_internal_witness as witness
from mainchip_witness_engine_build import fingerprint

def raw_pairs(block):
    rows={}
    for name in witness.NAMES:
        net=block.findNet(name);c.require(net is not None,"selected writer net absent")
        wire=net.getWire();c.require(wire is not None,"selected writer wire absent")
        rows[name]=[[int(wire.getOpcode(i)),int(wire.getData(i))] for i in range(wire.length())]
        c.require(rows[name],"empty writer wire")
    return rows

def main():
    c.method(Path("/work/tail-source"))
    c.require(os.environ.get("NSSOC_TWO_SIGNAL_PHASE") in c.STATUSES,"only original tail audit phases")
    c.require(os.environ.get("NSSOC_TWO_SIGNAL_OUT")=="/work/out/work","canonical native output")
    c.require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN",c.WITNESS_ENV)),"native audit environment")
    import mainchip_two_signal_repair_native as native
    c.require(Path(native.__file__).resolve()==Path("/work/source/scripts/mainchip_two_signal_repair_native.py")
        and Path(native.n.__file__).resolve()==Path("/work/source/scripts/mainchip_original_clock_restoration_native.py"),"frozen native module paths")
    original.execute_native(native)
    if os.environ["NSSOC_TWO_SIGNAL_PHASE"]=="route-audit":
        path=Path("/work/out/work/routed-fixed.odb");before=fingerprint(path)
        db,block=n.load(path)
        try:rows=raw_pairs(block)
        finally:odb.dbDatabase.destroy(db)
        c.require(fingerprint(path)==before,"read-only writer ODB changed")
        c.atomic_record(Path("/work/out/writer-raw.json"),dict(
            status="PASS_READ_ONLY_SAVED_WRITER_RAW",routed_odb=before,raw_pairs=rows,
            physical_acceptance=False))
if __name__=="__main__":main()
