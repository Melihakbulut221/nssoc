#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""RX v2 real 150 fF load screen; immutable v1 equations and limits remain in use."""

import argparse
import gzip
import itertools
import json
from pathlib import Path
import shutil

import characterize_pcie_rx as rx
import review_pcie_rx as diagnostic

ROOT, tx, resistor = rx.ROOT, rx.tx, rx.resistor
NETLIST = ROOT / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice"
UI, BITS, LIMITS = rx.UI, rx.BITS, dict(rx.LIMITS)
execute, measure, measure_ac = rx.execute, rx.measure, rx.measure_ac


def cases(quick=False):
    """Keep every v1 corner/negative, make 150 fF the full-matrix required load."""
    result = []
    for original in rx.cases(quick):
        case = dict(original)
        if case["reference_a"] == 0.0005:
            case["reference_a"] = 0.00075
        if case["cap_f"] == 100e-15:
            case["cap_f"] = 150e-15
        if case["name"] == "load_150fF":
            case.update(name="load_100fF", cap_f=100e-15)
        if case["name"] == "clipped_overbias":
            # The smaller real collector loads make the old 3 mA stimulus
            # non-clipping. Preserve it as an extension, then apply a genuine
            # 6 mA overcurrent/headroom fault under the unchanged limits.
            result.append(dict(case, name="reference_3mA_extension", fault=None))
            case["reference_a"] = 0.006
        result.append(case)
    return result


def sequence(case):
    return rx.sequence(case)


def deck(case, models, osdi, ac=False):
    """Same native bench, 50-ohm sources, thresholds, options and self-heating."""
    text, bits = rx.deck(case, models, osdi, ac=ac)
    if text.count("rx_hbt_rsil.spice") != 1 or text.count("nssoc_rx_hbt_rsil") != 1:
        raise ValueError("Immutable v1 bench interface changed")
    text = text.replace("rx_hbt_rsil.spice", NETLIST.name)
    text = text.replace("nssoc_rx_hbt_rsil", "nssoc_rx_hbt_rsil_v2")
    return text, bits


def disposition(measurements_passed, numerical_clean):
    if not measurements_passed:
        return "FAIL_RX_V2_MEASUREMENT_SCREEN"
    if not numerical_clean:
        return "RX_V2_MEASUREMENT_PASS_NUMERICAL_RESIDUAL"
    return "PASS_RX_V2_LIMITED_SCREEN"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "ngspice", "openvaf", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() or not (
        out.is_relative_to(Path("/dev/shm")) or out.is_relative_to(ROOT / "hw/soc/out")
    ):
        ap.error("Use a fresh /dev/shm or project-output directory")
    tech = args.pdk.resolve() / "libs.tech"
    models = tech / "ngspice/models"
    expected = {
        **{str(models / n): h for n, h in tx.MODEL_HASHES.items()},
        **{str(tech / n): h for n, h in resistor.RES_HASHES.items()},
    }
    if any(tx.sha(Path(p)) != h for p, h in expected.items()):
        ap.error("Foundry model revision mismatch")
    inputs = [
        NETLIST,
        Path(__file__).resolve(),
        Path(rx.__file__),
        Path(diagnostic.__file__),
        Path(tx.__file__),
        Path(resistor.__file__),
        *map(Path, expected),
        args.ngspice.resolve(),
        args.openvaf.resolve(),
    ]
    pins = {str(p): tx.sha(p) for p in inputs}
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        pdk_revision=tx.PDK_REV,
        quick=args.quick,
        limits=LIMITS,
        ui_s=UI,
        bits=BITS,
        cases=[],
        ac_cases=[],
        assumptions=dict(
            vcm_v=1.36,
            ideal_reference_a=0.00075,
            source_impedance_each_ohm=50,
            output_load_each_f=150e-15,
            substrate_model_node_v=0,
            simulated_physical_substrate_tap_rc=False,
            clock_or_slicer_present=False,
        ),
        scope="Foundry-model four-HBT/four-rsil continuous-time RX preamplifier. Native self-heating resistors; ideal external bias/reference and source. No pad/ESD, offset/noise/jitter/BER, CTLE, slicer, CDR, PLL, lane bonding, PEX or PHY qualification.",
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
    )

    def save():
        p = out / "result.tmp"
        p.write_text(json.dumps(record, indent=2) + "\n")
        p.replace(out / "result.json")

    try:
        save()
        osdi = out / "r3_cmc.osdi"
        record["compile"] = execute(
            [
                str(args.openvaf.resolve()),
                str(tech / "verilog-a/r3_cmc/r3_cmc.va"),
                "-o",
                str(osdi),
            ],
            out,
            out / "compile.log",
        )
        record["osdi_sha256"] = tx.sha(osdi)
        selected = cases(args.quick)
        for case in selected:
            dest = out / case["name"]
            dest.mkdir()
            shutil.copyfile(NETLIST, dest / NETLIST.name)
            text, bits = deck(case, models, osdi)
            (dest / "bench.cir").write_text(text)
            entry = dict(case=case)
            record["cases"].append(entry)
            save()
            entry["execution"] = execute(
                [str(args.ngspice.resolve()), "-n", "-b", "bench.cir"],
                dest,
                dest / "run.log",
            )
            entry["measurement"] = measure(dest / "wave.dat", case, bits)
            entry["numerical_diagnostics"] = diagnostic.diagnostics(
                (dest / "run.log").read_text()
            )
            entry["expected_screen_pass"] = case["fault"] is None
            entry["expected_outcome_observed"] = (
                entry["measurement"]["screen_pass"] == entry["expected_screen_pass"]
            )
            entry["wave_sha256"] = tx.sha(dest / "wave.dat")
            with (
                (dest / "wave.dat").open("rb") as src,
                gzip.open(dest / "wave.dat.gz", "wb", compresslevel=1) as dst,
            ):
                shutil.copyfileobj(src, dst)
            (dest / "wave.dat").unlink()
            entry["output_sha256"] = {
                p.name: tx.sha(p) for p in dest.iterdir() if p.is_file()
            }
            save()
            print(
                case["name"],
                "EXPECTED" if entry["expected_outcome_observed"] else "UNEXPECTED",
                entry["measurement"]["min_signed_margin_v"],
                entry["measurement"]["min_vce_v"],
                flush=True,
            )
        # Independent balanced-bias AC decks: all nine HBT/resistor pairs at nominal V/T.
        ac_specs = (
            [("hbt_typ", "res_typ")]
            if args.quick
            else itertools.product(
                ("hbt_typ", "hbt_bcs", "hbt_wcs"), ("res_typ", "res_bcs", "res_wcs")
            )
        )
        for hbt, res in ac_specs:
            case = dict(selected[0], hbt=hbt, resistor=res, temp=27, supply=1.8)
            dest = out / ("ac_" + hbt + "_" + res)
            dest.mkdir()
            shutil.copyfile(NETLIST, dest / NETLIST.name)
            text, _ = deck(case, models, osdi, ac=True)
            (dest / "bench.cir").write_text(text)
            execution = execute(
                [str(args.ngspice.resolve()), "-n", "-b", "bench.cir"],
                dest,
                dest / "run.log",
            )
            record["ac_cases"].append(
                dict(
                    case=case,
                    execution=execution,
                    measurement=measure_ac(dest / "ac.dat"),
                    output_sha256={
                        p.name: tx.sha(p) for p in dest.iterdir() if p.is_file()
                    },
                )
            )
            save()
        measured = {x["case"]["name"]: x["measurement"] for x in record["cases"]}
        base = measured["hbt_typ_res_typ_27_1.8"]
        half = measured["half_timestep"]
        delta = abs(base["min_signed_margin_v"] - half["min_signed_margin_v"])
        power = abs(base["analog_supply_power_w"] / half["analog_supply_power_w"] - 1)
        record["timestep_sensitivity"] = dict(
            margin_difference_v=delta,
            power_relative_difference=power,
            screen_pass=delta < 0.001 and power < 0.002,
            scope="Two numerical steps, not extrapolated convergence.",
        )
        if any(tx.sha(Path(p)) != h for p, h in pins.items()):
            raise RuntimeError("Input bytes changed during simulation")
        record["source_bytes_unchanged"] = True
        passed = (
            all(x["expected_outcome_observed"] for x in record["cases"])
            and record["timestep_sensitivity"]["screen_pass"]
        )
        record["numerical_clean"] = all(
            x["numerical_diagnostics"]["numerical_clean"]
            for x in record["cases"]
            if x["case"]["fault"] is None
        )
        record["status"] = disposition(passed, record["numerical_clean"])
        record["complete_pvt_cross_product"] = not args.quick
    except BaseException as exc:
        record.update(status="ERROR_PRESERVED", error=repr(exc))
        raise
    finally:
        save()
    return (
        0
        if record["status"] == "PASS_RX_V2_LIMITED_SCREEN"
        else 2
        if record["status"] == "RX_V2_MEASUREMENT_PASS_NUMERICAL_RESIDUAL"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
