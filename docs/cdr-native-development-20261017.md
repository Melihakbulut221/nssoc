<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Native CDR development boundary — 17 October 2026

The current HBT RX sampler still uses an external clock. Four recovered-lane digital CDC/deskew blocks do not implement analog clock recovery. The mainchip packet-async layout is not an integrated serial PHY.

Lee, Kundert and Razavi describe an Alexander detector built from sampled data comparisons and explain why metastability and jitter require transistor-level characterization ([JSSC 2004, DOI 10.1109/JSSC.2004.831600](https://kenkundert.com/docs/jssc04-09.pdf), sections II–III). That work motivates this candidate; it does not qualify our process or circuit. In particular, their low-speed voltage-to-current conversion is distinct from assuming that the existing100MHz PLL charge pump can directly process arbitrary8GT/s pulses.

The new `cdr_xor_hbt_v1.spice` is an ORIGINAL connection wrapper around the existing native54-device differential mux. Crossed data inputs produce XNOR; crossed outputs produce XOR. No behavioral gate, ideal gain or current switch replaces intrinsic devices. External10ohm differential input sources, different data/select common modes,500uA ideal bias and50fF loads are explicit bench boundaries. It is a primitive experiment, not yet a phase detector, CDR, physical macro or connected receiver.

The cloud campaign checks256symbols at8GT/s at three fixed within-UI sample phases, all19HBT electrical bounds, zero-source operating point, actual OFF readback, and an actual swapped-output negative circuit. Nominal, hot/low and cold/high are finite sensitivity points, not completePVT. Every failed trace remains in a release. Only fresh actual reports may establish primitive success.

After this primitive, a coherent multi-sampler detector must preserve sample identity across rising/falling clock edges and measure early/late polarity and dead zone. Physical common-mode conversion and fanout, actual V/I response and loop polarity, acquisition with frequency offsets and missing transitions, jitter/BER andPVT, then per-lane physical routing and four-lane integration remain required. Existing TX/PLL/mainchip failures are unchanged. No end-to-end requirement is marked complete by this work.
