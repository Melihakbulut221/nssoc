# Fresh native extraction for the physically passed v31 CDR

Parent39718154517 atf6a7300ee045ab435546c7b1b31290946a9c0882 passed full476-device DRC/LVS and actual child geometry. The new GDS is0cd831dd0ac1dc05554ebb02c9dccfa50ad6b22833e8e296b6a564d155ac847c. Exactly four follower pull-down resistor references changed. All original parent polygons, labels and transforms were retained.

This workflow regenerates all160 native interfaces/51 nets, whole conductor graph,476 intrinsic devices/1382 terminals and938 reference points, then physical model bindings and native RC. No v30 parasitic values are reused.

The existing v30 baseline controls remain active. The new parent validator checks the exact new leaf/parent evidence and all26 source corruptions, including retained historical M4 repairs. Native extraction, geometry recovery, terminal binding, native fault checks and RC bodies remain unchanged. Intrinsic MIM audit/composition and the full loaded waveform matrix follow the measured fresh RC census; geometry alone does not establish electrical acceptance.
