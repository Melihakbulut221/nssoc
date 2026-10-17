#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the mapped replay address invariant, including its inverted LSB.

This is a local state-invariant proof over native Liberty functions, not
whole-chip equivalence, CDC, timing or serial-PHY qualification.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reset_zero_model(liberty):
    """Check the exact native sequential model used at this boundary."""
    start = liberty.index("cell (sg13g2_dfrbpq_1)")
    begin = liberty.index("{", start)
    level, end = 1, begin + 1
    while level:
        level += (liberty[end] == "{") - (liberty[end] == "}")
        end += 1
    cell = liberty[begin:end]
    match = re.search(r"ff\s*\([^)]*\)\s*\{([^}]*)\}", cell, re.S)
    assert match, "Missing native FF model"
    body = match[1]
    assert 'next_state : "D"' in body and 'clocked_on : "CLK"' in body
    assert re.search(r'clear\s*:\s*"(!RESET_B|RESET_B\')"\s*;', body)
    assert "preset" not in body and 'function : "IQ"' in cell


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), args.mapped_json, args.liberty, args.yosys]
    pins = {str(path.resolve()): digest(path) for path in sources}
    model = json.loads(args.mapped_json.read_text())["modules"]["soc_top"]
    reset_zero_model(args.liberty.read_text())
    cells = model["cells"]
    drivers = {}
    for name, cell in cells.items():
        for pin, direction in cell["port_directions"].items():
            if direction == "output":
                for bit in cell["connections"][pin]:
                    drivers.setdefault(bit, []).append((name, pin))
    primary = {
        bit for port in model["ports"].values() if port["direction"] == "input"
        for bit in port["bits"]
    }

    def ff(bit):
        found = drivers[bit]
        assert len(found) == 1 and found[0][1] == "Q"
        name = found[0][0]
        cell = cells[name]
        assert cell["type"] == "sg13g2_dfrbpq_1"
        assert cell["connections"]["CLK"] == model["ports"][args.clock_port]["bits"]
        assert len(cell["connections"]["D"]) == 1
        return name, cell

    def cone(roots):
        needed, leaves, included, visiting = set(), set(), set(), set()

        def visit(bit):
            if isinstance(bit, str):
                assert bit in ("0", "1"), "Unknown constant in mapped cone"
                return
            if bit in needed:
                return
            assert bit not in visiting, "Combinational cycle"
            visiting.add(bit)
            found = drivers.get(bit, [])
            if bit in primary:
                assert not found
                leaves.add(bit)
            else:
                assert len(found) == 1, (bit, found)
                name, pin = found[0]
                cell = cells[name]
                if cell["type"].startswith("sg13g2_df"):
                    assert pin == "Q"
                    leaves.add(bit)
                else:
                    assert re.fullmatch(r"sg13g2_[A-Za-z0-9_]+", cell["type"])
                    assert not cell["type"].startswith("sg13g2_dl"), "Unexpected latch"
                    included.add(name)
                    for port, direction in cell["port_directions"].items():
                        assert direction in ("input", "output")
                        if direction == "input":
                            for value in cell["connections"][port]:
                                visit(value)
            needed.add(bit)
            visiting.remove(bit)

        for bit in roots:
            visit(bit)
        return needed, leaves, included

    current = model["netnames"][args.current_net]["bits"]
    successor = model["netnames"][args.successor_net]
    nxt = successor["bits"]
    width = len(current)
    assert 2 <= width <= 16 and len(nxt) == width
    assert successor["attributes"]["unused_bits"].split() == ["0"]
    assert not any(nxt[0] in value for cell in cells.values()
                   for value in cell["connections"].values())
    current_ffs = [ff(bit) for bit in current]
    reset = current_ffs[0][1]["connections"]["RESET_B"][0]
    # Discover candidates from the actual current-address D cone. Instance
    # numbers and ABC prefixes are intentionally not part of the binding.
    _, boundary, _ = cone([current_ffs[0][1]["connections"]["D"][0]])
    aliases = {}
    for name, value in model["netnames"].items():
        if "flip_bits" in name and len(value["bits"]) == 1:
            bit = value["bits"][0]
            if bit in boundary:
                aliases.setdefault(bit, []).append(name)
    candidates = []
    for bit in sorted(aliases):
        try:
            _, cell = ff(bit)
        except AssertionError:
            continue
        if cell["connections"]["RESET_B"] == [reset] and bit not in current + nxt[1:]:
            candidates.append(bit)
    assert 0 < len(candidates) <= 128, "No bounded candidate set"

    def prove(candidate, tag, fault=None):
        qbits = [candidate] + nxt[1:]
        successor_ffs = [ff(bit) for bit in qbits]
        assert len(set(current + qbits)) == 2 * width
        assert all(cell["connections"]["RESET_B"] == [reset]
                   for _, cell in current_ffs + successor_ffs)
        cd = [cell["connections"]["D"][0] for _, cell in current_ffs]
        nd = [cell["connections"]["D"][0] for _, cell in successor_ffs]
        if fault == "hold_successor_lsb":
            nd[0] = qbits[0]
        elif fault == "swap_successor_bit1":
            nd[1] = qbits[2] if width > 2 else qbits[0]
        needed, leaves, included = cone(current + qbits + cd + nd + [reset])
        all_bits = set(needed)
        for name in included:
            for values in cells[name]["connections"].values():
                all_bits.update(bit for bit in values if isinstance(bit, int))

        def wire(bit):
            return "1'b" + bit if isinstance(bit, str) else "n" + str(bit)

        def vector(bits):
            return "{" + ",".join(wire(bit) for bit in reversed(bits)) + "}"

        lines = [f"module check(input [{len(leaves)-1}:0] boundary, output bad,",
                 f"output [{width-1}:0] current, successor, current_d, successor_d);"]
        lines += [f"wire {wire(bit)};" for bit in sorted(all_bits)]
        lines += [f"assign {wire(bit)}=boundary[{i}];"
                  for i, bit in enumerate(sorted(leaves))]
        for index, name in enumerate(sorted(included)):
            cell = cells[name]
            ports = []
            for pin, values in cell["connections"].items():
                assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", pin)
                ports.append(f".{pin}({vector(values)})")
            lines.append(f"{cell['type']} c{index} ({','.join(ports)});")
        lines += [f"assign current={vector(current)};",
                  f"assign successor={vector(qbits)}^{width}'d1;",
                  f"assign current_d={vector(cd)};",
                  f"assign successor_d={vector(nd)}^{width}'d1;",
                  f"wire [{width-1}:0] expected=current+{width}'d1;",
                  f"wire [{width-1}:0] expected_d=current_d+{width}'d1;",
                  f"assign bad={wire(reset)} && successor==expected &&",
                  "(successor_d!=expected_d || !(current_d==current ||",
                  "current_d==successor || current_d==0));", "endmodule"]
        verilog = out / (tag + ".v")
        verilog.write_text("\n".join(lines) + "\n")
        recipe, log = out / (tag + ".ys"), out / (tag + ".log")
        recipe.write_text(
            f"read_liberty -ignore_miss_func {json.dumps(str(args.liberty.resolve()))}\n"
            f"read_verilog {json.dumps(str(verilog))}\n"
            "hierarchy -top check\nflatten\nproc\nopt\n"
            "sat -verify -prove bad 0 -show-inputs -show-outputs\n")
        with log.open("x") as output:
            proc = subprocess.run([str(args.yosys.resolve()), "-s", str(recipe)],
                                  stdout=output, stderr=subprocess.STDOUT,
                                  preexec_fn=limits)
        text = log.read_text()
        passed = proc.returncode == 0 and "SUCCESS!" in text
        counterexample = proc.returncode != 0 and "proof did fail" in text
        assert passed or counterexample, "Native tool failure is not a counterexample"
        return dict(tag=tag, bit=candidate, passed=passed, counterexample=counterexample,
                    returncode=proc.returncode, combinational_cells=len(included),
                    boundary_bits=len(leaves), log_sha256=digest(log))

    trials = [prove(bit, "candidate-" + str(i)) for i, bit in enumerate(candidates)]
    selected = [row["bit"] for row in trials if row["passed"]]
    assert len(selected) == 1, "Successor polarity binding is not unique"
    selected = selected[0]
    controls = [prove(selected, fault, fault) for fault in
                ("hold_successor_lsb", "swap_successor_bit1")]
    assert all(row["counterexample"] for row in controls)
    assert all(digest(path) == value for path, value in pins.items())
    result = dict(
        status="PASS_MAPPED_SUCCESSOR_INVARIANT_UNIQUE_BINDING_AND_DPIN_CONTROLS",
        width=width, clock_port=args.clock_port, current_net=args.current_net,
        successor_net=args.successor_net, reset_bit=reset,
        inverted_lsb=dict(bit=selected, aliases=aliases[selected], cell=ff(selected)[0]),
        physical_flops=[dict(name=name, **cell) for name, cell in
                        current_ffs + [ff(bit) for bit in [selected] + nxt[1:]]],
        reset_base=dict(current=0, successor=1), trials=trials, controls=controls,
        inputs=pins, inputs_unchanged=True,
        scope="Native reset-zero FF semantics establish the reset base. Actual mapped "
              "D cones prove successor=current+1 modulo its width inductively, plus "
              "current hold/reset/advance alternatives. All other state and input "
              "boundary bits are unconstrained. Exactly one inverted-LSB candidate "
              "must pass; two actual D-pin changes must produce counterexamples. "
              "Not whole-chip equivalence, protocol progress, CDC, timing or PHY approval.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mapped-json", "liberty", "yosys", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--current-net", default="u_pcie.flow.packets.retry.read_pos")
    parser.add_argument("--successor-net", default="u_pcie.flow.packets.retry.next_read_pos")
    parser.add_argument("--clock-port", default="pcie_clk_i")
    args = parser.parse_args()
    result = run(args)
    print(result["status"])


if __name__ == "__main__":
    main()
