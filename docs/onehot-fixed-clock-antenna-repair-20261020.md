# Native antenna repair around the fixed clock candidate

Run39369450310 reached zero reported detailed-route markers, then reported16 antenna nets. Native repair stopped with ANT-0016 while attempting to create a wire for clknet_3_5_0_pcie_clk_i. Fresh RC and STA were not reached; no timing or antenna closure is claimed.

The exact generated guarded DRT Tcl is hash-pinned in the failure receipt. The successor changes only the net-level FIXED metadata to ROUTED for the duration of the original repair_antennas call. The existing encoded FIXED wire is never removed, rebuilt or replaced by this wrapper. Net metadata is restored before any later detailed routing, including when repair throws. Replacement of the wire object is an error. The existing final native fixed-clock geometry/identity check remains mandatory.

The observed failure is consistent with [OpenROAD WireBuilder](https://github.com/The-OpenROAD-Project/OpenROAD/blob/65dd113062af25743ead8ce41d06b31ec3002b7d/src/ant/src/WireBuilder.cc#L36): its existing-wire test checks net-level ROUTED, so FIXED can reach dbWire::create on a net that already owns a wire. That source explains the hypothesis; the new execution must verify it against the pinned native runtime.

No antenna repair iterations, diode/jumper options, antenna checks, DRC checks, electrical thresholds, clocks, derating or timing gates are removed. Native antenna repair remains active. The entire final source topology and physical clock route must still match their explicit invariants; any mutation outside that scope is rejected.
