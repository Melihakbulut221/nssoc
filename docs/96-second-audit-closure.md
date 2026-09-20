# 96 — Second audit closure register
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

Date: 20 September 2026. This register adds the second independent audit to
[the existing product acceptance contract](92-product-acceptance.md). It does
not replace the first review, ongoing native boot diagnosis, physical runs,
or the PCIe Gen3 x4 and Gigabit Ethernet targets. The audit examined both
`main` and `codex/complete-open-work`; a finding about `main` is rechecked
against this branch before changing code.

Source: user-supplied `nssoc-audit-2026-09-20 (2).md`, SHA256
`65799fd3a98b76a8eaf043249ade20b8925feae7d82719eee48c7465bb5fced9`. The original is retained locally. Its findings are inputs to
verification, not measured results of this branch.

Statuses: OPEN needs work; PARTIAL has a narrower implemented result;
VERIFY means a change awaits its stated checks; DONE requires evidence.
External dependencies remain OPEN rather than being converted into exclusions.

| Audit ID | Required work and acceptance | Status / current disposition |
|---|---|---|
| 0.1 | Project-specific TT test guide; regenerate manifest; synchronize TT repository | DONE. Generator updated; 18 TT checks pass / 1 absent-tool skip. Only guide and manifest changed; remote TT `main` is `aa870aba3b2c4d39460ae7a8da42918fa25df422`, verified with `git ls-remote`. Frozen RTL remains byte-identical. |
| 1.1 | Keep host checkpoints out of publication | DONE for current tree. Continuation notes preserved locally and removed from Git tracking; ignore rules added. Earlier public commits still contain their historical copies. |
| 1.2 | Reconcile signed LGPL decision, optional SpaceWire/CAN build, notices and licence texts | OPEN. Choose the audit's optional-build route; preserve complete interface functionality in an explicitly enabled profile. No legal advice or patent clearance is claimed. Correct docs/95 to CC-BY-4.0; inventory both source bundles and Ethernet reset patch. |
| 1.3 | Missing Tcl shell must produce explicit tool skips | DONE. `pytest sw/tests/test_corner_reports.py sw/tests/test_interface_flow.py`: 36 pass with Tcl; `PATH=/nonexistent` with an absolute Python path: 16 pass / 20 explicit skips. |
| 1.4 | Correct local-CI/workflow equivalence claim | DONE. Dated correction distinguishes Python/documentation gates from the workflow hardware jobs. |
| 1.5 | Evidence publication policy; portable paths; external binary assets | OPEN. Preserve exact hashes, licences and clean-clone recovery while migrating assets. Do not delete the only reproducible source before a verified replacement exists. |
| 1.6 | Topic-based history and public author identity | OPEN. Preserve a local recovery ref before any history rewrite. Current native runs and external CI refer to existing SHAs. |
| 1.7 | Numbered index table/headings; physical and Ethernet claim scope | PARTIAL. Local native pass and independent hosted failure are now distinguished. Docs/88–95 now occupy index table rows; headings are numbered and Ethernet shared-clock/MDIO limitations are explicit. |
| 1.8 | Close every existing product gate | OPEN. Retain all rows of docs/92, including PCIe, final timing/LVS, packaging, DFT, debug, POR and qualification. |
| 2.1 | Hardware CI, visible pytest skips, current verification ledger, pinned/scheduled workflow | PARTIAL. Hardware jobs now also include native-model RAM parity and its negative control. Every action is pinned to a verified commit, every job has a timeout, dependency caching and weekly dependency-update configuration are present. Nightly normal hardware jobs are configured; GitHub schedules become active only on the default branch. Full native boot remains explicit opt-in. |
| 2.2 | Full cocotb/formal rerun and source-bound ledger freshness | OPEN. Do not replace failed or incomplete obligations with aggregate PASS counts. |
| 2.3 | Reproducible physical toolchain/bootstrap; portable tool paths; requirements; Ibex elaboration | OPEN. Preserve frozen pilot scripts; provide controlled external environment overrides where editing would violate freeze. Check translated/patched Ibex against pinned inputs. |
| 2.4 | Valid design SDC; all relevant corners; timing/electrical closure and hold erratum | OPEN. Current native run preserves actual 5.0 percent derating. Old zero-derate ECO passes remain withdrawn. Reset exceptions need a justified timing contract, not blanket cuts. |
| 2.5 | Collect historical s83 evidence, complete digest coverage, publish physical artifacts | PARTIAL. Existing digest/recovery mechanisms cover more than the audited main snapshot; verify every named s83 run individually and preserve missing-data failures. |
| 2.6 | Real-codec core/regfile and M-extension formal obligations, explicit bounds in datasheet | PARTIAL. Added contract/equivalence proofs do not imply a closed whole-core reg_ch0 or M-extension proof. Reconcile dispositions and document actual limits. |
| 3.1 | SoC orphan reachability and simulation/macro memory parity | PARTIAL. Recursive inventory now covers both RTL trees and the generated-ROM template, preserves alternate module definitions, and follows per-module edges after stripping comments/strings. Five standalone AHB probe modules have reasoned ledger rows; CAN’s soc_apb_wb remains reachable. All six supported RAM geometry/latency profiles pass native SRAM parity; a corrupted-macro negative control fails after elaboration. Legacy ROM parity remains open. |
| 3.2 | UART/timer/PnP properties; direct serial/TMR/top tests; RX; FI/coverage/X failures | PARTIAL. Direct serial-master waveform/reset/timeout tests pass at HALF=2/3/7 (nine tests); direct TMR bank test covers widths 4/5/8/32/64 and all 339 single storage-bit upsets, plus a two-replica negative control. UART/timer/PnP properties, RX, broader FI/coverage and other requested work remain open. |
| 3.3 | Whole-SoC lint and targeted warnings; nettype discipline | OPEN. Frozen pilot warnings are recorded, not fixed in the submitted sources. |
| 3.4 | REUSE compliance, upstream IHP notices, generated licence inventory | PARTIAL. REUSE 6.2.0 now reports 880/880 files covered, zero invalid expressions, no missing licences. `REUSE.toml`, IHP aggregate notices and optional local/required installed CI gate are implemented. Live counts are now generated by `scripts/licence_inventory.py`; final source-bound rerun remains. |
| 3.5 | Concise README, preserved errata, block diagram, measured status registry, datasheet/index | OPEN. Current results must retain image/tool/corner scope; no SoC operating frequency or manufacturability claim. |
| 3.6 | Correct PNR profile selection, config inventory and energy hierarchy | OPEN. Do not delete or move frozen pilot configs; document their historical scope instead. |
| 3.7 | Transport-independent pilot driver, cocotb/host/RP2040 backends | PARTIAL. Shared `sw/pilotlink` register/weight/frame API and cocotb, pySerial bridge and standalone MicroPython SPI backends implemented. 27 host checks and two pin-level RTL tests pass (golden comparison and partial-write cancellation). Hardware transport qualification and any deduplication of frozen legacy helpers remain open. |
| 3.8 | Single-source register offsets and bare-metal HAL | OPEN. Preserve boot acceptance and compare generated register interfaces before changing firmware. |
| 3.9 | Repository/community/citation/tooling hygiene, papers/thesis CI, reproducible release/DOI | OPEN. Verify each deliverable separately; no release is published while product gates fail. Do not invent a DOI or declare an external contribution policy without checking the existing mirror contract. |
| 4 | Pads/ESD/package, clocks/POR, scan/MBIST/debug, integrity/AER, SRAM LVS, radiation and silicon qualification | OPEN. These remain engineering or external acceptance dependencies; a checklist alone does not close them. |

The audit's section 5 is an ordering of these same requirements, not another
set of completed results. Local continuation state records active commands and
immutable input identities outside the public tree. Every substantive closure
will add its command, result and applicable scope here or in docs/92.

Validation commands for the first audit fixes (20 September 2026):

```sh
.venv/bin/python -m pytest -q sw/tests/test_corner_reports.py sw/tests/test_interface_flow.py sw/tests/test_doc_links.py
# 146 passed
PATH=/nonexistent /absolute/path/to/python -m pytest -q -rs sw/tests/test_corner_reports.py sw/tests/test_interface_flow.py
# 16 passed, 20 skipped; all skips identify the absent Tcl shell
.venv/bin/python scripts/gen_tt_submission.py
.venv/bin/python -m pytest -q sw/tests/test_tt_submission.py
# Only the test guide and its manifest entry change; 18 pass / 1 absent-tool skip.
```

The combined documentation/TT/Tcl regression after the REUSE migration
completed with **164 passes and one absent-tool skip**. The licence front-door
command, with `REUSE` pointing to REUSE 6.2.0, completed **6 gates, zero failures,
zero skips**. The first local full-CI attempt is not accepted: its watched-tree
guard correctly rejected the then-uncommitted TT guide/manifest edits. A clean
commit replay is required; no dirty-tree exception was introduced.

The clean remote replay at `1c31426` completed successfully: **931 pytest
passes, one absent TinyTapeout-tool skip, zero failures**; **18 front-door
passes, zero failures, seven explicit skips**. This includes the new REUSE and
licence-inventory gates. Paper checks remain 27 re-derived / 15 manual /
zero missing / zero wrong. See [the exact-head record](evidence/fresh-clone-1c31426-20260920.json).

The recursive module inventory is a lexical reachability check, not elaboration:
conditional variants are unioned. The locally implemented Ibex register file is
an explicit external entry selected by `ibex_sources.sh`; when fetched Ibex is
present the check also verifies its parent instantiation. A clean clone reports
that boundary test as a tool/preparation skip instead of inventing a parent.
The module-inventory regression passes **four checks** with prepared Ibex present.

`make soc-memory-parity` downloads the checksum-pinned native models and runs
six profiles: 8,192-word RAM with/without ECC, 16,384-word unprotected RAM,
each at RDREG=0/1. All six pass with unchanged sources/models. Every RAM word
is initialized through ordinary bus writes; tests compare both implementations
and an independent byte-enable scoreboard, including bank boundaries, all
sixteen write masks, three random seeds, reset during an outstanding response,
and background scrubbing with foreground traffic. A scratch-copy one-bit
macro-read corruption fails a functional assertion after elaboration. See
[the measured record](evidence/memory-parity-20260920.json). This does not claim
power-up equality: the array model initializes itself and native SRAM starts
undefined. Legacy SRAM ROM initialization and physical timing are separate gates.

The untouched SRAM model also needs Icarus 13 or newer: a version-12 control
failed with unknown macro read data after bus initialization. The runner now
rejects that version before building, and the CI RAM job uses the pinned
2026-08-04 OSS CAD Suite. The preflight rejects version 12 (exit 2), and the
protected RDREG=1 profile passes again on version 13. Both outcomes are retained
in the RAM evidence record; the simulator failure is not a design pass.

The [pilot driver](../sw/pilotlink/README.md) is exercised through the unchanged
TT wrapper using `Makefile.pilotlink`; normal cocotb discovery includes it. Its
readback/state/weight/event test matches the integer model even when eight
spikes exceed the output buffering. The driver has bounded polling, rejects
overlapping use, and poisons a link after incomplete transport I/O rather than
repeating a possibly committed write or queue pop. Supplied physical geometry
sets the weight stride; a mutable active-neuron count is not used as SRAM
geometry. See [the measured scope](evidence/pilotlink-20260920.json). Hardware
backends have API-fake coverage only; no board or silicon run is claimed.

The clean remote replay at `4475b63` passes **932 Python tests, two explicit
skips, zero failures**, with **18 front-door passes, zero failures and seven
skips**. The extra skip is the unprepared external Ibex inventory boundary;
`make soc-prepared-guards` runs it again after fetching/conversion. See
[the exact revision record](evidence/fresh-clone-4475b63-20260920.json). The later
Icarus preflight change and driver work have their own checks and are not
retroactively attributed to this clean-clone run.

[Direct peripheral tests](evidence/direct-peripheral-tests-20260920.json) now
exercise the serial master and TMR banks independently of the integrated NPU
and watchdog suites. Default discovery runs TMR and HALF=2 serial checks;
HALF=3/7 are separate recorded runs. No frozen RTL or legacy test was edited.

The [hosted SRAM job](evidence/hosted-memory-parity-20260920.json) independently
passes all six profiles and the expected-failure control on Icarus 14. The same
revision's generic RTL job failed its completeness guard after 479 passing tests:
it did not yet recognize the SRAM suite's separate native-model driver. The
runner now checks the external driver/workflow binding and reports an explicit
skip whose results belong to that job. Removing either binding is tested to
fail discovery; this does not exempt an unexecuted suite from CI.
