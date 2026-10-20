# Native full32 plus64 input drivers: physical gates passed, new RC required

Run39466552523 passed all mandatory physical gates on the actual combined layout: full560-category DRC with zero markers, deep and flat LVS matching all8074 devices, and exact163-name external interfaces. Real handoff-open, substrate/supply-short, MOS-width and offgrid faults were rejected. The actual extraD0P port was rejected by the independent exact-interface gate while the native circuit comparer success remains reported. All five parser corruptions also rejected.

This proves this driver/core assembly within the locked native physical check scope. It does not prove full serial PHY, qualified PEX, electrical operation or mainchip integration. The layout contains589 HBTs,5376 MOS,504 rppd,1477 ptap1 and128 ntap1. The four-lane/whole-chip budget remains separate.

Fresh extraction starts from exactGDS9583c6cf7f70d4dad4736b808535ef564bed11d0730ce4674314025d0beaebdb and its matched flat LVS database. The original native metal/via graph method changes only source paths, exact device/port census and reporting names. All actual union, native layer equality, conductor ownership and terminal coverage checks remain.

The independently expected conductor census is377 core conductors +64*10 driver conductors -64 data handoff merges -192 shared AVDD/AVSS/substrate merges -63 shared DVDD merges =698. With common substrate and64 distinct wells, there are763 electrical nets. All28582 device terminals must be represented. The fresh graph must establish these numbers before terminal anchors, complete RC extraction,13 raw corruption controls and full native model composition. Existing per-child RC cannot stand in for this combined layout.
