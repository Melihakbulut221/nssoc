#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native nominal VCO sensitivity to measured, collapsed clock-net capacitance.

This is a lumped-load experiment, not post-layout PEX. Ground plus one/two
incident coupling sums mean fixed quiet/opposed-aggressor approximations;
actual aggressor waveforms, route resistance/inductance and input devices
are not represented. No source, model or original screen threshold changes.
"""

import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import characterize_pcie_clock_vco as vco

SOURCE_SHA = "b7fd696ed658650b5be118dc897db690e6c225250fc334706714dd62256df3f9"
CIRCUIT_SHA = "b93e478e3d6a766051b82aabd5796d6fa8f2dbac68f25f1c1757d411369d5426"
CAP_SHA = "b3b7cad6c31a916f0461adec082336968d3ef882bda08492ff2e9e31ede25ad5"


def loads(record):
    clocks = {r["native_label"]: r for r in record["clock_nets"]}
    if (
        set(clocks) != {"CLOCKP", "CLOCKN"}
        or not record["clock_annotation_geometry_and_device_cap_records_unchanged"]
    ):
        raise ValueError("Clock extraction identity changed")
    result = [("reference_50fF", [50e-15, 50e-15])]
    for weight, name in [
        (0, "ground_only"),
        (1, "quiet_aggressor_equivalent"),
        (2, "opposed_aggressor_equivalent"),
    ]:
        result.append(
            (
                name,
                [
                    clocks[n]["intrinsic_ground_f"]
                    + weight * clocks[n]["incident_mutual_f"]
                    for n in ("CLOCKP", "CLOCKN")
                ],
            )
        )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ["out", "pdk", "ngspice", "models", "capacitance"]:
        p.add_argument("--" + arg, type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists():
        p.error("Fresh output directory required")
    if (
        vco.sha(Path(vco.__file__)) != SOURCE_SHA
        or vco.sha(vco.CIRCUIT) != CIRCUIT_SHA
        or vco.sha(a.capacitance) != CAP_SHA
    ):
        p.error("Require exact frozen sources and actual capacitance capture")
    native_models = [
        a.models.resolve() / n
        for n in ["r3_cmc.osdi", "psp103.osdi", "psp103_nqs.osdi"]
    ]
    provenance = json.loads((a.models / "result.json").read_text())
    for path in native_models:
        # Native compiled binary identity is inherited from the actual original72-case producer.
        if provenance["compiled_models"][str(path)] != vco.sha(path):
            p.error("Compiled model changed")
    for source, want in provenance["source_sha256"].items():
        if "/libs.tech/" in source:
            selected = a.pdk.resolve() / "libs.tech" / source.split("/libs.tech/", 1)[1]
            if vco.sha(selected) != want:
                p.error("PDK input changed")
    if vco.sha(a.ngspice) != provenance["source_sha256"].get(str(a.ngspice.resolve())):
        p.error("Native ngspice input changed")
    out.mkdir(parents=True)
    (out / "spinit").write_text("set num_threads=1\n")
    inputs = [
        Path(__file__),
        Path(vco.__file__),
        vco.CIRCUIT,
        a.ngspice,
        a.capacitance,
        a.models / "result.json",
        *native_models,
    ]
    record = dict(
        status="RUNNING",
        input_sha256={str(p.resolve()): vco.sha(p) for p in inputs},
        limits=vco.LIMITS,
        cases=[],
        scope=__doc__,
        qualified_pex=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        for name, (cp, cn) in loads(json.loads(a.capacitance.read_text())):
            d = out / name
            d.mkdir()
            case = dict(vco.BASE, name=name, load_f=cp)
            text = vco.deck(
                case, a.pdk.resolve() / "libs.tech/ngspice/models", native_models
            )
            old = f"CLOADN clkn 0 {cp:.12g}"
            assert text.count(old) == 1
            text = text.replace(old, f"CLOADN clkn 0 {cn:.12g}")
            (d / "bench.cir").write_text(text)
            (d / vco.CIRCUIT.name).write_text(vco.CIRCUIT.read_text())
            command = [str(a.ngspice.resolve()), "-b", "bench.cir"]
            with (d / "run.log").open("w") as log:
                result = subprocess.run(
                    command,
                    cwd=d,
                    env=dict(os.environ, SPICE_SCRIPTS=str(out)),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                )
            row = dict(
                name=name,
                load_p_f=cp,
                load_n_f=cn,
                argv=command,
                returncode=result.returncode,
                numerical=vco.diagnostics((d / "run.log").read_text()),
            )
            if result.returncode == 0 and (d / "wave.dat").exists():
                row["measurement"] = vco.measure(vco.read_wave(d / "wave.dat"))
                original = (d / "wave.dat").read_bytes()
                with gzip.open(d / "wave.dat.gz", "wb") as f:
                    f.write(original)
                with gzip.open(d / "wave.dat.gz", "rb") as f:
                    assert f.read() == original
                (d / "wave.dat").unlink()
            row["output_sha256"] = {
                p.name: vco.sha(p) for p in d.iterdir() if p.is_file()
            }
            record["cases"].append(row)
            save()
            print(name, row.get("measurement", {}).get("screen_pass"), flush=True)
        before = record["input_sha256"]
        if before != {p: vco.sha(Path(p)) for p in before}:
            raise ValueError("Inputs changed")
        if any(
            r["returncode"] or not r["numerical"]["clean"] or "measurement" not in r
            for r in record["cases"]
        ):
            raise ValueError("Incomplete or numerically unclean native run")
        if not record["cases"][0]["measurement"]["screen_pass"]:
            raise ValueError("Nominal reference failed")
        record["status"] = "COMPLETE_LUMPED_LOAD_EXPERIMENT_NOT_PEX"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        save()
    return record["status"] != "COMPLETE_LUMPED_LOAD_EXPERIMENT_NOT_PEX"


if __name__ == "__main__":
    raise SystemExit(main())
