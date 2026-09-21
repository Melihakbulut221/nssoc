// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0

/* Register offsets for the blocks docs/40-interrupts-timers-watchdog.md
 * adds, and the machine-mode CSR bit positions the tests use.
 *
 * Slot bases come from generated soc_memmap.h. CLINT and BUSSTAT
 * offsets come from generated soc_reg_offsets.h and their YAML files
 * in regmap/peripherals. GPTIMER's generated stride and relative offsets
 * retain the parameter-dependent timer/watchdog layout below.
 *
 * The CLINT offsets are the standard RISC-V ones; the GPTIMER offsets
 * are GRLIB's (grip.pdf table 463); WDOGSTAT and the key are this
 * project's documented extension, hw/soc/rtl/soc_wdog.v W5.
 */
#ifndef SOC_TIMERS_H
#define SOC_TIMERS_H

#include "soc_memmap.h"
#include "soc_reg_offsets.h"

/* ---- CLINT, hw/soc/rtl/soc_clint.v ---------------------------------- */
#define CLINT_MSIP      (SOC_CLINT_BASE + SOC_CLINT_MSIP_OFF)
#define CLINT_MTIMECMPL (SOC_CLINT_BASE + SOC_CLINT_MTIMECMPL_OFF)
#define CLINT_MTIMECMPH (SOC_CLINT_BASE + SOC_CLINT_MTIMECMPH_OFF)
#define CLINT_MTIMEL    (SOC_CLINT_BASE + SOC_CLINT_MTIMEL_OFF)
#define CLINT_MTIMEH    (SOC_CLINT_BASE + SOC_CLINT_MTIMEH_OFF)
/* An offset the block does not implement. soc_clint.v faults it. */
#define CLINT_UNMAPPED  (SOC_CLINT_BASE + 0x0100u)

/* ---- BUSSTAT, hw/soc/rtl/soc_busstat.v ------------------------------
 *
 * The fault counters docs/44 adds, in the slot the frozen map has
 * reserved for them since docs/39. The base comes from soc_memmap.h;
 * the offsets are this project's own and are defined in
 * hw/soc/rtl/soc_busstat.v's header.
 *
 * READ THE UNITS OFF THE NAMES, because these two counters are not the
 * same quantity and one of them is the one a mission telemetry frame
 * carries:
 *
 *   BST_RFSEC   UPSETS. The register file's scrub walks x1..x31 and
 *               re-encodes what it finds, so a single-bit upset the
 *               program does not overwrite first is counted exactly
 *               once. This is the upset-rate counter.
 *   BST_RFRD    CYCLES in which a read port returned a corrected word.
 *               One upset read ten times before the scrub reaches it
 *               counts ten. It is an upper bound on the upset count.
 *               RFRD much larger than RFSEC means upsets are being read
 *               before they are scrubbed.
 *   BST_RFDED   Uncorrectable syndromes: two upsets in one register
 *               between two scrubs.
 *   BST_TMRERR  Mismatches the watchdog's voter masked, docs/41 W6.
 *
 * and three the NPU connection drives, docs/55. Read the unit off the
 * name here too, because two of them are not the same quantity:
 *
 *   BST_NPUCOR  UPSETS THE QUEUES SURVIVED. aer_fifo's pointers are
 *               triple-redundant and reload every replica from the vote
 *               on the next edge, so this counts corrected
 *               disagreements: nothing was lost. It is the connection's
 *               upset-rate counter, the way BST_RFSEC is the core's.
 *   BST_NPUDET  EVENTS THE CONNECTION LOST: a queue entry whose stored
 *               parity failed, or a read whose two rd_valid rails
 *               disagreed. Deliberately not folded into BST_NPUCOR --
 *               one counts survival and this one counts dropped work.
 *   BST_NPUTMR  Mismatches the NPU control-and-cause bank's own voter
 *               masked (soc_npu.v H3). Separate from BST_TMRERR because
 *               a watchdog vote and an NPU vote are different parts
 *               with different remedies.
 *
 * and one the CLINT drives, docs/58:
 *
 *   BST_MTECC   CYCLES in which the stored mtime codeword was not a
 *               codeword. mtime is held as the data field of a (72,64)
 *               SECDED word that is decoded, corrected and re-encoded on
 *               every tick, so this is an upset-rate counter over those
 *               72 flip-flops with a scrub period of one cycle -- but it
 *               DOES NOT SEPARATE a correction from an uncorrectable,
 *               and soc_busstat.v's header says why there is one bit
 *               left and not two. If this counter moves and the clock is
 *               also wrong, the second upset was the one that mattered;
 *               the only way to tell from software is to compare mtime
 *               against the core's own mcycle, which advances at the
 *               same rate at TICK_DIV = 1.
 */
#define BST_STATUS      (SOC_BUSSTAT_BASE + SOC_BUSSTAT_STATUS_OFF)
#define BST_IRQEN       (SOC_BUSSTAT_BASE + SOC_BUSSTAT_IRQEN_OFF)
#define BST_RFSEC       (SOC_BUSSTAT_BASE + SOC_BUSSTAT_RFSEC_OFF)
#define BST_RFRD        (SOC_BUSSTAT_BASE + SOC_BUSSTAT_RFRD_OFF)
#define BST_RFDED       (SOC_BUSSTAT_BASE + SOC_BUSSTAT_RFDED_OFF)
#define BST_TMRERR      (SOC_BUSSTAT_BASE + SOC_BUSSTAT_TMRERR_OFF)
#define BST_CLR         (SOC_BUSSTAT_BASE + SOC_BUSSTAT_CLR_OFF)
#define BST_NPUCOR      (SOC_BUSSTAT_BASE + SOC_BUSSTAT_NPUCOR_OFF)
#define BST_NPUDET      (SOC_BUSSTAT_BASE + SOC_BUSSTAT_NPUDET_OFF)
#define BST_NPUTMR      (SOC_BUSSTAT_BASE + SOC_BUSSTAT_NPUTMR_OFF)
#define BST_MTECC       (SOC_BUSSTAT_BASE + SOC_BUSSTAT_MTECC_OFF)
#define BST_APBTO       (SOC_BUSSTAT_BASE + SOC_BUSSTAT_APBTO_OFF)

/* One bit index per source, shared by STATUS, IRQEN and CLR. */
#define BST_S_RFSEC     (1u << 0)
#define BST_S_RFRD      (1u << 1)
#define BST_S_RFDED     (1u << 2)
#define BST_S_TMRERR    (1u << 3)
#define BST_S_NPUCOR    (1u << 4)
#define BST_S_NPUDET    (1u << 5)
#define BST_S_NPUTMR    (1u << 6)
#define BST_S_MTECC     (1u << 7)
#define BST_S_APBTO     (1u << 9)
#define BST_S_ALL       (BST_S_RFSEC | BST_S_RFRD | BST_S_RFDED \
                         | BST_S_TMRERR | BST_S_NPUCOR | BST_S_NPUDET \
                         | BST_S_NPUTMR | BST_S_MTECC | BST_S_APBTO)
/* STATUS bit 8: any enabled sticky is set, i.e. the line is asserted.
 * Bit 7 is now BST_S_MTECC and the sticky field is full: a ninth source
 * cannot be added below the interrupt bit. docs/58 section 9.
 * 2026-09-19: APB timeout therefore uses bit 9, preserving bit 8. */
#define BST_STATUS_IRQ  (1u << 8)

/* ---- GPTIMER, hw/soc/rtl/soc_gptimer.v ------------------------------ */
#define GPT_SCALER      (SOC_TIMER0_BASE + SOC_GPTIMER_SCALER_OFF)
#define GPT_SCRELOAD    (SOC_TIMER0_BASE + SOC_GPTIMER_SCRELOAD_OFF)
#define GPT_CONFIG      (SOC_TIMER0_BASE + SOC_GPTIMER_CONFIG_OFF)
#define GPT_TIMER(n)    (SOC_TIMER0_BASE + SOC_GPTIMER_TIMER_STRIDE * (n))
#define GPT_CNT(n)      (GPT_TIMER(n) + SOC_GPTIMER_TIMER_CNT_OFF)
#define GPT_RLD(n)      (GPT_TIMER(n) + SOC_GPTIMER_TIMER_RLD_OFF)
#define GPT_CTRL(n)     (GPT_TIMER(n) + SOC_GPTIMER_TIMER_CTRL_OFF)

/* GRLIB timer control bits, grip.pdf table 463. */
#define GPT_EN  (1u << 0)
#define GPT_RS  (1u << 1)
#define GPT_LD  (1u << 2)
#define GPT_IE  (1u << 3)
#define GPT_IP  (1u << 4)
#define GPT_CH  (1u << 5)

/* Two general timers plus the watchdog: NGEN = 2 in soc_top.v, so the
 * watchdog is timer 3 and WDOGSTAT sits one slot past it. */
#define GPT_NGEN      2
#define WDOG_TIMER    (GPT_NGEN + 1)
#define WDOG_CNT      GPT_CNT(WDOG_TIMER)
#define WDOG_RLD      GPT_RLD(WDOG_TIMER)
#define WDOG_CTRL     GPT_CTRL(WDOG_TIMER)
#define WDOG_STAT     (SOC_TIMER0_BASE + SOC_GPTIMER_TIMER_STRIDE * (WDOG_TIMER + 1))
/* WDOGWIN, soc_wdog.v W7 and W8. It sits at the watchdog's own +0xC,
 * which is a general timer's LATCH register in GRLIB (grip.pdf table
 * 463) and which this block has never decoded for the watchdog. */
#define WDOG_WIN      (GPT_TIMER(WDOG_TIMER) + SOC_GPTIMER_TIMER_LATCH_OFF)

/* Every write to a watchdog register carries this in bits 31:16 or has
 * no effect at all (soc_wdog.v W5). */
#define WDOG_KEY      0xA51Fu
#define WDOG_W(v)     ((WDOG_KEY << 16) | ((v) & 0xFFFFu))

/* WDOGSTAT read fields. */
#define WDOG_ST_NMI       (1u << 0)
#define WDOG_ST_WDOGRST   (1u << 1)
#define WDOG_ST_ESCALATED (1u << 2)
#define WDOG_ST_DISABLED  (1u << 3)
#define WDOG_ST_TMRERR    (1u << 4)
#define WDOG_ST_EARLY     (1u << 5)   /* W7: a kick arrived too early */
#define WDOG_ST_BUDGET    (1u << 6)   /* W8: a phase ran out of kicks */
#define WDOG_ST_RSTCNT(v) (((v) >> 8) & 0xFFu)

/* WDOGWIN fields, soc_wdog.v W7 and W8.
 *
 * WINS is the number of halvings: the window is open for the last
 * 2^-WINS of the period, so the shortest interval between two kicks the
 * block will accept is T * (1 - 2^-WINS). WINS = 0, the reset default
 * and the value a stage-2 reset restores, opens the window for the
 * whole period and is exactly the watchdog docs/40 and docs/42
 * describe.
 *
 * A program choosing WINS is declaring a bound on the JITTER of its own
 * kick cadence: with i_min and i_max the shortest and longest interval
 * it can produce, WINS is usable only if i_max / i_min < 1/(1 - 2^-WINS)
 * -- 2:1 at WINS = 1, 4:3 at WINS = 2, 8:7 at WINS = 3. That is a
 * property of the software and it has to be measured, not assumed.
 *
 * BUDEN loads KICKS into the kick budget and arms it. Every accepted
 * kick spends one; a kick with none left is a violation. It is disarmed
 * by every stage-2 reset. */
#define WDOG_WIN_WINS(s)   ((s) & 0xFu)
#define WDOG_WIN_BUDEN     (1u << 7)
#define WDOG_WIN_KICKS(n)  (((n) & 0xFFu) << 8)
#define WDOG_WIN_BUDARM    (1u << 4)      /* read-back */
#define WDOG_WIN_LEFT(v)   (((v) >> 8) & 0xFFu)

/* ---- machine CSR bits ----------------------------------------------- */
#define MSTATUS_MIE (1u << 3)
#define MIE_MSIE    (1u << SOC_IRQID_MSOFT)
#define MIE_MTIE    (1u << SOC_IRQID_MTIMER)
#define MIE_FAST(l) (1u << (SOC_FAST_IRQ_BASE + (l)))

#endif /* SOC_TIMERS_H */
