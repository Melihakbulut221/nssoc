<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# 91 — PCIe Gen3 x4: implementation dependencies

Research date: 2026-09-19. The requested target remains Gen3 x4. No PCIe
controller or serial PHY is instantiated in `soc_top`, and no existing GDS
contains a PCIe link. This investigation does not close that implementation item.

## Reference and candidate assessment

[Gaisler's GR801](https://www.gaisler.com/products/gr801) targets PCIe Gen3 x4
with Root Port and Endpoint modes, Gigabit Ethernet and ST 28 nm FDSOI. Its
product page describes a development project. The present SG13G2 Ibex SoC is
not an implementation of that processor or a drop-in equivalent.

| Candidate | What is available | Decision for this ASIC |
|---|---|---|
| [Synopsys PCIe 3 PHY](https://www.synopsys.com/designware-ip/interface-ip/pci-express/pcie3-phy.html) | Commercial multi-lane PHY with x4 support, equalization and associated controller/VIP portfolio | Technically relevant supplier candidate. Public information does **not** establish SG13G2 availability, license, price or delivery time. |
| [Rambus/Snowbush Gen3 PHY](https://www.rambus.com/semtechs-snowbush-ip-family-now-includes-new-ultra-low-power-ultra-low-latency-pci-express-3-0-phy-ip-platform-expanding-storage-server-markets/) | Historical announcement names TSMC 28 HPM and earlier 40 nm implementations | Evidence that commercial Gen3 PHY IP exists; not evidence of a current SG13G2 deliverable. |
| [Rambus PCIe 3.1 controller](https://www.rambus.com/interface-ip/pci-express/pcie3-controller/) | Commercial ASIC/FPGA controller with Endpoint, Root Port and PIPE configurations; AXI variant available | Additional controller supplier candidate checked 2026-09-20. It still requires licensed RTL and a compatible PHY; public material does not establish an SG13G2 physical implementation. |
| [verilog-pcie](https://github.com/alexforencich/verilog-pcie) | TLP, AXI, DMA and vendor FPGA PCIe interface modules | Useful application/controller-side logic. FPGA hard PCIe blocks remain necessary; this is not a complete ASIC PHY/link implementation. |
| [LitePCIe](https://github.com/enjoy-digital/litepcie) | FPGA PCIe integration, DMA and host software; UltraScale support includes Gen3 | Candidate for a separate FPGA prototype, not a portable analog PHY. |
| [openCologne-PCIE](https://github.com/chili-chips-ba/openCologne-PCIE) | GateMate-oriented Gen1 x1 project | Does not meet the requested generation or width. |
| [OpenSerDes](https://arxiv.org/abs/2105.13256) | Research serial link in SkyWater 130 nm, with reported 2 Gb/s post-layout simulation | Neither the requested 8 GT/s per-lane rate nor a verified SG13G2 PCIe Gen3 x4 PHY/controller; a portable research SerDes is not a qualified PCIe link. |
| [TI XIO1100](https://www.ti.com/product/XIO1100) | Discrete single-lane 2.5 Gb/s PCIe PHY | Does not meet Gen3 x4. |

The [IHP reference library inventory](https://ihp-open-pdk-docs.readthedocs.io/en/main/contents/01_libraries.html)
and the installed PDK at `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`
provide device, standard-cell, IO and SRAM resources. No ready PCIe Gen3 PHY
was identified there. This is a finding about available IP, **not** a claim
that the underlying BiCMOS process cannot support a custom high-speed circuit.

[PIPE](https://www.intel.com/content/www/us/en/io/pci-express/phy-interface-pci-express-sata-usb30-architectures-3-1.html)
specifies a PHY/controller boundary; it does not supply either implementation.
Likewise, [AMD's exposed PIPE simulation interface](https://docs.amd.com/r/en-US/xapp1184-pipe-mode-pcie/Introduction)
connects a verification model while bypassing transceivers. It is not a board-level
external PHY port. A PCIe switch or retimer also cannot supply an SoC's missing
Endpoint controller merely by attaching to its serial pins.

## Viable routes and the boundary that remains open

For **on-die PCIe**, obtain a licensed controller and a PHY qualified for the
selected process, or commission a PHY port/custom design. Acceptance requires
the actual RTL/netlist, GDS/LEF, PVT Liberty, power/reset/clock constraints,
package/channel requirements, simulation models, integration license and
verification material. Gen3 equalization, lane bonding, reset, reference-clock
mode and fallback to lower rates must be covered. Root Port support should be
retained in the supplier requirements to match the cited reference; it must not
be inferred from an Endpoint-only core. No supplier has been contacted or
purchase made as part of this research.

For an **external FPGA demonstrator**, an appropriate UltraScale/UltraScale+
device and verilog-pcie or LitePCIe can terminate Gen3 x4 and bridge buffered
transactions to this SoC. This changes the board architecture and leaves the
ASIC itself without PCIe. A specific board, host interface, DMA/interrupt design
and driver must be selected and tested before this route becomes an implementation.

The bandwidth mismatch is independent of PHY choice: 32 bits at 50 MHz gives
an ideal **200 MB/s** internal-bus upper bound before stalls. Gen3 x4's
8 GT/s/lane with 128b/130b encoding gives approximately **3.94 GB/s** per
direction before packet overhead. These are calculated ceilings, not measured
throughput. A PCIe register adapter alone cannot make the present memory system
consume that rate; sustained transfers need a wider/faster datapath and DMA.

**Disposition:** no verified, freely accessible SG13G2 Gen3 x4 controller/PHY
pair was found. The on-die implementation remains dependent on actual IP and
physical views. An empty blackbox or constant link-up signal would not close it.

## IHP-specific follow-up — 2026-09-20

The [European Commission's VHiSSI final report](https://cordis.europa.eu/project/id/284389/reporting)
documents an ACE-IC SerDes integrated with STAR-Dundee's SpaceFibre logic and
Ramon Chips' libraries on IHP's 130 nm process. It reports operation at the
2.5 Gbit/s design target; the 3.125 Gbit/s experiment had an unacceptable eye.
This is evidence of a manufactured IHP serial-link design. It does not supply
an accessible SG13G2 PCIe Gen3 x4 controller/PHY, its integration views, or
PCIe qualification. Compatibility with this repository's exact open PDK and
availability of licensed design files remain unverified.

STAR-Dundee's [STAR-Ultra PCIe datasheet](https://www.star-dundee.com/wp-content/star_uploads/product_resources/datasheets/STAR-Ultra-PCIe.pdf)
separately specifies a Gen3 x8 host interface on a complete SpaceFibre board.
A board product is not a downloadable ASIC PHY macro. Neither finding closes
the integration requirement above; no external bridge architecture, IP purchase,
or vendor contact has been initiated.


## Project-authored digital work — 2026-09-22

The user requested implementation rather than waiting solely for third-party
IP. [The new transaction-layer register backend](98-pcie-transaction-backend.md)
implements a tested configuration/BAR0 subset and single-DWORD APB transactions.
It is an independently built block; no instance is connected to `soc_top` and
no PCIe link is present in any layout. Full Endpoint/Root Port, DLL/LTSSM and
Gen3 x4 PHY development and qualification remain open. This update changes
"no project-authored digital block" into a measured partial implementation,
not the controller/PHY integration verdict above.

## Custom PHY feasibility reassessment — 2026-09-22

The absence of a ready macro is an integration dependency, not a reason to
exclude development of a project-owned PHY. The user explicitly requested
research into designing it. The following evidence makes a custom SG13G2
development path worth investigating; it does not establish a working PCIe IP.

### Evidence beyond the earlier supplier search

* Christian Bohn's 2024 KIT dissertation,
  [Broadband Circuits for High-Speed Short Reach Optical Transceivers](https://publikationen.bibliothek.kit.edu/1000170334),
  section 5.1, printed pages 91–102, describes a **fabricated and measured
  10.4 Gb/s 8:1 serializer in SG13G2**. It combines CMOS stages with a
  BiCMOS current-mode final multiplexer. The test uses an external clock;
  the transmitter targets CEI-11G-SR. The measured-eye result is evidence
  for high-speed serialization in this process, not for a PCIe receiver,
  clock recovery, integrated PLL, compliance or radiation qualification.
  No reusable, licensed layout/netlist package for that circuit was located
  in the inspected thesis repository record.
* The [IHP Open PDK](https://github.com/IHP-GmbH/IHP-Open-PDK) supplies MOS,
  HBT and passive models for analog simulation. Those model families also
  exist in this project's pinned PDK. They support investigating custom
  circuits, but transistor transition-frequency figures do not prove a
  complete link's bandwidth, jitter, power or yield.
* [OpenSERDES](https://github.com/SparcLab/OpenSERDES) actually publishes
  serializer, receiver/CDR and physical design files. Its
  [paper](https://arxiv.org/abs/2105.13256) reports **2 Gb/s post-layout
  simulation in SkyWater 130 nm**, not measured SG13G2 Gen3 operation.
  The repository identifies GPL-3.0 licensing. It is a research reference;
  its files have not been imported into this project.
* A [2026 SG13G2 LC-VCO/PLL publication](https://arxiv.org/abs/2607.08852)
  and its [design repository](https://github.com/Manimohan05/SG13G2_2.4GHz_LC_VCO_FPLL)
  provide an additional clock-design reference at 2.4 GHz. The inspected
  repository tree `18822c15f453cc394dc4869547ad4185ec55ef12` contains
  schematics, GDS and verification report paths. File presence is not an
  independently reproduced PASS; GitHub did not identify a repository
  license. Reuse rights and suitability for a PCIe clock remain unresolved.
* The [JKU SG13G2 analog/mixed-signal tutorial](https://iic-jku.github.io/ihp-sg13g2-ams-chip-template/index.html)
  documents schematic simulation, mismatch characterization, layout,
  DRC/LVS and parasitic extraction using open tools. This supplies a
  development workflow, not a high-speed PHY implementation.

### Proposed development sequence and acceptance boundaries

This is an engineering proposal, not a measured architecture or schedule.
Start with one lane and establish its electrical behavior before replicating
it four times or assigning a final SoC floorplan region.

1. Derive the electrical, clocking, channel and training requirements from
   the applicable PCIe/PIPE specifications. Maintain traceable requirements
   and test vectors. Public summaries alone do not supply every limit.
   [PCI-SIG's Gen3 FAQ](https://pcisig.com/faq?field_category_value%5B%5D=pci_express_3.0)
   identifies 8 GT/s signaling and negotiated equalization; an arbitrary
   fast serial connection cannot substitute for those behaviors.
2. Characterize SG13G2 transistor-level current-mode latches, multiplexers,
   level conversion and programmable differential TX stages. Compare
   full-rate/half-rate clocking and voltage domains using actual models;
   do not extrapolate standard-cell RTL timing to the serial pins.
3. Develop termination, receiver detection, electrical-idle handling,
   equalization, sampling/CDR and reference-clock/PLL circuitry. Use channel
   models and PRBS tests, including noise, jitter and PVT/mismatch sweeps.
   Receiver topology and equalizer complexity must follow these measurements.
4. Lay out the lane and clock macros; run device-level LVS, DRC, extraction
   and post-layout analog/channel simulations. High-frequency interconnect,
   package, pad/ESD and power coupling need appropriate models, including
   electromagnetic analysis where lumped RC is insufficient.
5. Integrate four lanes with the digital PCS/controller, lane alignment,
   Gen1/2 fallback, training and reset/power states. The existing DWORD
   transaction adapter is only one small part of this implementation.
6. Produce GDS/LEF, CDL/SPICE, characterized digital-boundary timing views,
   behavioral/channel models and integration constraints from the verified
   circuit. Liberty alone cannot describe analog link acceptance. Fabricated
   test silicon and suitable measurement equipment are required to establish
   measured silicon performance and compliance.

The agent can develop and exercise the design files, simulations, automation,
layout and integration checks with available tools and models. A successful
Gen3 PHY cannot be promised before those checks; fabricated-device behavior
cannot be established from generated files. This investigation has not added
a PHY, run a new transistor-level simulation or changed the SoC layout.

**Updated disposition:** custom PHY R&D is a technically motivated path,
supported by published SG13G2 serializer measurements. A ready, qualified
SG13G2 Gen3 x4 PHY has still not been found or implemented. Treat its design
and characterization as remaining work, not as an impossible process feature
or an already integrated macro.
