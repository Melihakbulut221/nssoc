# v50 actual loaded physical leaf

The corrected v50 layout passed560 native DRC categories with zero markers and deep/flat18-device transistor LVS, including all nine physical faults. FreshRC40036071799 and native binding40036071886 were independently source-matched to physical wire40035558577. Composition40036688906 passed all14faults with18native devices and actual53R93C.

This screen uses only the new immutable composed model. The native interface is sub,ip,inn,avdd,avss,iref,on,op,wire_cref; that differs from v49's ordinal order. The testbench maps by port names and validates exact native order, model parameters and every intrinsic terminal. Eight corrupt-binding tests remain required.

Original34.25ns/256bits,10ohm source,150fF output loads, nominal/hot-low/cold-high/swapped-output/bias-off cases, solver and all HBT/MOS/common-mode/signal gates are unchanged. The cloud control compares the original analysis region. All61 physical/body wire nodes and native currents remain in the full capture. No artificial wire scaling, extra ideal parent bias or relaxed37.5ps timing target is introduced.

Pending native waveform results. Leaf pass would still require real parent bias/load integration, full CDR loop, RF/substrate qualification, full serial Gen3x4, routed mainchip and final timing evidence.
