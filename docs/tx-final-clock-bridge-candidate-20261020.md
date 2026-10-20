# Physical differential load candidate for the final TX selector

The exact wire24 waveform has four failed final selector HBTs (xd0109–xd0112) and two failed final tail HBTs (xd0114–xd0115). The original minimum VCE requirements remain unchanged at 0.4 V. The worst recorded selector VCE is 0.356461 V; tail minima are 0.381433 and 0.379991 V. Their extrema occur at different times. The complete rejected capture and native path review remain pinned in the evidence directory.

Lowering the common clock bias can improve a selector while reducing its tail's collector headroom. The proposed separate experiment instead adds a physical differential resistor between the final sp/sn clock terminals. The original source PWL amplitude, phase, edge times and 25-ohm source impedances will remain unchanged; any attenuation must arise from the actual added device and its extracted wires. A changed stimulus or a relaxed voltage bound is not equivalent evidence.

The first implementation step generates an IHP native rppd with W=6 um, L=1.2 um and one explicit ptap1 substrate contact. The substrate remains distinct from both clock terminals. Native schematic, GDS and LEF are generated together. This is a new two-device macro, not an already-integrated whole PHY.

The cloud verifier retains the pinned full 560-category DRC deck, deep and flat native LVS, literal two-device and three-port census, and six real faults: wrong width, wrong length, missing resistor, opened clock port, bridged clock ports and off-grid drawing. Each fault must be rejected by the native tool for the expected reason.

The two-device macro must subsequently receive fresh native terminal extraction, finite body/contact binding, complete conductor RC and compact-model checks. Only then can it be composed with the unchanged failed full32 tree and evaluated against all original bits, phases, interfaces and 604 HBT/512 MOS bounds. Loading can reduce steering gain or slow edges; no improvement is claimed from the proposed divider alone.

This final-stage experiment is independent of the groups2/3/4 lower-bias candidate in run39372036289. Keep the sources and outcomes distinct until both are measured. PLL run39370629792 and mainchip route39369450310 remain separate live workstreams. All CAD and retained outputs are cloud-only.
