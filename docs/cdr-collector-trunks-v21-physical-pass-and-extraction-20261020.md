# CDR collector routing: native physical pass, new extraction required

Run39440691879 at4446725afb079d53c9f707c92fc4cfb2a94e31a7 passed
560-category native DRC with zero markers, unsimplified deep/flat484-device
transistor LVS and all nine original circuit/physical faults. Serialized
geometry and all16native child placements/eight child drawings pass their
independent controls. New GDS SHA256:
3fdfff892b3c84d78349c7358699dfa2ec8fd98a98b887573beb4f4b3219c936.

A/B groups reuse disjoint vertical spans in columns x959.6/954.6um. This removes
7761.4um of horizontal parent wire without changing any transistor, schematic,
native leaf drawing, public pin or LEF. Full native TM1 corridor analysis
rejects the previous measured AVDD short; the original failed candidate stays
preserved. This is a physical pass for the phase-detector parent only.

Fresh extraction must follow this GDS, never the old v20 values. The staged
cloud workflow retains all original158-plane/51-net/484-device/1394-terminal
checks, reachable primitive drawing/pin checks,946real anchors, native device
binding controls and13raw wire-RC corruption controls. Exact source deltas
allow only source identities and the new independently proven physical
routing contract. Original PDK/model methods and gates remain.

After extraction, rebuild actual11MIM plate/terminal composition, run raw
audits and original complete early/late waveforms with stopped-clock and
V/I-off controls. Old CDR sampling rejection is still open. No full PHY,
closed-loop operation, qualified RF/substrate extraction, mainchip integration
or final setup/hold acceptance is inferred from this native physical pass.
