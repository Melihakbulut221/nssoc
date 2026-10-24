# Mainchip route interruption and recovery boundary

Run 39436610858 ended cancelled at the configured 360-minute job limit. Its always-publication step succeeded. The exact source summary and 99,024,293-byte archive are hash-pinned in the evidence receipt.

Fresh global routing completed and its actual OpenDB and guides survive. Detailed routing made progress: completed iterations reported 173847, 98150 and 87219 violations. These are intermediate router counts, not signoff DRC or final setup/hold. The final detailed-route database was not written; the live detailed-router process was not checkpointed. The third completed iteration therefore cannot be claimed as a saved restart point.

A cloud-only inventory job reads the actual saved global database with the same pinned native runtime, verifies the 152762-instance census, and records executable wrappers, ELF libraries and environment paths. It does not restart long routing. Before another multi-hour run, establish portable process checkpoint/restore for the exact native OpenROAD runtime. Existing PLL checkpoint success does not by itself prove OpenROAD portability.

OpenROAD documents detailed-route iteration controls and single-step operation, but those alone do not establish cross-process continuation of internal optimization state: https://openroad.readthedocs.io/en/latest/main/src/drt/README.html . Preserve original DRC/antenna/connectivity/RC and timing gates. No iteration limit or diagnostic result may be treated as route completion.
