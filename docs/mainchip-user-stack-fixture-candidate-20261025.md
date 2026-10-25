# Executable harmless user-stack fixture candidate — 2026-10-25

This implements the first stage of the bounded user-stack proposal. It has no registered workflow and has not executed. The only executable entrypoint compiles and owns a small counter program; OpenROAD attachment and process restore are false. The original route, admission and observed-diagnostic sources remain unchanged.

The observer collects 20 sets of at most 16 frames per actual LWP. It checks the same process, executable, root, namespaces, command line and cgroup before attachment, while stopped and after detach. Native task start times and actual executable mappings accompany each frame. Target executable/library bytes are read through its proc root; automatic loading and debuginfod remain off. All write, call and breakpoint/tracepoint permissions are disabled.

Each attachment has a ten-second deadline, with owned debugger-group cleanup after errors or leader exit. All observed thread tracers must be zero after cleanup. A remaining tracer or tracing stop rejects. GDB's temporary all-stop intervention is explicitly reported as a scheduling perturbation. The fixture executable is the only target the current controller constructs; no external PID entrypoint or chip controller is activated.

The 24 fixture control groups include actual 20-sample acquisition, active counter progress, initialization canaries, no debuginfod requests, blocked register/memory/function-call attempts, an already traced target, error and timeout detach, a descendant surviving its debugger-wrapper leader and ignoring TERM, bounded-output rejection, and a stripped target with honest missing symbols. They also exercise identity, thread census, changed source, exact saved-capsule metadata and result-disposition corruption.

The source-only proposal's broader controls must not be relabelled as fully passed by this fixture. In particular:

- Actual container-ID/StartedAt/cpuset binding and the OpenROAD runtime remain unexecuted. The fixture checks process cgroup/namespace drift, not a restored container.
- Breakpoint, tracepoint and fast-tracepoint permissions are read back as disabled; this fixture does not start tracing or deliberately insert a native breakpoint.
- Target-root file binding uses the actual fixture root; a different container root and exact NSSOC library inventory still need the later admitted run.
- The strict latest-capsule module checks public metadata and can restore files using the existing authenticated reader, but the fixture never calls archive restoration. The complete 23-image/13-work-file/inner-report checks remain unexecuted.
- Original assertion-site proof and current-input checks will remain in a separately reviewed reversible controller adapter. This candidate does not wire the observer into that controller yet.
- Artifact upload success is an Actions result, not something the checker can prove in advance.

The latest-capsule module retains the actual original failure and makes no source-unchanged claim absent from the historical inner report. Its file-only restoration path has no Docker start/restore command. The small original summary, saved-IP receipt and source basis are copied byte-for-byte into a separate diagnostic-source-basis directory with immutable hashes.

The manual template is fixture-only and cannot dispatch a native chip job. Independent source review and actual hosted fixture outcome are required before original-controller integration. Repeated frames, missing symbols or active counter/CPU cannot establish routing progress, deadlock or root cause.
