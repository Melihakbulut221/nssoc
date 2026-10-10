# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
R=Path.cwd(); F=R/'hw/soc/flow'
s=(F/'make_pcie_clock_div4_v6.py').read_text()
s=s.replace('Actual native VCOv3/div4v5 composite; preserves all prior layouts and circuits.', 'Standalone native divider v7 with L4 conditioner; preserves all prior layouts.')
s=s.replace('nssoc_clock_div4_v6_layout','nssoc_clock_div4_v7_layout')
s=s.replace('PORTS = ("CLKP", "CLKN", "QP", "QN", "VCTRL", "VCO_AVDD", "DIV_AVDD", "AVSS", "SUB")','PORTS = ("CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB")')
s=s.replace('TAPS = 30','TAPS = 18')
s='\n'.join(l for l in s.split('\n') if '"hw/soc/analog/pcie/clock_vco_hbt_v3.spice"' not in l)
s=s.replace('clock_div2_conditioned_hbt.spice": "6986c012843f603f7ab7769e951ae01314acdbc0c8e8fc62ce8b5c7a9af25ec3','clock_div2_conditioned_hbt_v3.spice": "158720385252c1dde2d11d4920baeb4a062674894620aa0ffbefe979f101135c')
s=s.replace('clock_div4_hbt_v5.spice": "e68db6846dbfee30afa526a988ff1d585e1f74e10aab06ed65a10de300c944fc','clock_div4_hbt_v7.spice": "49226d5b3a40fc4f8faafbaee3adb5580d8346222a825b79daaddc0358b2c65c')
s=s.replace('                "SG13_HV_PMOS": ("pmos", 4),\n','')
a=s.index('            else:\n                if set(params) != {"W", "L", "NG", "M"}'); b=s.index('            rows.append(row)',a); s=s[:a]+s[b:]
a=s.index('    walk(\n        "NSSOC_CLOCK_VCO_HBT_V3",'); b=s.index('    walk(\n        "NSSOC_CLOCK_DIV4_HBT_V5",',a); s=s[:a]+s[b:]
s=s.replace('NSSOC_CLOCK_DIV4_HBT_V5','NSSOC_CLOCK_DIV4_HBT_V7').replace('hbt=64, resistor=42, capacitor=12, pmos=1','hbt=34, resistor=33, capacitor=6')
a=s.index('        else:\n            if ns[-1] != "VCO_AVDD":'); b=s.index('    lines += [f"RTAP',a); s=s[:a]+s[b:]
s=s.replace('["RNTAP VCO_AVDD NWELL ntap1 A=4p P=8u", ".ends " + TOP, ""]','[".ends " + TOP, ""]')
s=s.replace('if name in ("VCO_AVDD", "DIV_AVDD"):', 'if name == "DIV_AVDD":').replace('"OUTPUT" if name in ("CLKP", "CLKN", "QP", "QN") else "INPUT"','"OUTPUT" if name in ("QP", "QN") else "INPUT"').replace('VCO physical pin','Divider physical pin')
a=s.index('    osc_core ='); b=s.index('    first =',a); s=s[:a]+s[b:]
s=s.replace('119','73').replace('groups = [osc_core, driver, first, interstage, second]','groups = [first, interstage, second]').replace('[23, 23, 30, 17, 26]','[30, 17, 26]').replace(', "pmos": 3','').replace('rid in (2, 4)','rid in (0, 2)')
s=s.replace('Use a fresh project or /dev/shm/nssoc-vco- directory','Use a fresh project or /dev/shm/nssoc-div4- directory')
a=s.index('        elif row["kind"] == "pmos":'); b=s.index('        else:\n            cell = pc(\n                "cmim"',a); s=s[:a]+s[b:]
s=s.replace('Five topology groups','Three topology groups').replace('hbt=64, pmos=1, rppd=42, cmim=12, physical_ptap=TAPS, physical_ntap=1','hbt=34, rppd=33, cmim=6, physical_ptap=TAPS')
s=s.replace('scope="Exact Tiled VCO v3 plus divider v5 composite, explicit finite body contacts and independent VCO/DIV rails. "\n        "No PLL/clock recovery, post-layout oscillation/fanout/current/RF qualification or complete PHY."','scope="Exact standalone divider v7, L4 first conditioner, 73 primitives and 18 finite substrate contacts. "\n        "No oscillator, CMOS feedback chain, extracted division, qualified RC, PLL or complete PHY acceptance."')
assert not any(x in s for x in ('VCO_AVDD','NWELL','pmos','OSC__','VCTRL','119','div4_v6_layout'))
(F/'make_pcie_clock_div4_v7.py').write_text(s)
s=(F/'check_pcie_clock_div4_v6.py').read_text()
s=s.replace('Strict unchanged native DRC/LVS and physical faults for VCOv3/divider-v5.','Strict native DRC/LVS and actual physical faults for standalone divider v7.')
s=s.replace('from check_pcie_rx_cell import execute\n','')
s=s.replace('make_pcie_clock_div4_v6','make_pcie_clock_div4_v7').replace('check_pcie_clock_div4_v6','check_pcie_clock_div4_v7')
s=s.replace('"follower_nx"','"conditioner_pullup"').replace('"control_open"','"clock_open"')
s=s.replace('"RDIV__XSECOND__XBIAS VCO_AVDD"','"RDIV__XSECOND__XBIAS AVSS"')
s=s.replace('"QOSC__XFPD2 VCO_AVDD OSC__BO_P CLKP BULK npn13G2 Nx=4"','"RDIV__XFIRST__XUP DIV_AVDD DIV__XFIRST__CKP BULK rppd w=1u l=4u"').replace('"QOSC__XFPD2 VCO_AVDD OSC__BO_P CLKP BULK npn13G2 Nx=3"','"RDIV__XFIRST__XUP DIV_AVDD DIV__XFIRST__CKP BULK rppd w=1u l=6.4u"')
s=s.replace('generated["peripheral_trunks"]["CLKP"]','generated["peripheral_trunks"]["DIV__S1P"]').replace('generated["peripheral_trunks"]["CLKN"]','generated["peripheral_trunks"]["DIV__S1N"]')
s=s.replace('generated["ports"]["VCTRL"]','generated["ports"]["CLKP"]')
s=s.replace('        y = (b[1] + b[3]) / 2\n        lines += [','        y = (b[1] + b[3]) / 2\n        edge = generated["bbox_um"][2]\n        if b[2] != edge or b[0] != edge - 2:\n            raise ValueError("Exact right-edge clock input required")\n        lines += [')
s=s.replace('pya.DBox(3,{y - 2!r},4,{y + 2!r})','pya.DBox({edge - 4!r},{y - 2!r},{edge - 3!r},{y + 2!r})')
s=s.replace('("VCO_AVDD", "DIV_AVDD")','("DIV_AVDD", "AVSS")')
a=s.index('    expanded = []\n');b=s.index('\n\ndef validate_lvs',a)
s=s[:a]+'''    expanded = []
    for row in hbts:
        if len(row) != 10 or row[5] != "npn13G2":
            raise ValueError("Native HBT syntax")
        p = dict(v.split("=") for v in row[6:])
        if set(p) != {"we", "le", "Nx", "m"} or p["we"] != "70n" or p["le"] != "900n":
            raise ValueError("Native HBT geometry")
        nx, mult = int(p["Nx"]), int(p["m"])
        if nx not in (1, 2, 4) or mult != 1:
            raise ValueError("No merged or multiplied divider HBT permitted")
        expanded.append(nx)
    expected = [r["nx"] for r in devices(Path(__file__).resolve().parents[3]) if r["kind"] == "hbt"]
    if len(hbts) != 34 or Counter(expanded) != Counter(expected):
        raise ValueError("Exact 34 HBT census")
    if len(rows) != 74:
        raise ValueError("Exact 73 primitives plus one parallel finite tap class")
    for model, count in [("rppd", 33), ("cap_cmim", 6)]:
        if sum(model in row for row in rows) != count:
            raise ValueError("Exact native " + model + " census")
    taps = [r for r in rows if r[0].startswith("R") and len(r) >= 4 and r[3] == "ptap1"]
    if len(taps) != 1 or taps[0][1] != "SUB" or taps[0][2] in PORTS or taps[0][4:] != [f"A={TAPS * 4}p", f"P={TAPS * 8}u"]:
        raise ValueError("Exact 18 finite substrate contacts required")
''' + s[b:]
s=s.replace('!= 109','!= 74').replace('Strict composite native','Strict standalone divider native').replace('{"VCTRL"}','{"CLKP"}').replace('missing VCTRL control','missing CLKP input')
s=s.replace('!= 9}', '!= 7}').replace('VCO','Divider').replace('divider_v6.py','divider_v7.py')
s=s.replace('scope="Actual Divider v3/div4v5 connectivity and main-rule screen only; no extracted oscillation/division, PEX, PLL or chip-integration acceptance."','scope="Actual standalone divider v7 connectivity and main-rule screen only; no extracted division, qualified RC, PLL or chip integration acceptance."')
s=s.replace('scope="Actual Dividerv3/div4v5 connectivity and main-rule screen only; no extracted oscillation/division, PEX, PLL or chip-integration acceptance."','scope="Actual standalone divider v7 connectivity and main-rule screen only; no extracted division, qualified RC, PLL or chip integration acceptance."')
s=s.replace('PIN VCTRL\\n.*?  END VCTRL\\n','PIN CLKP\\n.*?  END CLKP\\n')
s=s.replace('PASS_DIV4_V6_COMPOSITE_MAIN_DRC','PASS_DIV4_V7_STANDALONE_MAIN_DRC')
assert not any(x in s for x in ('VCTRL','OSC__','VCO_AVDD','109','52','DIV4_V6','make_pcie_clock_div4_v6'))
(F/'check_pcie_clock_div4_v7.py').write_text(s)
