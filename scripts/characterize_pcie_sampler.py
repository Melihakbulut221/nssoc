#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Transistor RX+CML sampler experiment; external clock, no recovered-clock claim."""

import argparse
from bisect import bisect_left, bisect_right
import gzip
import itertools
import json
from pathlib import Path
import shutil

import characterize_pcie_rx_v2 as rx
import review_pcie_rx_v2 as diagnostics

ROOT = rx.ROOT
NETLIST = ROOT / "hw/soc/analog/pcie/rx_sampler_hbt.spice"
UI, START, BITS = 125e-12, 2e-9, 127
STOP = START + (BITS + 2) * UI
LIMITS = dict(
    min_margin_v=0.1,
    min_vce_v=0.4,
    max_vce_v=1.6,
    max_collector_a_per_emitter=0.003,
    min_tail_collector_a=0.0005,
    max_clock_to_valid_s=0.3 * UI,
)
RX_PIN = "d02827087e0cb43f447fc46fda05dbd23dcee13ad68755fd31ba738404332a4e"
FIXED = {
    "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice": RX_PIN,
    "scripts/characterize_pcie_rx_v2.py": "087ac0d41235f11fb64c532da0d4d9f13f85deea596652951d83d365e51ef1ef",
    "scripts/characterize_pcie_rx.py": "74d192ab7c95b8113cafbc0202f219c52f2ae9a1e07b410ba72b7512cceb4a99",
    "scripts/characterize_pcie_tx.py": "fdd6d927350d459ee68b7491047d0ceb976868bf93d6ff144a4339719d472f0c",
    "scripts/characterize_pcie_tx_rsil.py": "0028468eda30911b157bc650c78745c43a36f52437da61a1cfcc40972301e92e",
    "scripts/review_pcie_rx_v2.py": "0d3548490df7f908722106624002713528e2d578b2b994660ec836d9bb4237cf",
    "scripts/review_pcie_rx.py": "93485e70a1a2fd72e5cc76542f48b5fb27bf580edfbb463217348fac9fce8417",
}
RUNTIMES = {
    "820658317b0b54035208da41936fd6871ce924036e5ea4113a4168b821b7fc45": "42",
    "eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8": "47",
}
OPENVAF_PIN = "6918195bc6cca54016095923bea190f7a1d96dd8b062104c602e8c28578cb5e3"
HBT = {
    "xrx.xp": ("on", "ip", "xrx.tail", 4),
    "xrx.xn": ("op", "inn", "xrx.tail", 4),
    "xrx.xtail": ("xrx.tail", "ref", "0", 4),
    "xrx.xref": ("ref", "ref", "0", 1),
    "xsamp.xref": ("sr", "sr", "0", 1),
}
for stage in ("m", "s"):
    prefix = "xsamp.x" + stage
    qp, qn = ("xsamp.mp", "xsamp.mn") if stage == "m" else ("qp", "qn")
    dp, dn = ("xsamp.lp", "xsamp.ln") if stage == "m" else ("xsamp.mp", "xsamp.mn")
    cp, cn = ("scn", "scp") if stage == "m" else ("scp", "scn")
    for name, collector, base, emitter, nx in (
        ("dp", qn, dp, prefix + ".se", 2),
        ("dn", qp, dn, prefix + ".se", 2),
        ("lp", qn, qp, prefix + ".he", 2),
        ("ln", qp, qn, prefix + ".he", 2),
        ("cs", prefix + ".se", cp, prefix + ".te", 4),
        ("ch", prefix + ".he", cn, prefix + ".te", 4),
        ("t", prefix + ".te", "sr", "0", 4),
    ):
        HBT[prefix + ".x" + name] = (collector, base, emitter, nx)
THERMAL = ["xrx.x" + n for n in ("rp", "rn", "rtp", "rtn")]
THERMAL += ["xsamp.x" + n for n in ("ip", "in", "bp", "bn")]
THERMAL += [
    "xsamp.x" + s + ".x" + n for s in ("m", "s") for n in ("rp", "rn", "bs", "bh")
]
NODES = sorted({n for c, b, e, _ in HBT.values() for n in (c, b, e)} - {"0"})
VECTORS = [
    *["v(" + n + ")" for n in NODES],
    "i(vdd)",
    "i(vsamp)",
    "i(vcm)",
    "i(vp)",
    "i(vn)",
    "i(vscp)",
    "i(vscn)",
    *["@q." + n + ".qnpn13g2[ic]" for n in HBT],
    *["v(" + n + ".dt)" for n in THERMAL],
]


def cases(quick=False):
    base = dict(
        hbt="hbt_typ",
        resistor="res_typ",
        temp=27,
        rx_supply=1.8,
        supply=2.5,
        reference_a=0.0005,
        rx_reference_a=0.00075,
        vcm=1.36,
        amplitude_v=0.08,
        cap_f=150e-15,
        rx_cap_f=5e-15,
        clock_vcm=1.29,
        clock_amplitude_v=0.15,
        clock_rise_s=5e-12,
        clock_source_ohm=10,
        phase_ui=0.5,
        step_s=1e-12,
        mode="prbs",
        fault=None,
        role="required",
    )
    matrix = (
        [("hbt_typ", "res_typ", 27, 1.8)]
        if quick
        else itertools.product(
            ("hbt_typ", "hbt_bcs", "hbt_wcs"),
            ("res_typ", "res_bcs", "res_wcs"),
            (-40, 27, 125),
            (1.71, 1.8, 1.89),
        )
    )
    result = [
        dict(
            base,
            name=f"{h}_{r}_{t}_{v}",
            hbt=h,
            resistor=r,
            temp=t,
            rx_supply=v,
            supply=2.5 * v / 1.8,
        )
        for h, r, t, v in matrix
    ]
    extras = [
        ("alternating", dict(mode="alternating")),
        ("half_timestep", dict(step_s=0.5e-12)),
        ("load_100fF", dict(cap_f=100e-15)),
        ("source_60mV", dict(amplitude_v=0.06)),
        ("clock_rise_10ps", dict(clock_rise_s=10e-12, role="extension")),
        ("clock_source_50ohm", dict(clock_source_ohm=50, role="extension")),
        ("rx_interconnect_150fF", dict(rx_cap_f=150e-15, role="extension")),
        (
            "independent_low_rx_high_sampler",
            dict(rx_supply=1.71, supply=2.625, role="extension"),
        ),
        (
            "independent_high_rx_low_sampler",
            dict(rx_supply=1.89, supply=2.375, role="extension"),
        ),
        ("no_bias", dict(reference_a=0, fault="no_bias")),
        ("clock_stopped", dict(fault="clock_stopped")),
        ("clock_common_only", dict(clock_amplitude_v=0, fault="clock_common_only")),
        ("swapped_output", dict(fault="swapped_output")),
        ("no_regeneration", dict(fault="no_regeneration")),
        ("overload", dict(cap_f=100e-12, fault="overload")),
    ]
    result.extend(dict(base, name=n, **d) for n, d in extras)
    phases = (0, 0.5, 1) if quick else [i / 20 for i in range(-2, 23)]
    result.extend(
        dict(base, name=f"aperture_{i:02d}", phase_ui=p, role="aperture")
        for i, p in enumerate(phases)
    )
    return result


def sequence(case):
    return (
        rx.tx.prbs7(count=BITS)
        if case["mode"] == "prbs"
        else [i % 2 for i in range(BITS)]
    )


def pwl(bits, case, inverted=False):
    def level(bit):
        return case["vcm"] + case["amplitude_v"] * (1 if bool(bit) != inverted else -1)

    points = [(0, level(bits[0]))]
    for i in range(1, BITS):
        if bits[i] != bits[i - 1]:
            points.extend(
                [
                    (START + i * UI, level(bits[i - 1])),
                    (START + i * UI + 10e-12, level(bits[i])),
                ]
            )
    points.append((STOP, level(bits[-1])))
    return "PWL(\n+ " + "\n+ ".join(f"{t:.12g} {v:.12g}" for t, v in points) + ")"


def circuit(case):
    text = NETLIST.read_text()
    if case["fault"] == "no_regeneration":
        for a, b in (
            ("XLP qn qp he", "XLP qn ref he"),
            ("XLN qp qn he", "XLN qp ref he"),
        ):
            if text.count(a) != 1:
                raise ValueError("Native feedback mutation anchor differs")
            text = text.replace(a, b)
    return text


def deck(case, models, osdi):
    bits = sequence(case)
    c = case
    output = "qn qp" if c["fault"] == "swapped_output" else "qp qn"
    low, high = (
        c["clock_vcm"] - c["clock_amplitude_v"],
        c["clock_vcm"] + c["clock_amplitude_v"],
    )
    rise = c["clock_rise_s"]
    delay = START + c["phase_ui"] * UI - rise / 2
    if delay <= 0 or rise <= 0 or rise >= UI / 2:
        raise ValueError("Clock timing outside experiment")

    def clock(a, b):
        return f"PULSE({a:.12g} {b:.12g} {delay:.12g} {rise:.12g} {rise:.12g} {UI / 2 - rise:.12g} {UI:.12g})"

    cp, cn = (
        (str(low), str(high))
        if c["fault"] == "clock_stopped"
        else (clock(low, high), clock(high, low))
    )
    lines = [
        "NSSOC native RX plus clocked CML sampler experiment",
        f'.lib "{models}/cornerHBT.lib" {c["hbt"]}',
        f'.lib "{models}/cornerRES.lib" {c["resistor"]}',
        f'.include "{rx.NETLIST.name}"',
        f'.include "{NETLIST.name}"',
        f".temp {c['temp']}",
        ".options reltol=1e-4 abstol=1e-12",
        f"VDD avdd 0 {c['rx_supply']}",
        f"VSAMP savdd 0 {c['supply']}",
        f"VCM cm 0 {c['vcm']}",
        f"IREF avdd ref {c['rx_reference_a']}",
        f"ISAMP savdd sr {c['reference_a']}",
        "VP sp 0 " + pwl(bits, c),
        "VN sn 0 " + pwl(bits, c, True),
        "RSP sp ip 50",
        "RSN sn inn 50",
        f"CP op 0 {c['rx_cap_f']}",
        f"CN on 0 {c['rx_cap_f']}",
        "XRX ip inn op on avdd 0 0 ref cm nssoc_rx_hbt_rsil_v2",
        f"VSCP scp0 0 {cp}",
        f"VSCN scn0 0 {cn}",
        f"RCP scp0 scp {c['clock_source_ohm']}",
        f"RCN scn0 scn {c['clock_source_ohm']}",
        f"XSAMP op on {output} scp scn savdd 0 0 sr nssoc_rx_sampler_hbt",
        f"CQP qp 0 {c['cap_f']}",
        f"CQN qn 0 {c['cap_f']}",
        ".nodeset v(ref)=.85 v(xrx.tail)=.5 v(op)=1.65 v(on)=1.65",
        ".control",
        f"pre_osdi {osdi}",
        "set wr_singlescale",
        "set wr_vecnames",
        "set numdgt=12",
        "save " + " ".join(VECTORS),
        f"tran {c['step_s']:.12g} {STOP:.12g} 0 {c['step_s']:.12g}",
        "wrdata wave.dat " + " ".join(VECTORS),
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def crossings(times, values, rising=None):
    result = []
    for i in range(1, len(times)):
        a, b = values[i - 1], values[i]
        direction = 1 if a <= 0 < b else -1 if a >= 0 > b else 0
        if direction and (rising is None or (direction == 1) == rising):
            result.append(times[i - 1] + (times[i] - times[i - 1]) * -a / (b - a))
    return result


def measure(path, case):
    data = rx.rx.read_table(path, ["time", *VECTORS])
    ts = data["time"]
    if (
        ts[0] > 1e-15
        or ts[-1] < STOP - 1e-15
        or any(b <= a or b - a > case["step_s"] * 1.01 for a, b in zip(ts, ts[1:]))
    ):
        raise ValueError("Incomplete native time coverage")
    begin = bisect_left(ts, START + 16 * UI)

    def value(n):
        return data["v(" + n + ")"] if n != "0" else [0.0] * len(ts)

    samples = []
    continuous = []
    setup, hold, delays, edges = [], [], [], []
    out = [p - n for p, n in zip(value("qp"), value("qn"))]
    clock = [p - n for p, n in zip(value("scp"), value("scn"))]
    clock_edges = crossings(ts, clock, True)
    actual_data = [p - n for p, n in zip(value("xsamp.lp"), value("xsamp.ln"))]
    data_edges = crossings(ts, actual_data)
    bits = sequence(case)
    for i in range(16, BITS - 1):
        expected = START + (i + case["phase_ui"]) * UI
        hits = [e for e in clock_edges if abs(e - expected) < 0.2 * UI]
        if len(hits) != 1:
            continue
        edge = hits[0]
        edges.append(edge)
        sign = 1 if bits[i] else -1
        samples.extend(
            rx.tx.interpolate(ts, out, edge + p * UI) * sign for p in (0.3, 0.6, 0.9)
        )
        a, b = bisect_left(ts, edge + 0.3 * UI), bisect_right(ts, edge + 0.9 * UI)
        continuous.extend(x * sign for x in out[a:b])
        valid = [
            ts[k] - edge
            for k in range(bisect_left(ts, edge), b)
            if out[k] * sign >= LIMITS["min_margin_v"]
        ]
        delays.append(min(valid) if valid else UI)
        if bits[i] != bits[i - 1]:
            intended = START + i * UI
            hits = [t for t in data_edges if -0.1 * UI < t - intended < 0.5 * UI]
            if len(hits) == 1:
                setup.append(edge - hits[0])
        if bits[i + 1] != bits[i]:
            intended = START + (i + 1) * UI
            hits = [t for t in data_edges if -0.1 * UI < t - intended < 0.5 * UI]
            if len(hits) == 1:
                hold.append(hits[0] - edge)
    devices = {}
    for name, (cn, bn, en, nx) in HBT.items():
        # The negative controls change real native wiring, so diagnostic
        # voltages must follow that wiring too, not the positive schematic.
        if case["fault"] == "swapped_output" and name.startswith("xsamp."):
            swap = {"qp": "qn", "qn": "qp"}
            cn, bn, en = (swap.get(n, n) for n in (cn, bn, en))
        if case["fault"] == "no_regeneration" and name.endswith((".xlp", ".xln")):
            bn = "sr"
        c, b, e = value(cn), value(bn), value(en)
        current = data["@q." + name + ".qnpn13g2[ic]"][begin:]
        vce = [x - y for x, y in zip(c[begin:], e[begin:])]
        vbe = [x - y for x, y in zip(b[begin:], e[begin:])]
        devices[name] = dict(
            nx=nx,
            min_vce_v=min(vce),
            max_vce_v=max(vce),
            min_vbe_v=min(vbe),
            max_vbe_v=max(vbe),
            min_collector_a=min(current),
            max_abs_collector_a=max(map(abs, current)),
        )

    def average(name):
        y = data[name]
        return sum(
            (y[j] + y[j - 1]) * 0.5 * (ts[j] - ts[j - 1])
            for j in range(begin + 1, len(ts))
        ) / (ts[-1] - ts[begin])

    all_margins = samples + continuous
    margin = min(all_margins) if all_margins else None
    check = dict(
        clock_census=len(edges) == BITS - 17,
        margin=margin is not None and margin >= LIMITS["min_margin_v"],
        headroom=all(d["min_vce_v"] >= LIMITS["min_vce_v"] for d in devices.values()),
        vce_maximum=all(
            d["max_vce_v"] <= LIMITS["max_vce_v"] for d in devices.values()
        ),
        current_density=all(
            d["max_abs_collector_a"] < d["nx"] * LIMITS["max_collector_a_per_emitter"]
            for d in devices.values()
        ),
        active_tail=all(
            devices[n]["min_collector_a"] >= LIMITS["min_tail_collector_a"]
            for n in ("xrx.xtail", "xsamp.xm.xt", "xsamp.xs.xt")
        ),
        clock_to_valid=bool(delays) and max(delays) <= LIMITS["max_clock_to_valid_s"],
    )
    return dict(
        rows=len(ts),
        captured_bits=len(edges),
        signed_samples=len(samples),
        continuous_hold_points=len(continuous),
        min_signed_margin_v=margin,
        sign_errors=sum(x <= 0 for x in all_margins),
        maximum_clock_to_first_valid_s=max(delays) if delays else None,
        minimum_observed_setup_s=min(setup) if setup else None,
        minimum_observed_hold_s=min(hold) if hold else None,
        setup_transitions=len(setup),
        hold_transitions=len(hold),
        actual_clock_edges=edges,
        devices=devices,
        rx_supply_power_w=-average("i(vdd)") * case["rx_supply"],
        sampler_supply_power_w=-average("i(vsamp)") * case["supply"],
        common_mode_supply_power_w=-average("i(vcm)") * case["vcm"],
        peak_clock_source_current_a=max(
            abs(x) for n in ("i(vscp)", "i(vscn)") for x in data[n][begin:]
        ),
        peak_input_source_current_a=max(
            abs(x) for n in ("i(vp)", "i(vn)") for x in data[n][begin:]
        ),
        max_resistor_temperature_rise_k=max(
            x for n in THERMAL for x in data["v(" + n + ".dt)"][begin:]
        ),
        checks=check,
        screen_pass=all(check.values()),
    )


def timestep_sensitivity(entries):
    names = [e["case"]["name"] for e in entries]
    if names.count("hbt_typ_res_typ_27_1.8") != 1 or names.count("half_timestep") != 1:
        raise ValueError("Exactly one nominal and half-timestep receipt required")
    measured = {e["case"]["name"]: e["measurement"] for e in entries}
    base, half = measured["hbt_typ_res_typ_27_1.8"], measured["half_timestep"]
    margin = abs(base["min_signed_margin_v"] - half["min_signed_margin_v"])
    power = abs(base["sampler_supply_power_w"] / half["sampler_supply_power_w"] - 1)
    return dict(
        margin_difference_v=margin,
        power_relative_difference=power,
        screen_pass=margin < 0.001 and power < 0.002,
        scope="Two native maximum timesteps, not extrapolated convergence.",
    )


def disposition(entries):
    required = [e for e in entries if e["case"]["role"] == "required"]
    passed = bool(required) and all(
        e.get("expected_outcome_observed") is True for e in required
    )
    passed = passed and timestep_sensitivity(entries)["screen_pass"]
    clean = all(
        e["numerical_diagnostics"]["numerical_clean"]
        for e in required
        if not e["case"]["fault"]
    )
    return (
        "FAIL_SAMPLER_REQUIRED_SCREEN"
        if not passed
        else "SAMPLER_MEASUREMENT_PASS_NUMERICAL_RESIDUAL"
        if not clean
        else "PASS_SAMPLER_LIMITED_SCREEN"
    ), clean


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
    models = args.pdk.resolve() / "libs.tech/ngspice/models"
    pins = {str(ROOT / p): h for p, h in FIXED.items()}
    pins.update({str(models / n): h for n, h in rx.tx.MODEL_HASHES.items()})
    pins.update(
        {str(models.parent.parent / n): h for n, h in rx.resistor.RES_HASHES.items()}
    )
    if any(rx.tx.sha(Path(p)) != h for p, h in pins.items()):
        ap.error("Frozen source/model input changed")
    runtime_sha = rx.tx.sha(args.ngspice.resolve())
    if runtime_sha not in RUNTIMES or rx.tx.sha(args.openvaf.resolve()) != OPENVAF_PIN:
        ap.error("Unqualified native runtime/compiler bytes")
    pins.update(
        {
            str(p): rx.tx.sha(p)
            for p in (
                NETLIST,
                Path(__file__).resolve(),
                args.ngspice.resolve(),
                args.openvaf.resolve(),
            )
        }
    )
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        quick=args.quick,
        ui_s=UI,
        bits=BITS,
        limits=LIMITS,
        source_sha256=pins,
        pdk_revision=rx.tx.PDK_REV,
        runtime_version=RUNTIMES[runtime_sha],
        cases=[],
        assumptions=dict(
            external_clock=True,
            recovered_clock=False,
            separate_sampler_supply_v=2.5,
            rx_supply_v=1.8,
            sampler_reference_a=0.0005,
            rx_reference_a=0.00075,
            clock_vcm_v=1.29,
            clock_amplitude_each_v=0.15,
            clock_rise_s=5e-12,
            clock_source_ohm=10,
            substrate_node_v=0,
            physical_tap_rc_simulated=False,
        ),
        scope="15-HBT/12-rppd clocked sampler connected to unchanged native RX v2. Coupled rail PVT matrix plus explicit independent rail extensions. Finite PRBS and deterministic phase sweep; no BER, mismatch, noise, jitter tolerance, recovered clock, PLL, CDR, deserializer, PEX or PCIe qualification.",
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
    )

    def save():
        (out / "result.tmp").write_text(json.dumps(record, indent=2) + "\n")
        (out / "result.tmp").replace(out / "result.json")

    try:
        save()
        osdi = out / "r3_cmc.osdi"
        record["compile"] = rx.execute(
            [
                str(args.openvaf.resolve()),
                str(models.parent.parent / "verilog-a/r3_cmc/r3_cmc.va"),
                "-o",
                str(osdi),
            ],
            out,
            out / "compile.log",
        )
        record["osdi_sha256"] = rx.tx.sha(osdi)
        for case in cases(args.quick):
            dest = out / case["name"]
            dest.mkdir()
            (dest / NETLIST.name).write_text(circuit(case))
            shutil.copyfile(rx.NETLIST, dest / rx.NETLIST.name)
            (dest / "bench.cir").write_text(deck(case, models, osdi))
            entry = dict(case=case)
            record["cases"].append(entry)
            save()
            entry["execution"] = rx.execute(
                [str(args.ngspice.resolve()), "-n", "-b", "bench.cir"],
                dest,
                dest / "run.log",
            )
            entry["measurement"] = measure(dest / "wave.dat", case)
            entry["numerical_diagnostics"] = diagnostics.diagnostics(
                (dest / "run.log").read_text()
            )
            entry["expected_screen_pass"] = (
                None if case["role"] != "required" else case["fault"] is None
            )
            entry["expected_outcome_observed"] = (
                None
                if entry["expected_screen_pass"] is None
                else entry["measurement"]["screen_pass"]
                == entry["expected_screen_pass"]
            )
            entry["wave_sha256"] = rx.tx.sha(dest / "wave.dat")
            with (
                (dest / "wave.dat").open("rb") as src,
                gzip.open(dest / "wave.dat.gz", "wb", compresslevel=1) as dst,
            ):
                shutil.copyfileobj(src, dst)
            (dest / "wave.dat").unlink()
            entry["output_sha256"] = {p.name: rx.tx.sha(p) for p in dest.iterdir()}
            save()
            print(
                case["name"],
                entry["measurement"]["screen_pass"],
                entry["measurement"]["min_signed_margin_v"],
                entry["measurement"]["checks"],
                flush=True,
            )
        if any(rx.tx.sha(Path(p)) != h for p, h in pins.items()):
            raise RuntimeError("Input bytes changed")
        record["source_bytes_unchanged"] = True
        record["timestep_sensitivity"] = timestep_sensitivity(record["cases"])
        record["status"], record["numerical_clean"] = disposition(record["cases"])
        record["full_pvt_matrix_cases"] = 1 if args.quick else 81
    except BaseException as exc:
        record.update(status="ERROR_PRESERVED", error=repr(exc))
        raise
    finally:
        save()
    return (
        0
        if record["status"] == "PASS_SAMPLER_LIMITED_SCREEN"
        else 2
        if record["status"] == "SAMPLER_MEASUREMENT_PASS_NUMERICAL_RESIDUAL"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
