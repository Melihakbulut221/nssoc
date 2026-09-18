<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# 86 — An external review, worked

An independent third party read the public mirror at `36efe03`,
reproduced every claim it made on a fresh clone, and wrote eleven
findings with a reproduction block, an acceptance block and a scope
guard each. This is what happened to them.

The review's own instruction was followed first: **re-run each
reproduction before acting on it**, and stop on any finding that does
not reproduce rather than inventing a fix. That mattered. Of the
eleven, nine reproduced as written, two reproduced with their
diagnosis wrong, and the reproduction turned up **three defects the
review did not have**.

Convention, as elsewhere: **[fact]** = measured in this environment on
the stated date.

---

## 1. Verdict first

| | |
|---|---|
| **Findings worked** | 11 of 11 |
| **Acceptance blocks met in full** | 10 |
| **Met in part, with the shortfall stated** | 1 (F6) |
| **Front door, this repository** | 17 passed / 3 failed / 3 skipped, exit 1 → **22 / 0 / 1, exit 0** |
| **Front door, the mirror** | 8 / 6 / 9, exit 1 → **16 / 0 / 7, exit 0** |
| **Silent gate terms found in the front door** | 1 |
| **Mirror test suite** | 499 passing / 47 skipped → **544 / 38, 0 failed** |
| **`check_claims` in the mirror** | 1 wrong, 15 need build output → **0 wrong, 7 need build output** |
| **Found by reproducing, not in the review** | 3 |
| **Found by re-reading this record, not in the review** | 5 |
| **Found by the proofs, in my own fixes** | 3 |

The middle row of those last three is the one worth the space. Five
defects were found not in the repository but in **this document and the
work it describes**, by going back over finished sections with the same
suspicion the review brought:

* `docs/86` F8 said the unresolved equivalence partition was "one of
  the two read ports, and only one". Reading the partition instead of
  its name showed it holds **both** read ports and all thirty-one
  registers — the whole substance, not a corner of it.
* `docs/86` F1 had no cost measurement while F2's and F3's did, against
  a standing constraint that says to measure anything added.
* `docs/60` documented no crash register, so a register had been added
  to the programming model and left out of the programming reference.
* `soc_boot`'s proof harness was silent about that same register: four
  directed tests, and nothing said for every reachable transaction.
* `docs/60`'s APB slot split is cited as measured from
  `regmap/memmap.yaml`, and that file stopped producing it some time
  ago — five implemented and eleven reserved is now nine and seven.

**The most useful thing the review did was not a finding.** It was the
instruction to re-run the reproduction, because two of its diagnoses
were wrong in the same direction: it attributed all three of F0's
failures to mirror generation, and one of them (F0c) is a defect in
the development repository that the mirror merely inherits. A fix
applied to the mirror would have left it in place.

---

## 2. The three defects the reproduction found and the review did not

**`scripts/ci_local.sh` did not use its own interpreter.** It resolves
one at line 54 and then used a bare `python3` at sixteen call sites, so
on a machine whose system python is not the venv the licence, docs,
paper, mirror and suite gates all failed for the interpreter rather
than for the thing they check. A gate that fails for the wrong reason
is worse than no gate: it trains the reader to ignore it.

**Twenty-two formal directories were undispositioned.** Nineteen are
results `docs/63` sections 22 and 23 already record in full — the
twelve M-extension checks bounded at 7,200 s under bitwuzla, and the
seven register-file scrub tasks. What was missing was the row, not the
work. **A measurement that is documented but not dispositioned is
still an undispositioned non-PASS.** The other three were `soc_npu`'s
proofs reading PASS-STALE: they had been proved before `WAKE_GNT` was
added to `soc_npu.v`, so the verdict was about different bytes. Re-run
against today's RTL, all three pass again **[fact, 2026-09-17]**.

**Two skips were avoidable.** The paper build probed for `pdflatex`
while `paper/Makefile` resolves tectonic first, so it skipped on every
machine that has tectonic and no TeX Live — which is this one. The
probe is now the Makefile's own.

---

## 3. The three defects the proofs found in my own fixes

All three are the reason the review's standing constraint — *re-run
the affected proofs before claiming a fix* — is the most valuable
sentence in it. Note what they have in common: none was found by
writing the fix, reviewing the fix, or running the existing tests over
the fix. A solver found each one, in seconds, after the fix looked
finished.

**The APB timeout delivered two responses for one request.** After a
timeout fired, a slave that asserted PREADY late sent the machine back
to idle and answered again. A6 and A9 both forbid it and the fabric's
ownership queue would mis-pop on it. `&& !to_fired` closes it, and a
simulation test drives the late PREADY so it stays closed. **Found by
`prove_to`, not by reading.**

**The crash register broke five guards, and every one of them was
right to break.** The flip-flop budget derivation, the unprotected-flop
allow-list and the `HARDEN = 0` baseline all pinned a number that the
33 new flip-flops moved. They now name the 33 as a term rather than
absorbing it, and `docs/68` section 9.1's 92 stays 92, because 92 is
what it measured.

**The crash register's own first property was false.** `D11`, written
2026-09-18 to state what the new register guarantees, said no APB write
to any offset changes it. `bmc` refuted that in seconds: a write and a
double fault can arrive in the same cycle, and then the record does
move — not because of the write. The carve-out is `!$past(crash_seen_i)`,
which is `D9`'s `!prot_mismatch` one cycle across. Without the proof the
property file would have carried a sentence the block does not honour,
and it would have read as more assurance rather than less. **Found by
`bmc`, on the first run, on a property I had just written to be true.**

---

## 4. Finding by finding

### F0, F0a, F0b, F0c, F0d — the front door

`scripts/ci_local.sh all` is the command `README.md` tells a reader to
run and `.github/workflows/checks.yml` invokes. It exited 1.

Five causes, not the three the review found. Two were mirror-only and
both were the same shape, *a tool that is correct upstream and cannot
run in the tree it generates*:

* **F0a.** The redaction assertion fired on an already-redacted
  fragment. The assertion was not the defect and deleting it would
  have been — its comment states the guarantee, that a fragment
  REWORDED upstream must fail the build because the alternative is
  that it travels. Each entry now carries an explicit marker and a
  zero-match is accepted **only** when the marker proves a previous
  run redacted it. Three rows, and the third is the one that matters:

  | pattern | marker | outcome |
  |---|---|---|
  | matches once | absent | redact — the upstream case |
  | matches zero | present | already done — the mirror case |
  | matches zero | absent | **FAIL** — the reworded case |

  `sw/tests/test_mirror_redaction_is_idempotent.py` proves all three.
  Writing it turned up that one entry is a fixed point and the other
  two are not: `ci_local.sh`'s redacted form still matches the pattern
  that found the original, because `'(account status, not published)'`
  is itself a `'[^']*'` match. So the property that holds for all three
  is not *the pattern is gone* but *the marker is present and
  regenerating changes nothing*.

* **F0b.** The logs named development commits as bare hashes that
  resolve nowhere in the mirror, so `check_claims` called the last row
  WRONG — in a file whose entire purpose is that a measurement names
  the commit it was taken at. Deleting the row or substituting a mirror
  commit would have been fabricating provenance. The hash is kept and
  prefixed, `upstream:587fdd8`, the convention is in each log's own
  header, and the claim now reports `man` with that reason. A claim may
  name one output meaning *this tree cannot re-derive this, and here is
  why*; it is a value the command PRINTS, so a tree that CAN re-derive
  it still must.

* **F0c** is **not** a mirror artefact, which is where the review's
  diagnosis is wrong. `\mbox` entered `paper/main.tex` on 2026-09-13
  inside a dated correction note, the file is byte-identical in both
  trees and the renderer fails in both. `\mbox` means *do not break
  this across lines*, so it maps to a non-breaking span rather than
  being swallowed, and the same construct is what the thesis's `\dcite`
  expands to.

  **The gate was never missing.** It has been in `ci_local.sh` since it
  was written and it caught the defect the moment it was run. The
  problem is that it was not run: `ci-local-log.tsv`'s last row was
  2026-09-10 and the defect arrived on the 13th. The same property is
  now also in `pytest`, which runs on every change. *A guard in a place
  nobody runs* is `docs/78`'s rule read the other way round.

* **F0d.** The log now names the commit that made the front door green,
  on a clean tree.

### F5 — what the line and proof counts do not cover

`hw/rtl/npu_regbank.v` (936 lines) and `hw/rtl/scrub.v` (332) are
complete, tested and proved, and are built into nothing: not
`pilot_top.v`, which carries its own inline banks; not the TTIHP26b
submission, whose `source_files` names neither; not `soc_top.v`, which
instantiates `soc_scrub`, a different module in a different file.

**1,268 of 6,883 lines (18.4 %) and 14 of 54 proof tasks (25.9 %)**
**[fact]**. Nothing is wrong with the modules or the proofs. What was
missing is anyone saying so, and the review named the right fix: state
the scope, do not shrink the set. `README.md`, `docs/11`'s new `Built
into` column and `docs/09` row 6 each say it now.

Stating it once fixes today. `sw/tests/test_no_orphan_modules.py` makes
the next one fail: every module under `hw/rtl/` must be reachable by
instantiation from `tt_um_melihakbulut_nssoc` or `soc_top`, or carry a
row in `hw/known-unbuilt.txt` with a reason. It fires in both
directions, and that was checked by making it fire rather than by
reading it **[fact, 2026-09-18]**: an empty module dropped into
`hw/rtl/` fails it by name — `assert not ['zz_orphan_probe']` — and a
row naming a module that does not exist fails it too. Both probes were
removed and the tree verified clean afterwards. A guard nobody has
seen fail is a guard nobody has tested.

The ledger is beside the frozen tree and not inside it. The first
version put it in `hw/rtl/` and `test_soc_npu_guards.py` caught it
within the minute, which is the freeze doing its job.

### F6 — the evidence, and where this falls short

Every `runs/` tree is gitignored, for the good reason that a 113 MB GDS
does not belong in git. The consequence was that nothing this corpus
says about layout could be checked from a clone.

The evidence is small. `final/metrics.json` is about 10 kB and
`resolved.json` about 30 kB; fifteen cited runs is **722 kB**, now
under `docs/evidence/`. `sw/tests/evidence.py` is what the tests read
them through: the live run tree wins when present, the record answers
when it is not, and `source` says which — so a test reports *checked
against the recorded artefact* rather than *checked*, which is a weaker
claim and deliberately weaker.

| | before | after |
|---|---|---|
| mirror tests passing | 499 | **544** |
| mirror tests skipped | 47 | **38** |
| `test_flow_evidence` skips | 11 | **5** |
| `check_claims`: need build output | 15 | **7** |
| `check_claims`: re-derived | 12 | **20** |

The claims took a second pass to move. The first round of this work
taught the TESTS to read the record and left the CLAIMS alone, so
`check_claims` still reported fifteen. Five of those read
`s77gate/resolved.json` and one `s81ptd/final/metrics.json` — records
this repository already had — and two more named `s81timing` and
`s81drv`, which the collector did not list. `check_claims` now resolves
a run-tree path to its committed record when the tree is absent, and
says which answered.

**The acceptance asked for fewer than thirty skips and this is
thirty-eight.** Two measurements before the table, both taken
2026-09-18 in the generated mirror with
`.venv/bin/python -m pytest -q`:

* `check_claims` there reports **20 re-derived, 15 hand-read, 7 need
  build output, 0 wrong**. The acceptance asked for *substantially
  fewer than 15* needing build output; seven is that.
* The acceptance's condition was a clone **with yosys installed**, and
  that had not been tried. It was: the count does not move. 544 passed
  / 38 skipped without yosys on `PATH`, 542 / 38 with it -- the same
  thirty-eight skips, because none of them is waiting on yosys. (The
  two that changed column went red, not green, and for a reason that
  had nothing to do with this finding: that yosys was 0.67 where every
  count in `test_soc_synthesis_guards.py` was measured with 0.33. Under
  the pinned 0.33 the file is 69 passed / 2 skipped. The guards now say
  which mapper produced a disagreeing number.)

Every one of the thirty-eight is accounted for, and the reason matters
more than the number:

| count | needs | why it stays out |
|---|---|---|
| 17 | a whole-SoC or gate-level netlist | 17 MB of build output; the finding's own instruction is to keep `runs/` ignored |
| 5 | `hw/soc/gen/` | gitignored by a **licensing decision**, not by size: `LICENSES.md` and `docs/14` section 2.2 both state as a **[fact]** that `git ls-files` returns nothing under it, because third-party trees here are fetched and not vendored. Committing 680 kB would falsify a published sentence in two documents |
| 5 | the run tree's step directories and logs | not evidence in the sense this finding means |
| 5 | the sign-off DEF | the same |
| 3 | nothing — the redaction guard is inapplicable in a generated mirror | it says so, once per test rather than once per fragment |
| 1 | the gitignored Tiny Tapeout clone | fetched, not vendored |
| 1 | any run tree, to compare the record against | the comparison is what a machine holding the runs does |
| 1 | per-step `config.json` files | sixty-seven per run, and the property is about the step directories themselves |

So under thirty is reachable only by committing 17 MB of netlists or by
breaking a licensing posture that two documents state as fact. The
number is reported rather than reached, and the seven skips that WERE
mine to remove were removed.

These files are NOT in `docs/80-artefact-digests.tsv`. That file's own
header says every path in it is gitignored on purpose: its job is to
pin what git cannot see. These are tracked, so git pins them already
and a second copy would be a weaker guarantee. What git cannot tell you
is whether the record still matches the run tree it came from, and
`sw/tests/test_recorded_evidence.py` checks exactly that.

### F1 — the accelerator's flush reset

`blk_rst_n` was `rst_ni && !flush_pulse`, one combinational net driving
`aer_fifo`'s ASYNCHRONOUS `rst_n` and read synchronously by the
one-hold register at the same time. It was the only reset in this SoC
reaching flip-flops without the two-stage deassert `soc_top.v:352-359`
builds for every other one.

`aer_fifo.v` is frozen, so the port cannot gain a synchronous flush and
the fix lives in `soc_npu.v`: `blk_rst_n` is now asynchronous assert
with synchronous deassert and drives nothing but the two queues, and
the synchronous consumers read `blk_flush`.

**Measured, not assumed.** A new simulation test pins all three claims:
assert is immediate, `blk_flush` is the exact complement of
`blk_rst_n` at every edge, and release lands **three edges** after the
pulse clears rather than one **[fact]**. Deleting the synchroniser
makes it fail; it was checked that way.

**Cost, and it was missing until 2026-09-18.** The standing constraint
is to measure the cost of anything added, and this section had no
measurement while F2's and F3's did -- the review named those two and
this one adds logic as surely as they do. Against the same block with
`blk_rst_n` put back to `rst_ni && !flush_pulse`, yosys 0.33,
`synth -flatten`, `sg13g2_stdcell_typ_1p20V_25C` **[fact,
2026-09-18]**:

| | before | after | delta |
|---|---|---|---|
| flip-flops | 3,850 | 3,854 | **+4** |
| cells | 11,733 | 11,732 | **−1** |
| area, um2 | 193,087.7298 | 192,478.0914 | **−609.64** |
| | | | **−0.32 %** |

**Read the area as noise and the flip-flops as the result.** −0.32 % is
well inside the ~1.1 % mapping noise `docs/45` section 4.3 measured on
a block nobody had touched, so this document will not claim the fix
made the accelerator smaller. What it does claim is the sharp half:
**four flip-flops**, because flip-flop counts have no mapping noise.
The source adds two — `blk_rst_sync[1:0]` — and the other two are the
mapper's, duplication for fan-out being the usual cause; that was not
chased, because the question the constraint asks is the size of the
bill and the bill is four flops in a block of 3,854.

The lint pragma is four lines wide and sits on the synchroniser alone.
A reset synchroniser IS a register asynchronously reset and
synchronously shifted whose output resets something else
asynchronously; `SYNCASYNCNET` sees that shape and cannot tell it from
the defect the shape removes. Anywhere else in the block it still
fails.

### F2 — the crash record

`soc_top.v:568` read `.crash_dump_o ()` while `:569` wired
`double_fault_seen_o` out to a pin: the SoC exported the FACT of a
fatal fault and dropped everything that would say where it happened.

Only the faulting PC is kept, and that is a choice. `crash_dump_o` is
160 bits and BOOTREG's slot has room for one register at its own next
free offset, `0x010`. It lives in `soc_boot` because that block is
already in the power-on domain — the one place whose registers survive
the reset a double fault causes. First fault and not last, because a
fault the watchdog resets is likely to recur for the same reason.
Neither word is clearable.

**Cost, against the unmodified block, yosys 0.33 with
`sg13g2_stdcell_typ_1p20V_25C` [fact, 2026-09-17]:**

| | before | after | delta |
|---|---|---|---|
| flip-flops | 143 | 176 | **+33** (32 PC + 1 flag) |
| area, um2 | 12,316.2984 | 14,807.1672 | **+2,490.87** |
| of `soc_boot` | | | +20.22 % |
| of the SoC's 933,010 um2 of standard cells | | | **+0.267 %** |

**The block-level tests, and why they were not enough.** Four new tests
drive the capture directly and hold `rst_ni` low while `rst_por_ni`
stays high, which IS the watchdog reset, three times over. What they
cannot show is Ibex actually taking the fault, because they contain no
Ibex.

**The whole-SoC injection, done 2026-09-18.** This section said until
that date that it was not done, on the stated ground that there is no
whole-SoC cocotb testbench here. That ground was half right and the
conclusion was wrong: there is no whole-SoC *cocotb* testbench, but
`hw/soc/tb/tb_soc.v` is a whole-SoC Icarus testbench that has been here
all along, and `hw/soc/flow/sim_soc.sh` runs the real core on the real
fabric out of a real ROM image. The acceptance asked for cocotb because
that is what the rest of this repository uses; what it wanted was the
injection, and the harness that could do it was already built.

`crash_demo()` in `hw/soc/tb/sw/test_ibex.c`, behind
`-DCRASH_DUMP_DEMO`, is that injection. It arms the watchdog, writes an
unmapped address into `mtvec`, and executes `.word 0x00000000`. The
illegal instruction traps, the trap fetches from `mtvec` and faults
again, and Ibex raises `double_fault_seen_o`. Nothing acknowledges,
because nothing can; the watchdog escalates and reboots the SoC. Run
**[fact, `SOC_VVP_ARGS=+allow_double_fault
SW_DEFINES=-DCRASH_DUMP_DEMO hw/soc/flow/sim_soc.sh`, 2026-09-18]**:

```
crash demo: boot with BSTAT 0x00030000
crash demo: arming, then double-faulting
[TB] watchdog stage 1 (NMI) at cycle 115460
[TB] watchdog stage 2 (system reset) at cycle 121876
    [... the second boot's ROM copy and verify, 5 lines ...]
crash demo: boot with BSTAT 0x00030401
crash demo: faulting PC 0xff9fe000
crash demo: the record survived the reset the fault caused
RESULT PASS
    [... the testbench's nine per-block summaries ...]
[TB] PASS
```

Lines 20-42 of the run's log, in the order the run produced them, with
the two elisions marked. `RESULT PASS` is the program's own verdict and
`[TB] PASS` is the testbench's; both are needed, because the program
can be satisfied by a testbench that noticed something else wrong.

`0xff9fe000` is the exact `mtvec` the program set, read back by a
different boot of the same SoC across the reset the fault caused. Bit
10 of `BSTAT` in `0x00030401` is CRASHV. That is the acceptance, end to
end, on the real core.

**And a property, because the block's strongest evidence was silent
about it.** `soc_boot` has a proof harness carrying D1-D10, and a
register was added to that block without adding anything to it: four
cocotb tests sampled the new state and nothing said what was true of it
for every reachable transaction. `D11` now does -- once `CRASHV` is up
neither it nor the PC ever moves again, no write to any offset can
forge or clear either, the flag rises only in the cycle after the core
reported a fault, and the PC is zero exactly while the flag is down.
All five `soc_boot` tasks PASS with it, `prove` among them, so it holds
unbounded and not to a depth **[fact, `make -C hw/soc/formal boot`,
2026-09-18]**. Three cover statements come with it and all three are
reached, the second being the formal witness of the same thing the
simulation above shows: a record still there on the far side of the
system reset that the fault led to.

The first version of D11 was refuted in seconds, and the refutation is
worth more than the property. It said no write changes the record, full
stop. A write and a double fault can land in the same cycle, and then
the record does move -- not because of the write. The carve-out that
fixes it is `!$past(crash_seen_i)`, which is `D9`'s `!prot_mismatch`
one cycle across, and without the proof the file would have carried a
sentence the block does not honour.

**One testbench change was needed, and it is the interesting part.**
`tb_soc.v` treated `double_fault_seen_o` as fatal for any program, and
that is right for every program but this one, whose whole subject is a
double fault. The choice was between failing the run that demonstrates
the feature and never noticing a double fault in any other run. Neither
is acceptable, so the check is now gated on an explicit
`+allow_double_fault` plusarg -- tb_soc.v's own convention, alongside
`+ram_random`, `+ded_word` and `+strap` -- which `sim_soc.sh`'s header
documents and only this one build passes. The check is unchanged for
every other program **[fact: the 22-check baseline run still reports
`[TB] PASS` with the plusarg absent]**.

### F3 — the APB timeout, and what it costs in AMBA clauses

`ST_ACCESS` had exactly one exit. Not a live bug at today's parameters
— eight of nine mapped slaves drive PREADY as the literal 1 — but
`soc_apb_wb.v` has a genuinely non-constant PREADY and is written and
proved, so the first wait-state slave wired in makes it live.

**There is no protocol-clean timeout, and finding that out is most of
the work.** Dropping PSEL and PENABLE is a master-side abort, which APB
does not have and A4 forbids. Holding them means a late PREADY no
longer ends the transfer, which is A5. One of the two has to give, and
A4 is the one kept.

So at `APB_TIMEOUT != 0` the parameter costs exactly three AMBA
clauses — **A5, A9 and A10** — each antecedent-guarded and each stated
where it is deviated from. At `APB_TIMEOUT = 0`, the default, it costs
none of them, and the synthesised netlist is **identical**: 193 cells
and 93 flip-flops before and after **[fact, yosys 0.33 with
`sg13g2_stdcell_typ_1p20V_25C`; and re-measured on every run by
`sw/tests/test_soc_synthesis_guards.py::test_the_apb_timeout_costs_nothing_at_its_default`,
which is a stronger authority than a date because it fails the day the
netlist stops being identical]**. Three new invariants
(A12, A12a, A12b) are the price of keeping the rest inductive.

### F4 — the QSPI budget

The header stated a CEILING and the budget under it was stated
nowhere: no `set_input_delay` on `qspi_io_i` anywhere, so the flow used
LibreLane's blanket `IO_PCT` synthetic delay, which is a fraction of
the clock period and not a model of a flash.

The arithmetic is now in the three places that must agree, with every
input naming its file:

> `DIV >= ceil((tCLQV + 2 x board) / CLOCK_PERIOD) - 1`

`tCLQV = 6.0 ns` is the part's. The 2.0 ns board allowance each way is
**ASSUMED** and named as one in all three places, because there is no
board, no pad ring and no pad model here; the SDC holds it as a
variable so a measurement can replace it.

**Then measured**, which is what a ceiling cannot give. OpenSTA 3.1.0
over the sign-off netlist at the typical corner with the fragment
sourced: the input path closes at **+9.4682 ns** and the SCK output
path at **+16.7764 ns** **[fact, 2026-09-18]**. Re-measured the same
day from a script written fresh rather than reused -- same netlist,
corner, period and tool -- the two come back **+9.4777** and
**+16.7786**, which is 0.0095 and 0.0022 ns apart. The residual is not
diagnosed and the SDC's header says so; what it is not is a disagreement
worth hiding.

**No synchroniser belongs on this path**, and the RTL now says why
rather than leaving it to be reached for. `io_i` is source-synchronous:
the flash launches it off the SCK this block generates from `clk_i`.
Two flops on a read-data lane would delay the data two clocks relative
to the shift sequencer and corrupt every word read.

### F8 — the register-file property

Two of the three acceptance bullets were already met before the review
was written: `docs/63` section 23 records both the bounded route (the
real codec, which does not close, with the reason located in the
parity trees) and the abstracted one (`regfile_scrub_abs.sby`, R1–R4
proved unbounded in 44 seconds). The third was genuinely open and is
now closed: `formal-dispositions.tsv`'s thirteen `reg_ch0` rows stay
exactly as recorded on 2026-09-11 and the file's header names the
replacement, and `docs/63` gains section 24 for the distinction the
corpus did not contain — `regfile_scrub_abs` proves a property of the
BLOCK, `reg_ch0` a property of the CORE, and only the first is what a
file swap needs.

**The review's preferred route, attempted and reported.** It ranked
equivalence third and strongest: prove `ibex_regfile_secded` equivalent
to upstream's `ibex_register_file_ff` on the fault-free input space,
using the `eqy` machinery `formal/eqy/` already has. That was tried.

Two obstacles the review does not mention, and both are results. The
gold side lives in `hw/soc/gen/`, which is gitignored vendored Ibex and
is therefore absent from the mirror and from a fresh clone — so this
job cannot run where most of the suite runs. And the two modules are
**not interface-identical**: the substituted file adds `rf_ecc_err_o`,
so `eqy` refuses to combine them outright. `formal/eqy/regfile_shim.v`
restricts the question to the sixteen ports upstream has, which is
written out rather than hidden in a tool flag.

With that, at `SCRUB = 0` and depth 16, `eqy` forms **13 partitions**
and proves 12 **[fact, 2026-09-18]**. That ratio is arithmetically true
and rhetorically false, and the second pass through this section is
what caught it.

**What the twelve are.** `rcap_a_o`, `rcap_b_o` and their `u_rf.`
counterparts; the four bits of `cheriot_enable_i`; `dummy_instr_id_i`,
`dummy_instr_wb_i`, `test_en_i`, `wcap_a_i`. Every one is a tie-off, a
constant, or the capability path, which at `CapWidth = 1` is one wire.
They are the periphery of the question.

**What the one is.** `eqy` merges partitions that share a cone, and the
thirteenth is where everything that matters ended up: reading the
partition's own generated module shows it carries
`__po_rdata_a_o__gold` **and** `__po_rdata_b_o__gold` together with all
thirty-one `rf_reg_q` register outputs **[fact,
`rf/partitions/regfile_shim.rdata_a_o.sv`]**. There is no separate
`rdata_b_o` partition at all. So the unproved partition is not *one
read port of two*; it is **the register array, both read ports, the
write path, the encoder and the decoder** — the whole substance of the
substitution, in one piece.

An earlier draft of this section said the unresolved partition was
"one of the two read ports, and only one, which is itself worth a
look". It was worth a look, the look was taken, and the sentence was
wrong: it read a partition NAME as if it were a partition's CONTENTS.
That is this repository's own recurring failure shape and it is
recorded rather than quietly deleted.

**The verdicts on that one partition, both bounded and unbounded.**

| strategy | engine | result |
|---|---|---|
| `sat` | eqy's own SAT, depth 16 | `UNKNOWN` — *reached maximum number of time steps*, 316 s |
| `pdr` | `use sby`, `engine abc pdr`, `mode prove`, 3000 s cap | `TIMEOUT` at 3000 s — *did not return a status*, no traces |

**How far `abc pdr` actually got is the sharper number.** That
partition's generated miter has **172 outputs**. In 3000 seconds the
engine reached **output 3**, timing out on output 1 alone fifty-nine
times in its anytime retries before moving on **[fact,
`rf/strategies/regfile_shim.rdata_a_o/pdr/.../logfile.txt`,
2026-09-18]**. It is not close. Nor is more time obviously the answer:
the same engine, on the same question with the codec ABSTRACTED AWAY,
closes `regfile_scrub_abs.sby` unbounded in 44 seconds (`docs/63`
section 23). Forty-four seconds against fifty minutes and 3 of 172 is
the cost of the parity, measured twice by two different routes.

**It was not refuted, and that is the whole of what can be said.** No
counterexample was produced by either route: the bounded one reached
its bound, the unbounded one reached its clock and produced no trace,
and `eqy` itself warns that its method is sound for proofs and
**incomplete for refutations**, so a non-verdict here is not evidence
of a difference. What the exercise establishes positively is
the periphery; what it establishes negatively is that the review's
"much easier problem than `reg_ch0`" is easier but not easy, and the
reason is the one `docs/63` section 23 already located — thirty-two
encoders and two decoders of parity, which CDCL SAT cannot resolve in
polynomial size and which no pinned engine here carries Gaussian
elimination to shortcut. `formal/eqy/regfile_secded.eqy.in` carries
both strategies so the next person starts where this stopped.

### A defect the front door itself had, found 2026-09-18

Running the MIRROR's front door -- not the development repository's --
turned two gates red, and the second of them is worth the space here.

`verify.sh --dispositions` printed

```
0 formal task directories, 0 not a fresh PASS, 0 undispositioned
```

and exited 1, with **nothing on stderr at all**. Three zeros and a red
light. The counts were correct and had nothing to do with the verdict:
the gate is a conjunction of five terms and the one that failed was
`frozen`, the count of tracked files modified under `hw/rtl/`,
`hw/tb/`, `tt/`, `formal/` and `hw/openlane/`. One regenerated file
under `formal/` was uncommitted in the mirror, which is exactly what
that term is for -- the verdict was right. The message was about
something else.

A red gate whose message names the wrong subject is worse than a red
gate, because the reader debugs the thing it named. This is the same
shape as the two synthesis guards further up, which blamed the design
for a mapper version, and as `tb_soc.v`'s summary line, which blamed
the register for a display: **three defects in one day, all of them a
correct verdict wearing the wrong explanation, and none of them
detectable by any test in this repository.** The term now prints what
it found and what those trees are for.

### F7 and section 5 — documentation

`ROADMAP.md` gains the macro-edge keep-out experiment as a named,
costed item, and a table of what a foundry and a test house will ask
for that this repository does not have. The review's second F7 action
needed no change: no summary sentence reads as *the SoC layout is
DRC-clean*, and `paper/main.tex` carries an explicit house rule against
the phrasing.

### F10 — the pytest numeral

`README.md` said the root collects 503; a fresh clone collects 532 and
this machine 543. **The correction is to stop printing the number.**
`test_soc_clkgate_guards.py` parametrises one case per gate-level
netlist under the gitignored `hw/soc/out/`, so running synthesis
changes the count without changing a tracked file. The other four
numerals name a command *and* a value because both are stable; this one
now names the command only. The 2026-09-10 and 2026-09-11 entries stand
as written — they were right on their dates.

---

## 5. What the review got wrong, stated plainly

Two things, and both in the same direction — a diagnosis reaching one
step further than its evidence.

1. **"All three failures are mirror-generation artefacts."** F0c is
   not. It is a development-repository defect that the mirror
   inherits, and a fix applied to the mirror would have left it
   standing upstream.
2. **F8's three options described as untaken.** `docs/63` section 23,
   dated 2026-09-15 and 2026-09-16, records options 1 and 2 both taken
   and measured. The review read sections 17.2 and 23 and reported the
   state before the latter.

Neither is a serious error and both are the kind a reader of a large
corpus makes. They are recorded because this document would be
dishonest without them: the review found eleven real things, and the
two it got wrong were found by the procedure it insisted on.

---

## 6. What none of this changes

No silicon. No beam. No frequency. The part is placed and routed and is
a core-only block with no pad frame, which section 5b of `ROADMAP.md`
now says in one place. Every hardening claim remains a mechanism plus a
simulated fault-injection campaign.

---

*2026-09-18. Nothing was built for this document; it records eleven
findings worked, three defects the reproduction added, three the proofs
found in the fixes, five this document's own second reading found in
the first, and one place where the acceptance was not reached.*

*The second reading is the part worth keeping. The first pass through
these eleven findings ended with a document that was true in every
sentence a reader would check and wrong in two a reader would believe:
"the whole-SoC injection is not done", when the testbench to do it had
been in the tree the whole time, and "twelve of thirteen partitions
proved", when the thirteenth was the question and the twelve were its
margins. Neither was a lie and neither would have been caught by any
test here. They were caught by going back over finished work with the
suspicion the review arrived with, which is the only procedure in this
repository that has ever found this class of defect, and which no
amount of green CI substitutes for.*
