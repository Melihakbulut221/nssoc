# Full TX headroom diagnosis and LCRC word-select candidate, 2026-10-23

All work and raw data are on GitHub-hosted runners/releases; the local checkout remains empty.

## TX electrical diagnosis

Run [39888254509](https://github.com/Melihakbulut221/nssoc/actions/runs/39888254509) reproduced all 604 original HBT checks from the complete 34 ns normal return32 capture. The same 85 devices fail; the native simulation was not restarted or accepted. Receipt: `docs/evidence/tx-return32-headroom-results-20261023.json`.

The final mux stage has selector minimum VCE 0.345116490 V and tail minimum VCE 0.368394966 V against the unchanged 0.4 V gate. Its frozen-voltage clock-shift interval is empty: +31.605 mV minimum versus -54.884 mV maximum. Thus that algebraic fixed-current model does not support a clock-commonmode-only repair of the final stage. Actual nonlinear sensitivity and current distribution must be examined before choosing a bias/geometry change; these intervals are not new electrical simulation results.

The worst remaining parent HBT, xtree.xd5644, has minimum VCE about 0.334621 V. At that instant C=0.464017 V, E=0.129396 V and Ic=9.373859 mA (Nx=8). Source topology and loaded waveform evidence must determine the physical current-path repair. Wider AVSS return alone did not close the loaded gates.

## LCRC timing candidate

The pinned placement estimate has a long PCIe max path starting at transmit_packet.index[0]. The new candidate registers a full-address-width one-hot word cursor and replaces the binary word selector with a parallel byte reduction. It retains binary index for control, exact cycles, original byte order, prefix/CRC behavior, and undefined out-of-range reads.

The canonical RTL is unchanged. The cloud screen proves the cursor relation as an observation against the frozen pre-bank reference; it does not assume the relation. It retains arbitrary defined-memory read checks, wrong-word/order counterexamples and a stuck-cursor sequential counterexample. Capacities 4, 5, 8 and 16 are checked. The default capacity also runs original port tests before/after actual IHP mapping and the reliable-packet integration tests. No clocks, loads, timing exceptions or acceptance gates change.

A passing screen establishes behavior only. Mapped/routed timing comparison and a fresh mainchip netlist/layout are still required before adoption. The ongoing route11 uses its exact older immutable candidate; it is not silently replaced by this experiment or the CDC reset fix.
