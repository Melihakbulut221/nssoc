# Balanced CRC: native block improvement does not close packet timing

Run [39900301089](https://github.com/Melihakbulut221/nssoc/actions/runs/39900301089) passed the exhaustive defined-input CRC proof, explicit-clock-event LCRC proofs (502/518 points, zero unproved), and 36 original RTL/mapped positive port cases. The wrong CRC bit produced a formal counterexample and both expected failing port cases. No test was skipped.

At the slow corner, balanced CRC improves standalone LCRC setup slack from -6.768252850 ns to -4.435173035 ns, but the complete reliable-packet path worsens from -9.733874321 ns to -10.886579514 ns. Adding the registered word cursor worsens that packet result further to -15.100089073 ns. Canonical RTL is unchanged; no standalone result is promoted to full-path closure.

The preserved old LCRC worst paths launch from byte_index. Clock-to-Q and the following control stages account for several nanoseconds in these unbuffered mappings. This motivates quantifying mapped fanout and buffering; delay alone does not establish the cause or prove a physical sensitivity. The next diagnosis must inspect full packet native paths and actual buffering/sizing under the original clock.

All results use fixed 4 ns, 0.25 ns uncertainty, 5% derates, 0.05 ns transition, 0.01 pF output load, ideal clock and zero wire RC. Routed-chip STA remains separate and required.
