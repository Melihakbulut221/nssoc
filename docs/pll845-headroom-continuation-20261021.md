# Exact PLL continuation with measured hosted headroom

The extra hosted SDK cleanup passed in39599806731, increasing free space to
135125282816 bytes. This still does not prove that the entire uncompressed
5106-column1us trajectory plus checkpoint reserves fits. The next job restores
the exact original39502073954 process on the already qualified, preallocated
shared Btrfs storage with zstd:3. It uses the validated all-column reader;
none of the native model, solver, stimuli, observations, capture or original
acquisition gates changes.

The existing allocation policy keeps6GiB host allocation margin,4GiB backing
checkpoint reserve and12GiB native reserve. After the full hash-verified archive
is restored, the unchanged capture-ready gate checks real inside and outside
free space before native activation. Compression occupancy is measured. If
the gate passes, the exact process continues until the requested host segment,
completion or the existing reserve guard, then publishes all original bytes
and its real process checkpoint. A capacity limit remains possible; it is not
reported as electrical acceptance. No cold restart, thinning, truncation,
sparse hole punching or invented raw values is allowed.

The new workflow shares the legacy native concurrency group. The older
controller, publisher and reader/storage migration evidence remain frozen.
All computation and persistent evidence are cloud-only. Failed restore or
electrical results remain preserved.
