# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind narrow CDC constraints to actual mapped register pins, fail on drift.

These are conservative development budgets, not qualified layout constraints.
The mailbox holds bundled data through a synchronized four-phase handshake.
Never replace the two first-stage control exceptions with clock-group cuts:
that would also hide the bundled-data paths that must meet explicit budgets.
"""

import argparse
import json
from pathlib import Path


def constraints(module, source_period=4.0, destination_period=20.0):
    if source_period <= 0 or destination_period <= 0:
        raise ValueError("Clock periods must be positive")
    cells = module["cells"]
    ports = module["ports"]

    def registers(name, width, clock):
        bits = module["netnames"][name]["bits"]
        if len(bits) != width or len(set(bits)) != width:
            raise ValueError(f"Missing/aliased register bits: {name}")
        records = []
        for bit in bits:
            matches = [
                (n, c)
                for n, c in cells.items()
                if c["port_directions"].get("Q") == "output"
                and c["connections"].get("Q") == [bit]
            ]
            if len(matches) != 1:
                raise ValueError(f"No unique physical register driver for {name}")
            n, c = matches[0]
            if (
                c["type"] != "sg13g2_dfrbpq_1"
                or c["connections"]["CLK"] != ports[clock]["bits"]
                or len(c["connections"]["D"]) != 1
            ):
                raise ValueError(f"Wrong cell/clock for {name}")
            if any(ch in n for ch in "{}\n\r"):
                raise ValueError("Unsafe Tcl cell name")
            records.append(dict(cell=n, q=n + "/Q", d=n + "/D", clk=n + "/CLK"))
        return records

    inventory = dict(
        request=registers("request_payload", 49, "source_clk_i"),
        response=registers("response_payload", 33, "destination_clk_i"),
        destination=sum(
            (
                registers(n, w, "destination_clk_i")
                for n, w in [
                    ("m_pwrite_o", 1),
                    ("m_paddr_o", 12),
                    ("m_pwdata_o", 32),
                    ("m_pstrb_o", 4),
                ]
            ),
            [],
        ),
        source=registers("response", 33, "source_clk_i"),
        request_sync=registers("request_sync", 2, "destination_clk_i"),
        acknowledgement_sync=registers("acknowledgement_sync", 2, "source_clk_i"),
    )
    # Prove that each control's second D really comes from its first Q, so
    # the first-stage exception cannot silently move to a functional endpoint.
    for key in ("request_sync", "acknowledgement_sync"):
        a, b = [cells[r["cell"]]["connections"] for r in inventory[key]]
        if b["D"] != a["Q"]:
            raise ValueError(f"Broken two-stage synchronization: {key}")

    lines = [
        f"create_clock -name packet_clock -period {source_period} [get_ports source_clk_i]",
        f"create_clock -name cpu_clock -period {destination_period} [get_ports destination_clk_i]",
        "set_input_delay -clock packet_clock 0.2 [get_ports {s_psel_i s_penable_i s_pwrite_i s_paddr_i* s_pwdata_i* s_pstrb_i*}]",
        "set_input_delay -clock cpu_clock 0.2 [get_ports {m_pready_i m_pslverr_i m_prdata_i*}]",
        "set_input_transition 0.1 [all_inputs]",
        "set_output_delay -clock packet_clock 0.2 [get_ports {s_pready_o s_pslverr_o s_prdata_o*}]",
        "set_output_delay -clock cpu_clock 0.2 [get_ports {m_psel_o m_penable_o m_pwrite_o m_paddr_o* m_pwdata_o* m_pstrb_o*}]",
        "set_load 0.01 [all_outputs]",
        "set_input_delay -clock cpu_clock 0 [get_ports reset_ni]",
        "set_false_path -from [get_ports reset_ni]",
    ]

    def select(label, records, pin):
        names = " ".join("{" + r[pin] + "}" for r in records)
        lines.append(f"set {label} [get_pins [list {names}]]")
        lines.append(
            f'if {{[llength ${label}] != {len(records)}}} {{error "CDC pin inventory drift: {label}"}}'
        )

    select(
        "control_first_d",
        [inventory["request_sync"][0], inventory["acknowledgement_sync"][0]],
        "d",
    )
    lines.append("set_false_path -to $control_first_d")
    for label, target, budget in [
        ("request", "destination", 0.8 * destination_period),
        ("response", "source", 0.8 * source_period),
    ]:
        select(label + "_launch", inventory[label], "clk")
        select(target + "_d", inventory[target], "d")
        lines.append(
            f"set_max_delay {budget:.6f} -ignore_clock_latency -from ${label}_launch -to ${target}_d"
        )
        lines.append(f"set_false_path -hold -from ${label}_launch -to ${target}_d")
    return "\n".join(lines) + "\n", inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapped-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    module = json.loads(args.mapped_json.read_text())["modules"]["soc_pcie_apb_cdc"]
    sdc, inventory = constraints(module)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "development.sdc").write_text(sdc)
    (args.out / "register-pins.json").write_text(json.dumps(inventory, indent=2) + "\n")


if __name__ == "__main__":
    main()
