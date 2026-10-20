# Native OpenROAD continuation across cloud jobs

Portable runtime39494338440 passed exact saved-database equivalence. The actual103633024-byte OpenROAD ELF is pinned, along with its full runtime image. This establishes a reproducible isolated execution environment.

The next workflow checks a real process with the152762-instance mainchip database loaded. It preserves an open journal, native database memory, an in-memory token and loop counter through a Docker/CRIU checkpoint. Same-job restore must produce the unchanged native database and every journal row. A dependent job with a different VM boot ID then restores the same process image, reproducing the same journal and database bytes. Five corruptions detect omissions, repetitions, ordering, memory token changes and entrypoint replay.

This staged proof does not yet exercise active detailed-router workers. A successful result permits that next checkpoint experiment using the preserved original routing Tcl. It does not close routing, DRC, antenna, RC or final setup/hold gates. All binaries, process images and tests remain in the cloud.
