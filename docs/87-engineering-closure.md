# 87 — Fresh-clone engineering closure

2026-09-19. Starting revision: `473b84f56cb26ab97aa2a5d409c779568c2507a3`.
This is an implementation and verification update, not a tapeout release.
The frozen pilot RTL, submission files and pilot proof sources were not changed.

## 1. Work completed

### Register-file contract and upstream equivalence

The real ECC encoder, decoder, storage and scrub now have a fault-free
architectural proof. `hw/soc/formal/regfile_contract.sby` compares both
read ports with a resettable 31-word reference array, checks x0 behaviour,
codeword validity and the error outputs, and covers the scrub reaching x31.
Writes to x0 are permitted in the environment and must leave it zero.
The only environmental assumption is initial reset; subsequent resets,
write addresses, write data and both read addresses remain unconstrained.

`ibex_regfile_contract_props.v` supplies **asserted** inductive invariants:
each stored word equals its reference word, and its check field equals
the real encoder applied to that word. No ECC function is abstracted and
no data-correctness invariant is assumed. Both `SCRUB=1` and `SCRUB=0`
prove by induction with Bitwuzla. A first Yices attempt reached its
180-second timeout; that is not counted as a proof.

`hw/soc/formal/regfile_equivalence.sby` additionally compares the actual
pinned upstream `ibex_register_file_ff` with the substituted implementation.
The configuration is the supported RV32 file, 32-bit data, 35-bit capability
ports, no dummy instructions, default fast correction and default syndrome
placement. Both read-data and both capability outputs agree, with scrub
enabled and disabled, and the ECC error output stays zero.

Flattening and sharing the identical reference/upstream state lets induction
use the storage relationship. Before flattening, the miter returned UNKNOWN:
an arbitrary induction state could give the two arrays different contents.
That was not a reachable counterexample and was not counted as a failure of
the implementation. The final miter proves the complete shared interface.
This closes the register-file equivalence question in `docs/86` F8. It does
**not** close core-level `reg_ch0` or the M-extension instruction checks.

Three negative controls independently corrupt a data write, a check write,
and port B's address. All must produce reachable BMC counterexamples.
UNKNOWN, TIMEOUT, missing tools and compilation errors are rejected by the
control runner. The controls live in ignored output, not modified RTL.

### Boot header geometry

The loader previously accepted an odd entry address and a payload extending
past its 16 KiB flash slot, provided the other header checks held. RAM bounds
alone did not enforce the flash-slot boundary.

`hw/soc/tb/sw/boot_geometry.h` now validates the actual ROM copy/jump inputs:
word-aligned nonempty payload, word-aligned destination, halfword-aligned
RV32IMC entry, entry inside the image, destination below the loader's private
RAM, payload inside its own flash slot, and a representable QSPI length.
Subtraction bounds are checked before use, including for a nonzero RAM base.

The host tests compile that exact C predicate, exercise boundary cases and
10,000 seeded cases against an integer-arithmetic oracle. The CBMC harness
checks arbitrary 32-bit header and boundary values and an arbitrary copy-loop
word index. All **21** assertions/runtime checks pass. Removing the entry
alignment or slot bound is refuted independently. This is a proof of the
range predicate and its copy-address arithmetic, not of the entire loader,
the supervisor, MMIO hardware, or all C software in the repository.

Two flash-image counterfactuals, `entry0` and `length0`, preserve the header
checksum while breaking geometry. In whole-SoC simulations each is rejected
with `BOOT_CAUSE_GEOM`, the secondary image is selected, and all 28 application
checks pass. Normal boot passes the same 28 checks.

### Reproduction and verification gates

* Icarus 14 rejected a generate condition using `WIN_MAX` before its declaration
  in `soc_npu.v`, and an initial block using `allow_double_fault` before its
  declaration in `tb_soc.v`. The declarations/guard now precede their uses.
  The NPU's BMC, induction and cover tasks were re-run on the changed source.
* `run_cocotb.sh` used to accept empty XML and a nonzero make exit accompanied
  by passing partial XML. It now requires nonempty results and successful
  process completion, distinguishes skips from passes, rejects an unmatched
  filter, and retains each simulator log under `hw/soc/out/cocotb/`.
* Hardware Python dependencies are pinned in `hw/requirements.txt` to cocotb
  2.0.1, whose `unit=` API the testbenches use. Python 3.14 is not supported by
  that release; `make setup` checks the interpreter before creating environments.
* The local licence/generator gate now uses the generators' existing read-only
  `--check` modes. It neither regenerates files nor runs `git checkout` on user work.
* Formal source freshness now reads SBY's logged source-copy provenance.
  The previous output-parent heuristic was wrong for `sby -d` and for aliased
  inputs. Missing provenance remains unchecked, never silently fresh.
* The root Makefile exposes setup, tests, boot preparation and formal checks.
  GitHub Actions has separate RTL and formal/boot jobs, with evidence uploads.
  Hosted execution of the changed workflow is not claimed by this local run.

The initial fresh clone had **544 Python passes / 38 skips**. Fetching and
converting the pinned upstream source removes five missing-source skips;
the remaining build-output-dependent checks are not relabelled as passed.
The complete RTL sweep reported **460 passes, 0 failures, 15 skips**. The
older runner counted those 15 skipped cases as passes; these totals explicitly
exclude them. The final NPU-only regression, after the declaration-order
repair, passed all 42 cases. Local CI finished with 16 passing gates, no
failures and seven stated skips (six absent physical run trees and Pandoc). Frozen fault-injection/gate-level campaigns remain opt-in.

## 2. Measured artifacts

`docs/evidence/closure-20260919.json` records the final results,
tool identities, commands and source digests. It is a committed measurement
record; a clean clone can read it but must run the commands to reproduce it.

| Check | Result |
|---|---|
| NPU `bmc`, `prove`, `cover` | PASS on the changed source |
| Real-codec contract, scrub enabled/disabled | PASS, unbounded induction |
| Scrub coverage | PASS, x31 reached at step 32 |
| Direct upstream equivalence, scrub enabled/disabled | PASS, unbounded induction |
| Register-file mutation controls | 3 reachable counterexamples, as required |
| Boot range CBMC | 21 checks, 0 failed |
| Boot range mutation controls | 2 counterexamples, as required |
| Normal boot | 28 application checks, `[TB] PASS` |
| Odd-entry primary | Geometry rejected; secondary boot; 28 checks, `[TB] PASS` |
| Oversize primary | Geometry rejected; secondary boot; 28 checks, `[TB] PASS` |

Early experimental SBY directories remain on the development machine.
The Yices timeout and four PASS results whose harness was subsequently
strengthened are explicitly dispositioned as historical, superseded by the
fresh canonical jobs under `hw/soc/formal/`. They are not included in the
current proof count. Negative-control FAILs are separately dispositioned.

## 3. Reproduce

```sh
make setup PYTHON=/usr/bin/python3
make test
make rtl-test
make check

make soc-prepare
export OSS_CAD_SUITE=/absolute/path/to/oss-cad-suite
make rf-contract rf-equivalence
make boot-proof CBMC=/absolute/path/to/cbmc
make soc-boot-regression
```

Use OSS CAD Suite **2026-08-04** (Yosys **0.67+146**, Bitwuzla **0.9.1**)
and CBMC **6.11.0** for the new proofs. The SoC preparation target fetches
Ibex at `34b0705760ef3dfa00e99637432473d2be8f22f3`, sv2v **0.0.13**, and
xPack RISC-V GCC **15.2.0-1**, using the existing pins and archive checksums.
The CI workflow shows the pinned CBMC download and checksum. Icarus **12.0**
ran the RTL sweep; the pinned suite's Icarus **14.0** ran the whole-SoC cases.
The Python synthesis guards still use their existing Yosys **0.33** mapper;
their area counts are not interchangeable with the formal tool version.

## 4. Work that remains open

Follow-up: `docs/88-interface-integration.md` implements the four additional
spacecraft interfaces and records the subsequent physical work. The table below
is the open inventory at this earlier closure commit; use docs/88 for its update.


The repository combines a frozen pilot, a SoC prototype and a future product
roadmap. Passing the checks above does not finish the following work.

| Item | Remaining work and dependency |
|---|---|
| Physical closure | Setup, slew/cap, macro-edge DRC keep-out experiment, replica separation, and new-layout power/STA/fault campaigns remain open (`docs/67`, `docs/79`, `docs/83`, ROADMAP section 5a). No new place-and-route result was produced here. |
| Full ISA proofs | Core `reg_ch0` and outstanding M-extension checks remain separate from the register-file substitution theorem (`docs/63`). |
| Whole-software safety | Full supervisor/loader runtime-error analysis, scheduling requirements and PMP fault protection remain beyond the proved range predicate (`docs/09`, `docs/46`). |
| Chip/test integration | Pad ring, ESD, scan/ATPG, memory BIST, JTAG/debug and clock/reset circuitry are absent; these require implementation and physical/test validation (ROADMAP section 5b). |
| Product expansion | Additional spacecraft interfaces, multi-node/AER transport and optional camera support depend on the selected product requirements and IP licensing (`docs/02`, `docs/65`). |
| Evidence on a fresh clone | Physical/netlist checks still require the ignored artifacts or rebuilding them; recorded metrics do not replace those checks (`docs/86` F6). |
| Owner/external actions | Funding/application decisions, shuttle purchase, fabrication, board bring-up and radiation tests were not performed. No silicon or beam qualification is claimed. |

The physical tools were found on this machine, but this run did not execute
their multi-hour experiments. Those rows are unfinished engineering, not
missing-tool excuses and not completed items. The original dated measurements
and their limitations remain intact.
