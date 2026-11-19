# Fresh extraction import repair — 2026-11-19

Run 44458679921 at b591a63fe563dab0b77fa5caa04ff3d5a8483b86 failed before calculations with `ModuleNotFoundError: cloud_core_only_critical_clean_extraction`. No timing result or output artifact was produced; this says nothing about physical candidate quality.

Restore the exact helper from previously successful extraction commit 720ad3910edaa210b56b946d6cd0e9ced9454a77. Add a real import admission before bootstrap (syntax compilation alone does not resolve dependencies). Keep all artifact identities, hashes, route guards, original constraints and instance/name checks unchanged. Re-run on the same clean routed ODB f381bd8d9e79ca38918d4bbda5c4014959a0e6966ac9a130d4ea9274d6a5192e.
