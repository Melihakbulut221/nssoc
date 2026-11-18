# External I/O constraints and postroute antenna checkpoint — 2026-11-18

The user confirmed that the package, PCB and connected devices have not been selected. No QSPI memory model or SpaceWire/SPI/QSPI interface speeds were supplied. These remain unresolved design inputs, not timing waivers. Do not invent production input/output delays or claim external I/O timing closure. Continue internal implementation independently. The 50 MHz / 20 ns clock and existing 5% derate remain unchanged. PCIe and Ethernet remain excluded from the approved reduced scope.

## Verified antenna diagnosis

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44380476158 completed successfully at source 7029a266667f4c482a08fbc5a46c2cdd1a92fe0a, but is a read-only diagnosis, not successful chip signoff.

Artifact 14463487064 SHA-256: 5889d2bdbca4b709c35ddaf7f188eb8297d9b4758e8927199b7e4345f36dff40. Archive digest and all seven output hashes were verified. Source database was unchanged. The source route run 44337630426 failed its antenna gate after completing native routing: native routing DRC 0, antenna nets 363, antenna pins 399. Multiple layer rule violations can affect the same pin.

Layer rule records: Metal2 54; Metal3 189; Metal4 175; Metal5 27; TopMetal1 62.

Pinned OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 exposes repair_antennas with diode_only and jumper_only options. In src/grt/src/GlobalRouter.cpp, repairAntennas performs jumper insertion only when detailed routes are absent. For a detailed-route database, jumper_only also suppresses diode insertion. The previous route's jumper-only setting therefore cannot repair these postroute violations through this routine.

## Next experiment, not yet dispatched

Use the authenticated routed database as input for diode-enabled postroute repair and subsequent detailed routing. Preserve the source artifact. Explicitly audit inserted antenna cells, movement of existing cells, terminal connectivity, power connections and resulting wire geometry. A repair may legalize/move cells; unchanged placement must not be assumed. Recheck native DRC and antennas and perform fresh RC extraction and setup/hold analysis. The existing extraction workflow's successful-source admission must not be bypassed to accept the failed antenna source. No repair, postrepair timing or production acceptance is claimed by this checkpoint.

See core-only-posteco-antenna-failure.md for the source route identity and admission details. Native diode model convergence research is a separate open pad-timing investigation; it does not waive the 22 slow-corner pad slew violations.
