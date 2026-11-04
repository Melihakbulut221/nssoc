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

Class restoration does not change the result; the router itself created all 263 markers while reporting 5. Its in-loop count covers only the 161 ROUTED nets (47 selected plus 114 wireless). The routed wires of the 143659 temporarily FIXED regular nets did not act as conflicts for the router. Routing a subset under a temporary FIXED overlay therefore cannot close DRC with this engine, and its in-loop violation count is not a DRC measurement. The next routing attempt has to keep the neighbouring signal wires visible to the router (all signal nets ROUTED, with a protection mechanism the router honours for clocks), and must be judged by full `check_drc` on its output.
