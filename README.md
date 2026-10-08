# NSSOC — Building an Open-Source GR801 Counterpart

[![checks](https://github.com/Melihakbulut221/nssoc/actions/workflows/checks.yml/badge.svg?branch=codex%2Fcomplete-open-work)](https://github.com/Melihakbulut221/nssoc/actions/workflows/checks.yml)

**Our mission is to build an open-source counterpart to GR801 for space applications.**
NSSOC brings together fault-tolerant computing, neuromorphic acceleration and spacecraft interfaces. We are committed to completing this open-source GR801 counterpart, from RTL and software through
physical implementation, silicon validation and qualification. The product acceptance gates below define when that goal is achieved.

The current IHP SG13G2 implementation combines an Ibex RISC-V core, a spiking-neural-network accelerator, ECC-protected storage, memory scrubbing and TMR control. It forms the foundation for the product we are building.

## Product goal

GR801 is our product reference. NSSOC is an independent open-source design. Our development scope includes:

- Fault-tolerant processing and neural acceleration, protected memories, recovery and radiation qualification.
- SpaceWire, **PCIe Gen3 x4**, Gigabit Ethernet, CAN, I2C, SPI and UART, with controllers, PHY integration and software.
- Complete chip layout, characterized memories, padframe, clock/reset networks, power distribution and test access.
- Reproducible RTL, firmware, verification, physical flows and documentation under the [component licences](LICENSES.md).

Completion means meeting the integrated design requirements and [product acceptance gates](docs/92-product-acceptance.md):
functional verification, extracted setup/hold timing, full-chip DRC/LVS and antenna checks, manufacturing review,
silicon testing and qualification. Each result below records progress toward that goal within its verified scope.

![SoC functional architecture](docs/img/soc-architecture.svg)

## Recorded verification evidence

The [7 October recovery](docs/151-pcie-ci-resume-and-timing-results.md) fixes eleven failing PCIe RTL suites: 63 local port scenarios pass. The completed main-chip repair leaves 952 setup and 15 hold endpoints in a global-route estimate; final timing and full-chip LVS remain open. The [pump/filter measurements](docs/152-pcie-pump-current-characterization.md) complete twelve nominal points and full saved-waveform replay; loaded PLL reachability and lock remain open. The [V26 verdict-writer campaign](docs/153-pcie-verdict-writer-functional-validation.md) passes 45 finite functional predicates; the [V27 frontier repair](docs/154-pcie-frontier-epoch-quarantine.md) improves slow setup by 26.992 ps but still fails the 4 ns target.

Setup/hold and full-chip LVS, including the I/O tap mismatch, remain open; see the [closure log](docs/106-timing-repair-research.md).
These selected milestones retain their original revision and scope; they are not a combined signoff result. [Power layout and timing convergence](docs/138-pcie-power-layout-and-timing-convergence.md) records the supply-headroom repair, compact divider DRC/LVS, routed setup failures and failed PLL time-step comparison. [NPU initialization repair](docs/137-npu-initialization-reconvergence.md) records the reproduced clear-cone failure and mapped repair. The [complete repaired boot](docs/141-pcie-capacitor-layout-and-repaired-boot.md) passes MBIST and all 28 firmware checks; physical timing remains open. The [matched chip placement and routed receiver record](docs/142-chip-placement-and-routed-receiver.md) reports completed fresh chip routing with remaining timing failures and a 101 ps receiver setup improvement after detailed routing. The [receiver and chip prerequisite record](docs/140-pcie-integrity-and-chip-prerequisites.md) retains the V22 setup failure and adds a local matched physical runner gated by complete proof, exact SRAM mapping and successful repaired boot.

<!-- project-status:start -->
| Area | Measured status | Evidence |
|---|---|---|
| Silicon / product | No silicon or radiation qualification; product gates open | [Acceptance contract](docs/92-product-acceptance.md) |
| Frozen pilot | TTIHP26b submission; source tree frozen | [Freeze contract](docs/34-pilot-freeze.md) |
| Python regression | 1872 pass, 0 skip; commit `136119c` | [Exact revision and command](docs/evidence/local-ci-mbist-physical-guards-20260927.json) |
| Peripheral checks | 10/10 new formal tasks; 6/6 native RAM profiles | [Formal scope](docs/evidence/peripheral-formal-20260920.json); [RAM + negative control](docs/evidence/hosted-memory-parity-20260920.json) |
| Mandatory formal sweep | 170 PASS at `1baeb63`, 6 historical exclusions | [Dated source-bound inventories](docs/evidence/formal-170-local-20260926.json) |
| Independent native boot | PASS base + full at `1d99a78`; functional four-state simulation | [Hosted result and retained prior failure](docs/evidence/native-recovery-1d99a78-20260922.json) |
| Local native correction | PASS: 28 checks, 653,726 cycles; firmware `100cad7` | [Same hosted netlist, verified serial initialization](docs/evidence/npu-native-startup-20260921.json) |
| 32-SRAM core geometry | Main DRC, density, antenna and transistor LVS PASS; timing/product open | [Exact GDS and supplemental checks](docs/evidence/ethernet-mbist-core-physical-20260927.json) |
| Historical timing estimate | Setup -2.867 ns, hold -0.089 ns; not final-core STA | [Earlier route and electrical failures](docs/evidence/startup-native-corners-20260920.json) |
<!-- project-status:end -->
The [machine-readable status](docs/project-status.json) derives from [selected records](docs/status-sources.json).
Check with `python3 scripts/project_status.py`; update with `--write`.

The [SRAM characterization record](docs/101-sram-characterization.md) documents core repairs and measured patterns.
Qualified coupled RC, complete SRAM timing/power libraries, final SoC timing,
PCIe PHY/padframe integration and manufacturing approval remain open.

SpaceWire, classic CAN, SPI, I2C and the Gigabit GMII PIO MAC have RTL and profile-specific layout evidence.
**PCIe Gen3 x4 remains open:** an optional [packet profile now shares GPIO/APB with the real CPU](docs/110-pcie-local-flow-and-clock-layout.md). The VCO and four-lane clocked sampler bank have separate DRC/LVS evidence; PLL/CDR, full SERDES/PCS/LTSSM and serial PHY/main-chip physical integration remain open. The [physical PCIe record](docs/143-pcie-divider-and-routed-transmitter.md) records the completed V18 long-packet regression, routed transmitter improvement and remaining divider and packet-integrity failures. The [loaded-divider study](docs/145-pcie-divider-time-step-and-prefix-timing.md) preserves earlier step failures and the rejected V24 packet-integrity timing regression. The [loaded PLL capture controls](docs/150-pcie-loaded-pll-observation-controls.md) pass 49 current observation/storage/lifecycle checks and twelve separate source-composition checks; the 2 ps startup control does not establish a functioning or locked 570-instance PLL. The [V25 command-pipeline study](docs/149-pcie-command-pipeline-timing-rejection.md) passes 43 current functional tests but regresses slow-corner setup to −3.421986 ns; it is retained as a rejected candidate. The [adjacent-step verification](docs/147-pcie-loaded-divider-numerical-agreement.md) now passes the fixed 100 ppm/50 ps checks at 0.625/0.3125 ps, with all 455 device screens and thirteen finite functional checks passing; this is one nominal open-loop point, not PLL lock or clock qualification. The [local capture update](docs/146-pcie-local-pll-capture.md) separates PLL simulation from network publication, with 69 passing current controls; the new acquisition run remains incomplete. The [publisher follow-up](docs/148-pcie-local-publisher-log-race.md) fixes a concurrent log-file race with 31 passing controls; the independently running simulation survived the publication failure. The [preceding transport repair](docs/144-pcie-publication-recovery-and-incomplete-pll.md) preserves the interrupted run as an error. Qualified clocks/RC, complete PHY and main-chip physical integration remain open.
UART has [8N1 RX/TX and CPU tests](docs/97-uart-receive.md), with its updated whole-SoC layout pending.
Ethernet needs an external PHY and has no DMA.
The complete GR801 interface set is not implemented.

The [product acceptance](docs/92-product-acceptance.md) and [second audit](docs/96-second-audit-closure.md) registers track remaining gates.
Earlier claims and corrections remain in [HISTORY.md](HISTORY.md), with a [migration digest](docs/evidence/readme-migration-20260920.json).

## Reproduce

Use Linux, Python 3.12 or 3.13, `make`, Git, a C compiler and `tclsh`. Start with `make help`.

```sh
make setup PYTHON=python3.12
make -f tools.mk fetch-oss-cad-suite PYTHON=python3.12
make -f tools.mk toolcheck
export PATH="$PWD/hw/soc/tools/oss-cad-suite/bin:$PATH"
make test
make rtl-test
make check
```

The installer verifies the pinned 2026-08-04 archive and preserves existing installations. Allow about 4 GB;
`OSS_CAD_SUITE=/absolute/path` selects another checkout. Physical tools/PDK are separate.

Local `make check` covers Python, licensing and documentation; hardware jobs are separate. Missing dependencies produce skips.

```sh
make soc-prepare
make soc-prepared-guards
make soc-sim
make soc-memory-parity
```

The default `SOC_INTERFACE_PROFILE=base` includes I2C/Ethernet and SPI. Set `SOC_INTERFACE_PROFILE=full`
for LGPL SpaceWire/CAN in preparation and every subsequent build command. See [interface profiles](docs/88-interface-integration.md).

On a prepared checkout, `python3 scripts/check_formal_sweep.py` runs formal checks with source guards and explicit exceptions.
RTL, RAM parity, formal and processor/boot jobs remain separate; whole-netlist native boot is a long-running workflow option.

The [pilot driver](sw/pilotlink/README.md) supports cocotb, serial and RP2040 SPI backends. Physical-board qualification remains open.

The [SoC datasheet](docs/60-soc-datasheet.md), section 0.4, describes implemented interfaces, profiles and verification limits.
Older measurements retain their original revisions; the [errata index](docs/ERRATA.md) links corrections and reproduction paths.

## Repository map

| Path | Contents |
|---|---|
| `hw/rtl/`, `hw/tb/`, `formal/`, `tt/` | Frozen pilot sources and verification; [freeze rules](docs/34-pilot-freeze.md) |
| `hw/soc/` | SoC RTL, firmware, verification and physical flows |
| `sw/golden/`, `sw/tests/`, `sw/pilotlink/` | Integer models, regression tests and host driver |
| `regmap/` | Register and memory-map specifications and generators |
| `docs/` | [Numbered technical index](docs/00-index.md), evidence and acceptance registers |
| `paper*/`, `thesis/` | Papers and thesis sources; claims require their recorded evidence |

## Licensing and citation

This repository is a published subset of a private development tree. See the [mirror contract](docs/78-the-public-mirror.md) and HISTORY.md for provenance.

The licence decision was **signed 2026-09-09**; see [LICENSES.md](LICENSES.md) for components and exceptions.

| Material | Project licence |
|---|---|
| RTL, verification HDL, formal configurations | CERN-OHL-W-2.0 |
| Software, generators and flow drivers | Apache-2.0 |
| Documents and measurement records | CC-BY-4.0 |

Fetched IP retains its own licences, including LGPL/MIT/Apache; SPDX and REUSE checks cover the distribution.

Use [CITATION.cff](CITATION.cff) and the exact commit; there is no release DOI or qualified silicon release.
See [CONTRIBUTING.md](CONTRIBUTING.md) for development, [SECURITY.md](SECURITY.md) for reports, and [CHANGELOG.md](CHANGELOG.md) for changes.
