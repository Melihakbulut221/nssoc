# Cut10j Ethernet and CLINT four-driver physical experiment

Candidate only; not timing or manufacturing acceptance. Independent comparison
against the running two-driver experiment 43495118377; neither run is cancelled.
Both start from routed artifact 14068260482, SHA256
cf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855,
source RTL ecef9ad7cc9cd38c40b37b2109c2c976c53d1e4b.

Measured baseline: routed STA run 43492086181, derived artifact 14071325282,
SHA256 b3c4435e6ac3b39991e4e30b6b76b78f2e88c393caff4013100d384c686c7b4f.
Slow worst CLINT code_in[57] to double_fault_seen_o has -2.134266 ns slack.
Its NOR2 instance $abc$730691$auto$blifparse.cc:397:parse_blif$762276 drives
0.253414 pF, with 2.499983 ns cell delay and 3.221390 ns output slew.
Following place24666 drives 0.272243 pF with 1.723723 ns cell delay and
1.720983 ns output slew. Replace these with nor2_2 and buf16 respectively.
The two Ethernet replacements place28029 buf2->buf16 and fanout67050
buf1->buf16 are identical to the separate two-driver experiment.

Four replacements only. Every original instance/master and replacement master
must exist in the archived PDK; pin names, directions and signal types must
match. Entire net/pin connectivity is checked before and after sizing and
legalization. Logic function families remain NOR2/NOR2 and buffer/buffer.
IHP upstream Verilog blob 21df13c7adfcdeebc8f40ef7cfc8d6ffb976042a lists
matching NOR2 and buffer functions; this is supplementary source evidence,
not a replacement for frozen-PDK checks or full netlist equivalence/LVS.

The hypothesis is lower driver delay and slew on two measured bottlenecks.
Higher input capacitance and rerouting can worsen other setup/hold paths;
no improvement is assumed. Regenerate all signal/clock detailed wires and
guides, retain PG wires, legalize, reroute, extract and run all three PVT corners.
Original 20/4/8/8 ns clocks, output delay, uncertainty and derate guards stay.
Require measured setup/hold/electrical/DRC/antenna results before adoption.
Nominal-only RC remains unqualified for RCmin/max. Source predates current
RTL width fixes; this is not final current-head chip layout. Native data stays
in cloud artifacts; derived results only may be inspected in RAM.
