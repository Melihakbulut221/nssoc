#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native four-rppd clock conditioner and frozen two-latch prescaler screen.

The divider, latch, device equations, thresholds and source ramps remain frozen.
A real series/pullup resistor network raises clock common mode. Every actual
HBT terminal, new resistor current/resistance and thermal vector is observed.
This finite schematic experiment does not implement a PLL or qualify a layout.
"""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import types
import statistics

import characterize_pcie_div2 as old
import characterize_pcie_div2_v2 as previous

VCO = previous.VCO
CIRCUIT = old.ROOT / "hw/soc/analog/pcie/clock_div2_conditioned_hbt.spice"
PARENT = previous.PARENT
STARTUP_REFERENCE = previous.STARTUP_REFERENCE
PILOT = previous.PILOT
CONDITIONERS = ("xdiv.xsp", "xdiv.xsn", "xdiv.xup", "xdiv.xun")
CONDITIONER_MIN_PEAK_V = 0.3
PREVIOUS_SHA = "e900340c5e7bb71cc8376c31c0ac6b72a8ae3b2ceed6acfb7e31aa198a569bf0"

require = previous.require


def verify_vco():
    previous.verify_vco()
    require(
        old.sha(Path(previous.__file__)) == PREVIOUS_SHA,
        "Frozen startup parent changed",
    )
    ports, rows = old.statements(
        CIRCUIT.read_text(), "nssoc_clock_div2_conditioned_hbt"
    )
    require(ports == "clkp clkn qp qn avdd avss sub".split(), "Exact conditioner ports")
    expected = [
        "xsp clkp ckp sub rppd w=4u l=3.6u b=0 sw_et=1",
        "xsn clkn ckn sub rppd w=4u l=3.6u b=0 sw_et=1",
        "xup avdd ckp sub rppd w=1u l=8u b=0 sw_et=1",
        "xun avdd ckn sub rppd w=1u l=8u b=0 sw_et=1",
        "xcore ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt",
    ]
    require(
        rows == [s.split() for s in expected], "Exact physical series/pullup topology"
    )


def device_contract(case):
    sources = {
        "nssoc_clock_div2_conditioned_hbt": CIRCUIT.read_text(),
        "nssoc_clock_div2_hbt": old.circuit(case),
        "nssoc_cml_latch": old.LATCH.read_text(),
        "nssoc_clock_vco_hbt_v2": VCO.read_text(),
    }
    hbts, resistors = {}, []

    def add(name, prefix, actual):
        ports, body = old.statements(sources[name], name)
        require(len(ports) == len(actual), "Actual subcircuit arity")
        mapping = dict(zip(ports, actual))

        def node(n):
            return mapping.get(n, prefix + "." + n)

        for words in body:
            if not words[0].startswith("x"):
                continue
            if len(words) > 5 and words[5] == "npn13g2":
                nx = [w[3:] for w in words[6:] if w.startswith("nx=")]
                require(len(nx) == 1 and 1 <= int(nx[0]) <= 10, "Native HBT Nx range")
                require(prefix + "." + words[0] not in hbts, "Duplicate HBT path")
                hbts[prefix + "." + words[0]] = (
                    tuple(node(n) for n in words[1:4]),
                    int(nx[0]),
                )
            elif len(words) > 4 and words[4] == "rppd":
                resistors.append(prefix + "." + words[0])
            elif words[-1] in sources:
                add(words[-1], prefix + "." + words[0], [node(n) for n in words[1:-1]])

    add("nssoc_clock_vco_hbt_v2", "xosc", ["clkp", "clkn", "vctrl", "avdd", "0", "0"])
    add(
        "nssoc_clock_div2_conditioned_hbt",
        "xdiv",
        [
            "clkp",
            "clkp" if case["fault"] == "same_clock" else "clkn",
            "qp",
            "qn",
            "dvdd",
            "0",
            "0",
        ],
    )
    require(
        len(hbts) == 33 and len(set(resistors)) == len(resistors) == 22,
        "Complete native device census",
    )
    return hbts, resistors


def electrical_vectors(case):
    hbts, resistors = device_contract(case)
    nets = {n for pins, _ in hbts.values() for n in pins} | {
        "clkp",
        "clkn",
        "xdiv.ckp",
        "xdiv.ckn",
        "qp",
        "qn",
        "avdd",
        "dvdd",
        "vctrl",
    }
    return (
        ["v(" + n + ")" for n in sorted(nets - {"0"})]
        + ["i(vdd)", "i(vddiv)", "i(vctrl)"]
        + ["@q." + n + ".qnpn13g2[ic]" for n in hbts]
        + ["v(" + n + ".dt)" for n in resistors]
    )


def vectors(case):
    # Resistance is not an electrical state, so it is not required to be zero
    # at initial OP. All original electrical/thermal vectors still are.
    return electrical_vectors(case) + [
        "@n." + name + ".nr1[" + field + "]"
        for name in CONDITIONERS
        for field in ("r_dc", "ibody", "power")
    ]


# These are new function objects with isolated dependency namespaces. The
# frozen bytecode and all numeric predicates remain identical, while actual
# nested terminals/vectors are bound explicitly. No imported global is mutated.
_native_measure = types.FunctionType(
    old.measure.__code__,
    {**old.measure.__globals__, "device_contract": device_contract},
)
read_wave = types.FunctionType(
    old.read_wave.__code__, {**old.read_wave.__globals__, "vectors": vectors}
)


def measure(data, case):
    result = _native_measure(data, case)
    active = [
        i for i, t in enumerate(data["time"]) if t >= old.LIMITS["observation_begin_s"]
    ]
    for key, p, n in (
        ("conditioned_clock", "v(xdiv.ckp)", "v(xdiv.ckn)"),
        ("raw_clock", "v(clkp)", "v(clkn)"),
    ):
        diff = [data[p][i] - data[n][i] for i in active]
        cm = [(data[p][i] + data[n][i]) / 2 for i in active]
        result[key] = dict(
            diff_range_v=[min(diff), max(diff)], common_mode_range_v=[min(cm), max(cm)]
        )
        result["checks"][key + "_peak"] = (
            min(max(diff), -min(diff)) >= CONDITIONER_MIN_PEAK_V
        )
    result["conditioner_models"] = {}
    for name in CONDITIONERS:
        row = {}
        for field in ("r_dc", "ibody", "power"):
            values = data["@n." + name + ".nr1[" + field + "]"]
            observed = [values[i] for i in active]
            row[field] = dict(
                min=min(observed),
                max=max(observed),
                mean=statistics.mean(observed),
                max_abs_capture=max(map(abs, values)),
            )
        row["maximum_selfheat_k"] = max(data["v(" + name + ".dt)"])
        result["conditioner_models"][name] = row
    result["checks"]["conditioner_resistance_positive"] = all(
        x["r_dc"]["min"] > 0 for x in result["conditioner_models"].values()
    )
    result["screen_pass"] = all(result["checks"].values())
    # Native logical negatives must break the original divide behavior, not
    # merely a new electrical/swing guard. Keep the frozen functional predicate.
    return result


def identities(case):
    hbts, _ = device_contract(case)
    return ["q." + name + ".qnpn13g2" for name in hbts]


def deck(case, models, osdi):
    verify_vco()
    text = old.deck(case, models, osdi)
    text = text.replace(
        '.include "clock_div2_hbt.spice"',
        '.include "clock_div2_hbt.spice"\n.include "clock_div2_conditioned_hbt.spice"',
    )
    text = text.replace(
        " nssoc_clock_div2_hbt\n", " nssoc_clock_div2_conditioned_hbt\n"
    )
    original_vectors = " ".join(old.vectors(case))
    require(
        text.count(original_vectors) == 2, "Exact original save and wave vector sets"
    )
    text = text.replace(original_vectors, " ".join(vectors(case)))
    require(
        not re.search(r"(?im)^\s*\.ic\b|\buic\b|\balter\b|^\s*\.nodeset", text),
        "No prior forced state or parameter alteration",
    )
    before = f'.include "{old.VCO.name}"'
    require(text.count(before) == 1, "Unique VCO include required")
    text = text.replace(before, f'.include "{VCO.name}"')
    before = "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt"
    require(text.count(before) == 1, "Unique native clock instance required")
    text = text.replace(before, before + "_v2")
    for source in ("VDD", "VDDIV", "VCTRL"):
        require(
            len(re.findall(r"(?m)^" + source + r" \S+ 0 PWL\(0 0 [^\n]+\)$", text))
            == 1,
            "Every external source must begin at zero",
        )
    flags = "".join(
        f"alter @{name}[off] = 1\n"
        f"echo NSSOC_DIV2_FLAG_BEGIN {name}\n"
        f"show {name} : off\necho NSSOC_DIV2_FLAG_END\n"
        for name in identities(case)
    )
    require(len(re.findall(r"(?m)^tran ", text)) == 1, "Unique unchanged transient")
    return text.replace(
        "\ntran ",
        "\n"
        + flags
        + "op\nwrdata initial-op.dat "
        + " ".join(electrical_vectors(case))
        + "\ntran ",
        1,
    )


def read_flags(log, case):
    rows = re.findall(
        r"(?ms)^NSSOC_DIV2_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_DIV2_FLAG_END\s*$", log
    )
    expected = identities(case)
    require([name for name, _ in rows] == expected, "Exact 33-HBT flag census/order")
    for name, body in rows:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+(\S+)\s*$", body) == ["1"],
            "Actual native OFF flag or device identity differs",
        )
    return dict.fromkeys(expected, 1)


def initial_op(path, case):
    lines = [line for line in Path(path).read_text().splitlines() if line.strip()]
    names = electrical_vectors(case)
    require(len(lines) == 2, "Exactly one native OP row required")
    require(lines[0].split()[1:] == names, "Exact native OP vectors required")
    values = list(map(float, lines[1].split()))
    require(
        len(values) == len(names) + 1 and all(math.isfinite(v) for v in values),
        "Nonfinite or incomplete OP",
    )
    require(
        max(map(abs, values[1:])) <= 1e-10, "Initial electrical/thermal OP is not zero"
    )
    return dict(zip(names, values[1:]))


def accepted(row):
    return (
        row.get("zero_initial_op") is True
        and row.get("flags_verified") is True
        and old.expected_result(row)
    )


def run(parent, output, pilot=False):
    parent, output = Path(parent).resolve(), Path(output).resolve()
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output",
    )
    verify_vco()
    require(
        old.sha(parent / "result.json") == PARENT,
        "Exact original limited capture required",
    )
    prior = json.loads((parent / "result.json").read_text())
    require(
        [x["case"] for x in prior["cases"]] == old.cases(False),
        "Complete original case census",
    )
    require(prior["limits"] == old.LIMITS, "No changed engineering limits")
    pins = dict(prior["inputs"])
    pins.update(prior["compiled_models"])
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                parent / "result.json",
                VCO,
                CIRCUIT,
                Path(previous.__file__).resolve(),
                Path(__file__).resolve(),
            )
        }
    )
    for path, expected in pins.items():
        require(old.sha(Path(path)) == expected, "Input changed: " + path)
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    require(len(runtime) == len(models) == 1, "Unique pinned runtime/models required")
    osdi = [Path(p) for p in prior["compiled_models"]]
    cases = [c for c in old.cases(False) if not pilot or c["name"] in PILOT]
    output.mkdir()
    (output / "spinit").write_text(
        "* Explicit native models and zero-source startup.\nset num_threads=1\n"
    )
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        pilot=pilot,
        limits=old.LIMITS,
        preserved_prior_status=prior["status"],
        startup_reference=STARTUP_REFERENCE,
        unchanged_divider_and_latch=True,
        conditioner_min_peak_v=CONDITIONER_MIN_PEAK_V,
        actual_hbt_count=33,
        actual_resistor_count=22,
        imported_module_globals_unchanged=True,
        native_vco_limiter_revision=True,
        no_uic_ic_nodeset_or_equation_changes=True,
        physical_power_sequencer=False,
        full_pvt_qualification=False,
        pll_implemented=False,
        cdr_implemented=False,
        scope="Separate finite four-native-rppd conditioned VCO-v2/divider experiment. Native OFF is an initial Newton flag; actual foundry equations remain enabled during the unchanged zero-source ramp. No layout, PLL, CDR or PCIe qualification.",
    )

    def save():
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    def bound():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    save()
    try:
        for case in cases:
            folder = output / case["name"]
            folder.mkdir()
            for p in (VCO, old.LATCH, CIRCUIT):
                shutil.copyfile(p, folder / p.name)
            (folder / old.CIRCUIT.name).write_text(old.circuit(case))
            (folder / "bench.cir").write_text(deck(case, models[0], osdi))
            row = dict(case=case, command=[str(runtime[0]), "-n", "-b", "bench.cir"])
            result["cases"].append(row)
            save()
            with (folder / "run.log").open("w") as log:
                try:
                    execution = subprocess.run(
                        row["command"],
                        cwd=folder,
                        env={**os.environ, "SPICE_SCRIPTS": str(output)},
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=180,
                        preexec_fn=bound,
                    )
                    row["returncode"] = execution.returncode
                except subprocess.TimeoutExpired:
                    row.update(returncode=None, execution_failure="timeout")
            log = (folder / "run.log").read_text()
            row["numerical"] = old.diagnostics(log)
            extra = [
                s
                for s in log.splitlines()
                if re.search(
                    r"(?i)\b(?:fatal|failed|infinity|infinite)\b|no such vector", s
                )
            ]
            row["numerical"]["lines"] += extra
            row["numerical"]["clean"] &= not extra
            try:
                require(row.get("returncode") == 0, "Native execution did not succeed")
                row["flags_observed"] = read_flags(log, case)
                row["flags_verified"] = True
                row["initial_op"] = initial_op(folder / "initial-op.dat", case)
                row["zero_initial_op"] = True
                row["measurement"] = measure(read_wave(folder / "wave.dat", case), case)
            except (ValueError, KeyError, OSError, StopIteration) as exc:
                row["execution_failure"] = row.get("execution_failure", repr(exc))
            row["expected_outcome_observed"] = accepted(row)
            wave = folder / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                with (
                    wave.open("rb") as src,
                    gzip.open(folder / "wave.dat.gz", "wb") as dst,
                ):
                    shutil.copyfileobj(src, dst)
                wave.unlink()
            row["outputs"] = {
                p.name: old.sha(p) for p in folder.iterdir() if p.is_file()
            }
            save()
            print(
                case["name"],
                row["expected_outcome_observed"],
                row.get("execution_failure"),
                flush=True,
            )
        for path, expected in pins.items():
            require(
                old.sha(Path(path)) == expected, "Native input changed during execution"
            )
        result["complete_inputs_rechecked"] = True
        good = all(r["expected_outcome_observed"] for r in result["cases"])
        nominal = next(
            r for r in result["cases"] if r["case"]["name"] == "nominal"
        ).get("measurement", {})
        result["nominal_input_range_pass"] = (
            old.LIMITS["nominal_input_min_hz"]
            <= (nominal.get("input_frequency_hz") or 0)
            <= old.LIMITS["nominal_input_max_hz"]
        )
        good &= result["nominal_input_range_pass"]
        if not pilot:
            half = next(
                r for r in result["cases"] if r["case"]["name"] == "half_step"
            ).get("measurement", {})
            a, b = nominal.get("output_frequency_hz"), half.get("output_frequency_hz")
            result["half_step_frequency_relative_delta"] = (
                abs(a / b - 1) if a and b else None
            )
            good &= (
                result["half_step_frequency_relative_delta"] is not None
                and result["half_step_frequency_relative_delta"] < 0.001
            )
        result["status"] = (
            "PASS_FINITE_CONDITIONED_DIV2_SCREEN" if good else "FAIL_PRESERVED"
        )
    except BaseException as exc:
        result.update(status="ERROR", error=repr(exc))
    finally:
        save()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    result = run(args.parent, args.out, args.pilot)
    print(result["status"])
    return 0 if result["status"] == "PASS_FINITE_CONDITIONED_DIV2_SCREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
