# CI suite observability proposal (source only)

This isolated proposal follows the authenticated six-hour cancellation of
[run 41222990617](https://github.com/Melihakbulut221/nssoc/actions/runs/41222990617).
The exact checks job reached the full pytest suite at 17:14:13 UTC, then
reported the six-hour job limit at 23:07:55 UTC. Tool installation had
finished. Cleanup showed Python, make and vvp descendants, but the exact
active test is unknown: ci_local.sh captured all child output in a shell
variable until that command returned. The complete log is preserved in

docs/evidence/general-ci-timeout-terminal-41222990617/.

The current root driver/workflow at 006a5f611b2b08500fbdb667c07d60b1734491c9
are byte-identical to that failed producer. The actual installed pytest was
9.2.0; neither pytest configuration nor the preserved dependencies enable
a global pytest-timeout plugin. Existing cocotb 300/900/3600-second limits
are unchanged by this proposal.

## Exact scope

- All existing gate commands, suite test selection, pytest capture semantics,
  counters and simulator limits remain unchanged. run() streams each gate's
  full stdout/stderr to the console and an exclusively created log instead
  of retaining a shell variable and showing only its last twelve lines.
- Only the existing whole-suite command receives the diagnostic plugin and
  pytest's ordinary JUnit output option. No test timeout, skip, retry,
  collection modifier or report-outcome hook is installed.
- The plugin fsyncs collection/test-start/report/finish events. A parent-side
  reader prints test identity outside pytest's output capture. The journal
  retains exact report text; its XML projection escapes XML-invalid control
  characters. Partial JUnit labels unexecuted/unfinished tests as incomplete
  errors, never passing/skipped tests. This report is explicitly diagnostic;
  pytest's standard JUnit and actual exit code remain separate.
- An initial checks step records a monotonic origin before checkout and tools.
  The workflow's 360-minute limit remains. The supervisor reserves 180 seconds
  within those 21,600 seconds for descendant cleanup/report upload. Time
  before the first user step is unknown and consumes that margin; the origin
  is not asserted to be the scheduler's exact job start. A hard external kill
  can still prevent final upload; already fsynced logs remain on the runner.
- No per-test duration changes. Without an explicit job-budget file, the
  supervisor adds no command wall deadline. With one, it stops starting gates
  at the overall finalization boundary, records the refusal and returns a
  failure rather than silently skipping/passing a gate.
- Cleanup is Linux-specific. A subreaper observes/adopts descendants even when
  helpers start new sessions. Before every signal, PID/starttime ownership is
  checked and journaled; a pidfd binds delivery to that process identity.
  TERM then KILL each have bounded three-second windows. Incomplete cleanup
  or a pipe that never reaches EOF makes the supervisor fail.
- All output directories are unique per driver invocation and gate. An always
  artifact step preserves the full logs, supervisor journal/results, pytest
  journal/partial JUnit and original budget record on success or failure.

This is a durable source draft, not a qualified implementation. It has not
been executed locally or in hosted controls. No broad CI run, native CAD,
current-run cancellation or simulator change has been authorized by it.
Focused hosted fixtures and independent source review must precede deployment.

## Reference contracts

The plugin uses the documented observational
[pytest hooks](https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_logstart).
Process identity delivery uses Python's
[pidfd_open](https://docs.python.org/3/library/os.html#os.pidfd_open) and
[pidfd_send_signal](https://docs.python.org/3/library/signal.html#signal.pidfd_send_signal)
interfaces. These references do not substitute for the pending hosted fixtures.
