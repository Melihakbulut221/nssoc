# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical candidate for the exact 43-device high-common-mode divide-by-two."""

from pathlib import Path
import sys, inspect, json

R = Path.cwd()
B = Path(__file__).resolve().parent
sys.path.insert(0, str(R / "hw/soc/flow"))
import make_pcie_clock_div4_v10_tail_v1 as m

CIRCUIT = "hw/soc/analog/pcie/clock_div2_high_input_v1.spice"
CIRCUIT_SHA256 = "e6b0a3f4f0c497d7290e9eab52133791cb035db3c37e797112bc8b15c32aab8a"
m.SOURCES = dict(m.SOURCES) | {CIRCUIT: CIRCUIT_SHA256}
m.TOP = "nssoc_hbt_highinput43_v1_layout"
m.TAPS = 12
source = (
    inspect.getsource(m.flatten)
    .replace('"NSSOC_CLOCK_DIV4_HBT_V10",', '"NSSOC_CLOCK_DIV2_HIGH_INPUT_V1",')
    .replace(
        "dict(hbt=34, resistor=33, capacitor=6)",
        "dict(hbt=19, resistor=20, capacitor=4)",
    )
)
exec(compile(source, str(B / "derived-flatten01.py"), "exec"), m.__dict__)
# Reuse the exact two reachable topology groups from v10, including local order.
source = (
    inspect.getsource(m.placement_plan)
    .replace("len(rows) != 73", "len(rows) != 43")
    .replace(
        "groups = [list(reversed(first)), interstage, list(reversed(second))]",
        "groups = [interstage, list(reversed(second))]",
    )
    .replace("[30, 17, 26]", "[17, 26]")
    .replace(
        "starts, net_rows, plan = {}, {}, {}",
        'priority = [priority[1], priority[2]]\n    priority[0] = [n for n in priority[0] if n not in ("DIV__S1P", "DIV__S1N")]\n    starts, net_rows, plan = {}, {}, {}',
    )
)
exec(compile(source, str(B / "derived-placement01.py"), "exec"), m.__dict__)
source = (
    inspect.getsource(m.main)
    .replace("!= [0, 1, 2]", "!= [0, 1]")
    .replace("len(power_straps) != 8", "len(power_straps) != 6")
    .replace("dict(hbt=34, rppd=33, cmim=6", "dict(hbt=19, rppd=20, cmim=4")
)
exec(compile(source, str(B / "derived-main01.py"), "exec"), m.__dict__)
if __name__ == "__main__":
    m.main()
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    p = out / "result.json"
    r = json.loads(p.read_text())
    r["input_sha256"].update({str(p): m.sha(p) for p in [Path(__file__)]})
    r.update(
        scope="Exact 19 HBT,20 rppd,4 MIM high-input divide2;12 finite substrate contacts. Two topology rows derived from native v10. DRC/LVS/metal RC and loaded division pending.",
        placement_method="Two reachable v10 topology groups; unchanged native PCell escape and routing algorithms.",
    )
    p.write_text(json.dumps(r, indent=2) + "\n")
