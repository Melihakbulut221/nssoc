# Timing-priority physical TX placement candidate

The measured minimax parent passed native DRC/LVS, but its unchanged full loaded test rejected123of768samples and24HBT minimum-VCE cases. Final input groups a/b and level4 inputs failed while level8/16 inputs passed. The31native clock paths have no unmatched edge events and only about1.114ps maximum paired edge bracket delay. This does not establish causality, but it does not support a clock-routing repair.

The next candidate prioritizes real data routes by receiver stride: weights16/8/4/2 for receivers f,a/b,p4,p8. This is a geometry proxy for shorter available intervals, never a fitted bit phase or claimed delay model. Optimize the maximum weighted native route length, then weighted total length at that optimum. Keep all16leaf rows and final row fixed, all macro X coordinates, the600um row lattice/separation, child drawings,719reference emitters/1674devices,rails,bit topology and clock sources.

Every route remains below the original independent geometric ceiling of80percent of the pre-minimax maximum. A solver reserve computed over every permitted rail-aware track bounds channel reassignment, with the actual drawn result checked independently. The weighted maximum and final-stage maximum must improve against actual minimax geometry; every lengthened upstream leg is listed. Analytic continuous and integer weighted-chain controls supplement the original solver controls. No native DRC/LVS or electrical threshold changes.

Actual GDS generation,560categoryDRC,deep/flat1674deviceLVS and all original faults must pass. Then fresh native RC, topology equivalence and the original loaded waveform/voltage/current tests are required. Shorter weighted wires alone do not prove fullGen3x4 or mainchip timing.
