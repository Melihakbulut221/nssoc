# All64 native CMOS input drivers in the full32:1 test — 2026-10-20

The current p4-drive3 fullwave includes a real routed1674-device serializer core and eleven real clock-reference macros. Its64input drivers still use aggregate schematic models. This preparation connects all64existing physical localpins driver models, with100raw devices and260R295C per driver. It retains their84individual MOS fingers, measured named D/S junctions and finite bulk contacts:5376MOS are now probed instead of512aggregate MOS, while all604HBT and124physical input legs remain observed.

The exact driver composition is run38909917993, summary ed35b35933e6514ad4e4b1a694513f04f4783b68147005d2852019929cc55209, model c624e9d1597ac8b68a2fb4772673ad0ffade0c35a21a027cbd449de1e2acf3d6. This source is physically extracted, but its older4:1 loaded test was rejected. It is not represented as an electrically accepted driver. The current32:1 downstream circuit and slower250MHz input bit streams differ from that old4:1 test; the entire new circuit must be simulated.

The existing source-bound adapter is expanded from8to64instances. Original PWL sources,256bits,34ns capture, all three sample phases, clock assignments, interface limits, everyHBT/MOS limit and solver remain unchanged. All source model hashes and source libraries must match. Actual missing-driver, swapped-port and omitted-probe corruptions are still rejected.

This workflow first constructs and validates the full native bench without simulating it, then reports the actual probe count and minimum raw capture size. This allows a disk/resource plan that preserves every raw sample. Preparation cannot pass an electrical gate. The full waveform is still mandatory.

This is loaded-model integration. Driver/core interconnect, chip supply distribution and differential clock modulation remain ideal boundaries. The output frontend, composite physical assembly, PVT/channel/RF/ESD, closed-loop PLL/CDR and mainchip signoff remain open. No full serialPHY completion is claimed.
