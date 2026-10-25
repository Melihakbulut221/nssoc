# Bounded mainchip user-stack proposal — 2026-10-25

This is a source-only proposal. No workflow is added, no process is attached, and no native execution is authorized. The exact 20-sample contract and required controls are in scripts/mainchip-userstack-proposal.json and scripts/mainchip-userstack-proposal-controls.json.

The saved-IP result from run40169634355 identifies one main-thread location in drt::FlexGridGraph::getRouteShapeCostAdj (ELF file offset25397912) and three worker locations in libc futex wait. It does not establish a caller stack, loop, deadlock or the cause of absent route-log progress. The original rejection remains mandatory.

## Exact continuation seam

Use saved process40120760532, source84b513cb437b68af0f4cb22bc4707db1a35958cf and its complete authenticated checkpoint. The original route controller remains SHA25608b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee.

The existing observed-diagnostic adapter surrounds same-process restore with immutable input checks and checkpoint with observer completion. It proves the exact original assertion site before accepting diagnostic evidence. Reuse these contracts with independently reviewed reversible deltas and all original controls.

There is a concrete admission gap: mainchip_rejected_capsule_admission.py still binds older failed40095811631. Changing only the observer cannot admit later40120760532. A separate adapter must bind its exact summary, both parts, complete archive, all23 images, native-log prefix and inner-controller result. Preserve archive/member and single-entrypoint checks; no cold route.

## Observation boundary

Perform20 distinct attach/read/detach cycles, five seconds apart while detached. Bound each attachment to ten seconds plus five seconds debugger cleanup. Limit each thread to16 frames and require all actual threads up to64. The480-second observer deadline leaves margin inside the existing600-second diagnostic window for final input checks/checkpoint. Measure stop durations and report truncation/unwind errors.

Start host GDB with initialization and automatic loading disabled before loading the target, and disable debuginfod. GNU documents the early auto-load option and separate initialization-file control. [Auto-loading](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Auto_002dloading.html) [Debuginfod](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Debuginfod-Settings.html)

Resolve the executable through /proc/PID/exe and libraries through /proc/PID/root with exact runtime hashes. Existing ProcObserver pins a proc directory, not a pidfd. A new pidfd may detect exit, but numeric GDB attach still requires in-stop identity validation before accepting frames, then after detach. Compare host LWP IDs to the actual stopped task census, not four assumed container TIDs.

Disable memory/register writes, breakpoints, tracepoints, fast tracepoints and inferior calls. Do not use set observer on as a shortcut: it also changes interrupt/non-stop settings. Exact runtime compatibility must pass real hosted fixtures without relaxing permissions. [GDB permissions](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Observer-Mode.html)

Attachment stops the target and detachment resumes it. Report scheduling perturbation even when no native memory/register write was allowed. Do not inherit the proc-only observer's unqualified target_modified=false. [Attach/detach](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Attach.html)

## Cleanup and evidence

Trusted GDB code always attempts detach in finally. On timeout/error, supervise only the debugger group, including descendants after leader exit. Independently verify target identity, no retained tracer and no tracing stop. Unproved detach is a hard failure; no target SIGCONT/kill may manufacture successful cleanup or progress.

Preserve each sample, raw output/error, module/offset binding, before/during/after identity, thread census and cleanup. A16-frame prefix is not a complete stack. Missing symbols/unwind limits remain explicit. GDB build/command support, no-auto-load behavior, root resolution and all-thread census are unproved prerequisites.

The24 controls are a required plan, not passed tests. Implement and run them on a harmless hosted multithreaded fixture first. After independent source review and actual controls, root may authorize one OpenROAD observation. Repeated frames can motivate a later software diagnosis, but cannot replace route-progress or timing gates.
