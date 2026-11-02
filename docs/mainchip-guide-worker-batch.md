# Bounded guide-worker memory candidate

Actual guide audit41449886129 measured92 native DRT markers,96 source nets,2593 stored guides and325 intersections. Earlier unchanged route41415994457 exceeded11GiB RSS during iteration20 guide flow. Native stored-guide measurements do not prove identical internal worker mapping or memory causality.

Pinned OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 guideTilesFlow precreates all workers and retains completed results for each independent batch. This candidate creates at most two live workers, processes and commits each chunk, then destroys its state before allocating more. It preserves guide selection/merging, all bounding boxes, independent batch grouping, worker IDs, costs, ripup mode, guide-following and the original full64 iteration schedule. Exactly one box per guide worker is required, matching the original construction; unexpected groups fail explicitly. Worker completion accounting must match the original total.

Commit timing within an independent batch changes. Full routing equivalence is NOT assumed. The compiled C++ source-control harness injects the actual replacement body into an instrumented worker implementation and checks all-worker completion, destructor accounting and <=2 live workers across seven scenarios; two invalid box-group cases must throw. Three modified upstream sources must be rejected. The complete source reversal is exact outside the identified lifetime section. Existing7positive/45refusal/25lifecycle and original internal-observer controls remain.

The original observer patch, all pinned submodules, compiler image,12GiB cgroup,2CPUs, no swap, build configuration, source-before/after checks and failure publication remain. This build can only qualify compilation/interfaces. Actual mainchip load/observer/native scope tests, full64 routing, final DRC/antenna, PG/LVS and freshRC/finalSTA must follow before accepting any engine or chip result. No increase of memory budget, clock change, geometry waiver or timing relaxation is proposed.


## Failed first full build and message-ID correction

Actual full engine build41453866417/source5a82cbd4068411de19acc73605ebb64250b010fc failed in the upstream DRT message checker at87%, after2063.7 seconds. DRT9999 occurred in both the new FlexDR guard and existing TritonRoute.cpp. No OOM event occurred; cgroup peak3717890048bytes,12GiB limit. The lifetime fixture had passed but did not cover cross-file logger-ID uniqueness. It was insufficient as a complete compilation check.

Cloud-only diagnostic41460346322 authenticated the entire failed archive and preserved full build logs. Derived artifact13147914267 is77579bytes SHA56f4602691b66d161598bd4dd8962e8cb6392a755c6172813683edf9a2645c17. Original failure release431499827 stays intact.

The correction changes only the new guard ID9999 to10000, the next free ID reported by the real checker. Guide boxes, worker lifetime, costs, iteration schedule, originals and all acceptance gates remain unchanged. Accounting guard9998 remains unique.

Source controls now run the exact upstream find_messages.py on both actual derived C++files and the observer header, and require the old duplicate-ID version to fail. The full build host additionally checks the complete actual DRT source directory immediately after source derivation and snapshot, before creating the compiler container. The upstream build's existing message check remains enabled. This does not establish a successful full engine build, native routing qualification or timing closure.
