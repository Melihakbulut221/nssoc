#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded native OFF-initialized zero-source startup; unchanged RX/sampler v2."""

import argparse
import json
import lzma
import math
from pathlib import Path
import re
import shutil

import characterize_pcie_sampler_v2 as s

RX_PIN = s.RX_PIN
SAMPLER_PIN = "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f"
DEPENDENCIES = {
    **s.FIXED,
    "scripts/characterize_pcie_sampler_v2.py": "4c5f52d68012d79f0c08809d269f79d357955571630297aa62dbcbb9f5da7f67",
}
OSDI_PIN = "9b41facf3c49d2266e542406547ed00677304f09c1dd281f3bf90414ee053828"
RAMP_S = 1e-9
PILOT = ("hbt_typ_res_typ_27_1.8", "hbt_wcs_res_wcs_-40_1.71", "hbt_wcs_res_bcs_125_1.71")
STRATEGIES = ("zero_off", "zero_default", "powered_off")
MANUAL = "https://ngspice.sourceforge.io/docs/ngspice-manual.pdf"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def replace_one(text, pattern, replacement):
    text, count = re.subn(pattern, replacement, text, flags=re.M)
    require(count == 1, "Exact source transformation anchor missing or repeated: " + pattern)
    return text


def hbts(kind):
    require(kind in ("rx", "sampler"), "Unknown native circuit")
    return [name for name in s.HBT if kind == "sampler" or name.startswith("xrx.")]


def vectors(kind):
    return s.VECTORS if kind == "sampler" else s.rx.rx.VECTORS


def transform(original, kind, strategy="zero_off"):
    require(strategy in STRATEGIES, "Unknown startup protocol")
    require(original.count(".options reltol=1e-4 abstol=1e-12") == 1, "Original tolerances required")
    require(not re.search(r"(?im)^\s*\.ic\b|\buic\b|\balter\b", original), "No prior forced state or alteration allowed")
    text = re.sub(r"^\.nodeset[^\n]*\n", "", original, flags=re.M)
    if strategy != "powered_off":
        sources = ["VDD", "VCM", "IREF"] + (["VSAMP", "ISAMP"] if kind == "sampler" else [])
        for source in sources:
            text = replace_one(text, r"^(" + source + r" \S+ \S+) ([-+.0-9eE]+)$", lambda m: m[1] + f" PWL(0 0 {RAMP_S:.12g} " + m[2] + ")")
        for source in ("VP", "VN"):
            text = replace_one(text, r"(" + source + r" \S+ 0 PWL\(\n\+ )0 ([^\n]+)", lambda m: m[1] + f"0 0\n+ {RAMP_S:.12g} " + m[2])
        if kind == "sampler":
            for source in ("VSCP", "VSCN"):
                match = re.search(r"^" + source + r" (\S+) 0 (.+)$", text, re.M)
                require(match is not None, "Missing native clock source")
                waveform = match[2]
                if waveform.startswith("PULSE(") and waveform.endswith(")"):
                    values = list(map(float, waveform[6:-1].split()))
                    require(len(values) == 7 and all(math.isfinite(v) for v in values), "Native PULSE form differs")
                    low, high, delay, rise, fall, width, period = values
                    require(delay > RAMP_S and min(rise, fall, width, period) > 0, "Clock ramp overlaps actual observation")
                    points, time = [(0, 0), (RAMP_S, low)], delay
                    while time < s.STOP:
                        points.extend([(time, low), (time + rise, high), (time + rise + width, high), (time + rise + width + fall, low)])
                        time += period
                else:
                    value = float(waveform)
                    require(math.isfinite(value), "Invalid stopped-clock value")
                    points = [(0, 0), (RAMP_S, value)]
                text = text[:match.start()] + source + " " + match[1] + " 0 PWL(" + " ".join(f"{t:.12g} {v:.12g}" for t, v in points) + ")" + text[match.end():]
    flags = ""
    if strategy != "zero_default":
        flags = "".join(f"alter @q.{name}.qnpn13g2[off] = 1\necho NSSOC_FLAG_BEGIN q.{name}.qnpn13g2\nshow q.{name}.qnpn13g2 : off\necho NSSOC_FLAG_END\n" for name in hbts(kind))
    require(len(re.findall(r"^tran ", text, re.M)) == 1, "Exactly one original transient required")
    text = text.replace("\ntran ", "\n" + flags + "op\nwrdata initial-op.dat " + " ".join(vectors(kind)) + "\ntran ", 1)
    require(not re.search(r"(?im)^\s*\.ic\b|\buic\b|^\s*\.nodeset", text), "No forced state allowed")
    return text


def initial_op(path, names):
    lines = [line for line in Path(path).read_text().splitlines() if line.strip()]
    require(len(lines) == 2, "Exactly one actual native initial OP required")
    require(lines[0].split()[1:] == list(names), "Initial OP vector identity differs")
    values = list(map(float, lines[1].split()))
    require(len(values) == len(names) + 1 and all(map(math.isfinite, values)), "Initial OP missing or nonfinite")
    return dict(zip(names, values[1:]))


def flags_observed(log, kind, strategy):
    expected = ["q." + name + ".qnpn13g2" for name in hbts(kind)]
    sections = re.findall(r"(?ms)^NSSOC_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_FLAG_END\s*$", log)
    if strategy == "zero_default":
        require(not sections, "Unexpected OFF readback in default-init control")
        return {}
    require([name for name, _ in sections] == expected, "Native OFF device coverage differs")
    for name, body in sections:
        # Native show reads IF_FLAG as integer in both ng42/ng47. The ng42
        # print-vector frontend misrenders IF_FLAG; do not use it as proof.
        devices = re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body)
        values = re.findall(r"(?m)^\s*off\s+(\S+)\s*$", body)
        require(len(devices) == 1 and devices[0] == name[:21], "Native OFF device identity differs")
        require(values == ["1"], "Native OFF readback differs: " + name)
    return dict.fromkeys(expected, 1)


def diagnostics(log):
    result = s.diagnostics.diagnostics(log)
    # Preserve additional native failure classes, even when ngspice returns zero.
    result["native_error_lines"] = [line for line in log.splitlines() if re.search(r"(?i)(?:^|\s)(?:error|fatal|aborted|failed|infinite|infinity|no such vector)\b", line)]
    result["numerical_clean"] = result["numerical_clean"] and not result["native_error_lines"]
    return result


def cases(kind, matrix):
    source = s.cases(False) if kind == "sampler" else s.rx.cases(False)
    chosen = [dict(c) for c in source if c["name"].startswith("hbt_") and (matrix == "full" or c["name"] in PILOT)]
    require(len(chosen) == (81 if matrix == "full" else 3), "Exact PVT case coverage differs")
    if matrix == "controls":
        chosen = [c for c in chosen if c["name"] == PILOT[-1]]
        chosen.extend(dict(c) for c in source if c["name"] in ("no_bias", "swapped_output"))
    return chosen


def input_pins(pdk, runtime, osdi):
    require(s.rx.tx.sha(runtime) in s.RUNTIMES, "Unpinned native runtime")
    require(s.rx.tx.sha(osdi) == OSDI_PIN, "Unpinned native OSDI model")
    require(s.rx.tx.sha(s.NETLIST) == SAMPLER_PIN and s.rx.tx.sha(s.rx.NETLIST) == RX_PIN, "Frozen v2 circuit differs")
    expected = {str(s.ROOT / name): digest for name, digest in DEPENDENCIES.items()}
    tech = pdk / "libs.tech"
    expected.update({str(tech / "ngspice/models" / name): digest for name, digest in s.rx.tx.MODEL_HASHES.items()})
    expected.update({str(tech / name): digest for name, digest in s.rx.resistor.RES_HASHES.items()})
    for name, digest in expected.items():
        require(s.rx.tx.sha(Path(name)) == digest, "Frozen source/model differs: " + name)
    expected.update({str(p): s.rx.tx.sha(p) for p in (s.NETLIST, s.rx.NETLIST, runtime, osdi, Path(__file__).resolve())})
    return expected


def run(pdk, runtime, osdi, output, kind, matrix, strategy):
    pdk, runtime, osdi, output = [Path(p).resolve() for p in (pdk, runtime, osdi, output)]
    require(not output.exists() and output.is_relative_to(Path("/dev/shm")), "Fresh bounded /dev/shm output required")
    pins = input_pins(pdk, runtime, osdi)
    selected = cases(kind, matrix)
    output.mkdir()
    result = dict(status="RUNNING", kind=kind, matrix=matrix, strategy=strategy, source_sha256=pins, runtime_version=s.RUNTIMES[s.rx.tx.sha(runtime)], ramp_s=RAMP_S, cases=[], models_unchanged=True, circuits_unchanged=True, tolerances_unchanged=True, no_uic_or_forced_state=True, external_startup_waveform=True, physical_startup_circuit_implemented=False, pcie_qualification=False, reference=MANUAL, scope="Native initial-condition and explicit external power/bias/clock startup diagnostic. The transistor OFF flag is only an initial Newton state; all foundry equations remain active. This does not cure the old fully powered direct-OP solver path or implement a physical power sequencer.")
    def save():
        (output / "result.tmp").write_text(json.dumps(result, indent=2) + "\n")
        (output / "result.tmp").replace(output / "result.json")
    save()
    try:
        for case in selected:
            dest = output / case["name"]
            dest.mkdir()
            shutil.copyfile(s.rx.NETLIST, dest / s.rx.NETLIST.name)
            (dest / s.NETLIST.name).write_text(s.circuit(case) if kind == "sampler" else s.NETLIST.read_text())
            original = s.deck(case, pdk / "libs.tech/ngspice/models", osdi) if kind == "sampler" else s.rx.deck(case, pdk / "libs.tech/ngspice/models", osdi)[0]
            (dest / "bench.cir").write_text(transform(original, kind, strategy))
            row = dict(case=case, expected_functional_pass=case["fault"] is None)
            result["cases"].append(row)
            save()
            try:
                row["execution"] = s.rx.execute([str(runtime), "-n", "-b", "bench.cir"], dest, dest / "run.log")
                log = (dest / "run.log").read_text()
                row["diagnostics"] = diagnostics(log)
                row["flags_observed"] = flags_observed(log, kind, strategy)
                op = initial_op(dest / "initial-op.dat", vectors(kind))
                row["initial_op"] = op
                row["zero_initial_op"] = max(map(abs, op.values())) <= 1e-10
                row["measurement"] = s.measure(dest / "wave.dat", case) if kind == "sampler" else s.rx.measure(dest / "wave.dat", case, s.rx.sequence(case))
                row["wave_sha256"] = s.rx.tx.sha(dest / "wave.dat")
                row["expected_function_observed"] = row["measurement"]["screen_pass"] == row["expected_functional_pass"]
                row["protocol_pass"] = row["diagnostics"]["numerical_clean"] and row["zero_initial_op"] and row["expected_function_observed"]
            except (ValueError, RuntimeError) as exc:
                row["error"] = repr(exc)
                row["protocol_pass"] = False
                if (dest / "run.log").exists():
                    row["diagnostics"] = diagnostics((dest / "run.log").read_text())
            # Retain the measured nominal/hot native waves and every failed case.
            wave = dest / "wave.dat"
            if wave.exists():
                retain = case["name"] in (PILOT[0], PILOT[-1]) or not row["protocol_pass"] or bool(case["fault"])
                row["wave_retained"] = retain
                row["wave_sha256"] = s.rx.tx.sha(wave)
                if retain:
                    with wave.open("rb") as src, lzma.open(dest / "wave.dat.xz", "wb", preset=1) as dst:
                        shutil.copyfileobj(src, dst)
                wave.unlink()
            row["output_sha256"] = {p.name: s.rx.tx.sha(p) for p in dest.iterdir()}
            save()
            print(kind, case["name"], row["protocol_pass"], row.get("measurement", {}).get("min_signed_margin_v"), flush=True)
        for name, digest in pins.items():
            require(s.rx.tx.sha(Path(name)) == digest, "Input changed during native execution")
        result["source_bytes_unchanged"] = True
        result["status"] = "PASS_BOUNDED_ZERO_START_PROTOCOL" if all(row["protocol_pass"] for row in result["cases"]) else "FAIL_PRESERVED"
        return result
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "ngspice", "osdi", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--kind", choices=("rx", "sampler"), required=True)
    parser.add_argument("--matrix", choices=("pilot", "full", "controls"), default="pilot")
    parser.add_argument("--strategy", choices=STRATEGIES, default="zero_off")
    args = parser.parse_args()
    result = run(args.pdk, args.ngspice, args.osdi, args.out, args.kind, args.matrix, args.strategy)
    return 0 if result["status"] == "PASS_BOUNDED_ZERO_START_PROTOCOL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
