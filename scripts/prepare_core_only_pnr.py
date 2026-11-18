# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare the release without PCIe/Ethernet: one clock, four system SRAMs.
This is placement preparation, not production signoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
from select_pnr_profile import configured_macros, mapped_macros


def prepare(mapped_json, netlist, out):
    mapped_json, netlist, out = (p.resolve() for p in (mapped_json, netlist, out))
    base_path = ROOT / "hw/soc/pnr/config-interfaces-logicrom.json"
    base_sdc = ROOT / "hw/soc/sta/ibex.sdc.in"
    config = json.loads(base_path.read_text())
    data = json.loads(mapped_json.read_text())
    module = data["modules"]["soc_top"]
    if any(n.startswith(("pcie_", "eth_")) for n in module["ports"]):
        raise ValueError("Network ports are forbidden in this release")
    if module["ports"]["clk_i"]["direction"] != "input" or len(module["ports"]["clk_i"]["bits"]) != 1:
        raise ValueError("Invalid core clock")
    master = "RM_IHPSG13_1P_2048x64_c2_bm_bist"
    config["MACROS"] = {master: config["MACROS"][master]}
    config["PDN_MACRO_CONNECTIONS"] = [
        rule for rule in config["PDN_MACRO_CONNECTIONS"] if rule.startswith("u_ram")]
    if len(config["PDN_MACRO_CONNECTIONS"]) != 2:
        raise ValueError("Expected two system SRAM supply rules")
    config["EXTRA_SPICE_MODELS"] = [
        "pdk_dir::libs.ref/sg13g2_sram/cdl/" + master + ".cdl"]
    actual = {n: c["type"] for n, c in module["cells"].items()
              if c["type"].startswith("RM_IHPSG13")}
    if len(actual) != 4 or actual != configured_macros(config) or actual != mapped_macros(netlist):
        raise ValueError("Native map/netlist/floorplan SRAM inventory mismatch")
    # OpenROAD's Verilog reader retains an internal backslash before literal
    # array brackets in instance names. Bind this observed representation
    # explicitly for PDN regexes. LibreLane's macro placer performs its own
    # conversion, so its config must retain the original Verilog names.
    odb_names = {n: n.replace("[", "\\[").replace("]", "\\]") for n in actual}
    config["PDN_MACRO_CONNECTIONS"] = [
        rule.replace(r"g_bank\[[0-7]\]", r"g_bank\\\[[0-7]\\\]")
        for rule in config["PDN_MACRO_CONNECTIONS"]]
    sdc = base_sdc.read_text().replace("@PERIOD@", "20.0")
    inventory = dict(clock_ports=["clk_i"], period_ns=20.0,
                     ports=sorted(module["ports"]), external_io_budgets_qualified=False)
    if any(x in sdc for x in ("pcie_", "eth_")):
        raise ValueError("Stale network constraints")
    if config["TIME_DERATING_CONSTRAINT"] != 5.0 or config["CLOCK_PERIOD"] != 20:
        raise ValueError("Unexpected core timing contract")
    # The synthesis screen intentionally has ideal clocks. Physical steps
    # must propagate CTS latency, using the same stage flag as LibreLane.
    anchor = "unset_propagated_clock [all_clocks]\n"
    if sdc.count(anchor) != 1:
        raise ValueError("Unexpected synthesis clock propagation commands")
    sdc = sdc.replace(anchor, "") + (
        "if {[info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS)} {\n"
        "    unset_propagated_clock [all_clocks]\n"
        "} else {\n    set_propagated_clock [all_clocks]\n}\n"
    )
    # Paths retain the base config's directory semantics after relocation.
    def relocate(v):
        if isinstance(v, str) and v.startswith("dir::"):
            return str((base_path.parent / v[5:]).resolve())
        if isinstance(v, list):
            return [relocate(x) for x in v]
        if isinstance(v, dict):
            return {k: relocate(x) for k, x in v.items() if not k.startswith("//")}
        return v
    config = relocate(config)
    config.update(VERILOG_FILES=[str(netlist)], VERILOG_DEFINES=[], SYNTH_PARAMETERS=[],
                  CLOCK_PORT=["clk_i"],
                  CLOCK_NET=["clk_i"],
                  PNR_SDC_FILE=str(out / "physical.sdc"),
                  SIGNOFF_SDC_FILE=str(out / "physical.sdc"), DRT_THREADS=4)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inventory.json", inventory),
                        ("state.json", {"nl": str(netlist), "metrics": {}})):
        (out / name).write_text(json.dumps(value, indent=2) + "\n")
    (out / "physical.sdc").write_text(sdc)
    inputs = [mapped_json, netlist, base_path, base_sdc, Path(__file__),
              ROOT / "hw/soc/flow/select_pnr_profile.py"]
    result = dict(status="PREPARED_NOT_ROUTED", macros=actual, removed_interfaces=["PCIe","Ethernet"],
                  odb_macro_names=odb_names,
                  inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                  serial_phy=False, physical_timing_acceptance=False,
                  scope="Core-only chip, four system SRAMs; native vendor views and external IO budgets still require production qualification. DRC/LVS/PEX and timing are not accepted by preparation.")
    (out / "preparation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapped-json", type=Path, required=True)
    p.add_argument("--netlist", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print(prepare(a.mapped_json, a.netlist, a.out)["status"])


if __name__ == "__main__":
    main()
