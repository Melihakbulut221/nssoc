#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native subprocess controls; run with pinned KLayout Python and a NEW directory."""
import argparse
import json
import resource
import shutil
import subprocess
import sys
from pathlib import Path

resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2,) * 2)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import klayout.db as db  # noqa: E402
from check_chip_supply_connectivity import sha  # noqa: E402
from supply_checkpoint import load  # noqa: E402
from supply_checkpoint_staged import prepare, verify  # noqa: E402


def produce(directory, kind):
    layout = db.Layout()
    layout.dbu = .001
    top = layout.create_cell("TOP")
    child = layout.create_cell("CHILD")
    li = layout.layer(8, 0)
    child.shapes(li).insert(db.Box(0, 0, 20, 20))
    for x in (0, 80):
        top.insert(db.CellInstArray(child.cell_index(), db.Trans(x, 0)))
    if kind == "connected":
        top.shapes(li).insert(db.Box(0, 0, 100, 20))
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, top, []))
    layer = l2n.make_polygon_layer(li, "metal8")
    l2n.connect(layer)
    l2n.include_floating_subcircuits = True
    l2n.extract_netlist()
    pins = {str(Path(__file__).resolve()): sha(Path(__file__))}
    probes = [dict(layer="metal8", box_dbu=[x, 0, x+20, 20]) for x in (0, 80)]
    prepare(db, l2n, directory, probes, "TOP", pins)
    try:
        verify(db, directory, sha(directory / "prepared.json"))
    except ValueError as e:
        assert "Producer must exit" in str(e)
        (directory / "live-producer-rejection.txt").write_text(str(e))
    else:
        raise AssertionError("Live producer accepted")
    assert not (directory / "manifest.json").exists()
    try:
        load(db, directory, sha(directory / "prepared.json"))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("PREPARED checkpoint accepted")


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = {}
    for kind in ("connected", "floating"):
        d = output / kind
        with (output / (kind + "-producer.log")).open("w") as log:
            subprocess.run([sys.executable, __file__, str(d), "--produce", kind],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        assert not (d / "manifest.json").exists()
        if kind == "connected":
            for failure in ("wrong_pin", "database", "snapshot", "method", "input"):
                bad = output / failure
                shutil.copytree(d, bad)
                p = bad / "prepared.json"
                m = json.loads(p.read_text())
                if failure == "database":
                    with (bad / "connectivity.l2n.gz").open("ab") as f:
                        f.write(b"changed")
                elif failure == "snapshot":
                    m["probe_snapshot"][0]["samples"][0]["equivalence_class"] = 999
                elif failure == "method":
                    m["method_sha256"] = "0" * 64
                elif failure == "input":
                    m["input_sha256"][str(Path(__file__).resolve())] = "0" * 64
                p.write_text(json.dumps(m))
                pin = "0" * 64 if failure == "wrong_pin" else sha(p)
                try:
                    verify(db, bad, pin)
                except ValueError as e:
                    cases[failure] = str(e)
                    (bad / "rejected.txt").write_text(str(e))
                else:
                    raise AssertionError(failure + " accepted")
                assert not (bad / "manifest.json").exists()
        pin = sha(d / "prepared.json")
        with (output / (kind + "-verifier.log")).open("w") as log:
            subprocess.run([sys.executable, str(ROOT / "scripts/supply_checkpoint_staged.py"),
                            "--checkpoint", str(d), "--prepared-sha256", pin],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        fresh, manifest = load(db, d, sha(d / "manifest.json"))
        expected = "PASS_SINGLE_TOP_NET_WINDOW_ONLY" if kind == "connected" else "UNRESOLVED_OR_FAILED_WINDOW"
        assert all(row["status"] == expected for row in manifest["probe_snapshot"])
        assert manifest["producer"] != manifest["verifier"]
        assert manifest["prepared_sha256"] == pin
        cases[kind] = dict(status=expected, manifest_sha256=sha(d / "manifest.json"),
                           producer=manifest["producer"], verifier=manifest["verifier"])
        try:
            verify(db, d, pin)
        except FileExistsError:
            cases[kind + "_overwrite_rejected"] = True
        else:
            raise AssertionError("Overwrite accepted")
    result = dict(status="PASS_STAGED_NATIVE_CONTROLS_ONLY", cases=cases,
                  address_space_cap_bytes=256 * 1024**2, klayout_version=db.__version__,
                  input_sha256={str(p): sha(p) for p in [Path(__file__).resolve(),
                       ROOT / "scripts/supply_checkpoint_staged.py", ROOT / "scripts/supply_checkpoint.py",
                       ROOT / "scripts/probe_supply_components.py"]},
                  chip_connectivity_accepted=False, full_chip_lvs_accepted=False,
                  manufacturing_approval=False)
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], len(cases))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--produce", choices=["connected", "floating"])
    args = parser.parse_args()
    if args.produce:
        produce(args.output, args.produce)
    else:
        run(args.output)
