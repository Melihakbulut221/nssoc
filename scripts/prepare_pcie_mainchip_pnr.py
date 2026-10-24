# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare a four-clock packet SoC physical experiment from an actual native map.

The existing 20-SRAM floorplan and checker thresholds are retained. This is
not a serial PHY layout or a manufacturing-qualified SRAM/RC configuration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from pcie_soc_constraints import render

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
    # POR MBIST replaces the inferred FIFO banks with explicit wrappers.
    # Keep the same physical bank index, master, coordinates and orientation.
    fifo = config["MACROS"]["RM_IHPSG13_2P_256x16_c2_bm_bist"]["instances"]
    renames = {f"u_eth.u_mac.{direction}_fifo.fifo_inst.mem.0.{i}":
               f"u_eth.u_mac.{direction}_fifo.fifo_inst.u_sram.g_bank[{i}].u_mem"
               for direction in ("rx", "tx") for i in range(8)}
    if set(fifo) != set(renames):
        raise ValueError("Unexpected base FIFO bank placement")
    config["MACROS"]["RM_IHPSG13_2P_256x16_c2_bm_bist"]["instances"] = {
        renames[n]: p for n, p in fifo.items()}
    config["PDN_MACRO_CONNECTIONS"] = [
        rule.replace(r"fifo_inst\.mem\.0\.[0-7]",
                     r"fifo_inst\.u_sram\.g_bank\[[0-7]\]\.u_mem")
        for rule in config["PDN_MACRO_CONNECTIONS"]]
    actual = {n: c["type"] for n, c in module["cells"].items()
              if c["type"].startswith("RM_IHPSG13")}
    if len(actual) != 20 or actual != configured_macros(config) or actual != mapped_macros(netlist):
        raise ValueError("Native map/netlist/floorplan SRAM inventory mismatch")
    # OpenROAD's Verilog reader retains an internal backslash before literal
    # array brackets in instance names. Bind this observed representation
    # explicitly for PDN regexes. LibreLane's macro placer performs its own
    # conversion, so its config must retain the original Verilog names.
    odb_names = {n: n.replace("[", "\\[").replace("]", "\\]") for n in actual}
    config["PDN_MACRO_CONNECTIONS"] = [
        rule.replace(r"g_bank\[[0-7]\]", r"g_bank\\\[[0-7]\\\]")
        for rule in config["PDN_MACRO_CONNECTIONS"]]
    sdc, inventory = render(module, base_sdc.read_text())
    # The synthesis screen intentionally has ideal clocks. Physical steps
    # must propagate CTS latency, using the same stage flag as LibreLane.
    anchor = "unset_propagated_clock [all_clocks]\n"
    if sdc.count(anchor) != 2:
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
                  CLOCK_PORT=["clk_i", "pcie_clk_i", "eth_rx_clk_i", "eth_tx_clk_i"],
                  CLOCK_NET=["clk_i", "pcie_clk_i", "eth_rx_clk_i", "eth_tx_clk_i"],
                  PNR_SDC_FILE=str(out / "physical.sdc"),
                  SIGNOFF_SDC_FILE=str(out / "physical.sdc"), DRT_THREADS=4)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("inventory.json", inventory),
                        ("state.json", {"nl": str(netlist), "metrics": {}})):
        (out / name).write_text(json.dumps(value, indent=2) + "\n")
    (out / "physical.sdc").write_text(sdc)
    inputs = [mapped_json, netlist, base_path, base_sdc, Path(__file__),
              ROOT / "scripts/pcie_soc_constraints.py",
              ROOT / "scripts/pcie_apb_cdc_constraints.py",
              ROOT / "hw/soc/flow/select_pnr_profile.py"]
    result = dict(status="PREPARED_NOT_ROUTED", macros=actual, fifo_renames=renames,
                  odb_macro_names=odb_names,
                  inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                  serial_phy=False, physical_timing_acceptance=False,
                  scope="Packet PCIe ports, native vendor SRAM; all acceptance still requires actual physical reports.")
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
