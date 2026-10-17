# Complete retimed PD physical candidate — 2026-10-18

The source-bound eight-child handoff includes35-device sampler proof39068644438, both buffer proofs39067291672, all three feed-forward proofs39067622805, XOR parent39048145296 and V/I leaf39063135809. Restoration verifies summary/parts hashes, every selected layout file, all560 native DRC rules and deep/flat unsimplified device counts. Plan39069071644 binds all41 native source cards into16 physical instances.

The generator copies actual GDS, verifies conservation on all non-port-annotation layers, strips only metal pin annotations, and draws finite TopMetal1/2 buses with native via-stack PCells. Signal trunks are3.2um wide; AVDD/AVSS/SUB are64um with multiple bus vias. Child references flatten to122HBT/102rppd/11MIM/159contacts=394 with a common physical BULK node. Parent native DRC/deep-flatLVS and five actual/reference faults are mandatory.

First run39069553921 completed FAILURE before parent DRC/LVS: sampler QP/QN are actual right-edge Metal5 pins at x878..880um, but the initial generator accepted only right TopMetal2 pins. The correction adds Metal5 escape and the native Metal5-to-TopMetal2 via stack outside those two specific sampler pins. Existing XOR right ports remain TopMetal2. Interior/unknown right pins remain rejected. Complete failed report is preserved.

Source review also found a coordinate bookkeeping issue: centering the3.2um public wire at x0 would overhang to x=-1.6 and require a translation that invalidates placement metadata. Wires now start at x1.6 so the edge is exactly0. Post-routing translation is removed. An attempted queued-run cancellation was prevented by the live-state guard because the job had started; no cancellation request was sent, and the run completed normally with its failure preserved.

This first complete parent remains a physical connectivity candidate. Fresh RC, delay, current density, power distribution, PD loading and VCO feedback/acquisition require verification and likely layout optimization. No fullPHY or mainchip timing pass is implied.
