# Increase native setup work before another expensive full routing

The qualified39669577979 candidate and fresh-wire handoff39672217279 are retained.
Its native optimizer ended after the configured80 global setup iterations:
estimated setup WNS -5.641ns/TNS -25188.7ns,8006 failing endpoints; estimated hold
WNS -0.469ns/TNS -2.612ns after220 hold buffers. These placement estimates are
not comparable to original routed SPEF measurements as a closure claim.

OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 RepairSetup.cc lines467-487
applies max_iterations to the whole opto_iteration count, not independently to
each endpoint.80 stops the complete100-percent endpoint repair effort early.

A separate cloud candidate raises only that setup iteration budget to5000.
Thread count1, one move per pass, all endpoint coverage, native progress
termination, area budget, original clocks/derates/uncertainty, hold limits,
source/geometry/fixed-clock/equation guards and inversion control remain.
The proved80-iteration candidate and its ready routing input stay immutable.
This starts from the same exact completed routed source and reproduces all
six extracted baseline slacks before modification. No source process is active.

The next candidate must pass native geometry and logic proof, then fresh
global/detailed routing, RC and three-corner timing. No PHY or signoff completion
is asserted by any estimated timing result.

Source: https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc#L467
