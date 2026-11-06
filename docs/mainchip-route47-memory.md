# Route47 bounded cloud memory policy

Run41393730481 stopped during iteration20 after7021.574seconds: RSS11218012KiB exceeded10GiB; hostMemAvailable4000064KiB remained above2GiB. Container12GiB memory.peak reached its limit (including file cache);6179max events, zeroOOM/oom_kill. Last completed iteration19 had92internal markers; iteration20 partial90is not final independentDRC.

New policy permits11GiB process-group RSS inside the SAME12GiB/no-swap container, leaving1GiB for non-RSS usage. Host minimum2GiB, all time/output/PID/CPU restrictions and exact ownership/exit checks remain. A growing workload can still be rejected; this is no guarantee of fitting all64iterations.

The original supervisor source is untouched. The returned isolated module has only its declared RSS constant and supervised keyword default updated. Both bindings are checked. Command evidence checker is derived from authenticated14874byte source SHA059e3e4edde4a63997cc841728f02d5b6a2aaf77335cb7d1b8dba70ed7d2e321 with one reversible resource constant substitution; every function body is AST-identical. Native and evidence bounds must agree. The original checker remains pinned and unchanged.

19hosted controls cover exact policy, altered caps/reserve/types, altered source, boundaryRSS/available, failed/signalled children, oldpolicyrecords, livechildren, memoryfailure, missingcounter and actual isolated keyword-default binding. Original route/source/control suites remain unchanged.

Same actual47-net seed, original64iterations/seed42/2threads, all1691clocks, untouched nonselected wire identities, reversible FIXED protection, snapshot preservation, final fullDRC/antenna and original class/PG/LVS/STA obligations remain. No electrical, DRC, LVS or timing threshold is loosened. All native output stays in GitHub; no local CAD work.

A separate same-source controls-only run must PASS before production dispatch. Failed41393730481 and rejectedVia141412504017 remain preserved in root checkpointv290. This resource revision is not route/PHY/timing acceptance.

## Snapshot window retry (after run 41699812301)

Run41699812301 reached detailed-route iteration63 (5 violations after iteration62) and was stopped at11754.29 seconds by a single memory snapshot that overran its own100ms wall-clock window: `CounterError('Total memory snapshot bounded window exhausted')`. The last successful sample was RSS7018548KiB and host MemAvailable8176584KiB; no RSS or available-memory bound was crossed. Over the route the container cgroup sat at its12GiB memory.max with7690 max events and zero OOM/oom_kill, because each iteration wrote a214MB snapshot ODB into page cache, and52202 of127243 CPU periods were throttled. Direct reclaim or CPU throttling inside that cgroup can stall the sampler past100ms without any memory bound being violated.

The supervisor now retakes only that exact overrun, as a complete fresh snapshot with the original100ms window and every original counter, identity and bound check, at most5 windows per sample and256 retries per supervisor. Each retry is a `memory_window_retry` event. Every other counter error (unreadable, malformed, missing VmRSS, identity change) still fails on first sight, and no stale or partial value is ever substituted. The12GiB/no-swap cgroup and the terminal OOM-counter check remain the hard memory backstop.

The two exact route programs `bulk-postdrt-antenna/narrow47-route-original.tcl` and `narrow47-route-actual.tcl`, already published in the native capsule, are added to the exact preservation list; other unexpected outputs are still refused.

25hosted controls now include the real exit-checked supervisor and sampler: one overrun retaken fresh, persistent overrun refused, unreadable and malformed counters refused without retry, spent retry budget refused, and a second adapter refused.

## Original snapshot-free route program

The original route program keeps `DRT_SAVE_SNAPSHOTS=0` and guards it. The route47 seed had inserted `set_debug_level DRT snapshot 1` and `detailed_route_debug -snapshot_dir`, so run41699812301 wrote 63 per-iteration ODBs of 214MB each (13.5GB of the 20.4GB capsule). Those writes held the cgroup at memory.max, and their compression and publication took most of the 83 minutes between the route stop and artifact upload. A completed route plus restore, audit, full DRC/antenna and the same publication would run past the 360-minute job limit.

The route program is now the original program with only its `read_db` input rebound (`route_program()` in `mainchip_route47_contract.py`). It refuses a second input or router call, a missing route stage, an enabled snapshot setting, and an input binding that already appears. The iteration-62 checkpoint (5 violations) from run41699812301 stays in release433106055 as the restart point if this route does not return. Seven more hosted controls cover this (27 in total).

## Run 41772302484 result: route completed, DRC not closed

Run41772302484 at e64115d completed every phase (`COMPLETE_GUIDE_ENGINE_ACTUAL_FULL64_ROUTE_OBSERVATION`, host success). The snapshot-free original program routed all 64 iterations in 8582 s (previously stopped at iteration 63 after 11754 s). No snapshot-window retry was needed. The router's last iterations report 5 violations. The full native check after class restoration finds 263 DRC markers (234 Short, 12 Cut Short, 17 Metal Spacing) and 27 antenna violations on 21 nets. Every one of the 263 markers involves at least one of the 47 rerouted nets; 96 nets appear in total.

Hosted run41792601886 ran the same engine's `drt::check_drc` on three databases from release433507733:

| Database | FIXED nets | ROUTED nets | Markers |
|---|---:|---:|---:|
| narrow47-cleared (router input, 47 wires removed) | 143659 | 161 | 0 |
| routed-fixed (router output, temporary FIXED overlay) | 143659 | 161 | 263 |
| narrow47-restored (original classes) | 142878 | 942 | 263 |

Class restoration does not change the result; the router itself created all 263 markers while reporting 5.

Correction from run41794550552 (same engine, same seed, the 47-net-cleared database with every original class restored): the original classes are themselves FIXED for 142878 nets, so the overlay is not what hides neighbours. With original classes the router reports 2024, 762, 697, 381 and 308 violations in iterations 0-4, identical to run41772302484, and `check_drc` on that 4-iteration output finds exactly 308 (229 Short, 79 Metal Spacing). Only the 47 selected nets change wires. The in-loop count therefore matches the global check in the standard iterations. The divergence appears later: run41772302484 reported 92 after iteration 19 and 5 at the end of the bounded "guides tiles" and "stubborn tiles" iterations, while the global check of the final database finds 263. The in-loop count of those bounded iterations is not a global DRC measurement, and the full check is the only acceptance measure. Run41797891492 repeated the same database for 21 iterations (0-20). The in-loop sequence matches run41772302484 exactly (..., 111, 220, 142, 92, 84), and `check_drc` on that output finds 84 markers (63 Short, 21 Metal Spacing), equal to the in-loop 84. The 47 selected nets are the only changed wires. This is the best measured state so far: the iteration-19 candidate 41440285882 has 92. Continuing through iterations 21-63 lowers the in-loop count from 84 to 5 but raises the global result to 263.

The guide engine's patch (`mainchip_guide_worker_batch_patch.py` at 6cae8ce) splits each guides-tiles worker box into bounded pieces with a one-GCell overlap and processes them one at a time. Each piece selects its best result and counts markers only inside its own box, so rerouting a piece can create conflicts just outside it that neither that piece nor the iteration total records. That fits the measured divergence, which begins exactly at the bounded tile iterations. Until the partition keeps global marker accounting, only iterations up to 20 of this engine give a usable result, and every result must be judged by full `check_drc`. The unbounded FIXED-guard engine (2a343c7491353a60e7b06aa134d4b67e3ef2e846a8341164dacffe88f5f7ec2f), with no container cap on the 16 GB hosted runner, did not finish within the six-hour job limit at two threads (run41810674289, no data). At four threads (run41861445532, progress streamed to the job log) it reached iteration 34. Iterations 0-19 match the guide engine (92 after iteration 19). Its unbounded tile iterations then report 82, 79, 79, 79, 77, 183 (optimization), 76, 65, 63, 63, 63, 59, 59 and 142 (optimization, iteration 33). Peak memory is 13.16 GB, above the 12 GiB container used by the native wrapper; that is why the bounded patch was introduced. Iterations 20-24 take 19-45 minutes each, so all 64 iterations need about seven hours on this runner. These counts come from unbounded workers but have not been confirmed by `check_drc`.

Three ways to close the route, each judged only by full `check_drc`: (1) fix the bounded partition so each piece's best-result selection and marker count include its whole guide tile, then rerun within 12 GiB; (2) split the unbounded run across jobs with a supported DRT checkpoint, without the self-imposed cap; (3) use a larger runner.

## Chained continuation with the original late-iteration schedule

The pinned engines have no start-iteration option. Run41990813751 showed that restarting `detailed_route` on drt_iter20.odb (release433106055, global 84) keeps the routes (check_drc 84 before and after) but restarts the schedule at iteration 0. Under FIXED nets, those rows turn ALL into INCR and repaired nothing. The continuation (`analysis/drt-resume`) therefore uses `detailed_route -single_step_dr` and replays the engine's own `strategy()` rows (shapeCost 8, markerCost 32, from OpenROAD dcf36133 FlexDR.cpp) with `drt::step_dr`. One INCR step first evaluates the markers; then rows 20 onward run, with a +6 clip-size increase on non-ALL rows, ALL rows mapped to INCR as `main()` does under FIXED nets, and a time budget. Finally `step_end` and `write_db`.

Run42001907194 (unbounded FIXED-guard engine, four threads) from drt_iter20 replayed rows 20-43 in 16096 s. The in-loop count went 84, 82, 82, 66, ..., 53, 50, 49, 46, 45, 44, and full `check_drc` on the written database is **44** (36 Short, 8 Metal Spacing), down from 84. The routed database is artifact 13423006669. Run42043211157 continues from it with rows 44-64 and a second pass over rows 50-64.

Run42043211157 continued from that database with rows 44-64 and a second pass, within the 15000 s budget. Full `check_drc` went from 44 to **42** (33 Short, 9 Metal Spacing). Rows 46-59 left the in-loop count at 42.

Most of the 42 remaining markers are between two nets whose wires keep the original route's FIXED type. OpenROAD dcf36133 `io.cpp` marks a net fixed when its first wire path is FIXED (`netIn->setFixed(true)`), and `updateDbConn` skips fixed nets, so no rip-up mode can move either net. The 42 markers name 63 nets: 58 signal nets, four clock nets (`clknet_*`) and VPWR. Six markers involve a clock net and one involves VPWR; the rest are signal-to-signal.

`unfix_nets.py` (branch `analysis/drt-resume`) re-encodes only the 58 signal nets from FIXED to ROUTED with identical geometry. It decodes every op, re-encodes with the ROUTED type, then compares the raw op streams; only path wire-type bits may differ, and clock, power and special nets are refused. The router can then rip those nets up at their markers. Run42089497499 applies this to the run42043211157 database and replays rows 20-64.

Run42091664267 re-encoded 30 of the 58 named signal nets from FIXED to ROUTED; the other 28 were already ROUTED. The geometry check compares decoded segments, vias, extensions, patch rectangles, terminals and length. The run then replayed rows 20-64 within the 15000 s budget. Full `check_drc` went from 42 to **14** (13 Short, 1 Metal Spacing; routed database artifact 13467202439). The in-loop count fell 42, 29, 28, 26, 25, 20, 17, 15, 14.

Of the 14 remaining markers, seven pair a clock net (`clknet_*`) with a signal net. Clock wires stay FIXED because the post-route handoff compares protected clock geometry with the baseline. Run42140204970 repeats the step with the 17 signal nets of the 14 markers.

Three OpenROAD Python binding limits shape `unfix_nets.py`:

- `getWireType` returns a string.
- `getRect`, `getBBox` and `dbWireShapeItr` are not usable from Python; rectangles are read from the raw `kRect`/`kOperand` ops.
- `addPoint(x, y, 0)` selects the extension overload, so plain points are written with two arguments.

Run42140204970 is the second round: 4 of the 17 named nets were still FIXED, followed by rows 20-64 and a second pass. Full `check_drc` went from 14 to **9** (all Short; artifact 13481445511). Seven of the nine are between a FIXED clock net and a signal net, on the signal net's Metal2 pin access or a Metal5 crossing:

- `clknet_leaf_9_clk_i_regs`
- `clknet_leaf_283_clk_i_regs`
- `clknet_leaf_219_pcie_clk_i`
- `clknet_5_29__leaf_u_ibex.clk`

The router cannot move the clock wire, and the signal pin has no other access. Run42171492719 also re-encodes those four clock nets, named explicitly through `NSSOC_UNFIX_CLOCKS`; power and special nets stay refused. This changes routed clock geometry on four leaf nets, so the post-route handoff's protected-clock comparison will report them. That difference is recorded with the result rather than hidden.

Run42171492719 is the third round. It re-encoded five nets: the four listed clock nets plus `$abc$1804206$new_n95183`. Each passed the geometry check with identical op counts, so the clock geometry is unchanged at the start of routing; the other seven named nets were already ROUTED. Rows 20-64 and the second pass followed. Full `check_drc` went from 9 to **1** (artifact 13486051106).

The one remaining Short is on Metal2 at (834.14, 1680.53) between `u_ibex...g_rf_flops[5].rf_reg_q[28]` and `net5933`, both ROUTED. Runs42182433951 (clip +12) and42182453319 (clip +2) replay rows 20-64 with other worker window sizes. Run42182501302 runs jumper-only antenna repair (`repair_antennas -jumper_only`, then a five-iteration incremental `detailed_route`) on the same database.

The DRT chain from the iteration-20 snapshot now stands at 84, 44, 42, 14, 9, 1.

## Antenna repair and full-chip DRC 0

Before repair the 1-marker database had 22 antenna nets and 24 pins, plus 112 one-terminal stub nets without wires and no unrouted multi-terminal nets (run42183767899). OpenROAD's `repair_antennas` needed three workarounds on this database (branch `analysis/drt-resume`, `antenna` mode):

- **Fixed net-level wire type.** The antenna wire builder treats a net whose net-level wire type is FIXED as unrouted, tries to rebuild its existing wire and fails (ANT-0016). This affects both jumper-only and diode-only repair. During repair only, every such net is marked ROUTED, then restored to FIXED before `write_db`.
- **Diode name collisions.** New diodes are named `ANTENNA_0..n` in each session, which collides with the 9143 `ANTENNA_*` diodes already present, so `dbInst::create` returns NULL and `setDiodeLoc` crashes. Existing names are parked, and the new diodes are renumbered above the highest index (9145) before the old names are restored.
- **Fixed violating nets.** The 22 violating nets are re-encoded FIXED to ROUTED first, so the router can connect their new diodes.

Run42185170771 inserted 44 diodes and ran a five-iteration incremental route. Antenna went from 22 nets to 5. Full `check_drc` rose to 46 (34 Short, 12 Metal Spacing) around the new diodes.

Run42189463974 re-encoded the 35 signal nets of those 46 markers and replayed rows 20-64. The in-loop count reached 0 at row 60, and **full `check_drc` on the written database is 0** (artifact 13493489102).

The DRT chain from the iteration-20 snapshot: 84, 44, 42, 14, 9, 1, then antenna repair (46), then **0**.

Run42200345446 re-checks antenna and unrouted nets on this database. Run42200403392 runs fresh RC and three-corner STA. The single Short left on the pre-antenna database was not resolved by clip +2 or +12 replays (runs42182453319, 42182433951); it is gone in the post-antenna route.
