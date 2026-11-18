# Six-case pad diagnostic admission

The runner previously aborted at the first failed turnoff transient. This left constant-enabled and constant-disabled controls unobserved. Run all six independent cases, preserve each failure and log, then fail the aggregate if any case is missing or incomplete. Source hashes must remain unchanged even when individual cases fail. No native warning, truncated capture, model change or tolerance relaxation is accepted.

A cloud fault-injection test returns native exit code zero with a transient failure in the first case. It requires all remaining cases to execute and the aggregate to fail. This synthetic test verifies failure propagation only; actual model evidence comes exclusively from native runs.

The predecessor iteration matrix is run 44369604102, source 6a39f0b767bb30b7bd78eeb6d2030249bf377e06. Do not cancel or duplicate it. This revision is staged for the next needed native diagnosis after its results are read. Future evidence experiments should use immutable cloud-* tags to avoid launching duplicate complete RTL regressions on every diagnostic branch.
