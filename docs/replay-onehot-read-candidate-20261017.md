# Replay read-path candidate from actual native STA

Native path extraction39057107220 on the exact CRC-repaired netlist reports worst slow setup -7.853238ns from retry.read_pos[5] to pcie_tx_data_o[4]. The binary address traverses decoding, substantial fanout buffering and memory selection. The PCIe4ns clock and external output requirement remain unchanged.

scripts/cloud_replay_onehot_candidate.py builds an unadopted candidate from canonical replay SHA1a15c0b9d6cfdfbf5ebed9a61c52901e126ca826008d167ff96bea4218a8f4dc. A registered one-hot cursor follows the original binary cursor: reset/start selects bit0; a successful nonfinal transmit rotates by one, including binary wrap; stalls, link loss and all other states hold exactly as the binary cursor does. Each byte selection is an AND/reduction over that register, retaining flat cross-bank addresses and undefined out-of-array behavior. There is no added transaction latency, changed throughput or constraint relaxation.

GitHub checks DEPTH/MAX_BYTES=(2,18),(3,38),(4,38). Arbitrary memory cuts cover every defined slot/address, including cross-bank reads, with actual inverted-bit and wrong-slot faults. Full sequential equivalence includes a golden observation wire for onehot=(1<<read_pos); this relation must itself be proven, not assumed. Full original port scoreboards run on baseline and candidate; a stuck-cursor mutation must fail actual packet checks. All logs and failure reports are retained. The canonical RTL remains unchanged while these tests run.

If the complete proof passes, rebuild source-bound synthesis/placement/CTS and evaluate the same native timing constraints before adoption as a timing improvement. The input pcie_link_up_i paths and final routing/hold remain additional work; this candidate cannot establish final timing closure by itself.

## Exact adoption after native proofs

Run39058935226/source306dacdd4491a55bd13f205edfc79ddaaa31aa6f passed all three configurations:675,1354,1675 proven equivalence points, zero unproven. Arbitrary-memory read cuts passed; wrong-byte/wrong-slot mutations produced actual formal counterexamples. Both baseline and candidate passed7replay+4reliable-packet tests with zero skips. A stuck one-hot cursor failed5of7replay tests, as required.

The canonical replay source now equals the exact proven candidate SHA b227c24f3f49bce1d8203a10e2039aabe04b6974466307737627023f60e5bc60. The prior1a15c0b9... source is frozen at sw/tests/fixtures/pcie_chip_timing/pre-onehot-replay-20261017.v. Full receipts are in evidence/replay-onehot-equivalence-pass-20261017.json. The candidate prover now explicitly reconstructs the old baseline from this fixture and requires byte-identical canonical adoption. The legacy bank prover retains arbitrary cross-bank reads and now proves the additional one-hot invariant in its full sequential check.

Fresh canonical proof, legacy bank proof, native mainchip boot/20SRAM MBIST and protocol jobs are launched by this adoption. These must be inspected before source-bound placement/CTS. Previous repaired ODB and timing results belong to the older source and cannot be claimed as timing evidence for the adopted design.
