<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# PCIe Gen3 x4: implementation dependencies

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
