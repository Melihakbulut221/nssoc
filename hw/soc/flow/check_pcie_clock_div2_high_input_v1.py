# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys, inspect

R = Path.cwd()
B = Path(__file__).resolve().parent
sys.path.insert(0, str(R / "hw/soc/flow"))
import make_pcie_clock_div2_high_input_v1 as generator
import check_pcie_sampler_cell as c
import check_pcie_clock_div4_v10_tail_v1 as v10

for n in ["PORTS", "TOP", "use_direction"]:
    setattr(c, n, getattr(generator.m, n))
c.CIRCUIT = generator.CIRCUIT
c.CIRCUIT_SHA256 = generator.m.sha(c.CIRCUIT)
c.physical_reference = lambda ignored: generator.m.physical_reference(R)
c.REFERENCE_FAULTS = (
    "limiter_load",
    "feedback",
    "limiter_nx",
    "feedforward_mim",
    "seed_asymmetry",
    "missing_tap",
    "supply_swap",
)
c.fault_reference = v10.fault_reference
source = inspect.getsource(c.mutation_source).replace(
    '("AVDD", "AVSS")', '("DIV_AVDD", "AVSS")'
)
source = source.replace(
    'f"region-=pya.Region(pya.DBox(3,{y-2!r},4,{y+2!r}).to_itype(l.dbu))"',
    'f"region-=pya.Region(pya.DBox({b[2]-4!r},{y-2!r},{b[2]-3!r},{y+2!r}).to_itype(l.dbu))"',
)
# Both clock pins are on the right. Power pins are on the left.
source = source.replace(
    "ys = [sum(",
    'x = generated["bbox_um"][2] - 1.5 if fault == "clock_short" else .5\n        ys = [sum(',
).replace(
    "pya.DBox(.5,{min(ys)!r},1.5,{max(ys)!r})",
    "pya.DBox({x!r},{min(ys)!r},{x+1!r},{max(ys)!r})",
)
exec(compile(source, str(B / "derived-mutations01.py"), "exec"), c.__dict__)
exec(
    compile(
        inspect.getsource(c.lef_script).replace("!= 10", "!= 7"),
        str(B / "derived-lef01.py"),
        "exec",
    ),
    c.__dict__,
)
exec(
    compile(
        inspect.getsource(c.validate_lvs).replace("!= 28", "!= 44"),
        str(B / "derived-lvs01.py"),
        "exec",
    ),
    c.__dict__,
)
source = (
    inspect.getsource(c.main)
    .replace(
        "PASS_SAMPLER_V2_MAIN_DRC_STRICT_DEEP_LVS_LEF_AND_TEN_NEGATIVE_CONTROLS_ONLY",
        "PASS_HIGHINPUT43_MAIN_DRC_STRICT_DEEP_LVS_LEF_TWELVE_NEGATIVE_CONTROLS",
    )
    .replace(
        "Fixed external-clock sampler physical connectivity and main-rule screen only; no RF/timing acceptance.",
        "43-device high-input divider and12 finite contacts; native main-rule/connectivity screen only. No loaded division, qualified RC, PLL or serial PHY acceptance.",
    )
)
source = source.replace(
    "out.mkdir(parents=True)",
    "pins[Path(__file__).resolve()] = digest(Path(__file__).resolve())\n    out.mkdir(parents=True)",
)
# c.__file__ remains the canonical checker for root calculation; pin wrapper explicitly.
c.WRAPPER = Path(__file__).resolve()
source = source.replace(
    "pins[Path(__file__).resolve()] = digest(Path(__file__).resolve())",
    "pins[WRAPPER] = digest(WRAPPER)",
)
exec(compile(source, str(B / "derived-main-check01.py"), "exec"), c.__dict__)
if __name__ == "__main__":
    c.main()
