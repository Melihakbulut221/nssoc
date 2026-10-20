# PLL845 remaining MOS rail reference investigation — 2026-10-20

All work and native CAD run on GitHub-hosted runners. The local NSSOC directory remains empty.

The previous native run39348680934 resolved every resistor end (178), all102 HBTs and all52 MIM plates.1830 terminals had actual metal references,819 intrinsic body/well identities and58 shared nonmetal diffusion identities were retained.30 MOS rail terminals remained unresolved. All235 wire components were covered. This failed result is retained, not replaced with a success claim.

The pinned IHP general_derivations.lvs and general_connections.lvs explicitly connect unblocked salicide along a shared edge between S/D diffusion and an adjacent opposite-type tap. The new candidate checks the original GDS active, implant, well, gate and salicide-block polygons; requires a positive-length common edge, one contiguous actual region and a real local tap contact on metal1; and independently re-probes both the native LVS owner and the extracted wire-component owner. It rejects ambiguous tap regions and uses no global-net-name alias or arbitrary remote contact.

All30 formerly unresolved references must be proved. The native runner must reject three physical corruptions for each reference: block the shared salicide boundary, remove the local tap contacts, or remove the tap's opposite implant. The eight previous terminal controls remain mandatory. Source GDS, LVS and wire data are immutable.

This binds reference locations only. Salicide/diffusion access resistance, substrate spreading, complete whole-PLL RC and electrical acceptance remain unqualified. The original819 body references and58 shared diffusion references remain explicit limitations. No full PHY, mainchip timing or production acceptance follows from this check.

PDK source: https://github.com/IHP-GmbH/IHP-Open-PDK/tree/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/tech/lvs/rule_decks

## Native result

Run39350440897 at sourceece13196ca044e4f8beb18b043fae6a679f9de54 completed successfully. Native CAD exit0, immutable source checks passed, unresolved references0. All2737 terminal identities are accounted for:1860 actual metal references,819 intrinsic body/well identities and58 shared intrinsic diffusion identities. Including17 public ports,1877 probe references cover all235 physical wire components.

All30 previously unresolved MOS rail references have actual salicide-edge/tap/contact proofs. Each of the three physical mutations was rejected at all30 references (90 geometry cases), and all eight earlier terminal corruption checks passed. The full4.71MB report, native databases, logs and proof polygons are retained in the cloud release; the repository stores compact immutable pins.

This closes missing terminal-reference locations, not whole-PLL RC qualification or full PHY acceptance. Body spreading and poly/diffusion/salicide access resistance remain explicitly unmodeled.

- [Native run](https://github.com/Melihakbulut221/nssoc/actions/runs/39350440897)
- [Immutable result release](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-39350440897-1-pll845-terminal-references)
