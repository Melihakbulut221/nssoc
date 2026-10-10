# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Trace CPU reset to packet data pins in an actual native whole-chip map.

All inputs of a combinational cell conservatively reach all its outputs.
Flip-flops and SRAMs terminate traversal. This is structural evidence, not
functional equivalence, reset recovery, metastability or timing signoff.
"""

import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import re


def inspect(module):
    cells, ports = module["cells"], module["ports"]
    reset = module["netnames"]["rst_sys_n"]["bits"]
    release = module["netnames"]["packet_reset_release"]["bits"]
    clock = ports["pcie_clk_i"]["bits"]
    if len(reset) != 1 or len(release) != 2 or len(clock) != 1:
        raise ValueError("Reset or clock width drift")
    if not all(isinstance(b, int) for b in reset + release + clock):
        raise ValueError("Constant reset/clock/release")
    drivers = defaultdict(list)
    graph = defaultdict(set)
    endpoints = defaultdict(list)
    for name, cell in cells.items():
        kind, connections = cell["type"], cell["connections"]
        inputs, outputs = [], []
        for pin, bits in connections.items():
            direction = cell["port_directions"][pin]
            if direction not in ("input", "output"):
                raise ValueError("Unsupported cell port direction")
            (inputs if direction == "input" else outputs).extend(bits)
            if direction == "output":
                for bit in bits:
                    drivers[bit].append((name, pin))
        if kind == "sg13g2_dfrbpq_1":
            if connections["CLK"] == clock:
                for bit in connections["D"]:
                    endpoints[bit].append(name + "/D")
        elif kind in (
            "RM_IHPSG13_1P_2048x64_c2_bm_bist",
            "RM_IHPSG13_2P_256x16_c2_bm_bist",
        ):
            continue
        elif re.fullmatch(
            r"sg13g2_(?:(?:a21o|a21oi|a221oi|a22oi|o21ai|and[234]|or[234]|"
            r"nand[234]b?|nor[234]b?|xor2|xnor2|mux[24]|buf|inv|lgcp)_\d+|tiehi|tielo)",
            kind,
        ):
            for bit in inputs:
                graph[bit].update(outputs)
        else:
            raise ValueError("Unclassified native cell: " + kind)
    for bit in release:
        if len(drivers[bit]) != 1:
            raise ValueError("Missing or multiple release drivers")
        name, pin = drivers[bit][0]
        cell = cells[name]
        if (
            cell["type"] != "sg13g2_dfrbpq_1"
            or pin != "Q"
            or cell["connections"]["CLK"] != clock
            or cell["connections"]["RESET_B"] != reset
        ):
            raise ValueError("Release clock or asynchronous reset binding drift")
    for name, port in ports.items():
        if name.startswith("pcie_") and port["direction"] == "output":
            for index, bit in enumerate(port["bits"]):
                endpoints[bit].append(f"{name}[{index}]")
    seen = set(reset)
    todo = deque(reset)
    while todo:
        for bit in graph[todo.popleft()]:
            if bit not in seen:
                seen.add(bit)
                todo.append(bit)
    reached = sorted({name for bit in seen for name in endpoints[bit]})
    return dict(
        status="PASS_NO_RAW_RESET_PACKET_DATA_PATH" if not reached else "FAIL",
        reached_packet_data_endpoints=reached,
        packet_data_endpoints=sum(map(len, endpoints.values())),
        reached_combinational_bits=len(seen),
        scope=__doc__,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mapped-json", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    raw = args.mapped_json.read_bytes()
    result = inspect(json.loads(raw)["modules"]["soc_top"])
    result["mapped_sha256"] = hashlib.sha256(raw).hexdigest()
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], len(result["reached_packet_data_endpoints"]))
    return int(result["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
