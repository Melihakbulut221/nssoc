#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the actual 444f input using the compiled ELF, without modifying the database."""
import os
from pathlib import Path
import sys
sys.path.insert(0,"/work/source/scripts")
import mainchip_built_engine_runtime_contract as c
from mainchip_witness_engine_build import fingerprint
from mainchip_two_signal_api_probe_native import census

def inspect_database(odb,path,report,read_census=census):
    database=None;primary=None;partial={}
    try:
        database=odb.dbDatabase.create()
        c.require(database is not None,"database creation failed")
        report["database_created"]=True
        odb.read_db(database,str(path));report["database_read"]=True
        chip=database.getChip();c.require(chip is not None,"chip missing")
        block=chip.getBlock();c.require(block is not None,"top block missing")
        report["census"]=read_census(odb,database,block,partial)
        c.require(report["census"]["all_net_count"]==143820 and report["census"]["all_instance_count"]==153130,"full chip census")
        report["complete_census"]=True
    except BaseException as exc:
        primary=exc;report["partial_census"]=partial;report["failure"]=c.error_record("native-database-census",exc)
    finally:
        def destroy():
            if database is not None:
                odb.dbDatabase.destroy(database);report["database_destroyed"]=True
        c.attempt(report,"destroy-read-only-database",destroy)
        c.attempt(report,"unchanged-input",lambda:c.require(fingerprint(path)==c.INPUT,"input changed"))
    if primary is not None:raise primary

def main():
    import odb
    out=Path("/work/out");path=Path("/work/input.odb")
    report=dict(schema="built-engine-native-readonly-census-v1",status="IN_PROGRESS",
                complete_census=False,database_created=False,database_read=False,database_destroyed=False,
                physical_acceptance=False,native_routing_started=False,source_geometry_mutated=False,
                observer_equivalence_qualified=False,terminal_errors=[])
    primary=None
    try:
        c.require("NNSOC_DRT_INTERNAL_WITNESS_DIR" not in os.environ,"unexpected observer activation")
        c.require(fingerprint(path)==c.INPUT,"input identity")
        inspect_database(odb,path,report)
    except BaseException as exc:primary=exc
    finally:
        report["status"]=("PASS_ACTUAL_DATABASE_LIFECYCLE_AND_FULL_READ_ONLY_CENSUS"
            if report["complete_census"] and report["database_destroyed"] and primary is None and not report["terminal_errors"]
            else "FAIL_ACTUAL_DATABASE_CENSUS")
        c.finish_record(out/"api-identity-census.json",report,"FAIL_ACTUAL_DATABASE_CENSUS",primary)
    return 0 if report["status"].startswith("PASS_")else 1
if __name__=="__main__":sys.exit(main())
