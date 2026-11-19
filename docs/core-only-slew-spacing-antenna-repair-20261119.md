# Slew-spacing antenna repair — 2026-11-19

The lower-metal-only spacing experiment failed the unchanged antenna gate: https://github.com/Melihakbulut221/nssoc/actions/runs/44475161358 at `b59825f413865ea26a0393bfad8fa649afa78c5c`, attempt 1.

Artifact 14506811740 SHA256 `b30e42148a9e33a78fbf63f57ed82b045efea9b0b15d1992e9db9a605d891eca`: all 49 manifest output hashes verified. Rejected routed ODB SHA256 `c872aa32fa3af58292e86a6caecf6e2fb2f8e875d3c8f1be077461304133d99d`.

Native DRC 0; independent wire/pin geometry has 0 inter-net contacts, no disconnected nets, no missing terminal geometry. All 103067 unselected net records and 2113 clocks preserved. The same `nssoc_sta_n_56323` / `nssoc_sta_i_55608/B` antenna violation remains: TopMetal1 cumulative ratio 212.86 against 200.00. Removing expanded upper-metal spacing did not resolve it. Neither spacing candidate is admitted or freshly timing-qualified.

Next experiment uses the measured rejected route only as an explicitly unqualified repair input. Insert exactly one sg13g2_antennanp diode on that signal net. Require all old cells, placements, terminal connections, PG geometry and all other net routes to remain unchanged. Check both diode power pins against actual same-net rails with negative controls. Check placement and inherited NDR assignment preservation. All 2113 clock net records must remain exact. Any additional diode, other changed net or missing supply contact fails the preparation.

A successful insertion is not routing or antenna closure. The added diode then requires selected-net routing, native DRC/antenna and independent geometry rechecks, fresh nominal RC/STA and updated netlist/diode provenance. Diode capacitance may offset the slew improvement; admission requires measurement. Full SRAM/RC qualification, full-chip signoff and manufacturing approval remain open.
