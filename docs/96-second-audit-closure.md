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
| 1.2 | Reconcile signed LGPL decision, optional SpaceWire/CAN build, notices and licence texts | DONE for the technical optional-build route. Default base excludes the LGPL cores; explicit full retains both. CPU, pin, discovery, dependency and physical-profile guards pass; see the dated evidence below. Original signed decision and upstream/Bosch notices remain; no patent clearance or silicon permission is claimed. Both source bundles and Ethernet reset patch remain inventoried; docs/95 uses CC-BY-4.0. |
| 1.3 | Missing Tcl shell must produce explicit tool skips | DONE. `pytest sw/tests/test_corner_reports.py sw/tests/test_interface_flow.py`: 36 pass with Tcl; `PATH=/nonexistent` with an absolute Python path: 16 pass / 20 explicit skips. |
| 1.4 | Correct local-CI/workflow equivalence claim | DONE. Dated correction distinguishes Python/documentation gates from the workflow hardware jobs. |
| 1.5 | Evidence publication policy; portable paths; external binary assets | OPEN. Preserve exact hashes, licences and clean-clone recovery while migrating assets. Do not delete the only reproducible source before a verified replacement exists. The standalone site now carries linked tracked evidence and licence files; external binary migration remains open. |
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
| 3.2 | UART/timer/PnP properties; direct serial/TMR/top tests; RX; FI/coverage/X failures | PARTIAL. Ten new UART/timer/PnP formal tasks pass, including unbounded proofs and the shipped 32/16-bit timer widths; five mutated designs produce reachable counterexamples. Direct serial-master tests pass at HALF=2/3/7; direct TMR test covers 339 single storage-bit upsets plus a two-replica negative control. RX now has pin-driven tests and real-CPU receive/IRQ/WFI validation; see docs/97. Its final layout, broader FI/coverage and other requested work remain open. |
| 3.3 | Whole-SoC lint and targeted warnings; nettype discipline | DONE for the defined lint gate and nettype discipline. Both base/full array and SRAM/logic-ROM/SYNPRE profiles pass exact diagnostic inventories; 20 owned width warnings are removed. Generated ROM diagnostics are attributed to the authored template. Frozen/upstream warnings remain recorded technical debt, not signoff waivers; see the dated physical-source extension below. |
| 3.4 | REUSE compliance, upstream IHP notices, generated licence inventory | DONE for current distribution checks. REUSE 6.2.0 passes with zero missing licences or invalid expressions; IHP aggregate notices and generated component inventory are retained. Source-bound publication checks accompany the latest energy-tool record (965 covered files). Live counts are generated in LICENSES.md and required in CI; this is compliance checking, not patent clearance. |
| 3.5 | Concise README, preserved errata, block diagram, measured status registry, datasheet/index | PARTIAL. README now links a block diagram and a status table generated from explicitly selected evidence hashes. Every byte of its previous body is retained in HISTORY.md; the docs builder includes that archive and publishes referenced assets and API pages with checked local file targets. Datasheet reconciliation remains open; no SoC operating frequency or manufacturability claim. |
| 3.6 | Correct PNR profile selection, config inventory and energy hierarchy | DONE for the tooling correction. PNR and energy tools derive actual mapped macro inventories; overrides, optional interfaces and ROM modes are checked. Historical configs remain catalogued reproducibility inputs; no frozen config was moved or edited. Native 20/24-macro energy-tool calibrations cover all 36/40 ports; see the dated record. Final timing, LVS and actual workload-power acceptance remain separate open gates. |
| 3.7 | Transport-independent pilot driver, cocotb/host/RP2040 backends | PARTIAL. Shared `sw/pilotlink` register/weight/frame API and cocotb, pySerial bridge and standalone MicroPython SPI backends implemented. 27 host checks and two pin-level RTL tests pass (golden comparison and partial-write cancellation). Hardware transport qualification and any deduplication of frozen legacy helpers remain open. |
| 3.8 | Single-source register offsets and bare-metal HAL | PARTIAL. Thirteen block maps (113 global/window offsets) generate RTL constants, C and Python definitions with an independent ABI guard. That constant-only migration preserves both firmware images. A subsequent shared HAL now passes both CPU profiles and FI baseline comparisons; the upstream CAN byte map and remaining firmware/coverage work stay open. See the separate records below. |
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


The clean remote replay of `091423c` completed **1,020 Python passes, two
explicit skips, zero failures** and **18 front-door passes, zero failures,
seven skips**; [the exact revision record](evidence/fresh-clone-091423c-20260921.json)
preserves its command and source identity. The later UART RX implementation
is not attributed to that earlier clean-clone result.

The [UART receive result](evidence/uart-receive-20260921.json) adds seven
pin-driven RX tests to the existing 17 TX/APB/race checks. All 24 also pass
on an IHP-mapped block with unchanged native cell models. Five RX mutations
fail functional assertions, and the CPU exercises reception, status clearing,
RI masking, fast interrupt vector 16 and a real WFI wake. A corrupted serial
byte is rejected by firmware; no internal receive state is forced. UART
formal BMC, PDR and receive/overrun/framing reachability use the delivered RTL.
The initial 300-second cover timeout is retained; the same obligation passes
with a 1,200-second budget. This closes the missing digital receiver portion
of audit 3.2, while its new whole-SoC layout, general FI/coverage and physical
qualification remain open. Hosted jobs now execute the CPU control and native
UART tests; the existing long manual acceptance run still refers to `091423c`.

The [independent hosted startup run](evidence/hosted-native-startup-20260921.json)
now rebuilds and boots `091423c` successfully: **28 checks, 653,726 cycles,
zero failure mask**, unchanged native IHP models. The failed earlier run remains
linked and preserved. This closes that particular hosted startup replay, not
later UART/profile changes or physical timing. The [hosted UART block run](evidence/hosted-uart-receive-20260921.json)
independently passes **24 native-cell tests** at `50b760f`. Its [clean remote
regression](evidence/fresh-clone-50b760f-20260921.json) passes **1,038 Python
checks, two explicit skips, zero failures**, plus 18 front-door passes and
seven explicit skips. None of these counts substitutes for the full formal
sweep or the remaining product gates.

The [optional-interface record](evidence/interface-profiles-20260921.json)
closes the technical build portion of audit 1.2. Both profiles pass **29 real-CPU
checks**; base also requires eight read/write access faults from disabled
SpaceWire/CAN slots and zero discovery records. Full restores their identities
and real data/interrupt paths. Pin suites report base **8 pass / 4 explicit
skips**, full **11 pass / 1 base-only skip**. Each discovery profile passes BMC,
unbounded PDR and cover; independent table tests compare every word. Both
whole-SoC hierarchies resolve. Full dependency output is byte-identical to the
previous unconditional bundle. All optional notices and historical evidence
remain retained. New whole-SoC mapped/physical acceptance is still separate.

The [SRAM energy migration](evidence/macro-energy-20260921.json) replaces
implicit six-instance pricing with a netlist-bound full inventory, including
ECC macros and both Ethernet ports. Forty-four checks pass, including all
four SRAM types' untouched Liberty tables at three corners. Native-model
calibration covers the 20-macro/36-port logic-ROM inventory and the historical
24-macro/40-port protected SRAM-ROM inventory. Every joint control state has
the independently scheduled number of clock edges. Missing/unknown activity
fails; scalar leakage is charged once per cell. These are synthetic calibration
results, not current SoC workload power or physical qualification. The old
calculation remains explicitly reproducible with `--legacy-six-macros`.

The [clean remote replay](evidence/fresh-clone-9ffe83b-20260921.json) of the
interface-profile commit passes **1,067 Python checks, two explicit skips,
zero failures** and **18 front-door checks, seven explicit skips**. It closes
the two failed PNR guard obligations from the earlier dirty-tree attempt;
that attempt's failure remains recorded. The subsequent energy-tool change
has its separate evidence above.


On 21 September, the [whole-SoC lint record](evidence/soc-lint-20260921.json)
adds `scripts/lint.sh` and `scripts/ci_local.sh lint`. The hardware CI invokes
this required gate after pinned source preparation. `all` explicitly skips it
on a source-only machine without the prepared processor or pinned Verilator;
the explicit `lint` command fails on missing prerequisites. Its selected
profile follows `SOC_INTERFACE_PROFILE=base|full`.

The runner uses Verilator `--lint-only --Wall` without disabling any warning
class. `-Wno-fatal` lets it collect the complete list; acceptance then requires
an exact match of file, line, column, message and multiplicity against
`hw/soc/lint-policy.json`, the reviewed Verilator version, unchanged inputs and
pinned frozen/upstream source hashes. New or removed diagnostics require review.
Unknown diagnostic syntax and compiler errors fail. This is a regression gate
with **987 base / 1,015 full recorded warnings**, not warning-free RTL.

Sixteen owned width warnings were removed through explicit integer predicates,
a width-matched I2C timeout limit and explicit observation-row zero extension.
No parameter defaults, register ABI, frozen pilot RTL or pristine upstream
checkout changed. All owned `.v` files, including standalone AHB probes, and
the logic-ROM template now scope `default_nettype none` and restore `wire`
after their module definitions. The synthesis guard's NSRC parser follows the
explicit boolean syntax while preserving its expected eight-source default.

Only the three named behavioural clock-gate latches and five named reset
chains qualify for the architectural diagnostic allowances; an exact record
is still required. The one upstream CAN implicit wire is a driven one-bit
`can_bsp` to `can_btl` connection. Ethernet range diagnostics arise from
unselected ID/DEST and PTP branches in this profile. These records do not
waive CDC, timing or physical qualification, or approve a different profile.

Validation: **63 focused Python checks**, **25 elaboration/register-file/formal
runner guards**, **11 full-profile peripheral tests / one profile-specific
skip**, and **all six native-SRAM parity configurations** pass. The deliberately
corrupted SRAM is rejected. Separate compiled lint controls reject a new width
mismatch and an undeclared signal. The initial elaboration-test collection
failed because its source parser still expected the old NSRC expression; the
corrected parser's rerun passed. The initial diagnostic logs and failed control
outputs remain retained with the final evidence.

The [independent hosted formal inventory](evidence/hosted-formal-inventory-20260921.json)
at `091423c` remains **FAIL**: 155 tasks passed with fresh sources, but the
Makefile never invoked two declared abstract-codec scrub tasks (`prove`, `bmc`).
Both Make stages returned zero; the separate inventory correctly prevented a
false aggregate PASS. The two obligations remain mandatory and are being run;
no exclusion was added. This failure is independent of the same revision's
passing native boot test.

The [clean remote replay at a79af62](evidence/fresh-clone-a79af62-20260921.json)
validates the delivered macro-energy and profile changes. It predates these
lint edits; its counts must not be treated as validation of a later tree.

The final local lint tree passes **1,128 Python tests, one absent-tool skip,
zero failures**, followed by **146 publication checks**. REUSE covers all
972 tracked files with zero missing/invalid licences. These results and their
log hashes are appended to the lint record; independent hosted acceptance of
this new revision is still pending.

The [physical-source lint extension](evidence/soc-physical-source-lint-20260921.json)
now includes both interface profiles with SRAM port declarations, a generated
fixed ROM from the compiled loader, and the same SYNPRE=1 / WAKE_GNT=1
selections used by synthesis. Its source snapshots include generator inputs,
the ROM image, generated files and unchanged upstream/frozen sources.
Generated diagnostics map back to the authored template/register file, so they
cannot accidentally receive upstream allowances. This exposed four additional
ROM parameter-width warnings; explicit-width instance arguments and integer
predicates remove them without changing defaults or the ROM's port contract.

All four profiles pass their exact diagnostic inventories: 987/1,015 warnings
for array memory and 1,012/1,040 for SRAM/logic ROM. **45 focused tests** pass,
including whole-SoC elaboration, every fixed-ROM address against the frozen
encoder, corruption controls and memory-protection guards. The earlier guard
failure expected the previous literal argument ordering; its replacement checks
both ROM profile arms and the common HARDEN connection. Hosted hardware CI now
requires the physical-source lint after building its CPU-interface loader.
This closes the audit's lint integration scope, not CDC, mapped-netlist or
physical acceptance. The named residual warnings remain explicitly visible.

The [scrub invocation correction](evidence/formal-scrub-invocation-20260921.json)
adds both missing abstract-codec tasks to the default Makefile target and keeps
attempting remaining scrub tasks after a failure. The separate mandatory-task
inventory is regression-tested against that target. The original properties,
assumptions, reset constraints and 40-cycle BMC depth remain unchanged.
PDR closes the delivered unbounded `prove` task with fresh copied sources.
The independent CaDiCaL BMC trial timed out after 900 seconds at frame 23;
that is **not PASS**. Its required run now has a 7,200-second task budget and
is incomplete at this publication. Nine runner/inventory controls pass.
The full 157-task result and whole-core/real-codec obligations remain open.

The [first register migration](evidence/peripheral-registers-20260921.json)
covers BOOT, BUSSTAT, CLINT, Ethernet, GPIO, I2C, NPUCFG, QSPI, SCRUB, SPI,
SpaceWire and UART. Each block's YAML feeds the actual decoder constants,
firmware offset header and Python test definitions. The generator rejects
ambiguous definitions and stale bindings; a separate pre-migration ABI digest
prevents a coordinated change to all generated files from silently moving the
105 existing registers. Both base/full application, loader and flash artifacts
remain byte-identical to the captured pre-migration builds. Probe identities
now include firmware headers. Four lint profiles retain precisely the same
warning classes, messages and counts; only owned-source line positions moved.
The later GPTIMER and shared HAL steps are recorded below. CAN remains open.
See [the generator contract](../regmap/peripherals/README.md).

A later [independent hosted native boot](evidence/hosted-native-interfaces-20260921.json)
at `9ffe83b` also passes all **28 baseline checks** in **653,726 cycles**, with
zero failure mask, flash violations or UART framing errors. This revision has
UART RX and explicitly selects the full SpaceWire/CAN RTL profile. Its image
is the baseline boot program, not the separate 29-check interface demo. Input
hashes were checked against that exact Git revision and the downloaded artifact;
no final layout, timing or additional interface-test coverage is inferred.

The clean remote replay at `328021c` passes **1,131 Python tests**, two explicit
skips and zero failures; its front-door checks report **18 passes**, zero failures
and eight skips. The additional skip explicitly names the unprepared lint
boundary. [The revision record](evidence/fresh-clone-328021c-20260921.json)
preserves the exact commands and results. The register migration's working-tree
checks are separate from that earlier delivered snapshot.

The subsequent [shared HAL](evidence/soc-hal-20260921.json) removes duplicated
console and basic MMIO code from the bootloader, SoC bring-up application and
three FI workloads. Interface polling and CAN byte access use its common
primitives. Bounded UART operations perform no transfer on a zero budget or
timeout; compiled host mutations verify those failure paths. Existing console
callers retain their blocking/watchdog policy and hexadecimal formatting.
The [API contract](../hw/soc/tb/sw/lib/README.md) states the ownership and timeout
rules. Firmware images change in this step: the earlier byte-identity result
applies only to the register-constant migration.

Both actual CPU profiles pass **29 checks**, zero failure mask and watchdog
stages **1/0/0**, with **669,731 base** and **675,757 full** cycles. All three FI
programs also complete fault-free runs. Rebuilding and replaying their earlier
`3b20b20` sources under the same hardware settings yields identical signatures,
console hashes, trap/NMI and watchdog outcomes. The dense kernel has four
stage-1 NMIs in both versions; that is not a zero-NMI claim or a new injection
campaign. New firmware also passes both SRAM/logic-ROM lint profiles without
changing the warning ledger. Its whole-SoC native and physical acceptance
remain separate pending work.

The clean remote replay of `3b20b20` completes **1,158 Python passes**, two
explicit skips, zero failures, and **18 front-door passes**, zero failures and
eight skips. [That revision record](evidence/fresh-clone-3b20b20-20260921.json)
covers the register migration; the HAL has its own later checks above.

The [GPTIMER migration](evidence/gptimer-registers-20260921.json) adds the
parameter-dependent timer/watchdog map to the same generator. Global byte
offsets, indexed-window stride and selectors now feed RTL, C and Python.
The existing register addresses and alias behavior are preserved: all ten
base/full firmware artifacts are byte-identical to the accepted HAL builds.
Independent C assertions guard the shipped watchdog addresses. All **10 timer
simulations**, **four unchanged formal tasks** (including the shipped 32/16-bit
proof), **61 register/HAL guards** and four lint profiles pass. Lint changes
only two owned-source diagnostic line positions per profile; its classes,
messages and counts remain unchanged. CAN, bit fields and the remaining
firmware/coverage obligations are still open.

A standalone-site check found **249 missing local file targets** in the
previous generator output. The earlier “zero unresolved” result counted
numbered prose references only; it did not establish the validity of explicit
Markdown links. The corrected builder renders linked API Markdown, copies
only explicitly referenced tracked assets and the distribution's licence
metadata/texts, and records byte counts and SHA256 hashes. It checks every
emitted local `href`/`src` after rendering, including multiline labels. Code
examples and remote URLs are preserved. Missing/untracked files, symlinks,
escapes and oversized asset sets fail the build. Fourteen new controls plus
the existing documentation/status checks pass (**136 tests**). See the
[publication record](evidence/document-site-links-20260921.json). Remote URL
availability, fragment validity and paths embedded inside evidence JSON remain
outside this file-target check; external evidence migration is still open.
