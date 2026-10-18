# TX fast-stage track isolation

Native unsimplified LVS of run39154915645 rejected the six-row placement with
1674devices on both sides. Hosted review39156102268 reproduces four exact
positive-area overlaps among parent TopMetal1 rectangles generated in that
failed layout: p8_0p/p8_2p, p8_0n/p8_2n, p8_5p/p8_7p, p8_5n/p8_7n.
The geometric diagnostic excludes vias, child shapes and supplies; it is not a
substitute for native LVS. The original full failed geometry remains preserved.

Only p8_2p/n move48um outward, and p8_7p/n move24um outward, to two tracks at
parent-right+88/+100um. These two pairs have disjoint Y spans. Original four
tracks for every other net, 4um widths, vias, cell shapes, six row positions,
1674devices/719emitters, logical connections, clocks and thresholds stay fixed.
The additional two horizontal stubs add96um per p8_2 wire and48um per p8_7 wire.
The shortened paths feeding f/a/b remain unchanged. This is not an electrical
improvement claim; new RC and original loaded waveforms are mandatory.

The source guard verifies an exact delta from the retained failed candidate.
The geometry checker checks each exact channel displacement/length, actual
parent TM1 coverage and absence of positive-area signal trunk overlaps, in
addition to the original primitive/placement/reference checks and fault controls.
All native deep/flat LVS, DRC and injected faults remain required. The hosted
workflow tx-v5-fast-stage-isolated-assembly-cloud performs these gates; until
that evidence passes, the candidate is unaccepted. Full PHY remains open.
