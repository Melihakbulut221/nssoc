# Read-only same-process observer design

This source-only prerequisite addresses a missing observation in rejected mainchip run40095811631 at4d85722e05fbda8440c6577d7d7baa18a642485b. Its original continuation checked container Running and native-log growth, then rejected no additional native log bytes after7200seconds. Neither that log condition nor CPU accounting from the failed process proves that routing advanced. The original controller, constraints, failure and saved artifact12564886005 are unchanged. Artifact recovery40110502492/ac1740af remains the sole cloud restoration of evidence; this observer does not restore it or start a controller.

scripts/mainchip_proc_observer.py only reads /proc, hashes the opened executable, timestamps observations and prints evidence. It runs only on Linux with GITHUB_ACTIONS=true. It has no ptrace, process signals, namespace changes, writes to target/proc, process creation, restore, Docker or routing command. A future separately reviewed diagnostic must bind its supplied PID to the actual native process and qualified executable/source; this standalone observer does not discover or authorize the target.

The observer holds /proc and the numeric process-directory file descriptor for its entire session. Every process and thread file is opened relative to those descriptors. A thread directory is held across its before/after reads. The kernel documents that an already open /proc/PID descriptor does not follow a newly reused PID. If the process dies, required reads fail and the observation is rejected. Bracketing records also check boot UUID, numeric PID/TID, starttime ticks, directory identity, executable path/inode/size/timestamps/SHA256 and namespace visibility. Across samples, the held process descriptor, boot/starttime/executable identity and monotonic ordering must remain stable. A caller may additionally require an exact previously captured identity through snapshot(expected_identity=...).

Each successful snapshot retains all raw stat/status/statm/io/wchan and boot-ID bytes with exact length, SHA256 and base64; directory and thread-list syscall results are retained as hashed JSON. Executable bytes are streamed only into SHA256, not copied as an artifact. Errors preserve errno and availability without inventing zero counters. An explicit read-order list binds every captured record; JSON object key ordering is not relied upon. Every read and executable-hash interval has monotonic start/end timestamps. Failed snapshots preserve completed raw reads and the actual error, then the standalone command stops. There is no silent retry or selected successful sample.

The stat parser locates the final closing parenthesis before the numeric tail, so spaces, internal parentheses and newlines in comm cannot shift fields. It records process and per-thread user/system ticks, state, wait channel, IO and available memory/status fields. SC_CLK_TCK and page size are explicit. Guest ticks are already part of user ticks and are not added again; waited-child CPU is reported separately, not counted as the process's own CPU. Thread and process counters are not forced to sum across different read times.

Thread membership must agree at both ends of one snapshot, the captured thread count must agree with process stat, and each observed TID must retain its identity and nondecreasing CPU counters. Detected membership/identity/CPU/IO inconsistency rejects the snapshot. Between snapshots, created/exited thread sets are recorded and surviving identities are checked. This is conservative: a rejection identifies unavailable or inconsistent evidence, not necessarily a proven PID-reuse incident.

## Explicit limits

These observations are not atomic and cannot prove the absence of a transient exec or thread creation/deletion between bracket reads. The target is never frozen. IO counters may be non-atomic and contain waited-child accounting; available decreasing readings are preserved as a rejected inconsistency. RSS/statm/status memory can be approximate. A zero wait channel can reflect running, configuration or restricted visibility. Missing optional values remain unknown. Hashing an executable and reading many threads adds observer overhead, which is included in measured sample intervals.

CPU movement, sleeping/waiting state, new IO bytes and continued process existence are diagnostic evidence only. route_progress_accepted, continuation_accepted, process_liveness_accepted and routing_complete always remain false. No threshold decides that the router is making useful progress; original log/progress/timing/DRC/LVS gates remain untouched.

## Cloud controls and activation

The unregistered template docs/workflow-templates/mainchip-proc-observer-controls.yml has only workflow_dispatch and a native-self-controls job. It cannot activate from its present docs location. Review must precede any cloud dispatch, and registration must use the existing isolated no-op mechanism rather than activating inherited generic CI.

The future controls collect three actual hosted Python self-process snapshots while one known worker thread remains present, compare the opened /proc/self/exe hash independently, and exercise real CPU counter movement. They preserve the complete samples even on a later failure. Thirty-eight corruptions target actual raw/hash/identity/CPU/membership/executable/clock evidence, within-snapshot and cross-snapshot PID/TID reuse, and malformed stat fields. Six positive comm fixtures include parentheses and a newline. Permission-denied optional IO/wchan remains unknown in a positive fixture. Source controls reject target-writing APIs and require all six file opens to be read-only. These are observer controls only; no route, simulator, restore or electrical validation runs.

At publication this is unexecuted source: neither the real self-process control nor future native routing diagnosis has passed yet.

## Primary references

- [Linux kernel /proc documentation](https://docs.kernel.org/filesystems/proc.html): held PID descriptors, task files, wait-channel and approximate memory accounting.
- [Linux man-pages proc_pid_stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html): field positions, starttime/CPU units and guest-time accounting.
- [Linux man-pages proc_pid_io](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html): IO semantics, permissions and non-atomic counters.
- [Linux man-pages proc_pid_task](https://man7.org/linux/man-pages/man5/proc_pid_task.5.html): per-thread directories and leader-exit availability.

These references were read on2026-10-24. This design paraphrases only the relevant API behavior; the original failed process's actual CPU/thread state remains unknown until authenticated native evidence exists.
