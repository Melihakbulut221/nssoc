# Cloud process checkpoint feasibility

The full PLL transient currently exceeds a single hosted job budget. A waveform prefix cannot restore simulator state. This isolated experiment checks a possible process-state continuation route without changing the active physical PLL run or its acceptance criteria.

Docker/CRIU is experimental and primarily targets same-host restore ([Docker reference](https://docs.docker.com/reference/cli/docker/checkpoint/), [CRIU integration](https://criu.org/Docker)). The test records the actual kernel, CRIU/Docker versions and immutable image ID/digest, then checkpoints a process with64MiB of mutable heap, RNG and floating-point state and an open binary output file. It restores into a separate container and requires byte-exact output and heap checksum against the uninterrupted deterministic sequence, an unchanged file prefix and exactly one entrypoint invocation. Truncation, state corruption and cold restart must be rejected.

A pass does not prove native ngspice/VBIC/OSDI continuation or cross-host migration. Those require additional exact-runtime, file-tree and continuous-versus-restored native capture comparisons. Full1us acquisition and all original acceptance limits remain mandatory. The ephemeral fixture does not have repository tokens, uses no network and never touches other running jobs.
