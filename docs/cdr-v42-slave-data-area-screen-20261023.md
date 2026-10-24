# CDR v42: C/D slave data/hold area screen — 2026-10-23

The source-bound v41 diagnosis run39935675031 reproduced all120 HBT and all4 sampler results from all four rejected complete native captures. Its followerNx8 early capture has zero master-output misses at the original deadline in both C and D, but65/97 slave-output samples below the original100mV gate. Each of255 source transitions is uniquely observed. These observations locate a remaining settling problem; they do not prove a causal aperture model or electrical acceptance.

The two new hypotheses change only the eight actual C/D slave data/hold HBTs fromNx6 toNx4 orNx5, retaining the exactv41follower_n8 parent. Smaller intrinsic area may reduce loading, but it also changes current density and voltages; no pass is predicted. The original geometry usedNx4 for these devices: returning them toNx4 removes eight of80 original parameter changes, leaving72; Nx5 leaves80. A/B, C/D master devices, every selector, retimer followers, bias/resistor/MOS parameters, all476 devices,17918R/12850C, actual terminal identities and connections remain unchanged relative to that parent.

The selected devices must match the actual diagnosed slave graph, including source inputs, output collectors, common emitters and cross-coupled hold pair. Five scalar and eight actual-graph corruption controls reject wrong models, identities, terminals, duplication or parent areas. All original34.25ns clocks/loads and data/device/phase/VI gates remain unchanged. A-channel margin and XOR/phase failures remain visible; improving C/D alone cannot pass this screen.

Fresh read-only source preflight now uses the wrapper proven in39930946907 and independently compared against870 identical files and original success markers in39933826243. It runs before and after each native case in separate Python processes; report bytes are retained. It never caches native or electrical outcomes.

This is a frozen-wire-RC exploratory simulation. Any useful electrical result still needs actual candidate GDS, full DRC/LVS, fresh extraction, PVT, full CDR loop and serial/mainchip validation. No result is labelled full PHY acceptance.
