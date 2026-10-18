# TX v5 actual full-wire rejection

Run 39067769686 finished the real nominal full-wire simulation. Its workflow completion is not electrical acceptance: `electrical_screen_passed` and `all_engineering_gates_passed` are false. All diagnostics were clear and all 604 native HBT OFF flags were read back. The 34 ns raw capture has 77636 rows and 3004 columns; its SHA256 is 03f517ef8df24a755028e09d8418c5161c7e0815f7260e1fb86b02d74c06301a. Every archived native byte remains in the release; no raw archive was downloaded to the local workspace.

The actual core contains 1674 devices, 116611 resistors and 77471 capacitors. All eleven physical six-device clock macros and their local RC are included; intermacro clock connections and specified external boundaries remain ideal and are not full-PHY signoff.

Of 768 unchanged original-bit samples at 0.3/0.5/0.7 UI, 227 have the wrong sign and 254 fall below 100 mV. Minimum signed margin is -0.287717399 V. No latency fitting or phase retiming was used to judge these results.

The interface screen passes the CMOS input, level_16 and level_8 checks. Level_4 fails with 486 wrong-sign samples out of 6912 and a minimum margin of -0.056209594 V; the final interface fails with 1815 wrong-sign samples and -0.289550857 V margin. These localize the next review to distributed paths after level_8, without asserting a root cause from the aggregate metrics alone. Several core HBTs also violate the unchanged minimum VCE gate; all failed identities and measurements are retained in the receipt. No MOS devices fail their recorded voltage limits.

The preceding compact nominal/hot/cold passes do not override this actual distributed-wire result. Next work must inspect the failed intermediate paths, clock arrival and physical return/signal networks, then modify and re-extract actual geometry/circuit before rerunning the original data/device gates. PVT, fault and timestep controls on a working full-wire candidate remain open.
