# Actual MOS gate resistance: interpretation and next physical step

Actual cloud diagnostic41695546092/source12f87169a29887cbae7edb1def1dc91ddeb92819 authenticated the complete original loaded runtime and library and the current200 MOS gate geometries. It passed after preserving two real diagnostic failures: treating compiled OSDI as text41694626851, then UTF8-only decoding of Latin1 annotations41695152558. Binary identity and lossless text decoding are now separate; original model bytes are unchanged.

The exact MOS wrapper defaults rfmode=0 and pre_layout=1. Non-RF uses sg13g2_lv_nmos_psp / psp103va. The RF alternative uses sg13g2_lv_nmos_psp_rf / pspnqs103va with swnqs='rfmode * 5.0', rshg='rfmode * 3.0', rgo='rfmode * 40.0'. The wrapper sets ngcon=2. These are actual model declarations, not proof that RF mode matches the actual single-contact physical gate arrangement, or that ordinary PSP has zero total gate impedance.

All200 physical gates form50 contact groups. For example the first6-unit group has a long0.3um-wide common poly stem with one top contact, and its200 native identities remain tied to actual physical coordinates. Metal/via RC does not include this path resistance. Do not infer unique physical ownership from the schematic aliases permuted by LVS.

Next cloud AC characterization compares both model modes at each actual unique W/L/AS/AD/PS/PD tuple, with explicit extracted area/perimeter mode pre_layout=0, fixed0.8V gate/0.6V drain bias and1MHz-10GHz frequency sweep. Native model readback and all complex impedance values are retained. This diagnosis must guide a distributed physical poly/contact model; it does not substitute for the original full loaded circuit, four-lane serial behavior, or final chip timing.

Magic technology resistance/contact variants also need complete interpretation before assigning sheet/contact resistance. Full poly-to-metal capacitance, MIM intrinsic composition, substrate and foundry-quality PEX remain unqualified.
