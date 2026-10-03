# 94 — External level interrupt and preserved interrupt context

2026-09-20. The product checklist called out the missing external interrupt
input separately from the missing debug module. `soc_top` now exposes one
active-high `irq_external_i`. Two synchronizer stages on the **ungated**
`clk_i`, reset by `rst_sys_n`, drive Ibex's machine-external interrupt input.
This implements a single level input. It does not instantiate a PLIC or
consume a fast peripheral interrupt line; the reserved PLIC address range
still faults. Debug/JTAG remains separate unfinished work.

## Input and software contract

The external device must hold its request high until serviced. Software can
mask it with `mie.MEIE`; it becomes pending in `mip.MEIP`, and an enabled
interrupt uses machine cause 11 (`mcause=0x8000000b`). The vector table now
has a matching vector-11 stub. The common handler masks the source before
returning; device-specific software must service/clear the external source
before unmasking it. This is a level handshake, not an edge-capture register.

In the digital model, assertion/deassertion crosses two sampling edges.
A short pulse can be missed. System/watchdog reset clears the synchronizer;
a request held high is sampled again after reset. These two flops provide
CDC synchronization, **not SEU protection**. Silicon metastability MTBF,
physical placement, I/O cells, ESD and board electrical characteristics are
not established by simulation.

The explicit future physical profile is
[`soc_interfaces_external_irq.sdc`](../hw/soc/sta/soc_interfaces_external_irq.sdc).
It retains the existing interface constraints and excepts paths starting at
the asynchronous input port. The first synchronizer's Q-to-second-stage D
path remains timed. It rejects a design without this port. Earlier physical
runs retain their original SDC and source inventory: **ECO18 and ECO22 do
not contain this newly added input**, and their physical results cannot be
used to sign off the new RTL.

## A real software defect found while adding the input

**Corrected 2026-09-20:** the old normal interrupt stub loaded a vector marker
into `t0` before saving the interrupted value. The common handler saved only
`t1`–`t3`, so `t0` was lost on every normal interrupt. The old comment's
"two instructions and no stack" description hid this missing preservation.
Each normal stub now allocates the existing 32-byte frame and saves `t0`
before loading its marker. The common handler restores it before `mret`.
The minimal-platform NMI fallback follows the same entry contract; the SoC's
watchdog NMI and synchronous exception handlers already saved `t0`.

An isolated real-CPU negative control retains the old stub with the new
external input. It finishes with signature `e1700002`, but software reports
`mask=exit=0x100`: the explicit `t0=0x13579bdf` check across an interrupting
WFI fails. The corrected run reports mask/exit zero with the same signature,
four external assertions, two observed sleep/wake episodes and three
completed test phases. Both run with protected memory/register file and
clock gating; no injected upset is involved. The initial prototype measured
5,126 versus 5,138 cycles. These are measured prototype results, not a timing
or radiation qualification. The delivered-source measurements below now
reproduce both outcomes.

## Reproduction

The reusable probe uses the normal boot, ECC memory, CPU and observation
infrastructure, with a board-side source driven in response to visible GPIO
and sleep outputs. It checks masked pending requests, cause and vector,
source masking, register preservation, level release, and WFI wake with
global interrupts enabled and disabled.

```sh
python3 hw/soc/flow/external_irq_probe.py --prepare hw/soc/out/external-irq
bash hw/soc/out/external-irq/run_rtl.sh
# Optional native-cell simulation; the supplied netlist must have the new port:
bash hw/soc/out/external-irq/run_gl.sh /absolute/path/to/soc_top.netlist.v
```

The negative control changes only a generated CRT copy. A successful control
is labelled `EXPECTED t0 FAILURE`, never product PASS:

```sh
python3 hw/soc/flow/external_irq_probe.py \
  --prepare hw/soc/out/external-irq-negative --legacy-t0
bash hw/soc/out/external-irq-negative/run_rtl.sh
```

The CI workflow runs both RTL cases and retains their logs. The
[delivered-source evidence](evidence/external-irq-20260920.json) records
RTL and native-cell gate simulation: both finish in **5,138 cycles**, with
21 matching functional fields and zero software failure mask. The isolated
legacy-stub control finishes in **5,126 cycles** with exactly the expected
`0x100` failure. Gate simulation uses no SDF; unavailable internal gate-level
observations remain `-1`, rather than being reported as zero errors.

The same record carries commands, source hashes and matched synthesis cost:

| Whole-SoC measurement | Before external IRQ | With external IRQ | Difference |
|---|---:|---:|---:|
| Cells | 65,562 | 65,731 | +169 |
| Flip-flops | 9,352 | 9,354 | +2 |
| Standard-cell area, µm² | 1,046,590.2972 | 1,046,193.2838 | -397.0134 |

Both builds retain 24 SRAM macros, whose physical area is excluded from
that standard-cell total. Whole-design ABC remapping explains why cell
count grows while mapped area slightly falls; this is not a negative
standalone cost for the IRQ circuit. Both use the same legacy `abc -D 20`
recipe, meaning 20 ps, and this measurement makes no timing-closure claim.

OpenSTA also verifies the new SDC's scope on the actual split-net netlist:
the asynchronous pin is excepted for setup/hold, the two synchronizer
stages remain timed for both, and a netlist without the input is rejected.
The typical, ideal-clock, preplacement stage-to-stage results are
**+19.443762 ns setup / -0.033690 ns hold**. The hold failure is retained;
scope validation is not timing closure. The record preserves two corrected
diagnostic attempts, including stale cell identifiers after netlist renaming.
The broader firmware regression also passes: **28 self-checks**, zero
failure mask, **642,152 cycles**, real QSPI boot from randomized data/ECC
RAM startup and one expected watchdog NMI. Its command and log hash are in
the same record. Placement/routing of this new RTL remains separate work;
ECO18/ECO22 still measure the earlier design.

<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
