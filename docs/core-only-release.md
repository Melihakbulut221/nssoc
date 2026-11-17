# Core-only release scope

The user removed PCIe and Ethernet from this release on 2026-11-17.
The 2–3 week target is a work target, not a production-readiness claim.

SOC_RELEASE_PROFILE=core-only, SOC_PCIE_PROFILE=off and SOC_ETH_SRAM=0
remove PCIe and Ethernet ports, clock domains, controller logic and Ethernet
FIFO SRAMs. The Ethernet APB address remains reserved and returns an error.
The legacy configuration remains reproducible for historical evidence.

Retained: Ibex, system SRAM and MBIST, SpaceWire, I2C, CAN, SPI, UART,
GPIO, QSPI, watchdog and existing protection logic. Use the full interface
profile so SpaceWire and CAN are implemented.

The initial CPU target remains 50 MHz (20 ns); no fabricated timing
exceptions or reduced voltage/temperature coverage are introduced.
New synthesis, boot, floorplan, CTS, routing and signoff evidence is required.
Previous PCIe/Ethernet timing and layout evidence does not qualify this design.
SRAM internal LVS/characterization, extracted timing, pad/ESD/DFT and foundry
approval remain mandatory where applicable. Removed-interface tests must
not be reported as passing tests of this release.
