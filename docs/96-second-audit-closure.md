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
| 2.3 | Reproducible physical toolchain/bootstrap; portable tool paths; requirements; Ibex elaboration | PARTIAL. Digital tools now default to the project-local checkout; the checksum-pinned OSS CAD Suite installer preserves existing installations and explicit overrides. No unrelated PATH fallback. Physical tool/PDK bootstrap and translated/patched Ibex equivalence remain open; preserve frozen pilot scripts. |
| 2.4 | Valid design SDC; all relevant corners; timing/electrical closure and hold erratum | OPEN. Current native run preserves actual 5.0 percent derating. Old zero-derate ECO passes remain withdrawn. Reset exceptions need a justified timing contract, not blanket cuts. |
| 2.5 | Collect historical s83 evidence, complete digest coverage, publish physical artifacts | PARTIAL. Existing digest/recovery mechanisms cover more than the audited main snapshot; verify every named s83 run individually and preserve missing-data failures. |
| 2.6 | Real-codec core/regfile and M-extension formal obligations, explicit bounds in datasheet | PARTIAL. Added contract/equivalence proofs do not imply a closed whole-core reg_ch0 or M-extension proof. Reconcile dispositions and document actual limits. |
| 3.1 | SoC orphan reachability and simulation/macro memory parity | PARTIAL. Recursive inventory now covers both RTL trees and the generated-ROM template, preserves alternate module definitions, and follows per-module edges after stripping comments/strings. Five standalone AHB probe modules have reasoned ledger rows; CAN’s soc_apb_wb remains reachable. All six supported RAM geometry/latency profiles pass native SRAM parity; a corrupted-macro negative control fails after elaboration. Legacy ROM parity remains open. |
| 3.2 | UART/timer/PnP properties; direct serial/TMR/top tests; RX; FI/coverage/X failures | PARTIAL. Ten new UART/timer/PnP formal tasks pass, including unbounded proofs and the shipped 32/16-bit timer widths; five mutated designs produce reachable counterexamples. Direct serial-master tests pass at HALF=2/3/7; direct TMR test covers 339 single storage-bit upsets plus a two-replica negative control. RX, broader FI/coverage and other requested work remain open. |
| 3.3 | Whole-SoC lint and targeted warnings; nettype discipline | OPEN. Frozen pilot warnings are recorded, not fixed in the submitted sources. |
| 3.4 | REUSE compliance, upstream IHP notices, generated licence inventory | PARTIAL. REUSE 6.2.0 now reports 880/880 files covered, zero invalid expressions, no missing licences. `REUSE.toml`, IHP aggregate notices and optional local/required installed CI gate are implemented. Live counts are now generated by `scripts/licence_inventory.py`; final source-bound rerun remains. |
| 3.5 | Concise README, preserved errata, block diagram, measured status registry, datasheet/index | PARTIAL. README now links a block diagram and a status table generated from explicitly selected evidence hashes. Every byte of its previous body is retained in HISTORY.md; the docs builder includes that archive and copies referenced local images. Datasheet reconciliation remains open; no SoC operating frequency or manufacturability claim. |
| 3.6 | Correct PNR profile selection, config inventory and energy hierarchy | PARTIAL. The physical launcher now matches the actual mapped macro names/types and ROM profile, including explicit overrides. SoC and frozen-pilot configuration indexes distinguish historical experiments from current candidates. No frozen config was moved or edited. Historical macro-energy activity names still require migration. |
| 3.7 | Transport-independent pilot driver, cocotb/host/RP2040 backends | PARTIAL. Shared `sw/pilotlink` register/weight/frame API and cocotb, pySerial bridge and standalone MicroPython SPI backends implemented. 27 host checks and two pin-level RTL tests pass (golden comparison and partial-write cancellation). Hardware transport qualification and any deduplication of frozen legacy helpers remain open. |
| 3.8 | Single-source register offsets and bare-metal HAL | OPEN. Preserve boot acceptance and compare generated register interfaces before changing firmware. |
| 3.9 | Repository/community/citation/tooling hygiene, papers/thesis CI, reproducible release/DOI | PARTIAL. CITATION.cff identifies the source repository and author without inventing a release or DOI. Other deliverables remain open; no release is published while product gates fail. The existing mirror contract still governs publication. |
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

The new [peripheral formal record](evidence/peripheral-formal-20260920.json)
contains ten passing tasks: UART and both discovery tables each have BMC,
unbounded PDR and cover; the general timer also has PDR at the shipped 32-bit
counter / 16-bit prescaler widths. Port-driven scoreboards check register
updates, reserved bits, timer load/restart/chaining, expiry-versus-clear priority,
and shared interrupts. Discovery properties check response timing, error policy,
address aliasing, the fixed identity ABI and input noninterference. Full generated
table contents still use the independent memory-map tests. No DUT RTL changed.
UART reception/serial timing, watchdog policy, fault injection and physical
behavior remain separate obligations. The Makefile's default sweep includes
all ten tasks and five scratch-only mutation controls:

```sh
make -C hw/soc/formal uart pnp gptimer peripheralcontrols
```

Initial k-induction attempts for the port-only UART/PnP contracts returned
UNKNOWN; PDR proved those same properties. Initial timer BMC with Yices timed
out after 180 seconds; ABC BMC passed at the unchanged depth of 24. Those
attempts remain in the record, rather than being reported as passes.

The [digital bootstrap record](evidence/digital-tool-bootstrap-20260920.json)
verifies the original 737,555,999-byte OSS CAD Suite archive against GitHub's
published SHA256 and checks the installed tool identity. Eight offline installer
tests cover integrity, rollback, path traversal, existing-target preservation,
locking and tool resolution; two formal reachability checks also pass. A second
full extraction was not performed while physical jobs need the remaining disk
space. The installer and its safe extraction require Python 3.12 or newer;
the digital release supports Linux x86-64. This does not close physical-tool
bootstrap, PDK installation or the broader audit item 2.3.

The clean remote replay at `c1a6f7a` passes **962 Python tests, two explicit
skips and zero failures**, with **18 front-door passes, zero failures and seven
skips**. [Evidence and exact ledger row](evidence/fresh-clone-c1a6f7a-20260920.json)
cover the delivered driver/direct-test changes. The later peripheral proofs,
tool installer and corner-parser correction have their own targeted results;
they are not part of that earlier revision's full replay.

A separate `formal-sweep` CI job now runs `scripts/check_formal_sweep.py`
from a fresh prepared checkout. It invokes the frozen pilot's `everything`
target and the SoC's `all` target, then requires every declared regression task
to have a new PASS and byte-identical copied sources. The current inventory is
54 pilot plus 103 SoC tasks. Six previously documented non-closing tasks remain
explicit exclusions in `hw/soc/formal/sweep-policy.json`; this preserves their
unresolved status and does not close whole-core RISC-V obligations. Eight
runner controls and the two Makefile reachability checks pass. The complete
157-task rerun is pending, so audit item 2.2 remains open.


The complete formal sweep now preserves all task verdicts and six named
historical exceptions. The initial 30-minute stage budget was too short for
the frozen AER reachability job alone (its recorded baseline exceeds 41
minutes). The runner now allows 150 minutes per stage and the CI job 330
minutes including preparation/upload. `make -k` attempts independent targets
after a failure, and the SoC stage still runs if the pilot stage fails. Neither
a timeout nor the six exceptions is promoted to PASS. A full fresh run remains
required; changing the time budget does not itself close audit 2.2.


The [NPU startup correction](evidence/npu-native-startup-20260921.json) now
passes both randomized-RAM RTL boot and a full native replay of the exact
previously failed hosted Yosys 0.67 netlist: **28 checks, zero failure mask,
653,726 cycles**, no UART framing or flash protocol errors. Startup writes and
verifies each neuron address, all twenty payload bits high, then zero while
the node is idle and disabled. Native models are unchanged and no memory is
preloaded or forced. Twelve compiled-C tests cover success and fail-fast paths;
the FI workload builds, but its full runtime campaign remains open. A subsequent
licence-comment-only correction was rebuilt: application, loader and both flash
images are byte-identical to those tested. This is local native acceptance for
the pinned image; independent hosted rebuilding/replay remains pending.
