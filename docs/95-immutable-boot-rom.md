<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 95 — Immutable boot contents in standard cells

**2026-09-20.** The SRAM implementation called ROM in earlier physical runs
has no mechanism to load its initial contents on silicon. Simulation's
`ROM_INIT` does not solve that problem. The optional `SOC_BOOT_ROM=logic`
profile now generates the compiled loader as constant gates in the delivered
`soc_top`, rather than relying on a preloaded SRAM. Earlier layout results
remain measurements of the SRAM stand-in.

The [integration record](evidence/logic-boot-rom-integration-20260920.json)
records commands, image/source hashes, block tests, whole-CPU checks and
synthesis. It does not assert final physical closure or radiation qualification.

## Contents and interface

`hw/soc/flow/gen_logic_boot_rom.py` accepts a little-endian loader binary of
1 through 8,064 bytes. It reserves the first 32 words for the existing reset
vector offset, pads the last partial word with zeros, and generates 2,048
39-bit SECDED codewords. The template contains a combinational case lookup
and a resettable row register. There is no `readmemh`, initialized memory
array, writable code storage or ROM SRAM macro in this implementation.

The existing `soc_mem_ecc` codec retains its bus protocol, read pipeline,
write rejection and error telemetry. Scrub writes have no effect on constant
gates. This protects data at the codec interface; it is not a claim that
address selection, control state, decoding gates or transient propagation
are radiation qualified. Contents are fixed before fabrication. A new
loader needs a new synthesis/layout image, not a software ROM patch.

The generator writes `manifest.json` with the binary, template, codec and
RTL hashes. Repeating an identical build is allowed. An existing output
with different contents is rejected; use a new build directory when changing
the loader. `ROM_INIT` remains accepted by the instance interface for source
compatibility but is not read by the logic ROM.

## Reproduction

From the repository root:

```bash
SOC_BOOT_ROM=logic SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 \
  SOC_WAKE_GNT=1 bash hw/soc/flow/sim_soc.sh hw/soc/out/logicrom-example
SOC_BOOT_ROM=logic \
  SOC_BOOT_ROM_IMAGE="$PWD/hw/soc/out/logicrom-example/test_soc.bin" \
  SOC_MEM=sram IBEX_REGFILE=secded IBEX_RF_SYNPRE=1 \
  SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 \
  SOC_WAKE_GNT=1 SOC_ETH_SRAM=1 \
  bash hw/soc/flow/syn_soc_top.sh 20 hw/soc/out/logicrom-example-syn
.venv/bin/python -m pytest -q sw/tests/test_logic_boot_rom.py
SOC_BOOT_ROM=logic make soc-boot-regression
```

The simulation generates constants from the exact loader it just built.
Synthesis requires an explicit binary and refuses a non-SRAM RAM profile or
an unhardened ROM. The default `legacy` profile remains available for
reproducing historical evidence. CI's existing normal/invalid-entry/zero-length
boot regression now selects the logic profile and archives its image manifests.

## Measured integration

- The generator and actual RTL tests cover both read-pipeline settings,
  all 2,048 addresses, little-endian mapping, partial words, invalid sizes,
  reproducibility and changed-image rejection. Injecting a wrong constant
  trips the independent frozen hardware encoder comparison.
- The native-cell block simulation performs 4,113 reads and 17 rejected
  writes, with scrubbing on and off, using the actual delivered generator.
- The delivered whole SoC boots and passes 28 firmware checks, including
  its expected watchdog stage-1 interrupt. This is RTL CPU verification;
  the block gate-level test is not whole-chip gate-level boot.
- Invalid-entry and zero-length primary-image cases also pass all 28 CPU
  checks after selecting the secondary image. All three cases have the same
  immutable loader manifest. Normal boot uses the registered-read profile;
  these two fallback measurements use the default read profile. The record
  distinguishes the interface-bundle hashes before and after the language
  directive correction; their non-directive RTL is byte-identical.
- Matched standalone logic-ROM mapping uses 4,236 cells, 115 flip-flops
  and 44,551.08 square micrometres of standard cells, with no SRAM macro.
  Whole-SoC synthesis uses 69,971 cells, 9,391 flip-flops and
  1,079,801.1882 square micrometres of standard cells. Against the preceding
  IRQ-enabled SRAM-ROM profile, that is +4,240 cells, +37 flip-flops and
  +33,607.9044 square micrometres, while removing four ROM SRAM macros.
  Twenty macros remain: four RAM and sixteen Ethernet packet banks.
  Macro area is excluded from these standard-cell areas.

## Physical profile and limits

`hw/soc/pnr/config-interfaces-logicrom.json` retains the ECO22 die and the
coordinates of the twenty surviving macros, the 20 ns SoC and 8 ns Ethernet
budgets, derate and checker thresholds. It selects the new external-IRQ SDC
and the logic-ROM define. Unplaced ROM library views remain declared so
lint can parse all branches of the common SRAM wrapper. They are not
instances in this netlist or floorplan.

For `pnr_soc_top.sh`, select that config, `SOC_BOOT_ROM=logic`, the same
`SOC_BOOT_ROM_IMAGE`, and `SOC_BOOT_ROM_DIR` pointing to synthesis's `boot-rom`
directory. The source-list resolver checks that the profile and macro agree,
and the generator checks the image identity. Feed the matching netlist through
an explicit `-i` initial state. As in the existing flow, project synthesis
supplies the mapped netlist; LibreLane synthesis must not replace it.

The first lint attempt found 17 parser errors: the bundled Ethernet parameter
checks use `$error`, but the bundle selected Verilog-2005 for every library.
`prepare_interfaces.py` now scopes language selection per source: Ethernet
uses SystemVerilog-2012, while CAN retains its required Verilog-2005 identifiers.
No vendor source was edited. The repeated native lint/error/timing-construct
check passes with zero errors and zero inferred latches; 1,139 warnings remain
reported under the existing warning policy. A lint process returning zero
before the error-checker step was not counted as acceptance.

Placement/routing, extracted timing, electrical checks, DRC, LVS, package/pads
and fault qualification are separate gates. ECO22's passing setup/hold and
other historical geometry checks do not apply to the new ROM or IRQ netlist.

## Reproducible whole-netlist boot

`hw/soc/flow/sim_logic_boot_gl.py` pairs a synthesis directory with the normal
firmware build. It rejects different loader manifests, changed generated ROM
contents, changed loader bytes, legacy ROM SRAM instances and invalid firmware
status addresses. The testbench uses native standard-cell and SRAM models;
only the external flash is loaded. It requires all 28 firmware checks, the
expected watchdog stage-1 event, correct UART output, no flash-protocol violation
and a clean software exit. The normal build must use UART scaler zero.

```bash
python3 hw/soc/flow/sim_logic_boot_gl.py \
  --synthesis hw/soc/out/logicrom-example-syn \
  --firmware hw/soc/out/logicrom-example \
  --pdk "$HOME/.ciel/ihp-sg13g2" \
  --tool "$HOME/.local/opt/iverilog13/usr/bin/iverilog" \
  --output hw/soc/out/logicrom-whole-gl
```

Icarus 13 or newer is required by the native flip-flop models. The default run
bound is four hours and one million clocks. Progress is flushed every 10,000
clocks; output directories are never overwritten. Commands, model/image hashes
and process results are retained. `--prepare-only` checks the build identity and
writes the commands without running simulation. Before compiling the whole SoC,
the runner now requires an untouched native flip-flop to pass reset, data capture,
hold and asynchronous reset reassertion. A successful compile alone is insufficient.

`--simulator verilator --tool /path/to/verilator` requests a randomized two-state
control with seeds 1 and 29, subject to the same native-cell gate. **The installed
Verilator 5.051 development build fails this gate**: the native `dfrbpq` reset
reassertion does not work; Icarus 13 passes the identical model and stimulus.
The preliminary Verilator whole-SoC runs timed out or were terminated after this
incompatibility was reproduced, and provide no boot evidence. Vendor models were
not modified to obtain a pass. Verilator documents limitations for
[specify constructs](https://verilator.org/guide/latest/warnings.html#specifyign).
This control does not replace four-state Icarus verification. Neither mode applies SDF.

The driver/ROM unit suite has 29 passing tests, including mismatched-image,
missing-macro, status-address and timeout negative controls. Whole-netlist boot
measurements are in progress; this runner's availability is not a boot PASS.


Correction, 2026-09-20: the first complete four-state mapped-SoC measurement
has now returned **FAIL**, rather than remaining merely pending. The CPU clears
RAM and prints 113 UART characters, but the banner ends with one framing error;
the application never starts within one million cycles. The final check count
and exit magic are zero. The identical fixed loader/application pass in RTL.
This is independent of the Verilator reset-model incompatibility and is being
investigated with a CPU/alert/flash progress probe. No SDF was applied and no
ROM/RAM contents were preloaded. See the
[retained native-Icarus failure](evidence/logicrom-whole-gl-failure-20260920.json).

The subsequent [startup observation](evidence/logicrom-startup-counter-diagnostic-20260920.json)
finds RAM SEC/DED counters containing unknown bits by cycle 100 while the CPU's
RAM-clear loop is still executing normally. At cycle 100,000 the old loader has
read that telemetry and CPU addresses, sleep and UART signals have become unknown.
An isolated Liberty-derived functional-cell control reproduces the same behavior;
this failure is not specific to the native Verilog UDP implementation.

The [prepared correction](evidence/logicrom-startup-clear-progress-20260920.json)
clears the RAM startup scrub sources on power-on without first reading them. The
assembly sweep still precedes C; warm-boot records and ROM telemetry remain
untouched. Normal RTL boot passes all 28 checks. The new 3,084-byte loader maps to
69,441 whole-SoC cells with 9,391 flip-flops and 1,080,737.6076 µm² of standard-cell
area. Native whole-SoC boot and fallback tests are still pending. This new immutable
image requires its own physical implementation. **The old-image ECO8 timing
PASS was subsequently withdrawn:** its serialized environment applied zero
derate. [Replaying the same routes at 5%](evidence/logicrom-derate-correction-20260920.json)
fails fast hold and slow setup; electrical violation counts remain zero.

**Verification update, 2026-09-20:** the corrected loader now passes normal RTL
boot and [both geometry fallback replays](evidence/logicrom-startup-clear-fallback-20260920.json),
28 application checks each, zero framing/protocol violations and the same
immutable image manifest. The fallback runs reject primary-image geometry with
cause 4 and boot image 1. These supersede the pending RTL statements above;
full native mapped boot and new-image physical implementation remain pending.

### Replaying native boot from a clean checkout

After `make soc-prepare`, run:

```bash
bash scripts/check_soc_native_boot.sh hw/soc/out/native-boot
```

This downloads ~~eight~~ **nine** locked, untouched upstream files: the PDK
licence, typical standard-cell and Ethernet SRAM mapping Liberty, and the six
native cell/SRAM model files used by the bench. **Correction, 2026-09-20:**
the first hosted run passed native reset and all 28 RTL checks, then rejected
the missing Ethernet mapping Liberty before synthesis. The original eight-file
package was insufficient; the retained failed run is `35506681972`.
`hw/soc/pnr/ihp-native-boot.lock.json` pins IHP commit `c4b8b4e` and
every byte count/SHA256; the files match the installed models used in the local
measurements. The shared downloader rejects a modified cache. It does not install
a complete PDK or provide physical verification inputs.

The wrapper refuses to replace prior evidence. It checks Icarus version and
native reset/data behavior, builds normal RTL firmware, maps the same fixed
loader, then runs the four-state whole-SoC test. It sets the profile explicitly
and removes inherited firmware corruption/fault-injection overrides. Tools resolve
through `tools.soc.mk`, and their actual versions accompany the output. Rebuilding
with a different Yosys version is a new measurement, not a reproduction of an old
cell count. Stage timeouts fail the run; they never become passes.

The `checks` workflow has an opt-in `native_boot` dispatch input for this long
test and retains both successful and failed logs, loader/netlist identities and
firmware. The ordinary push/PR RTL jobs remain separate. Adding this job is not
evidence that its hosted execution has passed; follow its actual result.

**Native boot acceptance, 2026-09-20:** the corrected loader now passes the
[complete four-state mapped-SoC run](evidence/logicrom-startup-clear-native-pass-20260920.json):
637,224 cycles, all 28 application checks, exit code zero, exit magic
`600dc0de`, watchdog stages 1/0/0, zero flash protocol violations and zero
UART framing errors. Native IHP cell and SRAM models remain unchanged, with
no ROM/RAM preload and matching loader manifests. Input hashes stayed
unchanged for the full 3,169.87-second simulation. This supersedes the pending
local native-boot statements and closes the diagnosed power-on telemetry
read defect; the original failure remains the negative baseline. It does
not establish SDF timing, radiation qualification or final-image physical
acceptance. The independent hosted rebuild remains a separate run.

### Hosted synthesis diagnostic compatibility (20 September 2026)

The next clean GitHub run (`35507310951`, head `f4e41e5`) passed native
cell reset, all 28 RTL checks and synthesis. Gate elaboration then failed:
Yosys 0.67 keeps `crash_dump`, while local Yosys 0.33 keeps
`u_ibex.crash_dump_o`. The progress display used the latter alias. Removing
this optional diagnostic leaves all acceptance conditions unchanged. Both
the actual downloaded CI netlist and the local netlist now compile with
unmodified IHP models. This compile control is not a hosted boot PASS; the
full hosted retry remains necessary. See
[evidence](evidence/native-boot-hosted-alias-20260920.json).

Correction, 20 September 2026: the old `soc_scrub.v` / `soc_busstat.v`
comments implied that a branch-based increment prevents startup X poisoning
in synthesized hardware. That inference was wrong. A procedural Verilog
branch can suppress an unknown event in RTL simulation while its mapped
logic still propagates X. Both comments now state that limit; the counter
logic is unchanged. The native full-boot evidence above verifies the loader
initialization fix, rather than relying on that RTL simulation behaviour.

### Hosted NPU-stage failure and reboot recovery (20 September evening)

The independent [hosted run 35508536540](evidence/native-boot-hosted-npu-failure-20260920.json)
passed native-cell reset, RTL boot and gate compilation, then failed the full
mapped boot: 24 application checks completed before unknown values appeared
during the NPU phase. It reached the million-cycle bound without the success
magic. The ROM and flash bytes match the distinct local passing build;
Yosys and Icarus versions differ. Root cause remains under investigation using
the exact hosted netlist and flash under local Icarus 13. The earlier local
28-check pass is retained with its original scope; hosted acceptance is open.

The host reboot interrupted the pending local physical runs. Their partial
outputs are retained and input hashes rechecked before restarting in new
`restart1` directories. Neither old RUNNING metadata nor missing final state
files is a pass. See [recovery record](evidence/reboot-recovery-20260920-evening.json)
The ongoing product requirements remain in [the acceptance record](92-product-acceptance.md).
