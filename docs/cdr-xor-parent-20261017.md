# CDR XOR physical parent

The load-v2 54-device core has native physical proof in run39035965556. This new candidate creates actual crossed metal nets, with the exact core unchanged, translated40um to provide an external routing channel. The dp and dn trunks use TopMetal1; four TopVia2 contacts join horizontal TopMetal2 access wires. Output polarity is bound to cdr_xor_hbt_load_v2.spice.

Fresh native DRC (560categories), hierarchical and flat54device LVS, physical open/short faults and a swapped-output reference control must all pass. Flat input removes only the12 original child labels after polygon equality verification. Source and fault layouts, references, logs and failures are retained. Parent LEF is a candidate requiring independent native integration verification.

Via dimensions follow [IHP rules](https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html):0.9um cut,2um landings; acceptance uses the pinned native deck, not documentation alone.

This is a comparison primitive. Fresh RC, physically matched loaded native waveforms, actual samplers, level interfaces, closed-loop CDR, four-lane serial PHY and mainchip integration remain required. Original passing schematic margins cannot substitute for these new wires.
