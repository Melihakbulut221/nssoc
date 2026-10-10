#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual 455-device loaded VCO/divider wire prerequisite, not closed full PEX.

Both native metal networks are preserved. Each block's body and wire reference
is independently exposed and grounded only by an explicit bench assumption.
CMOS /20 feedback remains schematic; this is not a closed-loop PLL or PHY.
"""

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
import types
import numpy as np

import build_pcie_clock_div4_v10_tail115_v1_hybrid_v1 as builder
import characterize_pcie_vco_v6_feedback_bias_v2 as previous

core = previous.core
n, stream, require = core.n, core.stream, core.require
ROOT = core.ROOT
ANALOG = ROOT / "hw/soc/analog/pcie"
TOP = "nssoc_pll_feedback_vco_v6_divider_tail115_v1_wire_v1"
CHAIN = ANALOG / "pll_feedback_vco_v6_divider_tail115_v1_wire_v1.spice"
DIVIDER = ROOT / "sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1"
PREVIOUS_SHA = "f084eae8150533acd8d2f788fb6007155f88431610702fad1b7f40e4bb33f30e"
BUILDER_SHA = "f6cc2fcc1d9c8ec14b0e5409a663cc41d9013ceea90f5500d0bda92b90270ea8"
REFERENCE = ANALOG / "clock_div4_hbt_v10.spice"
REFERENCE_PARENT = ANALOG / "clock_div4_hbt_v9.spice"
REFERENCE_PARENT_SHA = "5fc944cb5683dda328e6b3aedd21b2e206f03575a232394e8cb528d280e69c9a"
REFERENCE_SHA = "b3fcfce801776215938cd7130153e5bc43ccf378706b50fcd1138e2af6dfd6b0"
REFERENCE_CAP24 = ANALOG / "clock_div4_hbt_v8.spice"
REFERENCE_CAP24_SHA = "87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc"
REFERENCE_DIV2 = ANALOG / "clock_div2_hbt.spice"
REFERENCE_DIV2_SHA = "1b18a732c7736ad8c9805131c77fe1d5e467364ae8d6a2b7eb07061131cea4d7"
PREVIOUS_REFERENCE_SHA = "49226d5b3a40fc4f8faafbaee3adb5580d8346222a825b79daaddc0358b2c65c"
DIVIDER_PINS = {'hybrid-open.spice': '509f33b89c46d3bde72d7f331462faeb5ae07b33f0daa8146167814ecd96434f', 'composition.json': '524723aa9654adea53e5e892f3c3d6b244001308f3966ea39becf0c6445ebaf6', 'source-native-bijection.json': '0e088f6a7608aa4008304987fd9c1f36318043694f177bbdb08549e17c388613'}
OBS = core.OBS
physical, life = core.physical, core.life
OWN_LIMIT, FLOOR, RECEIPT_RESERVE = core.OWN_LIMIT, core.FLOOR, core.RECEIPT_RESERVE
HYBRID, PINS, SOURCE = core.HYBRID, core.PINS, CHAIN
capture, native_limit = core.capture, core.native_limit


def topology(text):
    expected = [
        f".subckt {TOP} vctrl clearb clkp clkn qp qn fb fbbar vco_avdd div_avdd core_vdd avss sub body_substrate wire_cref div_body_substrate div_wire_cref",
        "XOSC vco_avdd avss clkn clkp sub vctrl body_substrate wire_cref nssoc_vco_local_hybrid_open_v2",
        "XDIV avss clkn clkp div_avdd qn qp sub div_body_substrate div_wire_cref nssoc_clock_div4_v10_tail115_v1_hybrid_open_v1",
        "XFB qp qn clearb fb fbbar div_avdd core_vdd avss sub nssoc_pll_feedback_div20_v2",
        f".ends {TOP}",
    ]
    require([x for x in text.splitlines() if x and not x.startswith("*")] == expected,
            "Exact native VCO and divider wire topology")


def source_correspondence(composition, binding, old_rows):
    old = {r["path"]: r for r in old_rows if r["path"].startswith("xchain.xdiv.")}
    require(len(old) == 73, "All73 original divider schematic primitives")
    require(len(binding["devices"]) == 91 and len(composition["records"]) == 91,
            "All91 actual divider devices")
    by = {r["native_id"]: r for r in composition["records"]}
    source_seen, contacts = set(), []
    public = dict(CLKP="clkp", CLKN="clkn", QP="qp", QN="qn", DIV_AVDD="dvdd", AVSS="0", SUB="0", BULK="0")

    def source_node(value):
        # Compare the old schematic topology only. Actual body stays separate
        # in every emitted native row and at the explicit external boundary.
        return public.get(value, value.lower().replace("div__", "xchain.xdiv.", 1).replace("__", "."))

    for item in binding["devices"]:
        native = by[item["native_id"]]
        require(native["model"] == item["model"], "Bound native model")
        if item["model"] == "ptap1":
            contacts.append(item["source_name"])
            require(item["source_nets"] == ["SUB", "BULK"] and native["native_parameters"] == {"A":4.0,"P":8.0}, "Actual finite substrate contact")
            continue
        path = source_node(item["source_name"])
        require(path in old and path not in source_seen, "Actual source identity bijection")
        source_seen.add(path)
        row = old[path]
        require(row["model"] == native["model"].lower(), "Schematic/native model identity")
        require([source_node(x) for x in item["source_nets"]] == row["nets"], "Original logical terminal topology")
        params = {k.lower():v for k,v in native["simulator_parameters"].items()}
        for k,v in row["params"].items():
            require(k in params and builder.number(params[k]) == builder.number(v), "Original primitive geometry/value")
        extras = {k:v for k,v in params.items() if k not in row["params"]}
        allowed = ({"we":"0.07u","le":"0.9u"} if row["model"] == "npn13g2" else {"ps":"0u","m":"1"} if row["model"] == "rppd" else {})
        require(set(extras) == set(allowed) and all(builder.number(v) == builder.number(allowed[k]) for k,v in extras.items()), "Only native explicit default parameters")
    require(source_seen == set(old) and set(contacts) == {f"TAP{i}" for i in range(18)} and len(contacts) == 18, "Exact73 primitive plus18 contact source census")


def reference_rows(nominal, texts):
    """Bind exact V7→V8→V9 ancestry, then only second-stage reference in V10."""
    require(n.common.sha(REFERENCE) == REFERENCE_SHA, "Exact V10 reference bytes")
    require(n.common.sha(REFERENCE_CAP24) == REFERENCE_CAP24_SHA, "Exact saved Cap24 V8 reference bytes")
    require(n.common.sha(previous.DIVIDER) == PREVIOUS_REFERENCE_SHA, "Exact original V7 reference bytes")
    original = previous.DIVIDER.read_text()
    parent = REFERENCE_CAP24.read_text()
    require(n.common.sha(REFERENCE_PARENT) == REFERENCE_PARENT_SHA, "Exact saved Bias8 V9 reference bytes")
    bias8 = REFERENCE_PARENT.read_text()
    actual = REFERENCE.read_text()
    expected_parent = original.replace("nssoc_clock_div4_hbt_v7", "nssoc_clock_div4_hbt_v8")
    for name, left, right in (("XCP", "lp", "ckp"), ("XCN", "ln", "ckn")):
        before = f"{name} {left} {right} cap_cmim w=20u l=20u"
        after = f"{name} {left} {right} cap_cmim w=24u l=24u"
        require(expected_parent.count(before) == 1, "Unique original MIM reference")
        expected_parent = expected_parent.replace(before, after)
    circuit = lambda text: [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    require(circuit(parent) == circuit(expected_parent), "Exact historical two-MIM V7 to V8 delta")
    expected = parent.replace("nssoc_clock_div4_hbt_v8", "nssoc_clock_div4_hbt_v9")
    for name, node in (("XDP", "ckp"), ("XDN", "ckn")):
        before = f"{name} {node} avss sub rppd w=1u l=7u b=0 sw_et=1"
        after = f"{name} {node} avss sub rppd w=1u l=8u b=0 sw_et=1"
        require(expected.count(before) == 1, "Unique top-level second-stage pull-down")
        expected = expected.replace(before, after)
    require(circuit(bias8) == circuit(expected), "Only exact two-pull-down V8 to V9 reference delta")
    require(n.common.sha(REFERENCE_DIV2) == REFERENCE_DIV2_SHA, "Exact frozen first-stage core reference")
    require(texts[REFERENCE_DIV2.name] == REFERENCE_DIV2.read_text(), "Original core source in current nominal graph")
    cloned_core = REFERENCE_DIV2.read_text().replace("nssoc_clock_div2_hbt", "nssoc_clock_div2_tail_v10")
    before = "XBIAS avdd ref sub rppd w=1u l=12.7u b=0 sw_et=1"
    after = "XBIAS avdd ref sub rppd w=1u l=11.5u b=0 sw_et=1"
    require(cloned_core.count(before) == 1, "Exactly one local reference in cloned core")
    cloned_core = cloned_core.replace(before, after)
    expected_top = bias8.replace("nssoc_clock_div4_hbt_v9", "nssoc_clock_div4_hbt_v10")
    before = "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt"
    after = "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_tail_v10"
    require(expected_top.count(before) == 1, "Only second-stage core instance retargeted")
    expected_top = expected_top.replace(before, after)
    require(circuit(actual) == circuit(cloned_core) + circuit(expected_top), "Exact one-reference-only V9 to V10 cloned core")
    reference_texts = {k: v for k, v in texts.items() if k not in ("hybrid-open.spice", previous.CHAIN.name)}
    reference_texts[REFERENCE.name] = actual
    rows = n.graph(reference_texts, [("nssoc_clock_div4_hbt_v10", "xchain.xdiv", ["clkp", "clkn", "qp", "qn", "dvdd", "0", "0"])])
    old = {r["path"]: r for r in nominal if r["path"].startswith("xchain.xdiv.")}
    new = {r["path"]: r for r in rows}
    require(len(rows) == len(new) == len(old) == 73 and set(new) == set(old), "All73 exact source identities")
    changed = {name for name in new if new[name] != old[name]}
    caps = {"xchain.xdiv.xcp", "xchain.xdiv.xcn"}
    pulls = {"xchain.xdiv.xdp", "xchain.xdiv.xdn"}
    tail = {"xchain.xdiv.xsecond.xbias"}
    require(changed == caps | pulls | tail, "Historical four changes plus only second-stage tail reference")
    for name in caps:
        require(old[name]["model"] == "cap_cmim" and old[name]["params"] == {"w": "20u", "l": "20u"}, "Exact original two-MIM parameters")
        require(new[name] == dict(old[name], params={"w": "24u", "l": "24u"}), "Retain exact two Cap24 widths and lengths")
    for name in pulls:
        require(old[name]["model"] == "rppd" and old[name]["params"] == {"w": "1u", "l": "7u", "b": "0", "sw_et": "1"}, "Exact original top-level pull-down parameters")
        require(new[name] == dict(old[name], params=dict(old[name]["params"], l="8u")), "Only top-level pull-down lengths become8um")
    for name in tail:
        require(old[name]["model"] == "rppd" and old[name]["params"] == {"w": "1u", "l": "12.7u", "b": "0", "sw_et": "1"}, "Exact original second-stage reference")
        require(new[name] == dict(old[name], params=dict(old[name]["params"], l="11.5u")), "Only second-stage reference length becomes11.5um")
    require(new["xchain.xdiv.xfirst.xcore.xbias"] == old["xchain.xdiv.xfirst.xcore.xbias"], "First-stage reference unchanged")
    return rows, actual


def config(vctrl=0.6, fault=""):
    require(n.common.sha(previous.__file__) == PREVIOUS_SHA, "Frozen biasV2 capture")
    require(n.common.sha(builder.__file__) == BUILDER_SHA, "Frozen divider composer")
    require(set(DIVIDER_PINS) == {"hybrid-open.spice", "composition.json", "source-native-bijection.json"}, "Complete frozen divider inputs")
    for name, digest in DIVIDER_PINS.items():
        require(n.common.sha(DIVIDER/name) == digest, "Exact physical divider " + name)
    # Nominal graph provides a strict 73-device source correspondence. The fault
    # graph separately supplies the original real CMOS modulus mutation.
    c, before, old_texts = previous.config(vctrl, fault)
    _, nominal, nominal_texts = previous.config(vctrl, "")
    nominal, reference = reference_rows(nominal, nominal_texts)
    comp = json.loads((DIVIDER/"composition.json").read_text())
    binding = json.loads((DIVIDER/"source-native-bijection.json").read_text())
    source_correspondence(comp, binding, nominal)
    topology(CHAIN.read_text())
    texts = {k:v for k,v in old_texts.items() if k != previous.CHAIN.name}
    texts[CHAIN.name] = CHAIN.read_text()
    texts[REFERENCE.name] = reference
    texts["divider-hybrid-open.spice"] = (DIVIDER/"hybrid-open.spice").read_text()
    if fault == "disconnect_divider_clock":
        before_connection = "XDIV avss clkn clkp"
        require(texts[CHAIN.name].count(before_connection) == 1, "Actual divider input fault")
        texts[CHAIN.name] = texts[CHAIN.name].replace(before_connection, "XDIV avss clkp clkp")
    rows = [r for r in before if not r["path"].startswith("xchain.xdiv.")]
    expected_ports = ["AVSS", "CLKN", "CLKP", "DIV_AVDD", "QN", "QP", "SUB", "BODY_SUBSTRATE", "WIRE_CREF"]
    require(comp["ports"] == expected_ports, "Native divider public/model port order")
    ports = dict(zip([x.lower() for x in expected_ports], ["0", "clkp" if fault == "disconnect_divider_clock" else "clkn", "clkp", "dvdd", "qn", "qp", "0", "div_body_substrate", "div_wire_cref"]))
    for item in comp["records"]:
        words = item["line"].lower().split()
        count = len(item["terminals"])
        require(words[count+1] == item["model"].lower(), "Native divider model binding")
        require(words[1:count+1] == [t["node"].lower() for t in item["terminals"]], "Native divider named-terminal row")
        rows.append(dict(path="xchain.xdiv."+words[0], model=words[count+1], nets=[ports.get(x,"xchain.xdiv."+x) for x in words[1:count+1]], params=dict(x.split("=") for x in words[count+2:])))
    require(len(rows) == len({r["path"] for r in rows}) == 455, "All455 actual devices")
    require(sum(r["model"] == "npn13g2" for r in rows) == 64, "All64 HBT")
    require(sum(r["model"] in ("ptap1","ntap1") for r in rows) == 31, "All31 finite contacts")
    require(texts["hybrid-open.spice"] == old_texts["hybrid-open.spice"], "Unchanged physical VCO bytes")
    wire_lines = texts["hybrid-open.spice"].splitlines() + texts["divider-hybrid-open.spice"].splitlines()
    require(sum(x.startswith("R") for x in wire_lines) == 1271 and sum(x.startswith("C") for x in wire_lines) == 1414, "Both complete actual metal RC networks")
    c.update(case="loaded_physical_vco_v6_and_divider_v10_tail115_wire_div80", divider_schematic_records=0, divider_physical_records=91, feedback_schematic_records=302, contact_records=31, wire_resistors=1271, wire_capacitors=1414)
    c["fixture"] += ["VDIVBODY div_body_substrate 0 0", "VDIVWREF div_wire_cref 0 0"]
    c["extra_vectors"] += ["i(vdivbody)", "i(vdivwref)"]
    c["extra_vectors"] = [x for x in c["extra_vectors"] if x not in {f"v({node})" for r in rows for node in r["nets"] if node != "0"}]
    declared = set(n.vectors(rows,c["extra_vectors"]))
    for name in OBS[1:]:
        if name not in declared:
            c["extra_vectors"].append(name)
            declared.add(name)
    model, name, old_ports = c["roots"][0]
    require(model == previous.TOP, "Unchanged chain parent")
    c["roots"] = [(TOP, name, old_ports+["div_body_substrate","div_wire_cref"])]
    c["sources"] += [str(REFERENCE_CAP24),str(REFERENCE_PARENT),str(REFERENCE),str(REFERENCE_DIV2),str(CHAIN),str(Path(__file__)),str(Path(builder.__file__)), *[str(DIVIDER/x) for x in DIVIDER_PINS]]
    c["divider_body_boundary"] = "85 native body terminals retained; explicit grounded ideal bench boundary, not substrate-R qualification"
    return c, rows, texts


class Meter(stream.Meter):
    """Frozen424 device screens plus explicit31 contact terminal-voltage screens."""

    def __init__(self, columns, rows, c):
        self.contacts = [r for r in rows if r["model"] in ("ptap1", "ntap1")]
        super().__init__(columns, [r for r in rows if r not in self.contacts], c, OBS)
        self.contact_max = {r["path"]: 0.0 for r in self.contacts}

    def push(self, block):
        super().push(block)
        for row in self.contacts:
            values = [
                block[:, self.names.index(f"v({x})")]
                if x != "0"
                else np.zeros(len(block))
                for x in row["nets"]
            ]
            self.contact_max[row["path"]] = max(
                self.contact_max[row["path"]], float(abs(values[0] - values[1]).max())
            )

    def finish(self):
        safety, data, grid = super().finish()
        for row in self.contacts:
            vmax = self.contact_max[row["path"]]
            safety["all_device_bounds"].append(
                dict(
                    path=row["path"],
                    model=row["model"],
                    max_capture_terminal_difference=vmax,
                    voltage_limit=3.3,
                    inferred_ohmic_peak_a=vmax / float(row["params"]["r"]),
                    contact_current_qualified=False,
                    passed=vmax <= 3.3,
                )
            )
        safety["passed"] = safety["passed"] and all(
            r["passed"] for r in safety["all_device_bounds"]
        )
        require(len(safety["all_device_bounds"]) == 455, "Every device screen retained")
        return safety, data, grid


def deck(c, rows, texts):
    lines = ["Actual455-device VCOv6 and divider wire RC loaded /80 prototype"]
    lines += [
        f'.lib "{n.MODELS}/corner{k}.lib" {v}'
        for k, v in [
            ("HBT", "hbt_typ"),
            ("RES", "res_typ"),
            ("CAP", "cap_typ"),
            ("MOShv", "mos_tt"),
            ("MOSlv", "mos_tt"),
        ]
    ]
    lines += [f'.include "{p}"' for p in texts]
    lines += [".temp 27", ".options reltol=1e-4 abstol=1e-12", *c["fixture"]]
    for model, path, ports in c["roots"]:
        lines.append(path + " " + " ".join(ports) + " " + model)
    lines += [
        f".tran {c['step_s']:.12g} {c['stop_s']:.12g} 0 {c['step_s']:.12g}",
        ".control",
    ]
    lines += ["pre_osdi " + str(x) for x in n.OSDI]
    lines += [
        "set filetype=binary",
        "save " + " ".join(n.vectors(rows, c["extra_vectors"])),
    ]
    for r in rows:
        if r["model"] == "npn13g2":
            name = "q." + r["path"] + ".qnpn13g2"
            lines += [
                f"alter @{name}[off] = 1",
                "echo NSSOC_NATIVE_FLAG_BEGIN " + name,
                "show " + name + " : off",
                "echo NSSOC_NATIVE_FLAG_END",
            ]
    lines += [
        "op",
        "write op.raw all",
        "run stream.fifo",
        "setplot",
        "display",
        "rusage space",
        "quit",
        ".endc",
        ".end",
        "",
    ]
    return "\n".join(lines)


def guard(folder, pending=0):
    free = shutil.disk_usage("/dev/shm").free
    used = physical.owned_size(folder)
    # Include all this experiment's attempts, so a failed probe is not free space.
    used += sum(
        physical.regular_size(x)
        for x in Path("/dev/shm").glob("nssoc-vco-v6-divider-tail115-v1-wire-*")
        if x != folder
    )
    require(free - pending >= FLOOR, "Shared512MiB reserve")
    require(
        used + pending + RECEIPT_RESERVE <= OWN_LIMIT, "Own80MiB final-drain reserve"
    )
    return free, used


def run_native(out, rows, c):
    fifo = out / "stream.fifo"
    os.mkfifo(fifo)
    keep = os.open(fifo, os.O_RDWR)
    reader = fifo.open("rb")
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME")
    }
    env.update(SPICE_SCRIPTS=str(out), RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1")
    start, proc, pool = time.monotonic(), None, None
    free_min, own_peak = guard(out)
    affinity = None

    def close_keep():
        nonlocal keep
        if keep is not None:
            os.close(keep)
            keep = None

    with life.ProcessOwner(out / "owned-processes.json") as owner:
        try:
            with (out / "run.log").open("x") as log:
                proc = owner.launch(
                    "native",
                    [str(n.NG), "-n", "-b", "bench.cir"],
                    cwd=out,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=native_limit,
                )
                affinity = sorted(os.sched_getaffinity(proc.pid))
                require(affinity == [10], "Actual native CPU10 affinity")
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def consume():
                    try:
                        with reader:
                            return capture(reader, out, rows, c)
                    except BaseException as error:
                        owner.request_cancel(error)
                        raise

                future = pool.submit(consume)
                while True:
                    if future.done():
                        result = future.result()
                    owner.check()
                    free, used = guard(out)
                    free_min, own_peak = min(free_min, free), max(own_peak, used)
                    if proc.poll() is not None:
                        close_keep()
                        require(proc.returncode == 0, "Native nonzero exit")
                        if future.done():
                            result = future.result()
                            owner.complete(proc)
                            owner.check()
                            free, used = guard(out)
                            free_min, own_peak = min(free_min, free), max(own_peak, used)
                            break
                    owner.cancelled.wait(0.1)
        except BaseException as error:
            owner.stop_failed(error)
            close_keep()
            raise
        finally:
            close_keep()
            if pool is not None:
                pool.shutdown(wait=True)
            reader.close()
            n.common.atomic(
                out / "execution.json",
                dict(
                    returncode=None if proc is None else proc.poll(),
                    elapsed_seconds=time.monotonic() - start,
                    elapsed_watchdog_seconds=None,
                    address_space_limit_bytes=2 * 1024**3,
                    actual_affinity=affinity,
                    min_shared_free_bytes=free_min,
                    max_own_bytes=own_peak,
                ),
            )
    owner.check()
    free, used = guard(out)
    fifo.unlink()
    return result


def run(out, vctrl, fault=""):
    c, rows, texts = config(vctrl, fault)
    require(
        not out.exists() and out.resolve().is_relative_to("/dev/shm"),
        "Fresh RAM output",
    )
    require(shutil.disk_usage("/dev/shm").free >= 1024**3, "Native1GiB entry floor")
    _, owned = guard(out)
    require(owned + 24 * 1024**2 < OWN_LIMIT, "24MiB launch headroom")
    require(n.common.sha(n.NG) == n.common.NG47_SHA, "Exact ng47")
    require(
        {p.name: n.common.sha(p) for p in n.OSDI} == n.common.OSDI_PINS, "Exact OSDIs"
    )
    inventory = {p.name: n.common.sha(p) for p in sorted(n.MODELS.glob("*.lib"))}
    require(
        hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == n.common.MODEL_INVENTORY_SHA,
        "Exact PDK model inventory",
    )
    out.mkdir()
    for name, text in texts.items():
        (out / name).write_text(text)
    (out / "spinit").write_text("set num_threads=1\n")
    (out / "bench.cir").write_text(deck(c, rows, texts))
    paths = [
        SOURCE,
        *[HYBRID / x for x in PINS],
        n.NG,
        *n.OSDI,
        *n.MODELS.glob("*.lib"),
        *[Path(p) for p in c["sources"]],
        *[Path(p) for p in stream.previous.method_inventory()],
        *out.iterdir(),
    ]
    pins = {str(p.resolve()): n.common.pin(p) for p in paths}
    record = dict(
        status="RUNNING",
        inputs=pins,
        config=c,
        devices=rows,
        raw_estimate_bytes=int(34e-9 / 5e-12 + 32)
        * (len(n.vectors(rows, c["extra_vectors"])) + 1)
        * 8,
        limits="Finite27C loaded /80 with actual VCO and divider metal RC; explicit ideal body boundaries, no substrate spreading, device-wire coupling, RF/PVT, PLL lock, BER or foundry qualification.",
    )
    n.common.atomic(out / "result.json", record)
    try:
        record.update(run_native(out, rows, c))
        # Same 64 actual native OFF readbacks, zero-source OP and strict clean-log gate.
        record.update(stream.previous.startup_proof(out, dict(devices=rows, config=c)))
        require(
            all(n.common.pin(p) == pin for p, pin in pins.items()),
            "All inputs unchanged after native",
        )
        good = record["safety"]["passed"] and record["measurement"]["passed"]
        record["status"] = (
            "PASS_NATIVE_LOADED_FEEDBACK_SCREEN"
            if good
            else "FAIL_NATIVE_LOADED_FEEDBACK_SCREEN"
        )
        record["accepted_actual_fault"] = bool(
            fault and record["safety"]["passed"] and not record["measurement"]["passed"]
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_CAPTURE", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): n.common.pin(p)
            for p in out.rglob("*")
            if p.is_file() and p.name != "result.json"
        }
        n.common.atomic(out / "result.json", record)
    return record

# Unchanged functions retain exact code/defaults/closures in private globals.
_scope = dict(previous._scope, __file__=__file__, __name__=__name__, SOURCE=CHAIN,
              TOP=TOP, config=config, Meter=Meter, deck=deck, guard=guard,
              run_native=run_native, run=run)
_overrides = {"config", "Meter", "deck", "guard", "run_native", "run"}
for _name, _value in previous._scope.items():
    if isinstance(_value, types.FunctionType) and _value.__globals__ is previous._scope and _name not in _overrides:
        _scope[_name] = types.FunctionType(_value.__code__, _scope, _value.__name__, _value.__defaults__, _value.__closure__)
# Copied functions above use the inherited, independently frozen support names.
for _name in ("deck", "guard", "run_native", "run"):
    _value = globals()[_name]
    _scope[_name] = types.FunctionType(_value.__code__, _scope, _value.__name__, _value.__defaults__, _value.__closure__)
run, main = _scope["run"], _scope["main"]

if __name__ == "__main__":
    raise SystemExit(main())
