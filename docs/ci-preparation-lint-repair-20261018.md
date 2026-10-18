# Hosted CI preparation and diagnostic location repair

The archived CI evidence inspected by cloud run 39092549976 identifies two failures. RTL run 39088317644 passed 1168 tests but could not start `soc_pcie_ethernet`: its preparation installed only interface IP, while the actual CPU test requires generated and fault-port-patched Ibex RTL. The RTL job now calls the existing `soc-rtl-prepare` target. No suite was skipped or acceptance threshold changed.

The base lint result from run 39089804846 has return code zero, unchanged sources, no immutable drift, and no unaccepted owned warning. Its only diagnostic delta is the existing `sec_seen`/`ded_seen` UNUSEDSIGNAL pair moving from lines 699/700 to 725/726 in `ibex_regfile_secded.v`. The eight ledger profiles retain identical warning identities and multiplicities with these two source locations corrected. No RTL behavior or warning class is changed.

The focused hosted workflow reruns both base/full lint and the actual asynchronous PCIe/Ethernet joint CPU test with the pinned OSS CAD suite. Success requires the original two passing, zero failed, zero skipped integration tests and unchanged source/runtime checks. A dispatch is not proof of a pass; inspect the published result. This does not qualify serial PHY, layout, or timing.

The compact PD394 native MIM capture 39092549964 independently completed with 9655 resistors, 7555 capacitors, eleven explicit intrinsic MIM devices, 111 wire components and 776 points. Its raw-wire and intrinsic identity audit is the next gate. The corrected geometry has not yet passed the original loaded waveforms.

## First focused result and preparation follow-up

Hosted run 39093269754 passed base lint and the actual asynchronous joint CPU/PCIe/Ethernet test. The added full lint profile failed before elaboration because the focused workflow prepared only the default base interface bundle. Its log identifies missing `hw/soc/gen/interfaces-full.bundle.json`. The workflow now additionally calls the existing `soc-interfaces-prepare SOC_INTERFACE_PROFILE=full` target. All three checks rerun on fresh outputs; no validator or source-warning acceptance changed. The failed report and archive are pinned in `ci-prepared-rtl-lint-first-20261018.json`.
