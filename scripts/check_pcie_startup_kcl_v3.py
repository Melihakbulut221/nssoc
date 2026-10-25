#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent terminal-current KCL witness for the native zero-start protocol."""

import argparse
import json
import lzma
import math
import shutil
from pathlib import Path
import re

import diagnose_pcie_zero_start_v3 as d

s = d.s
SETTLE_S = 1e-6
STEP_S = 1e-10
KCL_RAMP_S = 1e-7
KCL_MAX_A = 1e-9
SOURCES = {
    "vdd": "avdd",
    "vsamp": "savdd",
    "vcm": "cm",
    "vp": "sp",
    "vn": "sn",
    "vscp": "scp0",
    "vscn": "scn0",
}
PASSIVES = {
    "rsp": ("sp", "ip"),
    "rsn": ("sn", "inn"),
    "rcp": ("scp0", "scp"),
    "rcn": ("scn0", "scn"),
    "cp": ("op", "0"),
    "cn": ("on", "0"),
    "cqp": ("qp", "0"),
    "cqn": ("qn", "0"),
}


def instrumentation():
    """Only zero-volt series ammeters; contracting them recovers exact originals."""
    definitions, texts, original_lines = {}, {}, {}
    for path in (s.rx.NETLIST, s.NETLIST):
        current, output = None, []
        for line in path.read_text().splitlines(keepends=True):
            words = line.split()
            if words and words[0].lower() == ".subckt":
                current = words[1].lower()
                d.require(current not in definitions, "Duplicate subcircuit")
                definitions[current] = dict(
                    ports=[w.lower() for w in words[2:]], devices=[]
                )
            if current and words and words[0].startswith("X"):
                model_index = next(
                    (
                        i
                        for i, w in enumerate(words)
                        if w.lower() in ("npn13g2", "rsil", "rppd", "nssoc_cml_latch")
                    ),
                    None,
                )
                d.require(model_index is not None, "Unexpected native device")
                model, terminals = (
                    words[model_index].lower(),
                    [w.lower() for w in words[1:model_index]],
                )
                definitions[current]["devices"].append(
                    dict(name=words[0].lower(), model=model, terminals=terminals)
                )
                if model != "nssoc_cml_latch":
                    d.require(
                        len(terminals) == (4 if model == "npn13g2" else 3),
                        "Native terminal count differs",
                    )
                    probes = [
                        f"zp_{words[0].lower()}_{i}" for i in range(len(terminals))
                    ]
                    for old, new in zip(words[1:model_index], probes):
                        output.append(f"V{new} {old} {new} 0\n")
                    changed = " ".join([words[0], *probes, *words[model_index:]]) + "\n"
                    output.append(changed)
                    original_lines[changed] = line
                    continue
            output.append(line)
            if words and words[0].lower() == ".ends":
                current = None
        text = "".join(output)
        restored = "".join(
            original_lines.get(line, line)
            for line in text.splitlines(keepends=True)
            if not line.startswith("Vzp_")
        )
        d.require(
            restored == path.read_text(),
            "Zero-volt ammeter contraction does not reproduce frozen source",
        )
        texts[path.name] = text
    leaves = []

    def visit(name, path, mapping):
        definition = definitions[name]

        def node(n):
            return "0" if n == "0" else mapping.get(n, path + "." + n)

        for device in definition["devices"]:
            terms = [node(n) for n in device["terminals"]]
            if device["model"] in definitions:
                visit(
                    device["model"],
                    path + "." + device["name"],
                    dict(zip(definitions[device["model"]]["ports"], terms)),
                )
            else:
                leaves.append(
                    dict(
                        path=path + "." + device["name"],
                        model=device["model"],
                        terminals=terms,
                        probes=[
                            "i(v." + path + ".vzp_" + device["name"] + f"_{i})"
                            for i in range(len(terms))
                        ],
                    )
                )

    visit(
        "nssoc_rx_hbt_rsil_v2",
        "xrx",
        dict(
            zip(
                definitions["nssoc_rx_hbt_rsil_v2"]["ports"],
                "ip inn op on avdd 0 0 ref cm".split(),
            )
        ),
    )
    visit(
        "nssoc_rx_sampler_hbt",
        "xsamp",
        dict(
            zip(
                definitions["nssoc_rx_sampler_hbt"]["ports"],
                "op on qp qn scp scn savdd 0 0 sr".split(),
            )
        ),
    )
    d.require(
        len(leaves) == 35 and sum(x["model"] == "npn13g2" for x in leaves) == 19,
        "Native device census differs",
    )
    d.require(
        sum(len(x["probes"]) for x in leaves) == 124, "Native probe census differs"
    )
    return texts, leaves


def constant_deck(case, models, osdi, leaves):
    text = d.transform(s.deck(case, models, osdi), "sampler")
    # The separate KCL experiment freezes data/clock after the independently defined 100 ns power ramp;
    # A 100 ps maximum step resolves this slower static ramp;
    # it does not replace the independent 8 GT/s functional campaign.
    for source in ("VP", "VN", "VSCP", "VSCN"):
        match = re.search(r"^" + source + r" (\S+) 0 PWL\(([^)]+)\)", text, re.M)
        d.require(match is not None, "Missing real native source")
        values = match[2].replace("+", " ").split()
        d.require(
            list(map(float, values[:3])) == [0, 0, d.RAMP_S], "Source startup differs"
        )
        text = (
            text[: match.start()]
            + source
            + " "
            + match[1]
            + " 0 PWL(0 0 1n "
            + values[3]
            + ")"
            + text[match.end() :]
        )
    text = text.replace("PWL(0 0 1n ", "PWL(0 0 1e-07 ").replace(
        "PWL(0 0 1e-09 ", "PWL(0 0 1e-07 "
    )
    observed = [
        *s.VECTORS,
        *[v for item in leaves for v in item["probes"]],
        *[f"@{name}[i]" for name in PASSIVES],
        *["v(" + n + ")" for n in ("avdd", "savdd", "cm", "sp", "sn", "scp0", "scn0")],
        *["v(" + n + ".t)" for n in s.HBT],
    ]
    text = d.replace_one(text, r"^save .+$", "save " + " ".join(observed))
    text = d.replace_one(
        text,
        r"^wrdata initial-op.dat .+$",
        "wrdata initial-op.dat " + " ".join(observed),
    )
    text = d.replace_one(
        text, r"^tran .+$", f"tran {STEP_S:.12g} {SETTLE_S:.12g} 0 {STEP_S:.12g}"
    )
    text = d.replace_one(
        text, r"^wrdata wave.dat .+$", "wrdata wave.dat " + " ".join(observed)
    )
    return text, observed


def analyze(table, leaves, case):
    d.require(
        leaves == instrumentation()[1],
        "Exact terminal ownership and probe coverage required",
    )
    d.require(
        all(
            len(v) == len(table["time"]) and all(map(math.isfinite, v))
            for v in table.values()
        ),
        "Nonfinite or incomplete native KCL vectors",
    )
    d.require(
        len(table["time"]) >= 1000 and abs(table["time"][-1] - SETTLE_S) < 1e-15,
        "Incomplete actual settled transient",
    )
    nodes = {
        "0",
        *SOURCES.values(),
        *[n for p in PASSIVES.values() for n in p],
        *[n for leaf in leaves for n in leaf["terminals"]],
    }
    d.require(
        abs(table["time"][0]) <= 1e-15
        and all(
            0 < b - a <= STEP_S * 1.01 for a, b in zip(table["time"], table["time"][1:])
        ),
        "Native settled waveform time coverage differs",
    )
    samples = []
    for index in range(len(table["time"]) - 100, len(table["time"])):
        residual = dict.fromkeys(nodes, 0.0)

        def add(a, b, current):
            residual[a] += current
            residual[b] -= current

        for leaf in leaves:
            for node, probe in zip(leaf["terminals"], leaf["probes"]):
                residual[node] += table[probe][index]
        for source, node in SOURCES.items():
            add(node, "0", table[f"i({source})"][index])
        for name, (a, b) in PASSIVES.items():
            add(a, b, table[f"@{name}[i]"][index])
        add("avdd", "ref", case["rx_reference_a"])
        add("savdd", "sr", case["reference_a"])
        samples.append(residual)
    maximum = max(abs(value) for row in samples for value in row.values())
    step_change = max(
        abs(values[-1] - values[-2])
        for key, values in table.items()
        if key.startswith("v(")
    )
    active = {
        n: min(table[f"@q.{n}.qnpn13g2[ic]"][-100:])
        for n in ("xrx.xtail", "xsamp.xm.xt", "xsamp.xs.xt")
    }
    return dict(
        active_tail_minima_a=active,
        pass_active=all(x >= s.LIMITS["min_tail_collector_a"] for x in active.values()),
        maximum_kcl_residual_a=maximum,
        kcl_limit_a=KCL_MAX_A,
        last_kcl_a=samples[-1],
        nodes=len(nodes),
        native_terminal_probes=124,
        settled_samples=100,
        final_time_s=table["time"][-1],
        maximum_last_voltage_step_v=step_change,
        pass_kcl=maximum <= KCL_MAX_A,
        pass_settling=step_change < 1e-7,
    )


def run(pdk, runtime, osdi, output):
    pdk, runtime, osdi, output = map(
        lambda p: Path(p).resolve(), (pdk, runtime, osdi, output)
    )
    d.require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded output required",
    )
    pins = d.input_pins(pdk, runtime, osdi)
    pins[str(Path(__file__).resolve())] = s.rx.tx.sha(Path(__file__))
    case = next(c for c in s.cases(False) if c["name"] == d.PILOT[-1])
    texts, leaves = instrumentation()
    output.mkdir()
    for name, text in texts.items():
        (output / name).write_text(text)
    text, observed = constant_deck(case, pdk / "libs.tech/ngspice/models", osdi, leaves)
    (output / "bench.cir").write_text(text)
    result = dict(
        status="RUNNING",
        case=case,
        ramp_s=KCL_RAMP_S,
        maximum_step_s=STEP_S,
        settle_s=SETTLE_S,
        source_sha256=pins,
        source_contraction_exact=True,
        leaf_map=leaves,
        scope="Separate static-after-ramp KCL experiment, with 124 zero-volt series ammeters. Frozen v2 device parameters and model equations unchanged. The full dynamic function uses uninstrumented circuits in the other campaign.",
    )
    try:
        result["execution"] = s.rx.execute(
            [str(runtime), "-n", "-b", "bench.cir"], output, output / "run.log"
        )
        log = (output / "run.log").read_text()
        result["diagnostics"] = d.diagnostics(log)
        result["flags_observed"] = d.flags_observed(log, "sampler", "zero_off")
        result["initial_op"] = d.initial_op(output / "initial-op.dat", observed)
        table = s.rx.rx.read_table(output / "wave.dat", ["time", *observed])
        result["analysis"] = analyze(table, leaves, case)
        result["wave_sha256"] = s.rx.tx.sha(output / "wave.dat")
        d.require(
            all(s.rx.tx.sha(Path(p)) == h for p, h in pins.items()), "Source changed"
        )
        result["status"] = (
            "PASS_NATIVE_SETTLED_KCL"
            if result["analysis"]["pass_kcl"]
            and result["analysis"]["pass_settling"]
            and result["analysis"]["pass_active"]
            and max(map(abs, result["initial_op"].values())) <= 1e-10
            and result["diagnostics"]["numerical_clean"]
            else "FAIL_PRESERVED"
        )
    finally:
        if (output / "wave.dat").exists():
            with (
                (output / "wave.dat").open("rb") as src,
                lzma.open(output / "wave.dat.xz", "wb", preset=1) as dst,
            ):
                shutil.copyfileobj(src, dst)
            (output / "wave.dat").unlink()
        result["output_sha256"] = {p.name: s.rx.tx.sha(p) for p in output.iterdir()}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("pdk", "ngspice", "osdi", "out"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    r = run(a.pdk, a.ngspice, a.osdi, a.out)
    print(r["status"], r.get("analysis"))
    return int(r["status"] != "PASS_NATIVE_SETTLED_KCL")


if __name__ == "__main__":
    raise SystemExit(main())
