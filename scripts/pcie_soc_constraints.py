# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the packet-async whole-SoC development SDC to actual mapped registers.

20 ns CPU, 4 ns packet and independent 8 ns GMII clocks. This does not add a
serial PHY, establish external pad budgets, or qualify SRAM/RC models.
"""

import argparse
import hashlib
import json
from pathlib import Path

from pcie_apb_cdc_constraints import constraints

ROOT = Path(__file__).resolve().parents[1]


def bind(module):
    ports = module["ports"]
    clock_names = ("clk_i", "pcie_clk_i", "eth_rx_clk_i", "eth_tx_clk_i")
    clocks = []
    for name in clock_names:
        p = ports[name]
        if p["direction"] != "input" or len(p["bits"]) != 1:
            raise ValueError("Invalid clock port: " + name)
        clocks.extend(p["bits"])
    if len(set(clocks)) != 4 or any(not isinstance(b, int) for b in clocks):
        raise ValueError("Independent clock ports are aliased or constant")
    nets = {
        n: module["netnames"]["u_pcie_cdc." + n]
        for n in ("request_payload", "response_payload", "response",
                  "request_sync", "acknowledgement_sync")
    }
    for dst, src in (("m_paddr_o", "ep_paddr"), ("m_pwrite_o", "ep_pwrite"),
                     ("m_pwdata_o", "ep_pwdata"), ("m_pstrb_o", "ep_pstrb")):
        nets[dst] = module["netnames"][src]
    # Reuse the strict native flop/clock/two-stage checks, without reusing its
    # standalone port constraints. No name-only CDC exception is admitted.
    _, inventory = constraints({
        "cells": module["cells"], "netnames": nets,
        "ports": {"source_clk_i": ports["pcie_clk_i"],
                  "destination_clk_i": ports["clk_i"]},
    })
    return inventory


def render(module, base):
    inventory = bind(module)
    lines = [base.replace("@PERIOD@", "20.0")]
    # These are development IO budgets, not measured pad/package values.
    lines += [
        "create_clock -name pcie_clk_i -period 4.0 [get_ports pcie_clk_i]",
        "create_clock -name eth_rx_clk_i -period 8.0 [get_ports eth_rx_clk_i]",
        "create_clock -name eth_tx_clk_i -period 8.0 [get_ports eth_tx_clk_i]",
        "unset_input_delay [get_ports {pcie_clk_i eth_rx_clk_i eth_tx_clk_i}]",
        "unset_input_delay [get_ports {eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]",
        "unset_output_delay [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o eth_gtx_clk_o}]",
        "create_generated_clock -name eth_gtx -source [get_ports eth_tx_clk_i] -divide_by 1 [get_ports eth_gtx_clk_o]",
        "set_input_delay -clock eth_rx_clk_i -max 3.0 [get_ports {eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]",
        "set_input_delay -clock eth_rx_clk_i -min 0.5 [get_ports {eth_rxd_i* eth_rx_dv_i eth_rx_er_i}]",
        "set_output_delay -clock eth_gtx -max 2.5 [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o}]",
        "set_output_delay -clock eth_gtx -min -0.5 [get_ports {eth_txd_o* eth_tx_en_o eth_tx_er_o}]",
        "set_clock_uncertainty 0.25 [all_clocks]",
        "set_clock_transition 0.15 [all_clocks]",
        "set_false_path -from [get_ports {rst_ni irq_external_i}]",
    ]
    for direction, delay in (("input", "input"), ("output", "output")):
        names = [n for n, p in module["ports"].items()
                 if n.startswith("pcie_") and n != "pcie_clk_i"
                 and p["direction"] == direction]
        if not names or any(not n.replace("_", "").isalnum() for n in names):
            raise ValueError("Invalid packet port inventory")
        patterns = " ".join(n + ("*" if len(module["ports"][n]["bits"]) > 1 else "")
                            for n in names)
        lines += [f"unset_{delay}_delay [get_ports {{{patterns}}}]",
                  f"set_{delay}_delay -clock pcie_clk_i -max 0.8 [get_ports {{{patterns}}}]",
                  f"set_{delay}_delay -clock pcie_clk_i -min 0.2 [get_ports {{{patterns}}}]"]
    # Existing Ethernet FIFO budgets. The packet clock is deliberately absent
    # from this group; only proven mailbox endpoints cross that boundary.
    for src in ("clk_i", "eth_rx_clk_i", "eth_tx_clk_i"):
        for dst in ("clk_i", "eth_rx_clk_i", "eth_tx_clk_i"):
            if src != dst:
                lines += [f"set_max_delay -ignore_clock_latency 8.0 -from [get_clocks {src}] -to [get_clocks {dst}]",
                          f"set_false_path -hold -from [get_clocks {src}] -to [get_clocks {dst}]"]

    def select(label, rows, pin):
        names = " ".join("{" + row[pin] + "}" for row in rows)
        lines.extend([f"set {label} [get_pins [list {names}]]",
                      f'if {{[llength ${label}] != {len(rows)}}} {{error "CDC pin inventory drift: {label}"}}'])

    select("packet_control_first_d", [inventory["request_sync"][0],
                                      inventory["acknowledgement_sync"][0]], "d")
    lines.append("set_false_path -to $packet_control_first_d")
    for source, destination, budget in (("request", "destination", 16.0),
                                        ("response", "source", 3.2)):
        select("packet_" + source + "_launch", inventory[source], "clk")
        select("packet_" + destination + "_d", inventory[destination], "d")
        suffix = f"-from $packet_{source}_launch -to $packet_{destination}_d"
        lines += [f"set_max_delay -ignore_clock_latency {budget} {suffix}",
                  f"set_false_path -hold {suffix}"]
    lines.append("unset_propagated_clock [all_clocks]")
    return "\n".join(lines) + "\n", inventory


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapped-json", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    base = ROOT / "hw/soc/sta/ibex.sdc.in"
    data = json.loads(a.mapped_json.read_text())
    sdc, inventory = render(data["modules"]["soc_top"], base.read_text())
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "development.sdc").write_text(sdc)
    (a.out / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    inputs = [a.mapped_json, base, Path(__file__),
              ROOT / "scripts/pcie_apb_cdc_constraints.py"]
    pins = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
    (a.out / "result.json").write_text(json.dumps({
        "status": "PASS_MAPPED_CDC_BINDING", "inputs": pins,
        "serial_phy": False, "physical_timing_acceptance": False,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
