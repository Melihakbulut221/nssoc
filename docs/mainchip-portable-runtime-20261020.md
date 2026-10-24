# Exact OpenROAD runtime for resumable cloud routing

The saved global-route database from run39436610858 was reopened successfully in run39491419606. The reported16KB openroad executable is a launcher, so its libc-only dependency list is insufficient to checkpoint the actual router safely.

The portable-runtime workflow captures the actual loaded OpenROAD ELF and its memory-mapped libraries after reading the152762-instance saved database. Inside the pinned AppImage namespace it copies the referenced Nix runtime closure into an isolated scratch image. Original CAD binaries are unchanged. The native executable must then read and serialize the same database in both the original runtime and a network-disabled container, with byte-identical output.

The exact container image, inventory, source routing Tcl, raw logs and immutable input hashes are published. This is a runtime prerequisite. It does not prove process checkpoint portability, detailed routing, DRC or setup/hold closure. The subsequent test must checkpoint and restore the actual OpenROAD process across hosted runners before another long detailed-route continuation.

All native execution, image construction and archives are cloud-only. No local source, CAD environment or result tree is created.
